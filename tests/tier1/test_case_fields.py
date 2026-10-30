"""VER-43 — the one walk over ``nanopnp/case/v0.5``, and what is built on it."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields
from pathlib import Path

from pydantic import ValidationError

from nanopnp import Case, Session
from nanopnp.core.stages import create, describe
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import (
    CaseDocument,
    CaseValidationError,
    dump_case,
)
from nanopnp.io.case_paths import (
    NEUTRAL_SECTIONS,
    case_fields,
    with_section,
)
from nanopnp.io.defaults import CONFIGURATION_PATHS, SWITCH_PATHS
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import stored_upstream


def test_fr25_switch_paths_are_the_same_walk() -> None:
    walked = {reference.path for reference in case_fields()}
    unreachable = [path for path in (*SWITCH_PATHS, *CONFIGURATION_PATHS) if path not in walked]
    assert not unreachable, (
        f"{sorted(unreachable)} are classified by nanopnp.io.defaults but are not fields "
        "case_fields() yields, so the editor indexes the case differently from the manifest"
    )


def test_if09_the_walk_reaches_a_block_behind_an_optional_and_a_sequence() -> None:
    paths = {reference.path for reference in case_fields()}
    assert "geometry.analyte.shape" in paths
    assert "electrolyte.species.0.name" in paths


QUICKSTART = Path(__file__).parents[2] / "examples" / "01-quickstart" / "quickstart.case.yaml"
"""A supplied-mesh case: the one beside which ``geometry: {}`` is refused."""


def _optional_sections() -> tuple[str, ...]:
    return tuple(
        name
        for name, info in CaseDocument.model_fields.items()
        if not info.is_required() and info.default is None
    )


def _without(document: CaseDocument, name: str) -> CaseDocument:
    payload = document.model_dump(by_alias=True, mode="json")
    payload.pop(name, None)
    return CaseDocument.model_validate(payload)


def _resolution(document: CaseDocument) -> dict[str, object]:
    resolved = resolve(document)
    return {
        item.name: getattr(resolved, item.name)
        for item in fields(resolved)
        if item.name != "document"
    }


def _bases(directory: Path, write_tube: Callable[..., Path]) -> tuple[CaseDocument, ...]:
    return (load_case(QUICKSTART), load_case(write_tube(directory)))


def test_ver60_a_listed_section_resolves_empty_as_absent(tmp_path: Path, charged_tube) -> None:
    for base in _bases(tmp_path, charged_tube.write):
        for name in NEUTRAL_SECTIONS:
            absent = _without(base, name)
            added = with_section(absent, name)
            assert getattr(added, name) is not None
            assert _resolution(added) == _resolution(absent), (base.name, name)


def test_ver60_every_unlisted_optional_section_is_refused_empty_or_resolves_differently(
    tmp_path: Path, charged_tube
) -> None:
    for name in sorted(set(_optional_sections()) - NEUTRAL_SECTIONS):
        evidence: list[str] = []
        for base in _bases(tmp_path, charged_tube.write):
            payload = _without(base, name).model_dump(by_alias=True, mode="json")
            payload[name] = {}
            try:
                empty = CaseDocument.model_validate(payload)
                if _resolution(empty) != _resolution(_without(base, name)):
                    evidence.append(f"{base.name}: resolves differently")
            except (ValidationError, CaseValidationError) as error:
                evidence.append(f"{base.name}: refused ({type(error).__name__})")
        assert evidence, f"{name}: {{}} resolves as its absence on every base case; list it"


def test_ver60_an_empty_charge_section_keys_every_physics_stage_as_its_absence(
    tmp_path: Path, charged_tube
) -> None:
    absent = _without(load_case(charged_tube.write(tmp_path / "tube")), "charge")
    added = with_section(absent, "charge")
    store = Store(tmp_path / "store")
    # The solve's inputs, without the solve: the charge and the materials walks
    # between them cover every stage the solve reads.
    for upto in ("charge", "materials"):
        Session(store).run(Case.load(dump_case(absent, tmp_path / "absent.yaml")), upto=upto)

    def keys(document: CaseDocument) -> dict[str, str]:
        found = stored_upstream(document, store=store)
        found["solve"] = create("solve").key(  # type: ignore[attr-defined]
            StageInputs(resolved=resolve(document), upstream=dict(found))
        )
        return {name: artefact.hash for name, artefact in found.items()}

    before, after = keys(absent), keys(added)
    assert set(before) == set(after)
    assert {name for name in before if before[name] != after[name]} == {"case"}
    assert all(describe(name).number <= 10 for name in before)
