"""The FR-25 provenance manifest and the validated-default diff it rests on.

A manifest is only worth writing if a run can be reconstructed from it, and the
way that claim fails is not by being false but by being *incomplete*: a switch
nobody thought to enumerate is a switch the manifest never mentions, and the
result reads as though it were produced by the validated model when it was not.

So the load-bearing test here is not that a manifest can be built. It is
:func:`test_fr25_every_switch_typed_field_of_the_schema_is_classified`, which
walks the case schema itself and refuses any bool-or-``Literal`` leaf that is in
neither :data:`~nanopnp.io.defaults.SWITCH_PATHS` nor
:data:`~nanopnp.io.defaults.CONFIGURATION_PATHS`. Adding a switch to the schema
and forgetting the manifest then fails at Tier 1, in seconds, rather than in a
comparison against COMSOL six months later.

The second is
:func:`test_fr25_the_model_and_the_case_agree_on_the_switches_they_share`.
Section 5.4.1 forbids ``physics/`` from importing ``io/``, so
:class:`~nanopnp.physics.models.CoupledModel` enumerates its own deviations and
:func:`~nanopnp.io.defaults.deviations` enumerates the case's, independently.
Two independent computations of the same fact are only worth having if something
asserts they agree, and nothing else does.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal, get_args, get_origin

import pytest
from pydantic import BaseModel

from nanopnp.core.hashing import Canonicalisable
from nanopnp.io import manifest as manifest_module
from nanopnp.io.artefact import CaseArtefact
from nanopnp.io.case import CaseDocument, loads_case, resolve
from nanopnp.io.defaults import (
    CONFIGURATION_PATHS,
    MODEL_SWITCH_PATHS,
    SWITCH_PATHS,
    VALIDATED_DEFAULT_CASE,
    UnknownSwitchPathError,
    deviations,
    value_at,
)
from nanopnp.io.manifest import GROUPS, MANIFEST_SCHEMA, build, read
from nanopnp.physics.models import CoupledModel

MINIMAL = """
schema: nanopnp/case/v1
name: minimal
inputs: {mesh: {path: pore.vol, format: vol}}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {bias_V: 0.1}
physics: {model: pnp-ns}
numerics: {continuation: default_ladder}
"""


def _manifest(document: CaseDocument, **kwargs: Canonicalisable) -> manifest_module.Manifest:
    """Build a manifest for ``document`` with nothing but the case supplied."""
    artefact = CaseArtefact(document)
    return build(document, case_text=MINIMAL, case_hash=artefact.hash, **kwargs)


# -- the enumeration that keeps the manifest honest ---------------------------


def _switch_typed_leaves(model: type[BaseModel], prefix: str = "") -> set[str]:
    """Return the dotted paths of every switch-typed leaf of ``model``.

    Switch-typed means ``bool`` or carrying a ``Literal`` — the shapes a
    configuration flag takes in this schema. Free-form strings and numbers are
    not detected here and are covered instead by
    :func:`test_fr25_every_classified_path_still_names_a_field`, which walks the
    two mappings in the other direction.
    """
    found: set[str] = set()
    for name, info in model.model_fields.items():
        path = f"{prefix}{name}"
        annotation = info.annotation
        nested = [
            candidate
            for candidate in (annotation, *get_args(annotation))
            if isinstance(candidate, type) and issubclass(candidate, BaseModel)
        ]
        if nested:
            found |= _switch_typed_leaves(nested[0], f"{path}.")
            continue
        literal = get_origin(annotation) is Literal or any(
            get_origin(argument) is Literal for argument in get_args(annotation)
        )
        if annotation is bool or literal or name == "model":
            found.add(path)
    return found


def test_fr25_every_switch_typed_field_of_the_schema_is_classified() -> None:
    """No switch of the schema is in neither the deviation set nor the exempt set.

    FR-25 asks for "every switch set away from the validated default". A switch
    the enumeration has never heard of cannot appear in that list, and no other
    test would notice: the run converges, the manifest validates, and the number
    is attributed to the validated model.
    """
    classified = set(SWITCH_PATHS) | set(CONFIGURATION_PATHS)
    unclassified = _switch_typed_leaves(CaseDocument) - classified
    assert not unclassified, (
        f"{sorted(unclassified)} are switch-typed fields of nanopnp/case/v1 that are "
        "neither compared against the validated default (SWITCH_PATHS) nor exempted "
        "with a reason (CONFIGURATION_PATHS)"
    )


def _all_leaves(model: type[BaseModel], prefix: str = "") -> set[str]:
    """Return the dotted path of every leaf field of ``model``, of any type."""
    found: set[str] = set()
    for name, info in model.model_fields.items():
        path = f"{prefix}{name}"
        nested = [
            candidate
            for candidate in (info.annotation, *get_args(info.annotation))
            if isinstance(candidate, type) and issubclass(candidate, BaseModel)
        ]
        if nested:
            found |= _all_leaves(nested[0], f"{path}.")
        else:
            found.add(path)
    return found


def test_fr25_every_classified_path_still_names_a_field() -> None:
    """Both mappings name real fields, so a rename cannot leave a dead path behind.

    The other direction of the test above, and the one that covers the
    ``str``-typed switches — ``electrolyte.parameters`` and
    ``numerics.wall_distance.sources`` — that a type walk cannot recognise. It
    is asked of the schema rather than of a document because four of the exempt
    paths live under the optional ``structure:``, ``geometry:`` and ``charge:``
    blocks, which a Phase-1 case does not carry at all.
    """
    stale = (set(SWITCH_PATHS) | set(CONFIGURATION_PATHS)) - _all_leaves(CaseDocument)
    assert not stale, f"{sorted(stale)} name no field of nanopnp/case/v1"


def test_fr25_every_switch_path_reads_off_the_validated_default() -> None:
    """Every deviation path resolves on the validated default case itself.

    :func:`~nanopnp.io.defaults.deviations` reads each path off both documents;
    a path that named a block the default omits would raise mid-diff rather than
    report a deviation.
    """
    for path in SWITCH_PATHS:
        value_at(VALIDATED_DEFAULT_CASE, path)


def test_fr25_the_two_classifications_are_disjoint() -> None:
    """A path is a deviation or an exemption, never quietly both."""
    assert not set(SWITCH_PATHS) & set(CONFIGURATION_PATHS)


def test_fr25_an_unknown_path_is_refused_by_name() -> None:
    """A typo in a switch path fails loudly rather than reading as no deviation."""
    with pytest.raises(UnknownSwitchPathError, match=re.escape("physics.flowe")):
        value_at(VALIDATED_DEFAULT_CASE, "physics.flowe")


# -- the diff itself ----------------------------------------------------------


def test_fr25_the_validated_default_case_deviates_from_nothing() -> None:
    """The validated default is the origin of the diff (PHY-22, PHY-23)."""
    assert deviations(VALIDATED_DEFAULT_CASE) == ()


def test_fr25_a_disabled_correction_is_recorded_as_a_deviation() -> None:
    """Turning the viscosity correction off names the path, the value and the default."""
    document = VALIDATED_DEFAULT_CASE.model_copy(deep=True)
    document.electrolyte.corrections.viscosity.model = "none"
    found = {deviation.path: deviation for deviation in deviations(document)}
    assert "electrolyte.corrections.viscosity.model" in found
    recorded = found["electrolyte.corrections.viscosity.model"]
    assert recorded.value == "none"
    assert recorded.validated == "willems2020_nacl"


def test_fr25_the_model_and_the_case_agree_on_the_switches_they_share() -> None:
    """``CoupledModel``'s own record and the case's diff name the same switches.

    Section 5.4.1 keeps ``physics/`` from importing ``io/``, so these are two
    independent enumerations of the same set. They are only evidence of anything
    if they are asserted equal on the overlap; a model that renamed one switch,
    or a schema that moved one, would otherwise leave the manifest and the model
    quietly disagreeing about what was run.
    """
    document = VALIDATED_DEFAULT_CASE.model_copy(deep=True)
    document.physics.inertia = False
    document.physics.dielectric_gradient_forces = True
    document.electrolyte.corrections.steric.model = "none"

    resolved = resolve(document)
    model = CoupledModel(
        electrolyte=resolved.electrolyte,
        concentration_M=resolved.concentration_M,
        inertia=False,
        dielectric_gradient_forces=True,
    )
    from_model = set(model.provenance["deviations_from_validated_default"])
    from_case = {deviation.path for deviation in deviations(document)}
    assert from_model & MODEL_SWITCH_PATHS == from_case & MODEL_SWITCH_PATHS
    # And the overlap is not vacuously empty, which is how this test would rot.
    assert from_case & MODEL_SWITCH_PATHS == {
        "physics.inertia",
        "physics.dielectric_gradient_forces",
        "electrolyte.corrections.steric.model",
    }


# -- the eight groups ---------------------------------------------------------


def test_fr25_the_manifest_carries_all_eight_groups_of_section_5_3_3() -> None:
    """Every group of section 5.3.3 is present even when no stage produced it."""
    document = loads_case(MINIMAL)
    written = _manifest(document).document()
    for group in GROUPS:
        assert group in written, f"the manifest omits the {group!r} group"
    assert written["schema"] == MANIFEST_SCHEMA


def test_fr25_a_group_no_stage_produced_names_the_reason() -> None:
    """A not-run group says *why* rather than being dropped or left empty.

    An absent key and an empty object are both readable as "nothing to record".
    A status and a reason are not, and this is the difference between a Phase-1
    manifest that admits it had no charge pipeline and one that appears to have
    run with zero charge everywhere.
    """
    document = loads_case(MINIMAL)
    written = _manifest(document).document()
    for group in ("geometry_and_mesh", "charge", "materials"):
        block = written[group]
        assert isinstance(block, dict)
        assert block["status"] == "not run"
        assert block["reason"]


def test_fr25_the_solver_group_records_the_settings_and_the_run() -> None:
    """The solver group carries what was asked for and what happened."""
    document = loads_case(MINIMAL)
    ladder = {"rungs": [], "iterations": 12, "minimum_damping_used": 0.5}
    written = _manifest(document, ladder=ladder).document()
    solver = written["solver"]
    assert isinstance(solver, dict)
    assert solver["model"] == "pnp-ns"
    assert solver["continuation"] == "default_ladder"
    assert solver["run"]["iterations"] == 12


def test_fr25_stabilisation_is_recorded_with_the_number(tmp_path: Path) -> None:
    """The mode the solve actually ran under is recorded beside the requested one.

    Sections 6.4 and 7.4 make this load-bearing: the reference COMSOL model ran
    stabilised and ours does not, so a number without its mode is not comparable
    to it, and a number whose mode disagrees with the request is worse.
    """
    document = loads_case(MINIMAL)
    written = _manifest(document, stabilisation="reference").document()
    block = written["stabilisation"]
    assert isinstance(block, dict)
    assert block["requested"] == "none"
    assert block["mode"] == "reference"
    assert block["matches_requested"] is False


def test_fr25_deviations_reach_the_manifest_by_path() -> None:
    """The Deviations group carries the same paths the diff produced."""
    document = loads_case(MINIMAL)
    written = _manifest(document).document()
    block = written["deviations"]
    assert isinstance(block, dict)
    paths = {switch["path"] for switch in block["switches"]}
    assert paths == {deviation.path for deviation in deviations(document)}
    assert block["count"] == len(paths)
    # ``pnp-ns`` with the schema's default corrections is a long way from the
    # validated model, and the manifest must say so rather than imply otherwise.
    assert "physics.model" in paths


# -- writing, reading and the environment -------------------------------------


def test_fr26_the_manifest_round_trips_with_the_case_beside_it(tmp_path: Path) -> None:
    """Written and read back, the manifest is unchanged and carries the case verbatim."""
    document = loads_case(MINIMAL)
    built = _manifest(document)
    written_path = built.write(tmp_path)
    restored = read(written_path)

    assert restored["hash"] == built.hash
    case = restored["case"]
    assert isinstance(case, dict)
    assert case["text"] == MINIMAL
    # The case beside the manifest re-validates, which is the half of FR-26 the
    # hash cannot express: a manifest whose case no longer parses reconstructs
    # nothing.
    assert loads_case(str(case["text"])).name == document.name


def test_fr25_the_environment_group_names_versions_without_importing_ngsolve() -> None:
    """``environment()`` reports NGSolve's version without importing NGSolve.

    ``importlib.metadata`` reads distribution metadata off disk. That is why the
    manifest can be assembled in the CLI and the sweep runner — which introspect
    stages without ever assembling a form — at no import cost. Asserting it in a
    subprocess is the only way to assert it at all: this test session has NGSolve
    imported many times over.
    """
    script = (
        "import sys, json;"
        "from nanopnp.io.manifest import environment;"
        "group = environment();"
        "print(json.dumps({'ngsolve': 'ngsolve' in sys.modules,"
        " 'version': group['packages']['ngsolve']}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    reported = json.loads(completed.stdout)
    assert reported["ngsolve"] is False
    assert reported["version"]
