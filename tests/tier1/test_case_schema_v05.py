"""G6 (WP42 D9, D10) — the first move of the case schema, to ``nanopnp/case/v0.5``.

WP42 narrows what a case may say: a value its model never applies is refused
(D3, D5, D6). A narrowing moves the schema (§5.3.1 NOTE on the compatibility
rule), and a document declaring an earlier identifier is read as its upgrade.
The upgrade carries exactly what it can: a switch the document left at a v2
default its model never applied is read as the value the model honours, and
logged; a value the document *wrote* is refused, because its author believed it
applied, and the refusal names the migration (§8.2.7 G6).
"""

from __future__ import annotations

import logging

import pytest

PNP = """
schema: {schema}
name: upgrade
inputs: {{mesh: {{path: absent.msh, format: msh41}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp, flow: false{switches}, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: none}}
outputs: [current]
"""

CLASSICAL = """
schema: {schema}
name: upgrade
inputs: {{mesh: {{path: absent.msh, format: msh41}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
  corrections: {{diffusivity: {{model: willems2020_nacl}}}}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: none}}
"""

MIGRATION = (
    "\nThis document declares 'nanopnp/case/v2' and is read as its 'nanopnp/case/v0.5' "
    "upgrade; CHANGELOG.md, 'Migrating a nanopnp/case/v2 document', lists what v0.5 refuses "
    "that v2 accepted"
)
"""WP42 *Design* §5: the line a refusal of an upgraded document ends with."""

WRITTEN = ", variable_density: false, inertia: false"


@pytest.mark.xfail(strict=True, reason="planned: WP42 D9")
def test_g6_the_schema_is_v05_and_names_the_identifiers_it_upgrades() -> None:
    """The identifier names the release that ships the move; v2 and v1 are its upgrades."""
    from nanopnp.io.artefact import CASE_SCHEMA, CASE_SCHEMA_V1, CASE_SCHEMA_V2
    from nanopnp.io.defaults import VALIDATED_DEFAULT_CASE

    assert CASE_SCHEMA == "nanopnp/case/v0.5"
    assert CASE_SCHEMA_V2 == "nanopnp/case/v2"
    assert CASE_SCHEMA_V1 == "nanopnp/case/v1"
    assert VALIDATED_DEFAULT_CASE.schema_id == "nanopnp/case/v0.5"


@pytest.mark.xfail(strict=True, reason="planned: WP42 D9")
def test_g6_a_v05_document_reads_as_itself() -> None:
    """A document declaring the current identifier is not an upgrade."""
    from nanopnp.pipeline.case import loads_case

    document = loads_case(PNP.format(schema="nanopnp/case/v0.5", switches=WRITTEN))
    assert document.schema_id == "nanopnp/case/v0.5"
    assert document.upgraded_from is None


@pytest.mark.xfail(strict=True, reason="planned: WP42 D9")
def test_g6_an_unknown_identifier_is_refused_naming_the_three_it_reads() -> None:
    """A future identifier fails naming the schema it claims, before any field error."""
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case

    with pytest.raises(CaseValidationError) as raised:
        loads_case(PNP.format(schema="nanopnp/case/v0.6", switches=WRITTEN))
    assert str(raised.value) == (
        "<string>: expected schema 'nanopnp/case/v0.5', or 'nanopnp/case/v2' or "
        "'nanopnp/case/v1' (each read as its upgrade), found 'nanopnp/case/v0.6'"
    )


@pytest.mark.xfail(strict=True, reason="planned: WP42 D10")
def test_g6_a_v2_pnp_document_carries_the_switches_its_model_honours(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Left at v2's default, ``variable_density`` and ``inertia`` are read as false, and logged.

    The carried document is the v0.5 document an author would write by hand: the
    two hash the same, so a stored solve of either serves the other.
    """
    from nanopnp.io.artefact import CaseArtefact
    from nanopnp.pipeline.case import loads_case, resolve

    with caplog.at_level(logging.INFO, logger="nanopnp.pipeline.checks"):
        carried = loads_case(PNP.format(schema="nanopnp/case/v2", switches=""))
    assert [record.getMessage() for record in caplog.records] == [
        f"<string>: physics.{name} is not written; its 'nanopnp/case/v2' default true was "
        f"never applied by physics.model 'pnp', so it is read as false, the value the model "
        "honours (CHANGELOG.md, 'Migrating a nanopnp/case/v2 document')"
        for name in ("variable_density", "inertia")
    ]
    assert carried.upgraded_from == "nanopnp/case/v2"
    assert carried.schema_id == "nanopnp/case/v0.5"
    assert carried.physics.variable_density is False
    assert carried.physics.inertia is False
    written = loads_case(PNP.format(schema="nanopnp/case/v0.5", switches=WRITTEN))
    assert CaseArtefact(carried).hash == CaseArtefact(written).hash
    options = resolve(carried).model_options
    assert options["variable_density"] is False
    assert options["inertia"] is False


@pytest.mark.xfail(strict=True, reason="planned: WP42 D10")
def test_g6_a_v2_document_that_wrote_an_unapplied_switch_is_refused_naming_the_migration() -> None:
    """A written ``variable_density: true`` under ``pnp`` was the author's belief; not carried."""
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case, resolve

    text = PNP.format(schema="nanopnp/case/v2", switches=", variable_density: true")
    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(text))
    assert str(raised.value) == (
        "physics.model 'pnp' honours physics.variable_density: false only (PHY-21), so "
        "physics.variable_density must be false; true would be recorded in the manifest and "
        "never applied. Models honouring true: epnp-ns, pnp-ns" + MIGRATION
    )


@pytest.mark.xfail(strict=True, reason="planned: WP42 D10")
def test_g6_a_v2_document_that_wrote_an_unread_leaf_is_refused_naming_the_migration() -> None:
    """A ``pnp-ns`` case that wrote a correction was solved classical under v2; v0.5 says so."""
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case, resolve

    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(CLASSICAL.format(schema="nanopnp/case/v2")))
    assert str(raised.value) == (
        "physics.model 'pnp-ns' does not read 1 key this case sets; it would be recorded in the "
        "manifest and never applied (PHY-21, section 5.4.3), so leave it at its default:\n"
        "  electrolyte.corrections.diffusivity.model: willems2020_nacl (default none; read by "
        "epnp-ns, pnp)" + MIGRATION
    )


@pytest.mark.xfail(strict=True, reason="planned: WP42 D10")
def test_g6_a_v05_document_is_refused_without_the_migration_line() -> None:
    """The same refusal of a v0.5 document has no upgrade to point at."""
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case, resolve

    with pytest.raises(CaseValidationError) as raised:
        resolve(loads_case(PNP.format(schema="nanopnp/case/v0.5", switches="")))
    assert str(raised.value) == (
        "physics.model 'pnp' honours physics.variable_density: false only (PHY-21), so "
        "physics.variable_density must be false; true would be recorded in the manifest and "
        "never applied. Models honouring true: epnp-ns, pnp-ns"
    )


@pytest.mark.xfail(strict=True, reason="planned: WP42 D10")
def test_g6_a_v1_document_reads_through_both_upgrades() -> None:
    """v1 is rewritten to v2, then carried to v0.5; it remembers the identifier it declared."""
    from nanopnp.pipeline.case import loads_case

    document = loads_case(PNP.format(schema="nanopnp/case/v1", switches=""))
    assert document.schema_id == "nanopnp/case/v0.5"
    assert document.upgraded_from == "nanopnp/case/v1"
    assert document.physics.variable_density is False


@pytest.mark.xfail(strict=True, reason="planned: WP42 D10")
def test_g6_the_upgrade_mark_survives_a_copy() -> None:
    """A swept or edited copy of an upgraded document is still an upgraded document."""
    from nanopnp.pipeline.case import loads_case

    document = loads_case(PNP.format(schema="nanopnp/case/v2", switches=WRITTEN))
    copied = document.model_copy(update={"name": "copied"})
    assert copied.upgraded_from == "nanopnp/case/v2"
