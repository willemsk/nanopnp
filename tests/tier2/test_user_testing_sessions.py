"""VER-69: each user-testing session's commands still run as written, and none is left untagged."""

from __future__ import annotations

import logging
import re
import shlex
import time
from pathlib import Path

import pytest

from nanopnp.validation.examples import PROGRAMS, copy_example, run_tagged, tagged_commands

pytestmark = pytest.mark.nightly

logger = logging.getLogger(__name__)

REPOSITORY = Path(__file__).resolve().parents[2]
SESSIONS = REPOSITORY / "docs" / "user-testing" / "sessions"

CONSOLE_FENCE = re.compile(r"```console\n(?P<body>.*?)\n```", re.DOTALL)


def _program_lines(readme: Path) -> list[list[str]]:
    lines: list[list[str]] = []
    for fence in CONSOLE_FENCE.finditer(readme.read_text(encoding="utf-8")):
        for line in fence.group("body").splitlines():
            words = shlex.split(line[2:]) if line.startswith("$ ") else []
            if words and words[0] in PROGRAMS:
                lines.append(words)
    return lines


@pytest.mark.parametrize(
    "readme", sorted(SESSIONS.glob("*/README.md")), ids=lambda path: path.parent.name
)
def test_session_commands_still_run_as_written(readme: Path, tmp_path: Path) -> None:
    # A protocol gone stale, or a block tagged so that it runs nothing, would leave the
    # author's sitting to find a broken step. Exit status is the oracle: the expected
    # outcomes of a session are the tester's to judge, so no number is asserted.
    tagged = [command for tag in ("run", "refused") for command in tagged_commands(readme, tag)]
    assert tagged, f"{readme.parent.name} has no tagged command"
    untagged = [words for words in _program_lines(readme) if words not in tagged]
    assert not untagged, f"{readme.parent.name}: untagged program lines {untagged}"

    session = copy_example(readme.parent, tmp_path, repository=REPOSITORY)
    started = time.perf_counter()
    run_tagged(session, "run")
    run_tagged(session, "refused")
    logger.info("session %s: %.1f s", readme.parent.name, time.perf_counter() - started)
