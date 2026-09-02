#!/bin/bash
# Bootstraps the uv-managed environment at the start of a Claude Code on the
# web session, so `uv run pytest`/`ruff`/`mypy` all work immediately without
# a manual `uv sync` first (see CLAUDE.md "Setup"), and prints where the work
# stands so a fresh session does not have to re-derive it.
#
# Everything on stdout becomes session context, so the sync — which is chatty —
# is redirected to stderr and only the summary is printed. The summary is
# best-effort: nothing in it may fail the hook or delay the session.
set -euo pipefail

root=${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}
cd "$root" || exit 0

# Only sync in Claude Code on the web / remote sessions — local devs manage
# their own venv per CLAUDE.md.
if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
    uv sync --all-extras --frozen >&2
fi

set +e

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
[ -n "$branch" ] || exit 0

# Only quote a position we can actually compute. origin/main is often not
# fetched (single-branch clones), and on a shallow clone the merge base sits
# below the graft point, so rev-list counts against a truncated history and
# returns a plausible wrong answer — Claude Code on the web clones shallow.
# Say nothing rather than something false.
position=""
if [ "$(git rev-parse --is-shallow-repository 2>/dev/null)" != "true" ] &&
    git rev-parse --verify --quiet origin/main >/dev/null 2>&1; then
    position=$(git rev-list --left-right --count origin/main...HEAD 2>/dev/null | awk '{
        s = ""
        if ($2 > 0) s = $2 " ahead"
        if ($1 > 0) s = s (s ? ", " : "") $1 " behind"
        if (s) printf " (%s vs origin/main)", s
    }')
fi

dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
[ "$dirty" = "0" ] && tree="clean" || tree="$dirty file(s) uncommitted"

echo "nanopnp — where the work stands (.claude/hooks/session-start.sh):"
echo "- branch ${branch}${position}, working tree ${tree}"

for plan in docs/plans/*.md; do
    [ -f "$plan" ] || continue
    # The status is the first **bold** span, and it wraps across source lines:
    # take the whole span, not the first line of it, or the qualifier is lost.
    status=$(awk '
        /^\*\*Status/ {
            buf = $0
            n = 0
            while (split(buf, parts, /\*\*/) < 3 && n++ < 4 && (getline line) > 0) buf = buf " " line
            if (split(buf, parts, /\*\*/) < 3) exit
            s = parts[2]
            # Trim on a word boundary: a byte-wise cut can split a multi-byte dash.
            if (length(s) > 140) { s = substr(s, 1, 140); sub(/[^ ]*$/, "", s); s = s "…" }
            print s
            exit
        }' "$plan" 2>/dev/null)
    [ -n "$status" ] && echo "- ${plan} — ${status}"
done

echo "- workflow: /wp-plan -> /wp-implement -> /wp-ship; CLAUDE.md 'Implementation workflow'"

exit 0
