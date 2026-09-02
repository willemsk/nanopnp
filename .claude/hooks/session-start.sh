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

position=$(git rev-list --left-right --count origin/main...HEAD 2>/dev/null | awk '{
    s = ""
    if ($2 > 0) s = $2 " ahead"
    if ($1 > 0) s = s (s ? ", " : "") $1 " behind"
    if (s) printf " (%s vs origin/main)", s
}')

dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
[ "$dirty" = "0" ] && tree="clean" || tree="$dirty file(s) uncommitted"

echo "nanopnp — where the work stands (.claude/hooks/session-start.sh):"
echo "- branch ${branch}${position}, working tree ${tree}"

for plan in docs/plans/*.md; do
    [ -f "$plan" ] || continue
    status=$(grep -m1 '^\*\*Status' "$plan" 2>/dev/null | sed 's/\*\*//g' | cut -c1-110)
    [ -n "$status" ] && echo "- ${plan} — ${status}"
done

echo "- workflow: /wp-plan -> /wp-implement -> /wp-ship; CLAUDE.md 'Implementation workflow'"

exit 0
