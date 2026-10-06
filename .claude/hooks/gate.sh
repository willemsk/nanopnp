#!/usr/bin/env bash
# The push gate of CLAUDE.md, enforced before Claude Code makes a commit.
#
# CLAUDE.md says "Before committing, run the whole gate". This hook makes that
# structural rather than something to remember: a PreToolUse hook on Bash that
# does nothing unless the command is a `git commit`, and denies the tool call
# when any stage fails, handing the failing output back so it can be fixed
# first. `git commit --no-verify` (or `-n`) skips it, matching git's own
# convention.
#
# Two ways in:
#   gate.sh          hook mode: reads the PreToolUse payload on stdin, and runs
#                    pytest's development selection, without the `extended`
#                    end-to-end walks
#   gate.sh run      runs the gate directly, prints each stage, exits non-zero
#                    on failure; adds `--extended`, so it is the whole of what CI
#                    gates on every push, and the branch coverage of the lines the
#                    branch changes (diff-cover, as CI's lint job). What the skills
#                    call before they push
#
# Every pytest call passes -rs, as CI does, so each skip is listed with its
# reason: a skip is missing evidence. `run` sets NANOPNP_REQUIRE_GMSH=1, as CI
# does, so a Gmsh that cannot import fails the push gate instead of skipping its
# tests; the hook sets it only when the change touches the Gmsh backend or its
# tests, so a session without Gmsh's system libraries can still commit elsewhere.
#
# It is wired up in .claude/settings.json. The matcher is the bare Bash tool
# rather than an `if: Bash(git commit*)` filter, because that filter is a
# prefix match and would miss the compound form `git add -A && git commit ...`.
#
# What is gated is the working tree, not the index: a compound
# `git add -A && git commit` reaches this hook before the `add` has run.
#
# pytest runs as CI runs it: -n auto --dist loadfile, one BLAS thread per
# worker. Serial, the BLAS threads buy no wall time on this suite; under xdist
# they oversubscribe the cores (6m10s serial, 7m20s unpinned, 3m19s pinned on
# 4 cores; .knowledge/07-software-stack.md).
#
# Two things keep it from costing even that on every commit:
# - a tree state that already passed is not re-run; the stamp is the tree id of
#   the working copy and the selection that passed, so any edit invalidates it,
#   and a development pass does not stand in for `run`;
# - when every changed path is prose, the lock check, mypy and pytest are
#   skipped: changed since HEAD for a commit, since the branch left main for
#   `run`. Prose is Markdown nothing reads; .github/scripts/prose-only.sh
#   holds the rule (not docs/ as a whole: tests read its YAML) and CI uses the
#   same script. Anything else is code, data/corrections/*.yaml and this hook
#   included.
#
# The stages share one budget (NANOPNP_GATE_BUDGET_S, default 1500 s), kept
# below the hook timeout in settings.json (1800 s). A gate that overruns its
# budget denies the commit; it must never be the harness's timeout that ends
# it, because an interrupted hook is not a refusal.
set -uo pipefail

mode=hook
[[ ${1:-} == run ]] && mode=run
target_dir=.

if [[ $mode == hook ]]; then
    payload=$(cat)
    command=$(printf '%s' "$payload" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0

    # The directory the command runs in is the payload's `cwd`, not this hook's:
    # the hook is started from the project directory, which in a worktree
    # session is the main checkout. Gating that tree, already stamped as passed,
    # let every worktree commit through ungated (WP32, 06fd43b).
    session_dir=$(printf '%s' "$payload" | jq -r '.cwd // ""' 2>/dev/null) || session_dir=""
    if [[ -n $session_dir && -d $session_dir ]]; then
        cd "$session_dir" || exit 0
    fi

    # A `git commit` as a command word, not `git commit-graph` and not a bare
    # mention. Anything else leaves the tool call untouched.
    # The regex lives in a variable: bash parses an unquoted =~ operand as shell
    # syntax first, and a bare "(" inside it is a syntax error, not a pattern.
    #
    # Global options sit between `git` and `commit`, and the ones below take
    # their value as a *separate* token: matching only `-[^space]+` stops at
    # that value and lets `git -C /repo commit` through the gate silently. Each
    # of these therefore consumes the token after it; every other option
    # consumes nothing.
    #
    # The last group captures the commit's own arguments, up to the next
    # command separator or line break, so that a heredoc body is not part of it.
    git_opt='[[:space:]]+(-[Cc]|--git-dir|--work-tree|--namespace|--exec-path|--config-env)[[:space:]]+[^[:space:]]+|[[:space:]]+-[^[:space:]]+'
    seg="[^;&|"$'\n'"]"
    commit_re="(^|[;&|(]|[[:space:]])git(${git_opt})*[[:space:]]+commit(\$|[[:space:]]${seg}*)"
    [[ $command =~ $commit_re ]] || exit 0
    matched=${BASH_REMATCH[0]}

    # --no-verify / -n count only as options of that commit: quoted strings
    # are removed first, so `-m "document --no-verify"` is still gated.
    args=${BASH_REMATCH[${#BASH_REMATCH[@]} - 1]}

    # The tree being committed is the one `-C` or `--work-tree` names, not this
    # hook's cwd, so that is the tree gated. Read from the global options alone:
    # the matched text less the commit's own arguments, and less the `commit`
    # itself, so a `-C` inside a quoted message is never taken for one. A
    # repeated option leaves the last value, which is git's own reading for
    # absolute paths.
    options=${matched%"$args"}
    options=${options%commit}
    option_re='(^|[[:space:]])(-C|--work-tree)(=|[[:space:]]+)([^[:space:]]+)'
    while [[ $options =~ $option_re ]]; do
        target_dir=${BASH_REMATCH[4]}
        options=${options#*"${BASH_REMATCH[0]}"}
    done
    target_dir=${target_dir#[\"\']}
    target_dir=${target_dir%[\"\']}
    [[ $target_dir == "~" || $target_dir == "~/"* ]] && target_dir=$HOME${target_dir:1}

    # A `cd` earlier in the same command moves where the commit runs, as in
    # `cd <dir> && git commit`: the last one before the commit is followed, and
    # a relative `-C` above then resolves against it, as git would.
    prefix=${command%%"$matched"*}
    cd_re='(^|[;&|(])[[:space:]]*cd[[:space:]]+([^[:space:];&|)]+)'
    moved=""
    while [[ $prefix =~ $cd_re ]]; do
        moved=${BASH_REMATCH[2]}
        prefix=${prefix#*"${BASH_REMATCH[0]}"}
    done
    moved=${moved#[\"\']}
    moved=${moved%[\"\']}
    [[ $moved == "~" || $moved == "~/"* ]] && moved=$HOME${moved:1}
    if [[ -n $moved ]]; then
        cd "$moved" 2>/dev/null || exit 0
    fi

    args=$(printf '%s' "$args" | sed -E "s/\"[^\"]*\"//g; s/'[^']*'//g")
    set -f
    for token in $args; do
        [[ $token == --no-verify || $token == -n ]] && exit 0
    done
    set +f
fi

root=$(git -C "$target_dir" rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0
[[ -f pyproject.toml && -d src/nanopnp ]] || exit 0

# Match CI: a uv.lock that pyproject.toml has moved away from is a failure,
# not something `uv run` should quietly rewrite.
export UV_LOCKED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
# As CI: cap NumPy's SIMD dispatch at X86_V3, the VER-62 reference environment,
# so an AVX-512 machine deploys the mesh CI does (.knowledge/06 section 8.1.5).
export NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"

# The tree the working copy would commit as with `git add -A`, built in a
# throwaway index: content-addressed, independent of HEAD and of how the
# changes are later split into commits, so a gated tree carved into several
# commits pays for the gate once.
state_hash() {
    local index
    index=$(mktemp) || return 1
    cp "$(git rev-parse --git-path index)" "$index" 2>/dev/null
    GIT_INDEX_FILE=$index git add -A >/dev/null 2>&1 &&
        GIT_INDEX_FILE=$index git write-tree 2>/dev/null
    rm -f "$index"
}

stamp_file="$(git rev-parse --git-dir)/nanopnp-gate.pass"
state=$(state_hash) || state=""

say() { [[ $mode == run ]] && printf '%s\n' "$*"; return 0; }

# Hook mode runs the development selection; `run` adds the `extended` tests, as
# CI does on every push (SPECIFICATION.md section 7.6 NOTE). A full pass also
# covers a later commit of the same tree, but a development pass never stands in
# for `run`, which is what the skills call before they push.
selection=development
pytest_extra=()
coverage_xml=""
if [[ $mode == run ]]; then
    selection=extended
    coverage_xml="$(git rev-parse --absolute-git-dir)/nanopnp-gate-coverage.xml"
    pytest_extra=(--extended --cov=src/nanopnp --cov-branch "--cov-report=xml:${coverage_xml}")
fi
passed=$(cat "$stamp_file" 2>/dev/null) || passed=""
if [[ -n $state && ( $passed == "$state extended" || $passed == "$state $selection" ) ]]; then
    say "gate: this tree state already passed ($selection selection); nothing to re-run."
    exit 0
fi

# The prose rule lives in one script that CI's `changes` job uses too. A commit
# is judged against HEAD, which was gated when it was committed. `run` judges the
# whole branch since it left main, as CI's pull_request range (base...head) does,
# the run a PR is merged on. Against HEAD alone, the clean tree the skills run it
# on reads as prose, and the `extended` tests would never run; against the
# upstream, so does an already-pushed branch, which is where /wp-ship and the
# steward run it from a fresh container (PR 74 review). A stale or shallow
# origin/main only widens the range. No base found is code.
base=HEAD
if [[ $mode == run ]]; then
    base=$(git merge-base HEAD origin/main 2>/dev/null) ||
        base=$(git merge-base HEAD main 2>/dev/null) || base=""
fi
docs_only=false
if [[ -n $base ]]; then
    { git diff --name-only "$base"; git ls-files --others --exclude-standard; } 2>/dev/null |
        .github/scripts/prose-only.sh && docs_only=true
fi

if [[ $mode == run ]]; then
    lead="The gate"
else
    lead="The commit was not made: the gate"
fi

# The Gmsh backend's tests fail rather than skip where it cannot import
# (tests/conftest.py), always in `run` and in the hook when the change is
# Gmsh's own; elsewhere a commit is not refused for a library it does not touch.
gmsh_paths='^(src/nanopnp/mesh/gmsh_backend\.py|src/nanopnp/mesh/meshers\.py|tests/tier2/test_mesh_backends\.py|tests/.*gmsh[^/]*)$'
if [[ $mode == run ]] ||
    { git diff --name-only HEAD; git ls-files --others --exclude-standard; } 2>/dev/null |
    grep -Eq "$gmsh_paths"; then
    export NANOPNP_REQUIRE_GMSH=1
fi
gmsh_remedy="Gmsh's wheel loads X and GL libraries at import (.knowledge/07-software-stack.md section 5).
On Debian or Ubuntu: apt-get install -y --no-install-recommends libglu1-mesa libxft2 libxinerama1 libxcursor1"

fail() {
    local reason=$1
    if [[ $mode == run ]]; then
        printf '%s\n' "$reason" >&2
        exit 1
    fi
    jq -n --arg reason "$reason" '{
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: $reason
        }
    }'
    exit 0
}

budget=${NANOPNP_GATE_BUDGET_S:-1500}
deadline=$((SECONDS + budget))
have_timeout=false
command -v timeout >/dev/null 2>&1 && have_timeout=true

check() {
    local name=$1
    shift
    local remaining=$((deadline - SECONDS))
    local output status
    say "gate: ${name}"
    if ((remaining <= 0)); then
        status=124
        output="(no budget left)"
    elif $have_timeout; then
        output=$(timeout "$remaining" "$@" 2>&1)
        status=$?
    else
        output=$("$@" 2>&1)
        status=$?
    fi
    ((status == 0)) && return 0

    if ((status == 124)); then
        fail "${lead} ran out of its ${budget} s budget at \`${name}\`.

A gate that cannot finish is not a pass. Find what made \`$*\` slow (pytest
--durations=10), or raise NANOPNP_GATE_BUDGET_S together with the hook timeout
in .claude/settings.json. To commit anyway, add --no-verify.

Last 40 lines:

$(printf '%s' "$output" | tail -40)"
    fi
    local remedy=""
    if [[ $output == *"NANOPNP_REQUIRE_GMSH=1 and gmsh does not import"* ]]; then
        remedy="

${gmsh_remedy}"
    fi
    fail "${lead} failed at \`${name}\`.

CLAUDE.md requires the whole gate — ruff check, ruff format --check, mypy src/,
pytest — to pass before committing. Fix this, then commit again. To commit
anyway, add --no-verify.

Last 40 lines of \`$*\`:

$(printf '%s' "$output" | tail -40)${remedy}"
}

# The lock first: under UV_LOCKED a stale lock would otherwise surface as a
# confusing failure of whichever `uv run` stage came first.
$docs_only || check "uv lock --check" uv lock --check
check "ruff check"          uv run ruff check .
check "ruff format --check" uv run ruff format --check .
if $docs_only; then
    say "gate: only prose changed; lock check, mypy and pytest skipped."
else
    check "mypy --strict"   uv run mypy src/
    # The `+` form: bash before 4.4 (macOS's /bin/bash is 3.2) treats an empty
    # array as unset under `set -u`, and would end the hook ungated.
    check "pytest ($selection)" uv run pytest -q -rs -n auto --dist loadfile \
        --ignore=tests/tier1/test_gui_widgets.py ${pytest_extra[@]+"${pytest_extra[@]}"}
    # Serially and alone, as in CI: it waits on a real QtWebEngine page by the
    # wall clock, which busy xdist workers can starve (ci.yml, run 113). Exit 5
    # ("no tests ran") is the module skipping itself where PySide6 cannot
    # import, the usual Linux case (no libEGL); CI's desktop runners, where it
    # must run, treat 5 as the failure it is there.
    check "pytest (GUI)"    bash -c 'uv run pytest -q -rs tests/tier1/test_gui_widgets.py; s=$?; ((s == 5)) && s=0; exit $s'
    # Every changed line of src/nanopnp, gui/ aside (its widgets run only on the
    # desktop legs), is executed on both sides of each of its branches, against
    # the same base the prose rule judged. It finds a branch no test takes; it
    # cannot find code that is missing, which is what a plan's planned tests are
    # for (.claude/skills/wp-plan). A line no test can reach says why in its
    # `# pragma: no cover - <reason>` (VER-72).
    if [[ -n $coverage_xml ]]; then
        if [[ -n $base ]]; then
            check "diff-cover"  uv run diff-cover "$coverage_xml" --compare-branch="$base" \
                --branch-coverage --include-untracked --fail-under=100 --show-uncovered \
                --include 'src/nanopnp/**/*.py' --exclude '*/src/nanopnp/gui/*'
        else
            check "diff-cover"  bash -c 'echo "no merge base with main to compare against" >&2; exit 1'
        fi
    fi
fi

# A hook's prose-only pass is stamped `development`, never `extended`: it was
# judged against HEAD, and code committed since the upstream is still `run`'s.
[[ -n $state ]] && printf '%s\n' "$state $selection" >"$stamp_file"
say "gate: passed."
exit 0
