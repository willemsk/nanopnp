#!/bin/bash
# Bootstraps the uv-managed environment at the start of a Claude Code on the
# web session, so `uv run pytest`/`ruff`/`mypy` all work immediately without
# a manual `uv sync` first. See CLAUDE.md "Setup".
set -euo pipefail

# Only run in Claude Code on the web / remote sessions — local devs manage
# their own venv per CLAUDE.md.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

uv sync --all-extras --frozen
