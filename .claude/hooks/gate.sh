#!/usr/bin/env bash
# The commit hook and the push gate of CLAUDE.md (SPECIFICATION.md section 7.6; WP44).
#
# A PreToolUse hook on Bash. It does nothing unless the command is a `git commit` or a
# `git push`; it denies the tool call when a stage fails, handing the failing output back.
# `git commit --no-verify` (or `-n`) skips the commit gate, matching git's own convention.
#
#   gate.sh        hook mode, payload on stdin. On a `git commit`: uv lock --check, ruff
#                  check, ruff format --check, mypy, then every Tier 1 test without the
#                  `extended` marker (the GUI file serially, apart). On a `git push`: runs
#                  nothing and goes through only when the stamp names the pushed tree with
#                  `extended`, the pass of `gate.sh run`. Text that only names a push, in a
#                  commit message or a pull request body, is no push.
#   gate.sh run    the push gate: the same four checks, then `pytest --extended` over the
#                  whole suite, no coverage, with the Gmsh and APBS requirements set. One
#                  run at a time: a second waits for the first. It stamps the tree
#                  `extended` only on a pass, and only if the tree did not change meanwhile.
#                  What the skills start in the background before they push.
#
# Every run appends one line to <git dir>/nanopnp-gate.log: time, mode, selection, seconds,
# tree and result.
#
# What is gated is the working tree, not the index: a compound `git add -A && git commit`
# reaches this hook before the `add` has run. A tree state that already passed is not re-run:
# the stamp is the tree id of the working copy and the selection that passed, so any edit
# invalidates it, and a commit-hook pass never stands in for `run`. When every changed path is
# prose (.github/scripts/prose-only.sh, which CI uses too), only ruff runs.
#
# pytest runs as CI runs it: -n auto --dist loadfile, one BLAS thread per worker.
#
# The stages share one budget (NANOPNP_GATE_BUDGET_S, default 1500 s), kept below the hook
# timeout in settings.json (1800 s): an interrupted hook is not a refusal.
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
    # A push also follows a quote, a brace or a backtick (`bash -c 'git push'`) and may end at a
    # closing one (`(git push)`); what is only quoted is filtered out below.
    push_re="(^|[;&|(\`'\"{]|[[:space:]])git(${git_opt})*[[:space:]]+push(\$|[[:space:])'\"\`]${seg}*)"

    # Where a matched git command runs: sets `moved` (the last `cd` before it)
    # and `target_dir` (its `-C` or `--work-tree`), from the matched text $1,
    # the command's own arguments $2 and its verb $3.
    #
    # The tree a command acts on is the one `-C` or `--work-tree` names, not this
    # hook's cwd. Read from the global options alone: the matched text less the
    # command's own arguments, and less the verb itself, so a `-C` inside a
    # quoted message is never taken for one. A repeated option leaves the last
    # value, which is git's own reading for absolute paths.
    #
    # A `cd` earlier in the same command moves where it runs, as in
    # `cd <dir> && git commit`: the last one before it is followed, and a
    # relative `-C` then resolves against it, as git would.
    locate() {
        local matched=$1 own=$2 verb=$3 options prefix
        local option_re='(^|[[:space:]])(-C|--work-tree)(=|[[:space:]]+)([^[:space:]]+)'
        local cd_re='(^|[;&|(])[[:space:]]*cd[[:space:]]+([^[:space:];&|)]+)'
        target_dir=.
        options=${matched%"$own"}
        options=${options%"$verb"}
        while [[ $options =~ $option_re ]]; do
            target_dir=${BASH_REMATCH[4]}
            options=${options#*"${BASH_REMATCH[0]}"}
        done
        target_dir=${target_dir#[\"\']}
        target_dir=${target_dir%[\"\']}
        [[ $target_dir == "~" || $target_dir == "~/"* ]] && target_dir=$HOME${target_dir:1}
        prefix=${command%%"$matched"*}
        moved=""
        while [[ $prefix =~ $cd_re ]]; do
            moved=${BASH_REMATCH[2]}
            prefix=${prefix#*"${BASH_REMATCH[0]}"}
        done
        moved=${moved#[\"\']}
        moved=${moved%[\"\']}
        [[ $moved == "~" || $moved == "~/"* ]] && moved=$HOME${moved:1}
        return 0
    }

    deny() {
        jq -n --arg reason "$1" '{
            hookSpecificOutput: {
                hookEventName: "PreToolUse",
                permissionDecision: "deny",
                permissionDecisionReason: $reason
            }
        }'
        exit 0
    }

    # Whether a refspec's source $1 (destination $2) is a tag. A tag names a
    # commit CI gated on `main`, and the release's own run gates it again.
    is_tag() {
        [[ $2 == refs/heads/* ]] && return 1
        [[ $1 == refs/tags/* || $2 == refs/tags/* ]] && return 0
        git show-ref --verify -q "refs/heads/$1" && return 1
        git show-ref --verify -q "refs/tags/$1" && return 0
        # A release tag not yet created here fails the push itself (CONTRIBUTING.md).
        [[ $1 =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]]
    }

    # Judge one `git push` in the current directory, from its own arguments $1.
    # Prints nothing when the push needs no stamp (not this repository,
    # --no-verify, a dry run, tags or deletions alone), `gated` when every tree it
    # sends is stamped `extended`, and the refusal otherwise.
    push_verdict() {
        local args token tokens=() positional=() expect=false all=false tags=false deleting=false
        local root stamp_path refspec src dst rev tree what revs=()
        root=$(git rev-parse --show-toplevel 2>/dev/null) || return 0
        [[ -f $root/pyproject.toml && -d $root/src/nanopnp ]] || return 0
        # Quotes are dropped, not the quoted text: a push carries no message, and a
        # quoted refspec is still a refspec.
        args=$(printf '%s' "$1" | tr -d "\"'")
        set -f
        tokens=($args)
        set +f
        for token in ${tokens[@]+"${tokens[@]}"}; do
            if $expect; then
                expect=false
                continue
            fi
            case $token in
                --no-verify | -n | --dry-run) return 0 ;;
                --tags) tags=true ;;
                --all | --mirror | --branches) all=true ;;
                -d | --delete) deleting=true ;;
                -o | --push-option | --repo | --receive-pack | --exec) expect=true ;;
                -*) ;;
                *) positional+=("$token") ;;
            esac
        done
        if $all; then
            printf '%s' "The push was not made: --all, --mirror and --branches send every branch, and the
push gate passes one tree. Push the branch by name. --no-verify skips this."
            return 0
        fi
        # The first positional argument is the remote; the rest are refspecs.
        if ((${#positional[@]} <= 1)); then
            # `git push --tags` with no refspec sends the tags alone.
            $tags && return 0
            revs=(HEAD)
        else
            for refspec in "${positional[@]:1}"; do
                refspec=${refspec#+}
                src=${refspec%%:*}
                dst=""
                [[ $refspec == *:* ]] && dst=${refspec#*:}
                # A deletion sends no tree.
                if $deleting || [[ -z $src ]]; then continue; fi
                is_tag "$src" "$dst" && continue
                # A source git cannot resolve fails the push itself; HEAD is judged.
                if git rev-parse -q --verify "$src^{commit}" >/dev/null 2>&1; then
                    revs+=("$src")
                else
                    revs+=(HEAD)
                fi
            done
            ((${#revs[@]} == 0)) && return 0
        fi
        stamp_path="$(git rev-parse --absolute-git-dir)/nanopnp-gate.pass"
        for rev in "${revs[@]}"; do
            tree=$(git rev-parse -q --verify "$rev^{tree}" 2>/dev/null) || tree=""
            if [[ -z $tree || ! -f $stamp_path ]] ||
                ! awk -v t="$tree" '$1 == t && $2 == "extended" { f = 1 } END { exit !f }' "$stamp_path"; then
                what="HEAD's tree"
                [[ $rev != HEAD ]] && what="the tree of $rev"
                printf '%s' "The push was not made: no passing push gate for ${what}${tree:+ (${tree:0:12})}. Run
.claude/hooks/gate.sh run (in the background), then push. --no-verify skips this."
                return 0
            fi
        done
        printf '%s' gated
    }

    # The command without what is only quoted: every character inside quotes, and every
    # line of a heredoc body, becomes "_". A `git push` that a commit message, an `echo` or
    # a pull request body merely names is a mention, and the guard must not answer it with
    # "no passing push gate" (--no-verify on a commit does not reach it, and `gh` has none).
    # Text after `eval` or a shell's `-c` is code and is kept; `$'...'` takes a backslash
    # to escape the next character, as the shell does. It is only a filter: the
    # pushes judged below are read from the command itself, quoted arguments included.
    read -r -d '' mask_awk <<'AWK' || true
function blank(text) { gsub(/./, "_", text); return text }
{
    line = $0
    if (here != "") {
        probe = line
        if (strip) sub(/^\t+/, "", probe)
        if (probe == here) { here = ""; out[NR] = line } else out[NR] = blank(line)
        next
    }
    result = ""
    size = length(line)
    for (i = 1; i <= size; i++) {
        c = substr(line, i, 1)
        if (quote == "'") {
            if (ansi && c == "\\" && i < size) {
                result = result (keep ? c substr(line, i + 1, 1) : "__"); i++
            } else if (c == "'") { quote = ""; result = result c }
            else result = result (keep ? c : "_")
        } else if (quote == "\"") {
            if (c == "\\" && i < size) {
                result = result (keep ? c substr(line, i + 1, 1) : "__"); i++
            } else if (c == "\"") { quote = ""; result = result c }
            else result = result (keep ? c : "_")
        } else if (c == "\\" && i < size) {
            result = result c substr(line, i + 1, 1); i++
        } else if (c == "'" || c == "\"") {
            before = substr(line, 1, i - 1)
            keep = (before ~ /[ \t]-[A-Za-z]*c[ \t]+$/ || before ~ /(^|[ \t;&|(])eval[ \t]+$/)
            ansi = (c == "'" && before ~ /\$$/)
            quote = c; result = result c
        } else if (substr(line, i, 3) == "<<<") { result = result "<<<"; i += 2 }
        else if (substr(line, i, 2) == "<<") {
            tail = substr(line, i + 2)
            if (match(tail, /^-?[ \t]*\\?['"]?[A-Za-z_][A-Za-z0-9_]*/)) {
                word = substr(tail, RSTART, RLENGTH)
                strip = (substr(word, 1, 1) == "-")
                sub(/^-?[ \t]*\\?['"]?/, "", word)
                here = word
            }
            result = result "<<"; i += 1
        } else result = result c
    }
    out[NR] = result
}
END { for (n = 1; n <= NR; n++) printf "%s%s", out[n], (n < NR ? "\n" : "") }
AWK
    scan=$command
    if [[ $command == *push* ]] && command -v awk >/dev/null 2>&1; then
        scan=$(printf '%s' "$command" | awk "$mask_awk") || scan=$command
    fi

    # The push guard (WP43 D7, J3). It runs no `uv` and no test: it reads the
    # stamp `gate.sh run` writes on a pass. Each push in the command is judged
    # in the directory it runs in.
    rest=$command
    pushes=0
    [[ $scan =~ $push_re ]] || rest=""
    while [[ $rest =~ $push_re ]]; do
        matched=${BASH_REMATCH[0]}
        args=${BASH_REMATCH[${#BASH_REMATCH[@]} - 1]}
        rest=${rest#*"$matched"}
        locate "$matched" "$args" push
        verdict=$(
            if [[ -n $moved ]]; then cd "$moved" 2>/dev/null || exit 0; fi
            cd "$target_dir" 2>/dev/null || exit 0
            push_verdict "$args"
        )
        case $verdict in
            "") ;;
            gated) pushes=$((pushes + 1)) ;;
            *) deny "$verdict" ;;
        esac
    done
    # A commit in the same command changes the tree the push then sends, which
    # no stamp read now can name: the two go in separate commands.
    if ((pushes > 0)) && [[ $scan =~ $commit_re ]]; then
        deny "The push was not made: the command also commits, so the tree it would push is not
the one any gate passed. Commit, run .claude/hooks/gate.sh run (in the background), then
push in a separate command. --no-verify on the push skips this."
    fi

    [[ $command =~ $commit_re ]] || exit 0
    matched=${BASH_REMATCH[0]}

    # --no-verify / -n count only as options of that commit: quoted strings
    # are removed first, so `-m "document --no-verify"` is still gated.
    args=${BASH_REMATCH[${#BASH_REMATCH[@]} - 1]}
    locate "$matched" "$args" commit
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
    # -p keeps the mtime: git re-reads an entry as racy only when the file is no
    # older than the index, and under core.checkStat=minimal compares only whole
    # seconds and size, so a fresh mtime would hide a same-size edit.
    cp -p "$(git rev-parse --git-path index)" "$index" 2>/dev/null
    GIT_INDEX_FILE=$index git add -A >/dev/null 2>&1 &&
        GIT_INDEX_FILE=$index git write-tree 2>/dev/null
    rm -f "$index"
}

git_dir=$(git rev-parse --absolute-git-dir)
stamp_file="$git_dir/nanopnp-gate.pass"
log_file="$git_dir/nanopnp-gate.log"
started=$SECONDS

say() { [[ $mode != hook ]] && printf '%s\n' "$*"; return 0; }

# One run at a time, across every worktree: the lock is a directory, created atomically,
# holding the owner's PID; a lock whose PID is gone is stale and taken over.
lock="$(git rev-parse --path-format=absolute --git-common-dir)/nanopnp-gate.lock"
take_lock() {
    local holder announced=false
    until mkdir "$lock" 2>/dev/null; do
        holder=$(cat "$lock/pid" 2>/dev/null) || holder=""
        if [[ -n $holder ]] && kill -0 "$holder" 2>/dev/null; then
            if ! $announced; then
                say "gate: waiting for the gate run in progress (PID $holder)."
                announced=true
            fi
            sleep 5
        elif [[ -z $holder ]] && [[ -z $(find "$lock" -maxdepth 0 -mmin +1 2>/dev/null) ]]; then
            # Created this minute and its PID not yet written: its owner is starting.
            sleep 1
        else
            rm -rf "$lock"
        fi
    done
    printf '%s\n' "$$" >"$lock/pid"
    trap 'rm -rf "$lock"' EXIT
}
[[ $mode == run ]] && take_lock

state=$(state_hash) || state=""
selection=development
[[ $mode == run ]] && selection=extended

log() {
    printf '%s %s %s %s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$mode" "$selection" \
        "$((SECONDS - started))" "${state:--}" "$1" >>"$log_file" 2>/dev/null
    return 0
}

# The stamp holds one "<tree> <selection>" line per selection, so a commit-hook pass never
# overwrites the `extended` line the push guard reads.
stamped() {
    [[ -f $stamp_file ]] &&
        awk -v t="$1" -v s="$2" '$1 == t && $2 == s { f = 1 } END { exit !f }' "$stamp_file"
}
stamp() {
    {
        [[ -f $stamp_file ]] && awk -v s="$selection" '$2 != s' "$stamp_file"
        printf '%s %s\n' "$state" "$selection"
    } >"$stamp_file.$$"
    mv "$stamp_file.$$" "$stamp_file"
}

if [[ -n $state ]] && { stamped "$state" extended || { [[ $mode == hook ]] && stamped "$state" development; }; }; then
    say "gate: this tree state already passed; nothing to re-run."
    exit 0
fi

# The prose rule lives in one script that CI's `changes` job uses too. A commit is judged
# against HEAD, which was gated when it was committed. `run` judges the whole branch since it
# left main, as CI's pull_request range does: against HEAD alone the clean tree the skills run
# it on would read as prose and the `extended` tests would never run. With no merge base found
# the whole gate runs.
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
    # CI requires the apbs binary where the apbs-binary wheel exists (VAL-06; pyproject.toml's
    # `apbs` group: Linux x86_64 and macOS); so does `run`. Elsewhere VAL-06 skips.
    case "$(uname -s)/$(uname -m)" in
        Darwin/* | Linux/x86_64) export NANOPNP_REQUIRE_APBS=1 ;;
    esac
else
    lead="The commit was not made: the gate"
fi

# Gmsh's tests fail rather than skip where it cannot import: always in `run`, as in CI; in the
# hook only for a change to Gmsh's own code or tests. A test file is Gmsh's when it takes the
# fixture (tests/conftest.py's `import_gmsh` or `gmsh_module`), wherever it lives.
gmsh_paths='^(src/nanopnp/mesh/gmsh_backend\.py|src/nanopnp/mesh/meshers\.py|tests/tier2/test_mesh_backends\.py|tests/.*gmsh[^/]*)$'
# The paths are collected first: `grep -q` exits at its first match, and under
# pipefail the writer's SIGPIPE would turn a match into a failed pipeline.
changed_paths=$({ git diff --name-only HEAD; git ls-files --others --exclude-standard; } 2>/dev/null)
gmsh_required=false
if [[ $mode == run ]] || grep -Eq "$gmsh_paths" <<<"$changed_paths"; then
    gmsh_required=true
else
    while IFS= read -r path; do
        if [[ $path == tests/*.py && -f $path ]] && grep -qE 'import_gmsh|gmsh_module' "$path"; then
            gmsh_required=true
            break
        fi
    done <<<"$changed_paths"
fi
$gmsh_required && export NANOPNP_REQUIRE_GMSH=1
gmsh_remedy="Gmsh's wheel loads X and GL libraries at import (.knowledge/07-software-stack.md section 4).
On Debian or Ubuntu: apt-get install -y --no-install-recommends libglu1-mesa libxft2 libxinerama1 libxcursor1"

fail() {
    local reason=$1
    log "failed"
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

CLAUDE.md requires lint, format, types and tests to pass before committing. Fix this, then
commit again. To commit anyway, add --no-verify.

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
    # The GUI file runs serially and alone, as in CI: it waits on a real QtWebEngine page by
    # the wall clock, which busy xdist workers can starve (ci.yml, run 113).
    if [[ $mode == run ]]; then
        check "pytest (extended)" uv run pytest -q -rsfE -n auto --dist loadfile \
            --ignore=tests/tier1/test_gui_widgets.py --extended
    else
        check "pytest (tier 1)" uv run pytest -q -rsfE -n auto --dist loadfile \
            --ignore=tests/tier1/test_gui_widgets.py -m "tier1 and not slow"
    fi
    # Exit 5 ("no tests ran") is the module skipping itself where PySide6 cannot import, the
    # usual Linux case (no libEGL); CI's desktop runners, where it must run, treat 5 as failure.
    check "pytest (GUI)"    bash -c 'uv run pytest -q -rsfE tests/tier1/test_gui_widgets.py; s=$?; ((s == 5)) && s=0; exit $s'
fi

if [[ $mode == run && -n $state ]]; then
    # A pass vouches for the tree it started on; an edit made while it ran, as a session may
    # make while the gate runs in the background, is not vouched for.
    if [[ $(state_hash) != "$state" ]]; then
        log "changed"
        printf '%s\n' "The gate passed, but the working tree changed while it ran, so nothing was stamped." \
            "Run .claude/hooks/gate.sh run again on the tree you mean to push." >&2
        exit 1
    fi
fi
[[ -n $state ]] && stamp
log "passed"
elapsed=$((SECONDS - started))
if [[ $mode == run ]]; then
    summary="gate: passed, ${elapsed} s"
    $docs_only && summary+=", prose only"
    say "${summary}."
else
    jq -n --arg message "gate: passed, ${elapsed} s." '{systemMessage: $message}'
fi
exit 0
