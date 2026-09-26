"""VER-47 — case schema v2, the v1 upgrade, and the supported interpreter range.

The oracle is a frozen corpus: every case file the project shipped under
``nanopnp/case/v1``, copied into ``tests/tier1/data/case_v1/corpus/`` together
with what the unmodified v1 code made of each of them (``golden.json``) and the
v1 field tree (``fields.txt``). All three were written by ``record.py`` in that
directory *before* the schema moved, so the upgrade is held to a record it did
not produce (WP17 D7). A record written by the code under test would agree with
it for the same wrong reason.
"""

from __future__ import annotations

import copy
import difflib
import json
import re
import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
import yaml
from packaging.specifiers import SpecifierSet

from nanopnp.core.hashing import content_hash
from nanopnp.core.stages import describe
from nanopnp.io.artefact import (
    CASE_SCHEMA,
    CASE_SCHEMA_V1,
    SOLUTION_SCHEMA,
    CaseArtefact,
    StageInputs,
)
from nanopnp.io.case import (
    SOLVE_IRRELEVANT_PROVENANCE,
    V2_ADDED,
    V2_MOVED,
    V2_RENAMED,
    CaseValidationError,
    ResolvedCase,
    UnsupportedCaseSection,
    case_fields,
    dumps_case,
    load_case,
    loads_case,
    resolve,
    upgrade_v1,
)
from nanopnp.io.defaults import deviations
from nanopnp.materials.stage import MaterialsStage
from nanopnp.validation.comsol import case_identity

DATA = Path(__file__).parent / "data" / "case_v1"
GOLDEN: dict[str, Any] = json.loads((DATA / "golden.json").read_text(encoding="utf-8"))
CORPUS: tuple[str, ...] = tuple(sorted(GOLDEN["cases"]))
V1_FIELDS: frozenset[str] = frozenset((DATA / "fields.txt").read_text(encoding="utf-8").split())

LEFT_THE_SOLVE_KEY: frozenset[str] = frozenset({"schema"})
"""Provenance the v1 solve key carried and the v2 one does not (section 5.3.2 NOTE).

The one entry is the schema string. A v1 document and its upgrade are one run,
so the string moved out of the key at the move to v2, and the three solve keys
of every stored case moved with it, once. Everything else in the record is
required to be unchanged, entry by entry.
"""


def _decoded(record: dict[str, Any]) -> dict[str, Any]:
    """Return a provenance record as ``golden.json`` holds it, tuples as lists."""
    decoded: dict[str, Any] = json.loads(json.dumps(record, sort_keys=True))
    return decoded


def _diff(recorded: dict[str, Any], resolved: dict[str, Any]) -> str:
    """Return a unified diff of two provenance records, for a failure message."""
    before = json.dumps(recorded, indent=2, sort_keys=True).splitlines()
    after = json.dumps(resolved, indent=2, sort_keys=True).splitlines()
    return "\n".join(difflib.unified_diff(before, after, "recorded (v1)", "resolved", lineterm=""))


def _identity_of(solve_provenance: dict[str, Any]) -> str:
    """Return :func:`case_identity` of a recorded solve provenance.

    :func:`case_identity` reads nothing of the resolved case but its solve
    provenance, so a stand-in carrying the recorded one asks it what v1 hashed.
    """
    return case_identity(cast(ResolvedCase, SimpleNamespace(solve_provenance=solve_provenance)))


def test_ver47_the_corpus_is_every_case_file_shipped_at_v0_5_0() -> None:
    """Thirteen files: seven examples, five validation cases, the sweep base case."""
    assert len(CORPUS) == 13
    on_disk = sorted(
        path.relative_to(DATA / "corpus").as_posix()
        for path in (DATA / "corpus").rglob("*.case.yaml")
    )
    assert on_disk == list(CORPUS)
    assert GOLDEN["schema"] == CASE_SCHEMA_V1
    for relative in CORPUS:
        text = (DATA / "corpus" / relative).read_text(encoding="utf-8")
        assert yaml.safe_load(text)["schema"] == CASE_SCHEMA_V1, relative


@pytest.mark.parametrize("relative", CORPUS)
def test_ver47_the_recorded_keys_are_the_hashes_of_the_recorded_provenance(relative: str) -> None:
    """The decoded record is exactly what v1 keyed, so comparing against it is sound.

    Without this, a record that had drifted from its own digests — a float
    re-encoded, a key dropped on the way to JSON — would make the field-by-field
    comparison below compare against something v1 never hashed.
    """
    recorded = GOLDEN["cases"][relative]
    provenance = recorded["solve_provenance"]
    assert content_hash(SOLUTION_SCHEMA, provenance) == recorded["restore_digest"]
    assert _identity_of(provenance) == recorded["case_identity"]


@pytest.mark.parametrize("relative", CORPUS)
def test_ver47_the_v1_corpus_resolves_to_its_recorded_solve(relative: str) -> None:
    """Each v1 file, upgraded, resolves to the solve v1 recorded, less the schema string.

    The stage-8 materials key never saw the case schema and is required to be
    unchanged. The restore digest and the case identity are required to be the
    hashes of the recorded provenance with :data:`LEFT_THE_SOLVE_KEY` removed:
    the physics, the numerics and the discretisation of every corpus case are
    what v1 resolved them to, and only the schema string has left the key.
    """
    recorded = GOLDEN["cases"][relative]
    resolved = resolve(load_case(DATA / "corpus" / relative))

    assert LEFT_THE_SOLVE_KEY <= SOLVE_IRRELEVANT_PROVENANCE
    expected = {
        key: value
        for key, value in recorded["solve_provenance"].items()
        if key not in LEFT_THE_SOLVE_KEY
    }
    provenance = _decoded(resolved.solve_provenance)
    assert provenance == expected, _diff(expected, provenance)
    assert content_hash(SOLUTION_SCHEMA, resolved.solve_provenance) == content_hash(
        SOLUTION_SCHEMA, expected
    )
    assert case_identity(resolved) == _identity_of(expected)

    materials = MaterialsStage().run(StageInputs(case=resolved.document))
    assert materials.hash == recorded["materials_key"]


@pytest.mark.parametrize("relative", CORPUS)
def test_ver47_a_v1_file_and_its_v2_rewrite_are_one_case(relative: str) -> None:
    """The v1 file and the v2 text written from it share a stage-9 key and a resolved run."""
    upgraded = load_case(DATA / "corpus" / relative)
    rewritten = loads_case(dumps_case(upgraded), source=f"<{relative} as v2>")

    assert "schema: nanopnp/case/v2" in dumps_case(upgraded)
    assert rewritten.schema_id == CASE_SCHEMA
    assert CaseArtefact(rewritten).hash == CaseArtefact(upgraded).hash
    assert resolve(rewritten).provenance == resolve(upgraded).provenance


def test_ver47_the_v1_tree_maps_onto_v2_in_both_directions() -> None:
    """The frozen v1 field tree and the v2 walk differ by exactly the declared map.

    Forwards: v1, less what was renamed and moved, plus what was added and the
    rename targets, is v2. Backwards: v2, less what was added and the rename
    targets, plus what was renamed and moved, is v1. A key changed later without
    an entry in the map fails one direction or the other.
    """
    v2 = frozenset(reference.path for reference in case_fields())
    # An added block, such as inputs.profile, is walked into its fields.
    under = {
        prefix: frozenset(path for path in v2 if path == prefix or path.startswith(f"{prefix}."))
        for prefix in V2_ADDED
    }
    assert all(under.values()), [prefix for prefix, fields in under.items() if not fields]
    added = frozenset().union(*under.values())
    renamed_from = frozenset(V2_RENAMED)
    renamed_to = frozenset(V2_RENAMED.values())
    moved = frozenset(V2_MOVED)

    assert renamed_from | moved <= V1_FIELDS
    assert not (added | renamed_to) & V1_FIELDS
    assert (V1_FIELDS - renamed_from - moved) | added | renamed_to == v2
    assert (v2 - added - renamed_to) | renamed_from | moved == V1_FIELDS
    # Each moved value lands in the one mapping that holds a solid's permittivity.
    assert {target.rpartition(".")[0] for target in V2_MOVED.values()} == {
        "physics.solid_permittivities"
    }
    assert "physics.solid_permittivities" in v2


def test_ver47_the_case_stage_declares_the_schema_it_emits() -> None:
    """The stage registry names the schema the stage-9 artefact carries."""
    assert describe("case").artefact_schema == CASE_SCHEMA


# -- the upgrade ---------------------------------------------------------------

QUICKSTART = DATA / "corpus" / "examples" / "01-quickstart" / "quickstart.case.yaml"


def _v1() -> dict[str, Any]:
    """Return a runnable v1 document as parsed YAML, to be edited per test."""
    raw: dict[str, Any] = yaml.safe_load(QUICKSTART.read_text(encoding="utf-8"))
    return raw


def _v2() -> dict[str, Any]:
    """Return the same document as a v2 mapping."""
    return upgrade_v1(_v1())


def _text(raw: dict[str, Any]) -> str:
    """Return a mapping as case-file text."""
    return str(yaml.safe_dump(raw, sort_keys=False))


def test_ver47_a_written_permittivity_moves_and_an_unwritten_one_is_not_invented() -> None:
    """``charge.eps_protein`` and ``geometry.membrane.eps_r`` move into the map, as written."""
    raw = _v1()
    del raw["physics"]["solid_permittivities"]
    raw["charge"] = {"ph": 7.0, "eps_protein": 15.0}
    raw["geometry"] = {"membrane": {"thickness_nm": 3.0, "eps_r": 2.5}}
    raw["structure"] = {"source": {"pdb": "2WCD.pdb"}, "symmetry": {"point_group": "C12"}}
    before = copy.deepcopy(raw)

    document = loads_case(_text(raw))

    assert raw == before, "the upgrade must not modify the mapping it was given"
    assert document.physics.solid_permittivities == {"membrane": 2.5, "protein": 15.0}
    assert document.charge is not None
    assert document.charge.ph == 7.0
    assert document.geometry is not None
    assert document.geometry.membrane.thickness_nm == 3.0
    assert document.structure is not None
    assert document.structure.source.path == Path("2WCD.pdb")

    # The quick-start writes only the membrane; nothing adds the protein's 20.
    assert load_case(QUICKSTART).physics.solid_permittivities == {"membrane": 3.2}


def test_ver47_a_moved_permittivity_equal_to_the_map_is_accepted() -> None:
    """Writing the same value twice is redundant, not a conflict."""
    raw = _v1()
    raw["geometry"] = {"membrane": {"eps_r": 3.2}}
    assert loads_case(_text(raw)).physics.solid_permittivities == {"membrane": 3.2}


def _refusal_cases() -> list[Any]:
    """Return ``(id, document, exception, fragments)`` for every VER-47 refusal."""
    cases: list[Any] = []

    for path in (*V2_ADDED, *V2_RENAMED.values()):
        raw = _v1()
        cursor = raw
        *head, last = path.split(".")
        for component in head:
            cursor = cursor.setdefault(component, {})
        cursor[last] = {"path": "x"} if path.startswith("inputs.") else 1.0
        cases.append(
            pytest.param(
                raw, CaseValidationError, (path, CASE_SCHEMA_V1, CASE_SCHEMA), id=f"v1-{path}"
            )
        )

    raw = _v1()
    raw["charge"] = {"eps_protein": 15.0}
    raw["physics"]["solid_permittivities"] = {"membrane": 3.2, "protein": 20.0}
    cases.append(
        pytest.param(
            raw,
            CaseValidationError,
            ("charge.eps_protein", "physics.solid_permittivities.protein", "15.0", "20.0"),
            id="v1-disagreeing-protein",
        )
    )
    raw = _v1()
    raw["geometry"] = {"membrane": {"eps_r": 2.0}}
    cases.append(
        pytest.param(
            raw,
            CaseValidationError,
            ("geometry.membrane.eps_r", "physics.solid_permittivities.membrane", "2.0", "3.2"),
            id="v1-disagreeing-membrane",
        )
    )

    for old, new in (*V2_RENAMED.items(), *V2_MOVED.items()):
        raw = _v2()
        if old.startswith("structure."):
            raw["structure"] = {"source": {"path": "a.pdb"}, "symmetry": {"point_group": "C12"}}
        cursor = raw
        *head, last = old.split(".")
        for component in head:
            cursor = cursor.setdefault(component, {})
        cursor[last] = "b.pdb" if old.endswith("pdb") else 20.0
        cases.append(
            pytest.param(raw, CaseValidationError, (old, new, CASE_SCHEMA), id=f"v2-{old}")
        )

    raw = _v1()
    raw["schema"] = "nanopnp/case/v3"
    cases.append(
        pytest.param(
            raw,
            CaseValidationError,
            ("nanopnp/case/v3", CASE_SCHEMA, CASE_SCHEMA_V1),
            id="undeclared-schema",
        )
    )

    for upstream, downstream in (("profile", "mesh"), ("pqr", "charge")):
        raw = _v2()
        raw["inputs"][upstream] = {"path": f"supplied.{upstream}"}
        raw["inputs"][downstream] = {"path": f"supplied.{downstream}"}
        cases.append(
            pytest.param(
                raw,
                CaseValidationError,
                (f"inputs.{upstream}", f"inputs.{downstream}"),
                id=f"chain-{upstream}-{downstream}",
            )
        )

    raw = _v2()
    raw["numerics"]["mesh"] = {"size_scale": 0.5}
    cases.append(
        pytest.param(
            raw, CaseValidationError, ("numerics.mesh.size_scale", "inputs.mesh"), id="size-scale"
        )
    )

    for name in ("exclusion_offset_nm", "dielectric_transition_nm"):
        raw = _v2()
        raw["charge"] = {name: -0.1}
        cases.append(
            pytest.param(raw, CaseValidationError, (f"charge.{name}",), id=f"negative-{name}")
        )
        raw = _v2()
        raw["charge"] = {name: float("inf")}
        cases.append(
            pytest.param(raw, CaseValidationError, (f"charge.{name}",), id=f"infinite-{name}")
        )
    raw = _v2()
    del raw["inputs"]["mesh"]
    raw["numerics"]["mesh"] = {"size_scale": float("inf")}
    cases.append(
        pytest.param(raw, CaseValidationError, ("numerics.mesh.size_scale",), id="infinite-scale")
    )

    # v1 refused a null physics: block, so its upgrade must not make one up.
    raw = _v1()
    raw["physics"] = None
    raw["charge"] = {"eps_protein": 20.0}
    cases.append(
        pytest.param(
            raw,
            CaseValidationError,
            ("physics.solid_permittivities.protein", "physics is a NoneType"),
            id="v1-null-physics",
        )
    )
    return cases


@pytest.mark.parametrize(("raw", "error", "fragments"), _refusal_cases())
def test_ver47_refusals(
    raw: dict[str, Any], error: type[Exception], fragments: tuple[str, ...]
) -> None:
    """Each refusal of the upgrade and of the v2 key set names every key involved."""
    with pytest.raises(error) as caught:
        loads_case(_text(raw))
    message = str(caught.value)
    missing = [fragment for fragment in fragments if fragment not in message]
    assert not missing, f"{missing} not named in: {message}"


@pytest.mark.parametrize(
    ("supplied", "fragments"),
    [
        # inputs.profile left this table in WP21, when stage 5 began to read it;
        # tests/tier1/test_region.py covers its refusals.
        ("pqr", ("inputs.pqr", "stage 7", "Phase 3")),
    ],
)
def test_ver47_a_new_input_is_refused_naming_the_stage_that_would_read_it(
    supplied: str, fragments: tuple[str, ...]
) -> None:
    """``inputs.pqr`` validates, and is refused at resolution until Phase 3 reads it."""
    raw = _v2()
    raw["inputs"][supplied] = {"path": f"supplied.{supplied}"}
    document = loads_case(_text(raw))
    with pytest.raises(UnsupportedCaseSection) as caught:
        resolve(document)
    message = str(caught.value)
    assert all(fragment in message for fragment in fragments), message


# -- the two new switches -------------------------------------------------------


def test_ver47_the_new_switches_are_deviations() -> None:
    """A non-zero offset or width is a deviation; an absent ``charge:`` block is none."""
    assert deviations(load_case(QUICKSTART)) == ()

    raw = _v2()
    raw["charge"] = {"exclusion_offset_nm": 0.3}
    listed = {deviation.path: deviation for deviation in deviations(loads_case(_text(raw)))}
    assert set(listed) == {"charge.exclusion_offset_nm"}
    assert listed["charge.exclusion_offset_nm"].validated == 0.0
    assert listed["charge.exclusion_offset_nm"].value == 0.3

    raw["charge"] = {"dielectric_transition_nm": 0.2}
    listed = {deviation.path: deviation for deviation in deviations(loads_case(_text(raw)))}
    assert set(listed) == {"charge.dielectric_transition_nm"}

    raw["charge"] = {}
    assert deviations(loads_case(_text(raw))) == ()


# -- the supported interpreter range (QR-09, section 2.5) -----------------------

ROOT = Path(__file__).resolve().parents[2]


def _minor_versions(first: str, last: str) -> list[str]:
    """Return ``3.x`` strings from ``first`` to ``last`` inclusive."""
    low, high = (int(version.split(".")[1]) for version in (first, last))
    return [f"3.{minor}" for minor in range(low, high + 1)]


def _specified_range() -> list[str]:
    """Return the interpreters section 2.5 names, read from the specification."""
    text = (ROOT / "SPECIFICATION.md").read_text(encoding="utf-8")
    found = re.search(r"^\| Python \| (3\.\d+) to (3\.\d+)", text, flags=re.MULTILINE)
    assert found is not None, "section 2.5 no longer has a 'Python | 3.x to 3.y' row"
    return _minor_versions(found.group(1), found.group(2))


def _python_versions(node: object) -> set[str]:
    """Return every literal ``python-version`` under a workflow node."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "python-version":
                values = value if isinstance(value, list) else [value]
                found.update(str(item) for item in values if "${{" not in str(item))
            else:
                found |= _python_versions(value)
    elif isinstance(node, list):
        for item in node:
            found |= _python_versions(item)
    return found


def test_ver47_the_declared_python_range_agrees() -> None:
    """``requires-python``, the classifiers, ruff's target and the CI matrix all say 3.11-3.14.

    Four declarations of one fact drift apart one edit at a time; a floor raised
    in ``pyproject.toml`` with the CI matrix still running 3.10 tests an
    interpreter nobody supports, and the reverse ships one nobody tests.
    """
    specified = _specified_range()
    assert specified == ["3.11", "3.12", "3.13", "3.14"]
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    requires = SpecifierSet(project["project"]["requires-python"])
    admitted = [version for version in _minor_versions("3.8", "3.20") if f"{version}.0" in requires]
    assert admitted == specified, f"requires-python {requires} admits {admitted}"

    prefix = "Programming Language :: Python :: "
    classified = [
        entry.removeprefix(prefix)
        for entry in project["project"]["classifiers"]
        if entry.startswith(prefix) and entry.removeprefix(prefix).count(".") == 1
    ]
    assert classified == specified

    target = project["tool"]["ruff"]["target-version"]
    assert target == f"py{specified[0].replace('.', '')}"

    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    tested = _python_versions(workflow["jobs"]["check"]) | _python_versions(
        workflow["jobs"]["test-matrix"]
    )
    assert sorted(tested) == specified, f"CI tests {sorted(tested)}"
