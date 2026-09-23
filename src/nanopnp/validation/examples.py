"""Execute the worked examples' documented commands, verbatim (VER-46).

A worked example's README marks each runnable step with a ``console`` fence
preceded by an HTML comment naming its tag::

    <!-- example: run -->
    ```console
    $ nanopnp mesh cylinder --out pore.msh
    ```

Each ``$`` line is one command; any other line in the fence is shown output and is
not run. The test runs exactly those lines, from a copy of the example's directory,
so the commands a reader copies are the commands that were tested (WP16 D8). They
run without a shell — :func:`shlex.split`, no pipes, no globs, no redirection — so
that the same README executes on Windows, and a command line that needed a shell
would be refused rather than half-run.

Two programs are allowed: ``nanopnp``, resolved to the console script installed
beside the running interpreter, and ``python``, resolved to that interpreter. A
reader of a development checkout prefixes each line with ``uv run``; the README
says so rather than writing it into every line.
"""

from __future__ import annotations

import logging
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "PROGRAMS",
    "CommandResult",
    "ExampleCommandError",
    "copy_example",
    "run_tagged",
    "tagged_commands",
]

logger = logging.getLogger(__name__)

TAGGED_BLOCK = re.compile(
    r"<!--\s*example:\s*(?P<tag>[\w-]+)\s*-->\s*\n```console\n(?P<body>.*?)\n```", re.DOTALL
)
"""A tagged console fence: the tag, and the fence's body."""

PROGRAMS: tuple[str, ...] = ("nanopnp", "python")
"""The programs a tagged command may name."""

UP = "../../"
"""The prefix a command uses to reach a repository file from an example directory."""


class ExampleCommandError(RuntimeError):
    """A documented command failed, or could not be run as written.

    The message carries the command, the directory, the exit status and both
    streams, because the one thing a failing example must not do is make its
    reader reconstruct what was run.
    """


@dataclass(frozen=True)
class CommandResult:
    """One documented command, as run."""

    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def tagged_commands(readme: Path, tag: str) -> list[list[str]]:
    """Return the commands of every ``tag`` block in ``readme``, in order.

    Raises
    ------
    ExampleCommandError
        If a command names a program other than :data:`PROGRAMS`.
    """
    commands: list[list[str]] = []
    for block in TAGGED_BLOCK.finditer(readme.read_text(encoding="utf-8")):
        if block.group("tag") != tag:
            continue
        for line in block.group("body").splitlines():
            if not line.startswith("$ "):
                continue
            argv = shlex.split(line[2:])
            if not argv or argv[0] not in PROGRAMS:
                raise ExampleCommandError(
                    f"{readme}: {line!r} runs {argv[0] if argv else 'nothing'}; a tagged "
                    f"command runs one of {', '.join(PROGRAMS)}, without a shell"
                )
            commands.append(argv)
    return commands


def _program(name: str) -> str:
    """Return the executable a command's first word resolves to."""
    if name == "python":
        return sys.executable
    scripts = Path(sys.executable).parent
    for candidate in (scripts / name, scripts / f"{name}.exe"):
        if candidate.is_file():
            return str(candidate)
    found = shutil.which(name)
    if found is None:
        raise ExampleCommandError(f"no {name!r} executable beside {sys.executable} or on PATH")
    return found


def copy_example(example: Path, root: Path, *, repository: Path) -> Path:
    """Copy an example directory into ``root``, laid out as in the repository.

    The example lands at ``root/examples/<name>``. A command that reaches a
    repository file by ``../../<path>`` gets that file's directory mirrored at
    ``root/<dir>`` too, so the same relative path resolves in the copy. Nothing
    the example generated in the source tree is copied: only tracked-looking
    inputs, never ``store/`` or a written mesh, which the test must produce itself.

    Returns
    -------
    Path
        The copied example directory, to run the commands in.
    """
    destination = root / "examples" / example.name
    shutil.copytree(
        example,
        destination,
        ignore=shutil.ignore_patterns("store", "*.msh", "run*", "iv-*", "phase1*", "__pycache__"),
    )
    for argv in tagged_commands(example / "README.md", "run") + tagged_commands(
        example / "README.md", "plan"
    ):
        for word in argv[1:]:
            if word.startswith(UP):
                source = (repository / word[len(UP) :]).parent
                target = root / source.relative_to(repository)
                if not target.exists():
                    shutil.copytree(source, target, ignore=shutil.ignore_patterns("*.msh"))
    return destination


def run_tagged(directory: Path, tag: str, *, timeout_s: float = 1800.0) -> list[CommandResult]:
    """Run every ``tag`` command of ``directory/README.md`` in ``directory``.

    Raises
    ------
    ExampleCommandError
        On the first command that exits nonzero, carrying both of its streams.
    """
    results: list[CommandResult] = []
    for argv in tagged_commands(directory / "README.md", tag):
        resolved = [_program(argv[0]), *argv[1:]]
        logger.info("%s$ %s", directory.name, shlex.join(argv))
        completed = subprocess.run(
            resolved,
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        result = CommandResult(
            argv=tuple(argv),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if completed.returncode != 0:
            raise ExampleCommandError(
                f"{shlex.join(argv)} exited {completed.returncode} in {directory}\n"
                f"--- stdout\n{completed.stdout}\n--- stderr\n{completed.stderr}"
            )
        results.append(result)
    return results
