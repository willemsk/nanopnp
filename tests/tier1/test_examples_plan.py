"""VER-46 (Tier 1) — the worked examples' cheap steps, and the README contract.

The examples' solves are Tier 2 (``tests/tier2/test_examples_*.py``); what is
gated here costs seconds. Every example's README must carry at least one tagged
block of commands a test executes, in programs the executor can run without a
shell, and each tag names the exit status its commands must return: ``refused``
is a gate refusal, exit 4, and a command that exits otherwise fails naming both
codes (WP25 D10). Example 05's planning block runs verbatim over the §8.3 reference sweep
and must enumerate it exactly as that sweep is specified, and its SLURM rendering
must submit every point once, wave by wave, in dependency order. Example 05's
case is a copy of a frozen Tier-3 case and must keep its identity.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import re
import shlex
from pathlib import Path

import pytest

from nanopnp.cli.errors import EXIT_GATE, EXIT_OK
from nanopnp.io.case import load_case, resolve
from nanopnp.validation.comsol import case_identity
from nanopnp.validation.examples import (
    EXPECTED_EXIT,
    ExampleCommandError,
    copy_example,
    run_tagged,
    tagged_commands,
)

REPOSITORY = Path(__file__).resolve().parents[2]
EXAMPLES = sorted(path.parent for path in (REPOSITORY / "examples").glob("*/README.md"))

REFERENCE_POINTS = 3675
"""5 configurations x 35 biases x 21 concentrations (SPECIFICATION.md section 8.3)."""

REFERENCE_WAVES = 42
"""The wave count docs/sweeps/README.md states for the reference sweep."""


def test_ver46_the_six_examples_exist() -> None:
    """The examples of the Phase-1 and Phase-2 documentation increments (section 8.1)."""
    assert [path.name for path in EXAMPLES] == [
        "01-quickstart",
        "02-charged-pore",
        "03-iv-sweep",
        "04-python-api",
        "05-clya-reference",
        "06-pdb-to-mesh",
    ]


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.name)
def test_ver46_every_readme_has_a_tagged_block_of_runnable_commands(example: Path) -> None:
    """At least one ``run`` block, and every tagged command parses for the executor."""
    readme = example / "README.md"
    commands = tagged_commands(readme, "run")
    assert commands, f"{readme} has no <!-- example: run --> block"
    tags = set(re.findall(r"<!--\s*example:\s*([\w-]+)\s*-->", readme.read_text("utf-8")))
    assert tags <= set(EXPECTED_EXIT), f"{readme} uses a tag no test executes: {tags}"


def test_ver46_the_tags_are_run_plan_and_refused() -> None:
    """``refused`` expects the gate class, 4; ``run`` and ``plan`` expect 0 (WP25 D10)."""
    assert dict(EXPECTED_EXIT) == {"run": EXIT_OK, "plan": EXIT_OK, "refused": EXIT_GATE}


@pytest.mark.parametrize(
    ("tag", "code", "message"),
    [
        ("refused", 0, "exited 0 in .*, and a 'refused' command must exit 4"),
        ("run", 4, "exited 4 in .*, and a 'run' command must exit 0"),
        ("refused", 3, "exited 3 in .*, and a 'refused' command must exit 4"),
    ],
)
def test_ver46_an_exit_the_tag_does_not_expect_fails_naming_both_codes(
    tag: str, code: int, message: str, tmp_path: Path
) -> None:
    """A refusal that succeeds, or a run a gate stops, fails the example (VER-46)."""
    (tmp_path / "README.md").write_text(
        f"<!-- example: {tag} -->\n```console\n$ python -c 'raise SystemExit({code})'\n```\n",
        encoding="utf-8",
    )
    with pytest.raises(ExampleCommandError, match=message):
        run_tagged(tmp_path, tag)


def test_ver46_a_refused_block_passes_on_exit_four(tmp_path: Path) -> None:
    """The one exit a ``refused`` block accepts is the gate class."""
    (tmp_path / "README.md").write_text(
        "<!-- example: refused -->\n```console\n$ python -c 'raise SystemExit(4)'\n```\n",
        encoding="utf-8",
    )
    (result,) = run_tagged(tmp_path, "refused")
    assert result.returncode == EXIT_GATE


def test_ver46_an_unknown_tag_is_refused(tmp_path: Path) -> None:
    """A tag no test executes cannot be run by accident as if it were one."""
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    with pytest.raises(ExampleCommandError, match="no test executes the tag 'skip'"):
        run_tagged(tmp_path, "skip")


def test_ver46_copy_mirrors_the_repository_files_of_every_tag(tmp_path: Path) -> None:
    """A ``../../`` argument in a ``refused`` block is mirrored as one in a ``run`` block is."""
    example = tmp_path / "source" / "examples" / "99-scratch"
    example.mkdir(parents=True)
    (example / "README.md").write_text(
        "<!-- example: refused -->\n```console\n$ nanopnp stage structure ../../data/a/x.txt\n"
        "```\n\n<!-- example: run -->\n```console\n$ python ../../data/b/y.txt\n```\n",
        encoding="utf-8",
    )
    repository = tmp_path / "source"
    for name in ("a/x.txt", "b/y.txt"):
        (repository / "data" / name).parent.mkdir(parents=True)
        (repository / "data" / name).write_text(name, encoding="utf-8")
    copied = copy_example(example, tmp_path / "copy", repository=repository)
    assert (copied / "../../data/a/x.txt").resolve().read_text(encoding="utf-8") == "a/x.txt"
    assert (copied / "../../data/b/y.txt").resolve().read_text(encoding="utf-8") == "b/y.txt"


@pytest.fixture(scope="module")
def planned(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run example 05's ``plan`` block verbatim in a copy, and return the copy."""
    example = copy_example(
        REPOSITORY / "examples" / "05-clya-reference",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    run_tagged(example, "plan")
    return example


def test_ver46_example_05_plans_the_reference_sweep_in_its_waves(planned: Path) -> None:
    """The §8.3 reference sweep: 3,675 points in 42 waves, contiguous and in order (FR-24)."""
    plan = json.loads((planned / "phase1" / "plan.json").read_text(encoding="utf-8"))
    assert len(plan["points"]) == REFERENCE_POINTS
    waves = plan["waves"]
    assert len(waves) == REFERENCE_WAVES
    assert waves[0][0] == 0 and waves[-1][1] == REFERENCE_POINTS
    assert all(left[1] == right[0] for left, right in itertools.pairwise(waves))


def test_ver46_example_05_renders_one_dependent_array_per_wave(planned: Path) -> None:
    """Every point is submitted once, each wave after the one before (FR-24, QR-06)."""
    plan = json.loads((planned / "phase1" / "plan.json").read_text(encoding="utf-8"))
    script = (planned / "phase1.sh").read_text(encoding="utf-8")
    # Each array counts from 0 within its wave, with the wave's first point index
    # exported beside it: SLURM's default MaxArraySize (1001) refuses a task
    # index at or above it, and this sweep's indices run to 3,674.
    arrays = re.findall(r"--array=0-(\d+)%\d+ --export=ALL,WAVE_FIRST=(\d+) ", script)
    assert [[int(first), int(first) + int(top) + 1] for top, first in arrays] == plan["waves"]
    assert max(int(top) for top, _first in arrays) < 1000
    submissions = [line for line in script.splitlines() if "sbatch" in line]
    assert len(submissions) == REFERENCE_WAVES
    assert all("--dependency=afterany:$previous" in line for line in submissions)

    member = (planned / "phase1.member.sbatch").read_text(encoding="utf-8")
    assert "nanopnp sweep run" in member
    assert '--index "$((WAVE_FIRST + SLURM_ARRAY_TASK_ID))"' in member
    # Paths are shell-quoted as the script writes them: bare on POSIX, quoted where
    # the path carries a backslash or a drive colon (Windows).
    assert shlex.quote(str((planned / "phase1" / "plan.json").resolve())) in member
    # The base case names its mesh from the repository root, so that is where
    # the members must run (the README's --workdir ../..).
    assert f"--chdir={shlex.quote(str(planned.parents[1].resolve()))}" in member
    assert f"--job-name={shlex.quote(plan['name'])}\n" in member


def test_ver46_example_05_quotes_the_sweep_name_and_refuses_a_line_break(
    planned: Path, tmp_path: Path
) -> None:
    """The name was the one value written into the member job unquoted."""
    spec = importlib.util.spec_from_file_location("render_slurm", planned / "render_slurm.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    plan = json.loads((planned / "phase1" / "plan.json").read_text(encoding="utf-8"))
    for name, refused in (("phase 1; rm -rf ~", False), ("phase1\necho injected", True)):
        path = tmp_path / f"plan-{refused}.json"
        path.write_text(json.dumps({**plan, "name": name}), encoding="utf-8")
        arguments = {
            "workdir": tmp_path,
            "store": tmp_path / "store",
            "out": tmp_path / f"submit-{refused}.sh",
            "time": "00:10:00",
            "concurrency": 4,
        }
        if refused:
            with pytest.raises(ValueError, match="control character"):
                module.render(path, **arguments)
            continue
        _, member = module.render(path, **arguments)
        text = member.read_text(encoding="utf-8")
        assert f"#SBATCH --job-name={shlex.quote(name)}\n" in text


def test_ver46_example_05_case_is_the_frozen_case() -> None:
    """The copy keeps the frozen Tier-3 case's identity and differs only in the mesh path."""
    frozen = load_case(REPOSITORY / "docs/validation/cases/clya-0.5M-plus50mV.case.yaml")
    copy = load_case(REPOSITORY / "examples/05-clya-reference/clya-0.5M-plus50mV.case.yaml")
    assert case_identity(resolve(copy)) == case_identity(resolve(frozen))
    left = frozen.model_dump(mode="json", by_alias=True)
    right = copy.model_dump(mode="json", by_alias=True)
    # A path dumps with the platform's separator, so compare paths, not strings.
    assert Path(left["inputs"]["mesh"].pop("path")) == Path("docs/sweeps/clya-reference.msh")
    assert Path(right["inputs"]["mesh"].pop("path")) == Path("clya-reference.msh")
    assert left == right
