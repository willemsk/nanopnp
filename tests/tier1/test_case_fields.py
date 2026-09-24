"""VER-43 — the one walk over ``nanopnp/case/v2``, and what is built on it.

:func:`~nanopnp.io.case.case_fields` is what makes the desktop editor *generated*
rather than hand-written (IF-09), and it is also what the FR-25 switch
classification is checked against. Both directions matter, and they fail
differently.

A path the walk yields that :func:`~nanopnp.io.case.field_at` cannot resolve is
an editor offering a field nothing can read or write. A field of the schema the
walk *misses* is worse and quieter: it becomes silently uneditable, and — because
:mod:`nanopnp.io.defaults`'s enumeration is checked against this same walk — it
also becomes a switch the FR-25 manifest never mentions, so a result reads as
though it came from the validated model when it did not.

So the oracle here is an explicit frozen list rather than a second walk. A second
walk would agree with the first for the same wrong reason; a written-out list is
the only thing that fails when a field is added to the schema and forgotten
everywhere else, and the failure names it.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from nanopnp.io.case import _walk_fields, case_fields, field_at
from nanopnp.io.defaults import CONFIGURATION_PATHS, SWITCH_PATHS

SCHEMA_PATHS: tuple[str, ...] = (
    "schema",
    "name",
    "inputs.mesh.path",
    "inputs.mesh.artefact",
    "inputs.mesh.format",
    "inputs.mesh.groups",
    "inputs.charge.path",
    "inputs.charge.artefact",
    "inputs.charge.format",
    "inputs.charge.groups",
    "inputs.eps_r.path",
    "inputs.eps_r.artefact",
    "inputs.eps_r.format",
    "inputs.eps_r.groups",
    "inputs.profile.path",
    "inputs.profile.artefact",
    "inputs.profile.format",
    "inputs.profile.groups",
    "inputs.pqr.path",
    "inputs.pqr.artefact",
    "inputs.pqr.format",
    "inputs.pqr.groups",
    "structure.source.path",
    "structure.source.variant",
    "structure.source.chains",
    "structure.source.selection",
    "structure.ensemble.trajectory",
    "structure.ensemble.frames.last_ns",
    "structure.ensemble.frames.count",
    "structure.symmetry.point_group",
    "structure.symmetry.axis",
    "geometry.density.grid_spacing_nm",
    "geometry.density.kernel",
    "geometry.density.sharpness",
    "geometry.contour.isolevel",
    "geometry.contour.smoothing",
    "geometry.contour.simplify_tol_nm",
    "geometry.membrane.thickness_nm",
    "geometry.membrane.centre_z_nm",
    "geometry.reservoir.radius_nm",
    "geometry.analyte.shape",
    "geometry.analyte.a_nm",
    "geometry.analyte.b_nm",
    "geometry.analyte.z_nm",
    "geometry.analyte.charge_e",
    "charge.ph",
    "charge.forcefield",
    "charge.titration",
    "charge.smearing.sharpness",
    "charge.smearing.grid_spacing_nm",
    "charge.smearing.axis_cutoff_nm",
    "charge.exclusion_offset_nm",
    "charge.dielectric_transition_nm",
    "electrolyte.species.0.name",
    "electrolyte.species.0.z",
    "electrolyte.concentration_M",
    "electrolyte.temperature_K",
    "electrolyte.parameters",
    "electrolyte.driver",
    "electrolyte.corrections.diffusivity.model",
    "electrolyte.corrections.diffusivity.concentration",
    "electrolyte.corrections.diffusivity.wall",
    "electrolyte.corrections.mobility.model",
    "electrolyte.corrections.mobility.concentration",
    "electrolyte.corrections.mobility.wall",
    "electrolyte.corrections.viscosity.model",
    "electrolyte.corrections.viscosity.concentration",
    "electrolyte.corrections.viscosity.wall",
    "electrolyte.corrections.permittivity.model",
    "electrolyte.corrections.permittivity.concentration",
    "electrolyte.corrections.permittivity.wall",
    "electrolyte.corrections.density.model",
    "electrolyte.corrections.density.concentration",
    "electrolyte.corrections.density.wall",
    "electrolyte.corrections.steric.model",
    "electrolyte.corrections.steric.a_ion_nm",
    "electrolyte.corrections.steric.a_water_nm",
    "boundary_conditions.bias_V",
    "boundary_conditions.ground",
    "boundary_conditions.walls.ion_flux",
    "boundary_conditions.walls.slip",
    "physics.model",
    "physics.flow",
    "physics.variable_density",
    "physics.inertia",
    "physics.dielectric_gradient_forces",
    "physics.solid_permittivities",
    "numerics.elements.phi",
    "numerics.elements.c",
    "numerics.elements.u",
    "numerics.elements.p",
    "numerics.mesh.backend",
    "numerics.mesh.wall_h_nm",
    "numerics.mesh.size_scale",
    "numerics.mesh.boundary_layer",
    "numerics.nonlinear.strategy",
    "numerics.nonlinear.damping",
    "numerics.nonlinear.max_iter",
    "numerics.nonlinear.rtol",
    "numerics.continuation",
    "numerics.stabilisation",
    "numerics.wall_distance.sources",
    "numerics.wall_distance.max_distance_nm",
    "numerics.linear.solver",
    "outputs",
)
"""Every editable field of ``nanopnp/case/v2``, in declaration order.

Written out rather than computed. A field added to the schema and forgotten
elsewhere fails the test below naming itself, which is the whole point; a field
*removed* fails it too, which is what stops a rename from leaving the editor
and the manifest pointing at nothing.
"""


def test_if09_case_fields_enumerates_the_whole_schema() -> None:
    """The walk is exactly the frozen list, in order, and every path resolves.

    Both directions in one assertion: an extra path and a missing one are the
    same equality failure, and the diff names whichever it was.
    """
    found = case_fields()
    assert tuple(reference.path for reference in found) == SCHEMA_PATHS


def test_if09_every_walked_field_is_the_one_field_at_resolves() -> None:
    """``case_fields()`` and ``field_at`` agree on every field, object for object.

    The annotation and the container kind, not only the path: an editor that
    took the declared type from one walker and the container kind from another
    could offer a mapping entry where the schema declares a block.
    """
    for reference in case_fields():
        assert field_at(reference.path) == reference


def test_if09_case_fields_refuses_a_mapping_of_blocks() -> None:
    """A mapping of blocks is refused by name rather than walked past.

    ``nanopnp/case/v2`` has none today. If one is added there is no
    representative key to stand on the way ``0`` stands on a sequence index, so
    the walk must say so: omitting the block's fields would make them silently
    uneditable *and* silently unclassified by FR-25, which is the failure this
    whole module exists to prevent.
    """

    class _Entry(BaseModel):
        value: float = 0.0

    class _Block(BaseModel):
        entries: dict[str, _Entry] = {}

    with pytest.raises(NotImplementedError, match="mapping of _Entry blocks"):
        _walk_fields(_Block, "")


# -- FR-25: the editor and the manifest index the case by the same paths -----


def test_fr25_switch_paths_are_the_same_walk() -> None:
    """Every FR-25 switch is a field the generated editor reaches, by that path.

    ``tests/tier1/test_manifest.py`` asserts the classification is complete
    against this walk, in both directions; what is asserted here is the other
    half of "one walker, not two" — that the paths
    :mod:`nanopnp.io.defaults` compares against the validated default are paths
    the editor itself enumerates and can therefore set.

    A switch the editor offered under some other path would be a switch the
    user could change and the FR-25 manifest would not report, which is exactly
    the manifest describing a run that never happened (§5.3.3).
    """
    walked = {reference.path for reference in case_fields()}
    unreachable = [path for path in (*SWITCH_PATHS, *CONFIGURATION_PATHS) if path not in walked]
    assert not unreachable, (
        f"{sorted(unreachable)} are classified by nanopnp.io.defaults but are not fields "
        "case_fields() yields, so the editor indexes the case differently from the manifest"
    )


def test_if09_the_walk_reaches_a_block_behind_an_optional_and_a_sequence() -> None:
    """Optional blocks and sequences of blocks are walked through, not around.

    ``geometry.analyte`` is ``AnalyteSpec | None`` and ``electrolyte.species``
    is ``list[SpeciesSpec]``; a walk that stopped at either would leave a whole
    block of the schema uneditable, and the frozen list above is the only thing
    that would notice.
    """
    paths = {reference.path for reference in case_fields()}
    assert "geometry.analyte.shape" in paths
    assert "electrolyte.species.0.name" in paths
