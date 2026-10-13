"""Execute the worked examples' documented commands, verbatim (VER-46)."""

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

from nanopnp.core.errors import EXIT_GATE, EXIT_OK

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

PROGRAMS: tuple[str, ...] = ("nanopnp", "python")

EXPECTED_EXIT: Mapping[str, int] = {"run": EXIT_OK, "plan": EXIT_OK, "refused": EXIT_GATE}

UP = "../"

GENERATED = ("__pycache__",)


class ExampleCommandError(RuntimeError):
    """Raised when a documented command failed, or could not be run as written."""


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
        If a command names a program other than ``PROGRAMS``.
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

    Raises
    ------
    ExampleCommandError
        On the first command that exits with an unexpected status, or if ``tag`` is unknown.
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
