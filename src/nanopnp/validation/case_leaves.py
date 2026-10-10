"""Classification of every case schema leaf by what reads it (WP42 D4, REV-12, VER-71).

Every leaf of the case schema is classified into exactly one kind, naming its
consumer stage or solve operator and why it is present. A leaf unread by the
selected model is refused away from its default.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

KINDS: tuple[str, ...] = (
    "solve",
    "solver",
    "stage",
    "post",
    "fixed",
    "checked",
    "provenance",
)


@dataclass(frozen=True)
class Leaf:
    """Classification record for a leaf in the case schema.

    Parameters
    ----------
    kind : str
        Classification kind from :data:`KINDS`.
    consumer : str
        Name of the stage or solver consuming this leaf, or empty string.
    reason : str
        Human-readable explanation of what reads or pins this leaf.
    """

    kind: str
    consumer: str
    reason: str


def unclassified(
    paths: Iterable[str], leaves: Mapping[str, Leaf]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Partition schema paths into missing and stale classifications.

    Parameters
    ----------
    paths : Iterable[str]
        Schema leaf paths to verify.
    leaves : Mapping[str, Leaf]
        Current leaf classification mapping.

    Returns
    -------
    tuple[tuple[str, ...], tuple[str, ...]]
        A pair ``(missing, stale)`` of sorted tuples, where ``missing`` contains
        paths present in `paths` but absent from `leaves`, and ``stale`` contains
        keys in `leaves` absent from `paths`.
    """
    path_set = set(paths)
    leaf_set = set(leaves)
    missing = tuple(sorted(path_set - leaf_set))
    stale = tuple(sorted(leaf_set - path_set))
    return missing, stale


LEAVES: dict[str, Leaf] = {
    # provenance (3)
    "schema": Leaf("provenance", "", "schema format identifier of the case file"),
    "name": Leaf("provenance", "", "human-readable run name recorded in manifest and provenance"),
    "structure.source.variant": Leaf(
        "provenance", "", "structure variant label recorded in provenance and ignored by keys"
    ),
    # solve (33)
    "physics.model": Leaf("solve", "solve", "selects the governing PDE system and its operators"),
    "boundary_conditions.bias_V": Leaf(
        "solve", "solve", "sets the electrostatic potential on the cis boundary"
    ),
    "boundary_conditions.ground": Leaf(
        "solve", "solve", "sets the grounded boundary for the electrostatic potential"
    ),
    "physics.flow": Leaf("solve", "solve", "switches fluid momentum coupling on or off"),
    "physics.variable_density": Leaf(
        "solve", "solve", "switches concentration-dependent fluid density on or off"
    ),
    "physics.inertia": Leaf("solve", "solve", "switches fluid inertial convection on or off"),
    "physics.dielectric_gradient_forces": Leaf(
        "solve", "solve", "switches dielectric gradient body force on or off"
    ),
    "physics.solid_permittivities": Leaf(
        "solve",
        "solve",
        "relative permittivities of solid domains in the electrostatic operator",
    ),
    "numerics.elements.phi": Leaf(
        "solve", "solve", "finite-element polynomial degree for electrostatic potential"
    ),
    "numerics.elements.c": Leaf(
        "solve", "solve", "finite-element polynomial degree for ion concentrations"
    ),
    "numerics.elements.u": Leaf(
        "solve", "solve", "finite-element polynomial degree for fluid velocity"
    ),
    "numerics.elements.p": Leaf(
        "solve", "solve", "finite-element polynomial degree for fluid pressure"
    ),
    "numerics.stabilisation": Leaf(
        "solve", "solve", "stabilisation method for advection-dominated transport"
    ),
    "numerics.wall_distance.sources": Leaf(
        "solve", "solve", "boundary tags used as sources for the wall distance field"
    ),
    "numerics.wall_distance.max_distance_nm": Leaf(
        "solve", "solve", "cutoff distance for the wall distance PDE"
    ),
    "electrolyte.concentration_M": Leaf(
        "solve", "solve", "reservoir bulk electrolyte concentration"
    ),
    "electrolyte.driver": Leaf(
        "solve", "solve", "governing concentration metric driving electrolyte property fits"
    ),
    "electrolyte.corrections.diffusivity.model": Leaf(
        "solve", "solve", "empirical model for concentration- and wall-dependent diffusivity"
    ),
    "electrolyte.corrections.diffusivity.concentration": Leaf(
        "solve", "solve", "toggles bulk concentration correction for diffusivity"
    ),
    "electrolyte.corrections.diffusivity.wall": Leaf(
        "solve", "solve", "toggles hydrodynamic wall correction for diffusivity"
    ),
    "electrolyte.corrections.mobility.model": Leaf(
        "solve", "solve", "empirical model for concentration- and wall-dependent ionic mobility"
    ),
    "electrolyte.corrections.mobility.concentration": Leaf(
        "solve", "solve", "toggles bulk concentration correction for mobility"
    ),
    "electrolyte.corrections.mobility.wall": Leaf(
        "solve", "solve", "toggles hydrodynamic wall correction for mobility"
    ),
    "electrolyte.corrections.viscosity.model": Leaf(
        "solve", "solve", "empirical model for concentration- and wall-dependent fluid viscosity"
    ),
    "electrolyte.corrections.viscosity.concentration": Leaf(
        "solve", "solve", "toggles bulk concentration correction for viscosity"
    ),
    "electrolyte.corrections.viscosity.wall": Leaf(
        "solve", "solve", "toggles hydrodynamic wall correction for viscosity"
    ),
    "electrolyte.corrections.permittivity.model": Leaf(
        "solve", "solve", "empirical model for concentration-dependent solvent permittivity"
    ),
    "electrolyte.corrections.permittivity.concentration": Leaf(
        "solve", "solve", "toggles bulk concentration correction for permittivity"
    ),
    "electrolyte.corrections.permittivity.wall": Leaf(
        "solve", "solve", "toggles wall correction for permittivity"
    ),
    "electrolyte.corrections.density.model": Leaf(
        "solve", "solve", "empirical model for concentration-dependent fluid density"
    ),
    "electrolyte.corrections.density.concentration": Leaf(
        "solve", "solve", "toggles bulk concentration correction for density"
    ),
    "electrolyte.corrections.density.wall": Leaf(
        "solve", "solve", "toggles wall correction for density"
    ),
    "electrolyte.corrections.steric.model": Leaf(
        "solve", "solve", "steric correction model modifying ion chemical potentials"
    ),
    # solver (4)
    "numerics.nonlinear.max_iter": Leaf(
        "solver", "solve", "maximum iterations for damped Newton solver"
    ),
    "numerics.nonlinear.rtol": Leaf(
        "solver", "solve", "relative convergence tolerance for damped Newton solver"
    ),
    "numerics.linear.solver": Leaf("solver", "solve", "backend linear solver for Jacobian systems"),
    "numerics.continuation": Leaf(
        "solver", "solve", "parameter continuation strategy across bias voltage rungs"
    ),
    # checked (2)
    "electrolyte.corrections.steric.a_ion_nm": Leaf(
        "checked", "", "effective ion diameter verified against steric model assumptions"
    ),
    "electrolyte.corrections.steric.a_water_nm": Leaf(
        "checked", "", "effective water diameter verified against steric model assumptions"
    ),
    # post (1)
    "outputs": Leaf(
        "post", "qoi", "requested scalar quantities of interest computed in post-processing"
    ),
    # fixed (12)
    "numerics.nonlinear.strategy": Leaf("fixed", "", "fixed to damped Newton in this release"),
    "numerics.nonlinear.damping": Leaf(
        "fixed", "", "fixed to geometric damping ladder in this release"
    ),
    "boundary_conditions.walls.ion_flux": Leaf(
        "fixed", "", "fixed to zero flux (blocking walls) in this release"
    ),
    "boundary_conditions.walls.slip": Leaf(
        "fixed", "", "fixed to no-slip at solid walls in this release"
    ),
    "charge.smearing.axis_cutoff_nm": Leaf(
        "fixed", "", "fixed to zero (no axis cutoff) in this release"
    ),
    "electrolyte.temperature_K": Leaf(
        "fixed", "", "fixed to 298.15 K (room temperature) in this release"
    ),
    "electrolyte.parameters": Leaf("fixed", "", "fixed to installed salt parameter file name"),
    "electrolyte.species.0.name": Leaf(
        "fixed", "", "species names fixed by the electrolyte parameter file"
    ),
    "electrolyte.species.0.z": Leaf(
        "fixed", "", "species valences fixed by the electrolyte parameter file"
    ),
    "inputs.mesh.artefact": Leaf("fixed", "", "supplied mesh by store hash deferred to v0.6"),
    "inputs.charge.artefact": Leaf(
        "fixed", "", "supplied charge field by store hash not scheduled"
    ),
    "inputs.eps_r.artefact": Leaf(
        "fixed", "", "supplied dielectric field by store hash not scheduled"
    ),
    # stage (50)
    # structure (8)
    "structure.source.path": Leaf(
        "stage", "structure", "atomic coordinate file ingested and aligned by stage 1"
    ),
    "structure.source.chains": Leaf(
        "stage", "structure", "chain selection for alignment and common index in stage 1"
    ),
    "structure.source.selection": Leaf(
        "stage", "structure", "atom selection query for alignment in stage 1"
    ),
    "structure.ensemble.trajectory": Leaf(
        "stage", "structure", "molecular dynamics trajectory file read by stage 1"
    ),
    "structure.ensemble.frames.last_ns": Leaf(
        "stage", "structure", "window duration for selecting trajectory frames in stage 1"
    ),
    "structure.ensemble.frames.count": Leaf(
        "stage", "structure", "number of evenly spaced trajectory frames in stage 1"
    ),
    "structure.symmetry.point_group": Leaf(
        "stage", "structure", "cyclic point group symmetry order for alignment in stage 1"
    ),
    "structure.symmetry.axis": Leaf(
        "stage", "structure", "symmetry axis mode applied during alignment in stage 1"
    ),
    # density (3)
    "geometry.density.grid_spacing_nm": Leaf(
        "stage", "density", "grid spacing for atomic density deposition in stage 2"
    ),
    "geometry.density.kernel": Leaf(
        "stage", "density", "smearing kernel function for atomic density in stage 2"
    ),
    "geometry.density.sharpness": Leaf(
        "stage", "density", "sharpness factor scaling atomic van der Waals radii in stage 2"
    ),
    # contour (3)
    "geometry.contour.isolevel": Leaf(
        "stage", "contour", "density isosurface level defining the pore surface in stage 4"
    ),
    "geometry.contour.smoothing": Leaf(
        "stage", "contour", "polyline smoothing algorithm for the pore contour in stage 4"
    ),
    "geometry.contour.simplify_tol_nm": Leaf(
        "stage", "contour", "simplification tolerance for contour vertices in stage 4"
    ),
    # region (13)
    "geometry.membrane.thickness_nm": Leaf(
        "stage", "region", "bilayer membrane slab thickness in stage 5 CAD assembly"
    ),
    "geometry.membrane.centre_z_nm": Leaf(
        "stage", "region", "bilayer membrane centre z coordinate in stage 5 CAD assembly"
    ),
    "geometry.reservoir.radius_nm": Leaf(
        "stage", "region", "trans and cis fluid reservoir radius in stage 5 CAD assembly"
    ),
    "geometry.analyte.shape": Leaf(
        "stage", "region", "analyte geometry shape refused in generated regions by stage 5"
    ),
    "geometry.analyte.a_nm": Leaf(
        "stage", "region", "analyte semi-axis a dimension refused in generated regions by stage 5"
    ),
    "geometry.analyte.b_nm": Leaf(
        "stage", "region", "analyte semi-axis b dimension refused in generated regions by stage 5"
    ),
    "geometry.analyte.z_nm": Leaf(
        "stage", "region", "analyte axial position z refused in generated regions by stage 5"
    ),
    "geometry.analyte.charge_e": Leaf(
        "stage", "region", "analyte total charge refused in generated regions by stage 5"
    ),
    "charge.exclusion_offset_nm": Leaf(
        "stage", "region", "exclusion shell standoff distance built into CAD region in stage 5"
    ),
    "inputs.profile.path": Leaf(
        "stage", "region", "supplied profile geometry file bypassing stages 1-4 in stage 5"
    ),
    "inputs.profile.format": Leaf(
        "stage", "region", "supplied profile file format verified in stage 5"
    ),
    "inputs.profile.groups": Leaf(
        "stage", "region", "boundary group mapping on supplied profile verified in stage 5"
    ),
    "inputs.profile.artefact": Leaf(
        "stage", "region", "supplied profile by store hash refused in stage 5"
    ),
    # mesh (7)
    "numerics.mesh.backend": Leaf("stage", "mesh", "meshing engine backend invoked in stage 6"),
    "numerics.mesh.wall_h_nm": Leaf(
        "stage", "mesh", "target mesh element size along pore walls in stage 6"
    ),
    "numerics.mesh.size_scale": Leaf(
        "stage", "mesh", "global mesh resolution scaling factor applied in stage 6"
    ),
    "numerics.mesh.boundary_layer": Leaf(
        "stage", "mesh", "boundary-layer prism extrusion refused in stage 6"
    ),
    "inputs.mesh.path": Leaf(
        "stage", "mesh", "supplied external finite-element mesh file read by stage 6"
    ),
    "inputs.mesh.format": Leaf(
        "stage", "mesh", "format specification of supplied mesh file read by stage 6"
    ),
    "inputs.mesh.groups": Leaf(
        "stage", "mesh", "boundary tag mapping from mesh vocabulary in stage 6"
    ),
    # protonation (7)
    "charge.ph": Leaf(
        "stage", "protonation", "solvent pH value driving PROPKA residue titration in stage 7"
    ),
    "charge.forcefield": Leaf(
        "stage",
        "protonation",
        "atom charge and radius parameter set used by PDB2PQR in stage 7",
    ),
    "charge.titration": Leaf("stage", "protonation", "titration scheme applied in stage 7"),
    "inputs.pqr.path": Leaf(
        "stage", "protonation", "supplied PQR atomic charge and radius file read by stage 7"
    ),
    "inputs.pqr.format": Leaf(
        "stage", "protonation", "supplied PQR file format verified by stage 7"
    ),
    "inputs.pqr.groups": Leaf(
        "stage", "protonation", "domain group mapping on supplied PQR verified by stage 7"
    ),
    "inputs.pqr.artefact": Leaf(
        "stage", "protonation", "supplied PQR by store hash refused by stage 7"
    ),
    # charge (9)
    "charge.smearing.sharpness": Leaf(
        "stage", "charge", "atomic charge smearing kernel sharpness in stage 7"
    ),
    "charge.smearing.grid_spacing_nm": Leaf(
        "stage", "charge", "lattice grid spacing for charge deposition in stage 7"
    ),
    "charge.dielectric_transition_nm": Leaf(
        "stage", "charge", "diffuse dielectric boundary layer transition width in stage 7"
    ),
    "inputs.charge.path": Leaf(
        "stage", "charge", "supplied fixed-charge density field file read by stage 7"
    ),
    "inputs.charge.format": Leaf(
        "stage", "charge", "file format for supplied fixed-charge field in stage 7"
    ),
    "inputs.charge.groups": Leaf(
        "stage", "charge", "domain group mapping for supplied charge field in stage 7"
    ),
    "inputs.eps_r.path": Leaf(
        "stage", "charge", "supplied relative permittivity field file read by stage 7"
    ),
    "inputs.eps_r.format": Leaf(
        "stage", "charge", "file format for supplied permittivity field in stage 7"
    ),
    "inputs.eps_r.groups": Leaf(
        "stage", "charge", "domain group mapping for supplied permittivity field in stage 7"
    ),
}
