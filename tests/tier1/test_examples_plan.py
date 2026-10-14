"""VER-46 (Tier 1): the worked examples' cheap steps and the README contract."""

from __future__ import annotations

import importlib.util
import itertools
import json
import re
import shlex
from pathlib import Path

import pytest

from nanopnp.core.errors import EXIT_GATE
from nanopnp.pipeline.case import load_case, resolve
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

# 5 configurations x 35 biases x 21 concentrations: SPECIFICATION.md section 8.3.
REFERENCE_POINTS = 3675

# Wave count: docs/sweeps/README.md, reference sweep.
REFERENCE_WAVES = 42


def test_ver46_the_seven_examples_exist() -> None:
    assert [path.name for path in EXAMPLES] == [
        "01-quickstart",
        "02-charged-pore",
        "03-iv-sweep",
        "04-python-api",
        "05-clya-reference",
        "06-pdb-to-mesh",
        "07-pdb-to-charged-run",
    ]


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.name)
def test_ver46_every_readme_has_a_tagged_block_of_runnable_commands(example: Path) -> None:
    readme = example / "README.md"
    commands = tagged_commands(readme, "run")
    assert commands, f"{readme} has no <!-- example: run --> block"
    tags = set(re.findall(r"<!--\s*example:\s*([\w-]+)\s*-->", readme.read_text("utf-8")))
    assert tags <= set(EXPECTED_EXIT), f"{readme} uses a tag no test executes: {tags}"


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
    (tmp_path / "README.md").write_text(
        f"<!-- example: {tag} -->\n```console\n$ python -c 'raise SystemExit({code})'\n```\n",
        encoding="utf-8",
    )
    with pytest.raises(ExampleCommandError, match=message):
        run_tagged(tmp_path, tag)


def test_ver46_a_refused_block_passes_on_exit_four(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "<!-- example: refused -->\n```console\n$ python -c 'raise SystemExit(4)'\n```\n",
        encoding="utf-8",
    )
    (result,) = run_tagged(tmp_path, "refused")
    assert result.returncode == EXIT_GATE


def test_ver46_an_unknown_tag_is_refused(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    with pytest.raises(ExampleCommandError, match="no test executes the tag 'skip'"):
        run_tagged(tmp_path, "skip")


def test_ver46_copy_mirrors_the_repository_files_of_every_tag(tmp_path: Path) -> None:
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


def test_ver46_copy_mirrors_a_sibling_example_without_its_generated_files(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "source"
    examples = repository / "examples"
    example = examples / "99-scratch"
    sibling = examples / "98-sibling"
    for directory in (example, sibling / "store", repository / "data"):
        directory.mkdir(parents=True)
    (examples / ".gitignore").write_text("store/\n*.msh\nwritten.pdb\n", encoding="utf-8")
    (example / "README.md").write_text(
        "<!-- example: run -->\n```console\n"
        "$ python ../98-sibling/prepare.py ../../data/x.txt written.pdb\n```\n",
        encoding="utf-8",
    )
    (sibling / "prepare.py").write_text("print('prepared')\n", encoding="utf-8")
    (sibling / "case.yaml").write_text("name: sibling\n", encoding="utf-8")
    (sibling / "store" / "entry").write_text("generated", encoding="utf-8")
    (sibling / "pore.msh").write_text("generated", encoding="utf-8")
    (sibling / "written.pdb").write_text("generated", encoding="utf-8")
    (repository / "data" / "x.txt").write_text("x", encoding="utf-8")

    copied = copy_example(example, tmp_path / "copy", repository=repository)
    mirrored = (copied / "../98-sibling").resolve()
    assert sorted(path.name for path in mirrored.iterdir()) == ["case.yaml", "prepare.py"]
    assert (copied / "../../data/x.txt").resolve().read_text(encoding="utf-8") == "x"
    (result,) = run_tagged(copied, "run")
    assert result.stdout == "prepared\n"


def test_ver46_a_file_beside_the_examples_is_copied_alone(tmp_path: Path) -> None:
    repository = tmp_path / "source"
    examples = repository / "examples"
    example = examples / "99-scratch"
    other = examples / "97-other"
    for directory in (example, other):
        directory.mkdir(parents=True)
    (examples / "shared.txt").write_text("shared", encoding="utf-8")
    (other / "case.yaml").write_text("name: other\n", encoding="utf-8")
    (example / "README.md").write_text(
        "<!-- example: run -->\n```console\n$ python -c pass ../shared.txt ../missing.txt\n```\n",
        encoding="utf-8",
    )

    copied = copy_example(example, tmp_path / "copy", repository=repository)
    assert sorted(path.name for path in copied.parent.iterdir()) == ["99-scratch", "shared.txt"]
    assert (copied / "../shared.txt").resolve().read_text(encoding="utf-8") == "shared"


@pytest.fixture(scope="module")
def planned(tmp_path_factory: pytest.TempPathFactory) -> Path:
    example = copy_example(
        REPOSITORY / "examples" / "05-clya-reference",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    run_tagged(example, "plan")
    return example


# FR-24
def test_ver46_example_05_plans_the_reference_sweep_in_its_waves(planned: Path) -> None:
    plan = json.loads((planned / "phase1" / "plan.json").read_text(encoding="utf-8"))
    assert len(plan["points"]) == REFERENCE_POINTS
    waves = plan["waves"]
    assert len(waves) == REFERENCE_WAVES
    assert waves[0][0] == 0 and waves[-1][1] == REFERENCE_POINTS
    assert all(left[1] == right[0] for left, right in itertools.pairwise(waves))


# QR-06
def test_ver46_example_05_renders_one_dependent_array_per_wave(planned: Path) -> None:
    plan = json.loads((planned / "phase1" / "plan.json").read_text(encoding="utf-8"))
    script = (planned / "phase1.sh").read_text(encoding="utf-8")
    arrays = re.findall(r"--array=0-(\d+)%\d+ --export=ALL,WAVE_FIRST=(\d+) ", script)
    assert [[int(first), int(first) + int(top) + 1] for top, first in arrays] == plan["waves"]
    assert max(int(top) for top, _first in arrays) < 1000
    submissions = [line for line in script.splitlines() if "sbatch" in line]
    assert len(submissions) == REFERENCE_WAVES
    assert all("--dependency=afterany:$previous" in line for line in submissions)

    member = (planned / "phase1.member.sbatch").read_text(encoding="utf-8")
    assert "nanopnp sweep run" in member
    assert '--index "$((WAVE_FIRST + SLURM_ARRAY_TASK_ID))"' in member
    assert shlex.quote(str((planned / "phase1" / "plan.json").resolve())) in member
    assert f"--chdir={planned.parents[1].resolve()}" in member
    assert f"--job-name={plan['name']}\n" in member


def test_ver46_example_05_sbatch_values_are_raw_and_refused_when_unpassable(
    planned: Path, tmp_path: Path
) -> None:
    spec = importlib.util.spec_from_file_location("render_slurm", planned / "render_slurm.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    plan = json.loads((planned / "phase1" / "plan.json").read_text(encoding="utf-8"))

    def attempt(name: str, workdir: Path, time: str = "00:10:00") -> Path:
        path = tmp_path / "plan.json"
        path.write_text(json.dumps({**plan, "name": name}), encoding="utf-8")
        _, member = module.render(
            path,
            workdir=workdir,
            store=tmp_path / "store",
            out=tmp_path / "submit.sh",
            time=time,
            concurrency=4,
        )
        return member

    text = attempt("clya-0.5M_reference", tmp_path).read_text(encoding="utf-8")
    assert "#SBATCH --job-name=clya-0.5M_reference\n" in text
    assert f"#SBATCH --chdir={tmp_path}\n" in text
    assert "#SBATCH --time=00:10:00\n" in text

    for character in (" ", "'", '"', "#", "%", "\n", "\t", "\x00"):
        with pytest.raises(ValueError, match="--job-name"):
            attempt(f"phase{character}1", tmp_path)
    with pytest.raises(ValueError, match="--chdir"):
        attempt("phase1", tmp_path / "a b")
    with pytest.raises(ValueError, match="--time"):
        attempt("phase1", tmp_path, time="1 day")


def test_ver46_example_05_case_is_the_frozen_case() -> None:
    frozen = load_case(REPOSITORY / "docs/validation/cases/clya-0.5M-plus50mV.case.yaml")
    copy = load_case(REPOSITORY / "examples/05-clya-reference/clya-0.5M-plus50mV.case.yaml")
    assert case_identity(resolve(copy)) == case_identity(resolve(frozen))
    left = frozen.model_dump(mode="json", by_alias=True)
    right = copy.model_dump(mode="json", by_alias=True)
    assert Path(left["inputs"]["mesh"].pop("path")) == Path("docs/sweeps/clya-reference.msh")
    assert Path(right["inputs"]["mesh"].pop("path")) == Path("clya-reference.msh")
    assert left == right
