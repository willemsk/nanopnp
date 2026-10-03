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

**The tag names the exit status every command in the block must return**
(:data:`EXPECTED_EXIT`). ``run`` and ``plan`` expect ``0``; ``refused`` expects
``4``, the gate class of the IF-02 exit NOTE, so that a README can show a gate
refusing an input and have that refusal tested rather than asserted in prose
(VER-46, WP25 D5, D10). A refusal that exits ``0``, or a run that exits ``4``,
fails naming both codes.
"""

from __future__ import annotations

import logging
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from nanopnp.cli.errors import EXIT_GATE, EXIT_OK

__all__ = [
    "EXPECTED_EXIT",
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

EXPECTED_EXIT: Mapping[str, int] = {"run": EXIT_OK, "plan": EXIT_OK, "refused": EXIT_GATE}
"""The tags a README may use, against the exit status each command in the block must return."""

UP = "../"
"""The prefix a command uses to reach a file outside its example directory.

``../../<path>`` reaches a repository file and ``../<sibling>/<file>`` a sibling
example's (WP32 D5).
"""

GENERATED = ("__pycache__",)
"""Ignored when copying an example, beside the patterns of ``examples/.gitignore``."""


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

    The example lands at ``root/examples/<name>``. A command word that starts
    with ``../`` and resolves, against the example directory, to a file inside
    ``repository`` gets that file's directory mirrored at the same place under
    ``root``, so the same relative path resolves in the copy: ``../../<path>``
    reaches a repository file, and ``../<sibling>/<file>`` runs a sibling
    example's script rather than a copy of it, so the two cannot drift apart
    (WP32 D5). A word naming a file directly in ``examples/`` copies that file
    alone: its directory holds every example. Nothing an example generated in
    the source tree is copied: only tracked-looking inputs, never ``store/`` or
    a written mesh, which the test must produce itself.

    What counts as generated is read from ``examples/.gitignore``, the one list of
    what running an example writes, so that list and this copy cannot drift. It
    filters the example and any sibling mirrored beside it; a directory outside
    ``examples/`` loses only its ``*.msh``.

    Returns
    -------
    Path
        The copied example directory, to run the commands in.
    """
    generated = _generated_patterns(example.parent / ".gitignore")
    destination = root / "examples" / example.name
    shutil.copytree(example, destination, ignore=shutil.ignore_patterns(*generated))
    repository = repository.resolve()
    examples = example.parent.resolve()
    readme = example / "README.md"
    commands = [command for tag in EXPECTED_EXIT for command in tagged_commands(readme, tag)]
    for argv in commands:
        for word in argv[1:]:
            if not word.startswith(UP):
                continue
            named = (example / word).resolve()
            source = named.parent
            if not source.is_relative_to(repository) or source == example.resolve():
                continue
            if source == examples:
                # A file beside the examples, not inside one: mirroring its
                # directory would copy every example. The file alone, if it exists.
                if named.is_file():
                    target = root / named.relative_to(repository)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(named, target)
                continue
            patterns = generated if source.is_relative_to(examples) else ("*.msh",)
            # Merged rather than skipped when the target exists: a directory
            # mirrored for an earlier word may be this one's ancestor or child.
            shutil.copytree(
                source,
                root / source.relative_to(repository),
                ignore=shutil.ignore_patterns(*patterns),
                dirs_exist_ok=True,
            )
    return destination


def _generated_patterns(gitignore: Path) -> tuple[str, ...]:
    """Return the name patterns of a ``.gitignore``, for :func:`shutil.ignore_patterns`.

    Only the plain name patterns the examples' file uses: a trailing ``/`` is
    dropped, since ``ignore_patterns`` matches a directory by its name alone, and
    comments and blank lines are skipped.
    """
    if not gitignore.is_file():
        return GENERATED
    patterns = [
        line.strip().rstrip("/")
        for line in gitignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return (*patterns, *GENERATED)


def run_tagged(directory: Path, tag: str, *, timeout_s: float = 1800.0) -> list[CommandResult]:
    """Run every ``tag`` command of ``directory/README.md`` in ``directory``.

    Each must exit with the status :data:`EXPECTED_EXIT` gives its tag.

    Raises
    ------
    ExampleCommandError
        On the first command that exits otherwise, naming both codes and carrying
        both of its streams; or if ``tag`` is not one of :data:`EXPECTED_EXIT`.
    """
    expected = EXPECTED_EXIT.get(tag)
    if expected is None:
        raise ExampleCommandError(
            f"no test executes the tag {tag!r}; the tags are {', '.join(EXPECTED_EXIT)}"
        )
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
        if completed.returncode != expected:
            raise ExampleCommandError(
                f"{shlex.join(argv)} exited {completed.returncode} in {directory}, and a "
                f"{tag!r} command must exit {expected}\n"
                f"--- stdout\n{completed.stdout}\n--- stderr\n{completed.stderr}"
            )
        results.append(result)
    return results
