"""VER-69: each user-testing session's commands still run as written, and none is left untagged."""

from __future__ import annotations

import logging
import re
import shlex
import time
from pathlib import Path

import pytest

from nanopnp.validation.examples import (
    PROGRAMS,
    TAGGED_BLOCK,
    copy_example,
    run_tagged,
    tagged_commands,
)

pytestmark = pytest.mark.nightly

logger = logging.getLogger(__name__)

REPOSITORY = Path(__file__).resolve().parents[2]
SESSIONS = REPOSITORY / "docs" / "user-testing" / "sessions"
# Every directory, not every README: one without a README is a session nothing would run.
SESSION_DIRECTORIES = sorted(path for path in SESSIONS.iterdir() if path.is_dir())
# In the order a session needs: its refusals read what its runs wrote.
TESTED_TAGS = ("run", "refused")

CONSOLE_FENCE = re.compile(r"```console\n(?P<body>.*?)\n```", re.DOTALL)


def _untagged_program_lines(readme: Path) -> list[list[str]]:
    # A tagged block is cut out whole, so what the console fences still hold is what no test runs.
    text = TAGGED_BLOCK.sub(
        lambda block: "" if block.group("tag") in TESTED_TAGS else block.group(0),
        readme.read_text(encoding="utf-8"),
    )
    lines: list[list[str]] = []
    for fence in CONSOLE_FENCE.finditer(text):
        for line in fence.group("body").splitlines():
            words = shlex.split(line[2:]) if line.startswith("$ ") else []
            if words and words[0] in PROGRAMS:
                lines.append(words)
    return lines


@pytest.mark.parametrize("session", SESSION_DIRECTORIES, ids=lambda path: path.name)
def test_session_commands_still_run_as_written(session: Path, tmp_path: Path) -> None:
    # A protocol gone stale, or a block tagged so that it runs nothing, would leave the
    # author's sitting to find a broken step. Exit status is the oracle: the expected
    # outcomes of a session are the tester's to judge, so no number is asserted.
    readme = session / "README.md"
    assert readme.is_file(), f"{session.name} has no README.md"
    tagged = [command for tag in TESTED_TAGS for command in tagged_commands(readme, tag)]
    assert tagged, f"{session.name} has no tagged command"
    untagged = _untagged_program_lines(readme)
    assert not untagged, f"{session.name}: untagged program lines {untagged}"

    copied = copy_example(session, tmp_path, repository=REPOSITORY)
    started = time.perf_counter()
    for tag in TESTED_TAGS:
        run_tagged(copied, tag)
    logger.info("session %s: %.1f s", session.name, time.perf_counter() - started)
