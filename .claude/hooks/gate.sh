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
# Three ways in:
#   gate.sh          hook mode: reads the PreToolUse payload on stdin, and runs
#                    the tests a test-impact selection finds the change to touch
#                    (tests/impact.py, VER-74), without the `extended` end-to-end
#                    walks; with no usable map, or a change the map cannot
#                    attribute, the whole development selection, naming why
#                    It is also the push guard: a `git push` goes through only
#                    when the stamp names the pushed tree with `extended`, the
#                    pass of `gate.sh run`; it runs nothing (WP43 D7, J3). Text that only
#                    names a push, in a commit message or a pull request body, is no push
#   gate.sh run      runs the gate directly and exits non-zero on failure,
#                    printing only the failure, or one line on a pass; adds
#                    `--extended`, so it is the whole of what CI gates, a pull
#                    request and a merge together, with diff-cover on the changed
#                    lines, and records the
#                    impact map as it goes. What the skills start in the
#                    background before they push. One run at a time: a second
#                    waits for the first (a PID file under the map's directory).
#                    After a pass on tree P, a run on tree T is a follow-up: it
#                    runs only the tests the change from P selects, under
#                    coverage, and diff-cover against P (Design section 2)
#   gate.sh map      records the impact map the hook selects from, at
#                    <git common dir>/nanopnp-impact/map.json, by running the
#                    development selection under the recorder; stamps nothing.
#                    The skills start it in the background as their first step
#
# Every run appends one line to <git dir>/nanopnp-gate.log: time, mode,
# selection, test count, seconds, tree and result (WP43 D11).
#
# pytest passes -rsfE: skips listed, as CI's -rs lists them (a skip is missing
# evidence), and failures kept. A bare -rs replaces pytest's default -rfE, so the
# FAILED lines would leave the summary and the 40-line tail below would show
# only skips.
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
case ${1:-} in
    run | map) mode=$1 ;;
esac
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
# The map is shared by every worktree: a tree recorded in one is a valid base in all.
map_dir="$(git rev-parse --path-format=absolute --git-common-dir)/nanopnp-impact"
map="$map_dir/map.json"
started=$SECONDS

say() { [[ $mode != hook ]] && printf '%s\n' "$*"; return 0; }

# One figure of .github/budgets.yaml, a `key: number` line; nothing where the file or key is absent.
budget_of() { sed -n "s/^$1:[[:space:]]*\([0-9.]*\).*/\1/p" .github/budgets.yaml 2>/dev/null | head -n 1; }

# One recording or push-gate run at a time, across every worktree: both write
# "$map.new" and either takes the machine's cores. The lock is a directory,
# created atomically, holding the owner's PID; a lock whose PID is gone is
# stale and taken over. `run` waits for the holder, then re-reads the stamp,
# so a second run of a tree the first passed does nothing; `map` leaves.
lock="$map_dir/gate.lock"
own_lock=false
take_lock() {
    local wait=$1 holder announced=false
    mkdir -p "$map_dir" || return 1
    until mkdir "$lock" 2>/dev/null; do
        holder=$(cat "$lock/pid" 2>/dev/null) || holder=""
        if [[ -n $holder ]] && kill -0 "$holder" 2>/dev/null; then
            $wait || { say "gate: a gate run or map recording is in progress (PID $holder)."; return 1; }
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
    own_lock=true
}
release() {
    $own_lock && rm -rf "$lock"
    rm -f "$map.new" "$map.follow"
}
if [[ $mode == run ]]; then
    take_lock true || exit 1
    trap release EXIT
fi

state=$(state_hash) || state=""

# One line per run: ISO time, mode, selection, test count, seconds, tree, result.
log_mode=$mode
log_selection=""
log_count=-
log() {
    printf '%s %s %s %s %s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$log_mode" \
        "${log_selection:--}" "$log_count" "$((SECONDS - started))" "${state:--}" "$1" \
        >>"$log_file" 2>/dev/null
    return 0
}

# The stamp holds one line per selection, "<tree> <selection>[ <commit>]", so a
# later commit-hook pass never overwrites the `extended` line the push guard
# reads; that line is kept last. The `extended` line carries a commit object of
# its tree whose parent is the merge base it was judged against, which a
# follow-up's diff-cover compares with (Design section 7).
stamped() {
    [[ -f $stamp_file ]] &&
        awk -v t="$1" -v s="$2" '$1 == t && $2 == s { f = 1 } END { exit !f }' "$stamp_file"
}
stamp() {
    local selection=$1 new="$state $1${2:+ $2}" kept=() line tree kind
    if [[ -f $stamp_file ]]; then
        while IFS= read -r line || [[ -n $line ]]; do
            read -r tree kind _ <<<"$line"
            [[ -n $line && ${kind:-} != "$selection" ]] && kept+=("$line")
        done <"$stamp_file"
    fi
    {
        for line in ${kept[@]+"${kept[@]}"} "$new"; do
            read -r tree kind _ <<<"$line"
            if [[ $kind != extended ]]; then printf '%s\n' "$line"; fi
        done
        for line in ${kept[@]+"${kept[@]}"} "$new"; do
            read -r tree kind _ <<<"$line"
            if [[ $kind == extended ]]; then printf '%s\n' "$line"; fi
        done
    } >"$stamp_file.$$"
    mv "$stamp_file.$$" "$stamp_file"
}

# The recorder needs sys.monitoring, Python 3.12 or later (WP43 D2).
recorder_python() {
    uv run python -c 'import sys; sys.exit(sys.version_info < (3, 12))' >/dev/null 2>&1
}

if [[ $mode == map ]]; then
    # A map whose tree this repository holds is usable: the selector reads every
    # change since that tree, so it never needs re-recording to stay sound.
    if [[ -f $map ]]; then
        recorded=$(jq -r '.tree // empty' "$map" 2>/dev/null) || recorded=""
        if [[ -n $recorded ]] && git cat-file -e "$recorded^{tree}" 2>/dev/null; then
            say "gate: an impact map of tree ${recorded:0:12} is in place; nothing to record."
            exit 0
        fi
    fi
    if ! recorder_python; then
        printf '%s\n' "gate map: the recorder needs Python 3.12 or later (sys.monitoring)." >&2
        exit 1
    fi
    # A run in progress records the map itself.
    take_lock false || exit 0
    trap release EXIT
    log_selection=development
    say "gate: recording the impact map (development selection)."
    PYTHONPATH="tests${PYTHONPATH:+:$PYTHONPATH}" uv run pytest -q -n auto --dist loadfile \
        --ignore=tests/tier1/test_gui_widgets.py -p impact "--impact-record=$map.new" \
        >"$map_dir/record.log" 2>&1
    status=$?
    # Only a green session leaves a map worth keeping: a failing test records what it
    # executed up to its failure, so a change to code it would reach after that point
    # would never select it. Without a map the hook runs the development selection.
    if ((status == 0)) && [[ -f $map.new ]]; then
        log_count=$(jq '.tests | length' "$map.new" 2>/dev/null) || log_count=-
        mv "$map.new" "$map"
        log "recorded"
        say "gate: impact map recorded ($log_count tests); pytest exited $status."
        exit 0
    fi
    log "failed"
    printf '%s\n' "gate map: pytest exited $status; no map recorded. See $map_dir/record.log." >&2
    exit 1
fi

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
    # CI requires the apbs binary where the apbs-binary wheel exists (VAL-06;
    # pyproject.toml's `apbs` group: Linux x86_64 and macOS); so does `run`.
    # Elsewhere (Windows, Linux aarch64) uv installs no binary and VAL-06 skips.
    case "$(uname -s)/$(uname -m)" in
        Darwin/* | Linux/x86_64) export NANOPNP_REQUIRE_APBS=1 ;;
    esac
    pytest_extra=(--extended --cov=src/nanopnp --cov-branch "--cov-report=xml:${coverage_xml}")
fi
already=false
if [[ -n $state ]]; then
    if stamped "$state" extended; then
        already=true
    elif [[ $mode == hook ]] && { stamped "$state" impact || stamped "$state" development; }; then
        already=true
    fi
fi
if $already; then
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
# origin/main only widens the range. `run` with no base found refuses below.
base=HEAD
if [[ $mode == run ]]; then
    base=$(git merge-base HEAD origin/main 2>/dev/null) ||
        base=$(git merge-base HEAD main 2>/dev/null) || base=""
    if [[ -z $base ]]; then
        # Before the long selection, not after it: the diff-cover stage needs a base.
        printf '%s\n' "The gate needs a merge base with main for its diff-cover stage, and none was found." \
            "Fetch it: git fetch origin main:refs/remotes/origin/main (add --unshallow if the clone is shallow)." >&2
        exit 1
    fi
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

# Gmsh's tests fail rather than skip where it cannot import: always in `run`,
# as in CI; in the hook only for a change to Gmsh's own code or tests. A test
# file is Gmsh's when it takes the fixture (tests/conftest.py's `import_gmsh` or
# `gmsh_module`), wherever it lives, conftest.py itself included.
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

# The commit hook's selection (WP43 D5): the tests tests/impact.py finds the
# change to touch since the map's tree, or, on any fallback, the development
# selection, with the reason kept for the message. A change to Gmsh's own code
# or tests runs the development selection, so Gmsh is required as before.
impact_files=()
fallback_reason=""
choose_impact_selection() {
    local out status line files=()
    if $gmsh_required; then
        fallback_reason="a change to Gmsh's code or tests"
    elif [[ ! -f tests/impact.py ]]; then
        fallback_reason="tests/impact.py is absent"
    elif [[ ! -f $map ]]; then
        fallback_reason="no impact map at $map (record one with .claude/hooks/gate.sh map)"
    else
        # Stdout alone carries node ids or the FALLBACK line; uv's own warnings go
        # to stderr and must never be read as a path.
        local errors last_error=""
        errors=$(mktemp) || errors=/dev/null
        out=$(uv run python tests/impact.py select --map "$map" 2>"$errors")
        status=$?
        if [[ $errors != /dev/null ]]; then
            last_error=$(tail -1 "$errors")
            rm -f "$errors"
        fi
        if ((status == 0)); then
            selection=impact
            log_count=0
            while IFS= read -r line; do
                [[ -z $line ]] && continue
                log_count=$((log_count + 1))
                line=${line%%::*}
                # The GUI file runs serially below, never under xdist (ci.yml, run 113).
                [[ $line == tests/tier1/test_gui_widgets.py ]] && continue
                [[ " ${files[*]-} " == *" $line "* ]] || files+=("$line")
            done <<<"$out"
            impact_files=(${files[@]+"${files[@]}"})
            return 0
        elif ((status == 3)); then
            fallback_reason=${out#FALLBACK: }
        else
            fallback_reason="the selector failed: ${last_error:-exit $status}"
        fi
    fi
    selection=development
    return 0
}

# pytest exits 5 when the marker expression deselects every test of the files named: a new
# Tier 3 or Tier 4 file, or one of `slow` or `extended` tests alone, which the selector lists
# by path because it has no node ids yet. That selection holds nothing to run, which is no
# failure; every other nonzero status stays one. Run as `bash -c "$exit_5_is_a_pass" _ <command>`.
exit_5_is_a_pass='"$@"; s=$?; ((s == 5)) && s=0; exit $s'

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

CLAUDE.md requires the whole gate — ruff check, ruff format --check, mypy src/,
pytest — to pass before committing. Fix this, then commit again. To commit
anyway, add --no-verify.

Last 40 lines of \`$*\`:

$(printf '%s' "$output" | tail -40)${remedy}"
}

# The follow-up (WP43 D7, J3; Design section 2). After a pass on tree P, stamped
# "<P> extended <commit P>", a run on tree T runs only the tests the change from
# P to T selects, `extended` walks included, under coverage, and diff-cover over
# the lines changed since P alone. Sound because a test the change does not
# select executes at T exactly what it executed at P (Design section 1), so it
# executes no line changed since P, and every selected test runs under coverage:
# for those lines the subset's coverage is the full run's. A line changed between
# main and P keeps P's verdict. Anything this cannot vouch for runs the whole
# gate: no `extended` stamp of another tree, its commit gone, another merge base
# (main moved, so P's verdict on the earlier lines no longer applies), a map of
# another tree, or any fallback of the selector.
followup=false
followup_from=""
followup_files=()
full_reason=""
choose_followup() {
    local line passed kind commit out status errors node changed files=() count=0
    if [[ ! -f $stamp_file || ! -f tests/impact.py ]]; then
        return 0
    fi
    line=$(awk '$2 == "extended" { l = $0 } END { print l }' "$stamp_file")
    read -r passed kind commit _ <<<"$line"
    if [[ -z ${passed:-} || -z ${commit:-} ]]; then
        return 0
    fi
    if ! git cat-file -e "$commit^{commit}" 2>/dev/null ||
        [[ $(git rev-parse "$commit^{tree}" 2>/dev/null) != "$passed" ]]; then
        full_reason="the last pass's commit object is gone"
        return 0
    fi
    if [[ $(git rev-parse -q --verify "$commit^1" 2>/dev/null) != "$base" ]]; then
        full_reason="the merge base with main moved since the last pass"
        return 0
    fi
    if [[ ! -f $map || $(jq -r '.tree // empty' "$map" 2>/dev/null) != "$passed" ]]; then
        full_reason="the impact map is not of the passed tree ${passed:0:12}"
        return 0
    fi
    if ! recorder_python; then
        full_reason="the recorder needs Python 3.12 or later"
        return 0
    fi
    # Stdout alone carries node ids or the FALLBACK line, as in the hook.
    errors=$(mktemp) || errors=/dev/null
    out=$(uv run python tests/impact.py select --map "$map" --extended 2>"$errors")
    status=$?
    if ((status != 0)); then
        if ((status == 3)); then
            full_reason=${out#FALLBACK: }
        else
            full_reason="the selector failed: $(tail -1 "$errors" 2>/dev/null)"
        fi
        [[ $errors != /dev/null ]] && rm -f "$errors"
        return 0
    fi
    [[ $errors != /dev/null ]] && rm -f "$errors"
    while IFS= read -r node; do
        [[ -z $node ]] && continue
        count=$((count + 1))
        node=${node%%::*}
        # The GUI file runs serially below, as in every run.
        [[ $node == tests/tier1/test_gui_widgets.py ]] && continue
        [[ " ${files[*]-} " == *" $node "* ]] || files+=("$node")
    done <<<"$out"
    # No test selected yet a source line changed: no report to judge it by.
    # The paths are collected first: `grep -q` under pipefail, as above.
    changed=$(git diff --name-only "$passed" "$state" -- 'src/nanopnp/*.py' 2>/dev/null)
    if ((${#files[@]} == 0)) && [[ -n $changed ]] && grep -qv '^src/nanopnp/gui/' <<<"$changed"; then
        full_reason="the change selects no test but changes src/nanopnp"
        return 0
    fi
    followup=true
    followup_from=$commit
    followup_files=(${files[@]+"${files[@]}"})
    log_count=$count
    return 0
}

# The recorder rides along a full run, so a pass leaves the map of its tree
# (Design section 7); where it cannot record, the run goes on without it.
record=()
if [[ $mode == run && -f tests/impact.py ]] && recorder_python; then
    record=(-p impact)
fi
# `-p impact` imports the plugin from tests/, before any conftest is read.
tests_path="tests${PYTHONPATH:+:$PYTHONPATH}"

# The lock first: under UV_LOCKED a stale lock would otherwise surface as a
# confusing failure of whichever `uv run` stage came first.
$docs_only || check "uv lock --check" uv lock --check
check "ruff check"          uv run ruff check .
check "ruff format --check" uv run ruff format --check .
if $docs_only; then
    say "gate: only prose changed; lock check, mypy and pytest skipped."
else
    check "mypy --strict"   uv run mypy src/
    # A previous run's report must not stand in for this one's: were pytest to
    # write none (PYTEST_ADDOPTS=--no-cov), diff-cover would judge the old one.
    [[ -n $coverage_xml ]] && rm -f "$coverage_xml"
    # The `+` form: bash before 4.4 (macOS's /bin/bash is 3.2) treats an empty
    # array as unset under `set -u`, and would end the hook ungated.
    if [[ $mode == hook ]]; then
        choose_impact_selection
    elif [[ $mode == run ]]; then
        choose_followup
        $followup && log_mode=follow-up
    fi
    log_selection=$selection
    if [[ $selection == impact ]]; then
        if ((${#impact_files[@]} == 0)); then
            say "gate: the change touches no test."
        else
            # Whole files, as the selection is made; the marker expression keeps a
            # named file's `extended` walks out, as the development selection does.
            workers=(-n auto --dist loadfile)
            ((log_count < 20)) && workers=(-n 0)
            check "pytest (impact: ${log_count} tests in ${#impact_files[@]} files)" \
                bash -c "$exit_5_is_a_pass" _ uv run pytest -q -rsfE "${workers[@]}" \
                -m "(tier1 or tier2) and not slow and not extended" -- "${impact_files[@]}"
        fi
    elif $followup; then
        # Whole files with their walks, under coverage and the recorder; the
        # recorded part replaces those files' records in the map on a pass.
        if ((${#followup_files[@]} > 0)); then
            workers=(-n auto --dist loadfile)
            ((log_count < 20)) && workers=(-n 0)
            check "pytest (follow-up: ${log_count} tests in ${#followup_files[@]} files)" \
                bash -c "$exit_5_is_a_pass" _ \
                env "PYTHONPATH=$tests_path" uv run pytest -q -rsfE "${workers[@]}" "${pytest_extra[@]}" \
                ${record[@]+"${record[@]}"} ${record[@]+"--impact-record=$map.follow"} \
                -- "${followup_files[@]}"
        fi
    else
        check "pytest ($selection)" env "PYTHONPATH=$tests_path" uv run pytest -q -rsfE -n auto --dist loadfile \
            --ignore=tests/tier1/test_gui_widgets.py ${pytest_extra[@]+"${pytest_extra[@]}"} \
            ${record[@]+"${record[@]}"} ${record[@]+"--impact-record=$map.new"}
    fi
    # Serially and alone, as in CI: it waits on a real QtWebEngine page by the
    # wall clock, which busy xdist workers can starve (ci.yml, run 113). Exit 5
    # ("no tests ran") is the module skipping itself where PySide6 cannot
    # import, the usual Linux case (no libEGL); CI's desktop runners, where it
    # must run, treat 5 as the failure it is there.
    check "pytest (GUI)"    bash -c 'uv run pytest -q -rsfE tests/tier1/test_gui_widgets.py; s=$?; ((s == 5)) && s=0; exit $s'
    # Full branch coverage of changed src/nanopnp lines, gui/ aside (its widgets
    # run only on the desktop legs), against the base the prose rule used; `run`
    # has refused above when there is none. A follow-up compares with the passed
    # tree's commit, two-dot: the change from that tree, not from a merge base.
    if $followup; then
        if ((${#followup_files[@]} > 0)); then
            check "diff-cover (since ${followup_from:0:12})" uv run diff-cover "$coverage_xml" \
                --compare-branch="$followup_from" --diff-range-notation=.. \
                --branch-coverage --include-untracked --fail-under=100 --show-uncovered \
                --include 'src/nanopnp/**/*.py' --exclude '*/src/nanopnp/gui/*'
        fi
    elif [[ -n $coverage_xml ]]; then
        check "diff-cover"  uv run diff-cover "$coverage_xml" --compare-branch="$base" \
            --branch-coverage --include-untracked --fail-under=100 --show-uncovered \
            --include 'src/nanopnp/**/*.py' --exclude '*/src/nanopnp/gui/*'
    fi
fi

pass_commit=""
if [[ $mode == run && -n $state ]]; then
    # A pass vouches for the tree it started on; an edit made while it ran, as a
    # session may make while the gate runs in the background, is not vouched for.
    if [[ $(state_hash) != "$state" ]]; then
        log "changed"
        printf '%s\n' "The gate passed, but the working tree changed while it ran, so nothing was stamped." \
            "Run .claude/hooks/gate.sh run again on the tree you mean to push." >&2
        exit 1
    fi
    # The map moves with the stamp: replaced by a full run's recording, or, after
    # a follow-up, given the re-run files' records and the new tree. A map that
    # cannot move keeps its old tree, and the next run is a full one.
    if $followup; then
        if [[ -f $map.follow ]]; then
            uv run python tests/impact.py merge --map "$map" --part "$map.follow" --tree "$state" \
                >/dev/null 2>&1 || printf '%s\n' "gate: the impact map could not be merged; the next run is a full one." >&2
        elif ((${#followup_files[@]} == 0)); then
            # Nothing selected: every record holds at the new tree as at the old.
            jq --arg tree "$state" '.tree = $tree' "$map" >"$map.$$" 2>/dev/null &&
                mv "$map.$$" "$map" || rm -f "$map.$$"
        fi
    elif [[ -f $map.new ]]; then
        log_count=$(jq '.tests | length' "$map.new" 2>/dev/null) || log_count=-
        mv "$map.new" "$map"
    fi
    # The commit object the next follow-up's diff-cover compares with; its parent
    # is the merge base this pass was judged against.
    pass_commit=$(GIT_AUTHOR_NAME=nanopnp-gate GIT_AUTHOR_EMAIL=gate@nanopnp.invalid \
        GIT_COMMITTER_NAME=nanopnp-gate GIT_COMMITTER_EMAIL=gate@nanopnp.invalid \
        git commit-tree "$state" -p "$base" -m "nanopnp gate pass" 2>/dev/null) || pass_commit=""
fi

# A hook's prose-only pass is stamped `development`, never `extended`: it was
# judged against HEAD, and code committed since the upstream is still `run`'s.
[[ -n $state ]] && stamp "$selection" "$pass_commit"
log_selection=$selection
log "passed"
if [[ $mode == run ]]; then
    summary="gate: passed, $((SECONDS - started)) s"
    if $docs_only; then
        summary+=", prose only"
    elif $followup; then
        summary+=", follow-up from ${followup_from:0:12}: ${log_count} tests in ${#followup_files[@]} files"
    else
        summary+=", the whole gate"
        [[ $log_count != - ]] && summary+=", ${log_count} tests recorded"
        [[ -n $full_reason ]] && summary+=" (${full_reason})"
    fi
    say "${summary}."
fi
if [[ $mode == hook ]]; then
    # The commit goes ahead; the message says what ran, why the whole
    # development selection ran if it did, and an overrun of the hook's 60 s
    # budget past its 50 % margin (VER-73). It never fails on time.
    elapsed=$((SECONDS - started))
    notice="gate: passed, ${selection} selection"
    [[ $log_count != - ]] && notice+=", ${log_count} tests"
    notice+=", ${elapsed} s."
    [[ -n $fallback_reason ]] && notice+=" Fell back to the development selection: ${fallback_reason}."
    # The budget and margin are .github/budgets.yaml's (VER-73); 60 s and 50 % where it has none.
    hook_budget=$(budget_of commit_hook_s)
    hook_budget=${hook_budget:-60}
    hook_limit=$(awk -v b="$hook_budget" -v m="$(budget_of margin)" \
        'BEGIN { if (m == "") m = 0.5; printf "%d", b * (1 + m) }' 2>/dev/null)
    hook_limit=${hook_limit:-$((hook_budget * 3 / 2))}
    ((elapsed > hook_limit)) &&
        notice+=" Over budget: the commit hook's budget is ${hook_budget} s, ${hook_limit} s with its margin."
    jq -n --arg message "$notice" '{systemMessage: $message}'
fi
exit 0
