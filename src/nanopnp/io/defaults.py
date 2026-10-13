"""The validated default configuration, and what it means to deviate from it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

from nanopnp.io.artefact import CASE_SCHEMA
from nanopnp.io.case import CaseDocument
from nanopnp.io.case_paths import UnknownCasePathError
from nanopnp.io.case_paths import value_at as case_value_at

SwitchValue: TypeAlias = Any

SWITCH_PATHS: tuple[str, ...] = (
    "physics.model",
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
    "physics.flow",
    "physics.variable_density",
    "physics.inertia",
    "physics.dielectric_gradient_forces",
    "boundary_conditions.walls.ion_flux",
    "boundary_conditions.walls.slip",
    # Floats, so the walk does not type them as switches; classified here by hand.
    "charge.exclusion_offset_nm",
    "charge.dielectric_transition_nm",
    # charge.ph is a condition of the experiment, as concentration_M is, and is not here.
    "charge.titration",
    "charge.forcefield",
    # w_i = 0.5 R_i: a float, classified by hand.
    "charge.smearing.sharpness",
    "numerics.stabilisation",
    "numerics.continuation",
    "numerics.nonlinear.strategy",
    "numerics.nonlinear.damping",
    "numerics.wall_distance.sources",
    # A float, classified by hand: below ~1 nm the wall functions no longer reach 1.
    "numerics.wall_distance.max_distance_nm",
    "numerics.linear.solver",
)

MODEL_SWITCH_PATHS: frozenset[str] = frozenset(
    {
        "physics.flow",
        "physics.variable_density",
        "physics.inertia",
        "physics.dielectric_gradient_forces",
        "electrolyte.corrections.steric.model",
    }
)

CONFIGURATION_PATHS: dict[str, str] = {
    "boundary_conditions.ground": (
        "which electrode is grounded is the operating point, not a model switch; it is "
        "recorded in the resolved case rather than as a deviation"
    ),
    "numerics.mesh.backend": (
        "the mesher is stage 6's choice (FR-10), recorded in the Geometry and mesh group of "
        "the manifest (section 5.3.3); it changes the discretisation, not the model"
    ),
    "numerics.mesh.boundary_layer": (
        "as numerics.mesh.backend: a discretisation choice, recorded with the mesh"
    ),
    "numerics.mesh.wall_h_nm": (
        "a mesh size in nm, or 'auto'; a discretisation choice like the two above, and "
        "the only reason it reads as a switch at all is the 'auto' literal"
    ),
    "structure.symmetry.axis": (
        "how stage 1 finds the axis, not a model term: z is admitted only inside the 0.01 nm "
        "displacement budget from the detected axis (section 5.3.1 NOTE on structure:)"
    ),
    "geometry.density.kernel": (
        "stage 2's kernel, which names its radius set; gaussian_vdw is the one kernel and "
        "is recorded with the density in the Geometry and mesh group (section 5.3.1 NOTE on "
        "geometry.density), so it is geometry input rather than a model switch"
    ),
    "geometry.contour.smoothing": (
        "stage 4's contour conditioning, which moves the wall by a few hundredths of a nm and "
        "is gated with the loop; it is recorded with the contour in the Geometry and mesh "
        "group (section 5.3.1 NOTE on geometry.contour), so it is geometry input rather than "
        "a model switch"
    ),
    "charge.smearing.grid_spacing_nm": (
        "the export lattice's spacing, on which stage 7 sums the kernel and takes the deposit's "
        "integrals; a discretisation choice recorded with the artefact, as "
        "numerics.mesh.size_scale is, and refused above half the narrowest kernel width "
        "(section 5.3.1 NOTE on charge.smearing)"
    ),
    "geometry.analyte.shape": (
        "the analyte body of stage 5 (FR-21): a generated region refuses it, so nothing reads "
        "it, and a supplied mesh carries its analyte already"
    ),
}

_VALIDATED_DEFAULTS: dict[str, Any] = {
    "schema": CASE_SCHEMA,
    "name": "validated-default",
    # The operating point below is arbitrary and never read: a case document cannot be built
    # without one, and only the paths of SWITCH_PATHS are compared.
    "inputs": {"mesh": {"path": "supplied.msh", "format": "msh41"}},
    "electrolyte": {
        "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
        "concentration_M": 1.0,
        "temperature_K": 298.15,
        "parameters": "willems2020_nacl",
        "driver": "average",
        "corrections": {
            "diffusivity": {"model": "willems2020_nacl", "concentration": True, "wall": True},
            "mobility": {"model": "willems2020_nacl", "concentration": True, "wall": True},
            "viscosity": {"model": "willems2020_nacl", "concentration": True, "wall": True},
            "permittivity": {"model": "willems2020_nacl", "concentration": True, "wall": True},
            "density": {"model": "willems2020_nacl", "concentration": True, "wall": True},
            "steric": {"model": "borukhov"},
        },
    },
    "boundary_conditions": {
        "bias_V": 0.1,
        "ground": "cis",
        "walls": {"ion_flux": "no_flux", "slip": "no_slip"},
    },
    # At its defaults so every switch path reads off this document, as without ``charge:``.
    "charge": {
        "titration": "propka",
        "forcefield": "CHARMM",
        "smearing": {"sharpness": 0.5},
        "exclusion_offset_nm": 0.0,
        "dielectric_transition_nm": 0.0,
    },
    "physics": {
        "model": "epnp-ns",
        "flow": True,
        "variable_density": True,
        "inertia": True,
        "dielectric_gradient_forces": False,
    },
    "numerics": {
        "elements": {"phi": "P2", "c": "P2", "u": "P2", "p": "P1"},
        "nonlinear": {"strategy": "newton", "damping": "residual"},
        "continuation": "default_ladder",
        "stabilisation": "none",
        "wall_distance": {"sources": "wall", "max_distance_nm": 3.0},
        "linear": {"solver": "umfpack"},
    },
}

VALIDATED_DEFAULT_CASE: CaseDocument = CaseDocument.model_validate(_VALIDATED_DEFAULTS)


@dataclass(frozen=True)
class Deviation:
    """One switch set away from the validated default."""

    path: str
    validated: SwitchValue
    value: SwitchValue

    def __str__(self) -> str:
        return f"{self.path}: {self.value!r}, validated default {self.validated!r}"

    def summary(self) -> dict[str, Any]:
        """Return the manifest's record of this deviation."""
        return {"path": self.path, "value": self.value, "validated_default": self.validated}


@dataclass(frozen=True)
class ContributedDeviation:
    """A deviation from the validated model that no case-file switch selects."""

    source: str
    description: str

    def __str__(self) -> str:
        return f"{self.source}: {self.description}"

    def summary(self) -> dict[str, Any]:
        """Return the manifest's record of this deviation."""
        return {"source": self.source, "description": self.description}


class UnknownSwitchPathError(KeyError):
    """A dotted path does not name a field of the case document."""


def value_at(document: CaseDocument, path: str) -> SwitchValue:
    """Return the value a dotted path names in a case document."""
    try:
        return case_value_at(document, path)
    except UnknownCasePathError as error:
        raise UnknownSwitchPathError(str(error)) from None


def deviations(document: CaseDocument) -> tuple[Deviation, ...]:
    """Return every switch this case sets away from the validated default, sorted by path."""
    found: list[Deviation] = []
    for path in SWITCH_PATHS:
        default = value_at(VALIDATED_DEFAULT_CASE, path)
        if _block_absent(document, path):
            continue
        value = value_at(document, path)
        if default != value:
            found.append(Deviation(path=path, validated=default, value=value))
    return tuple(sorted(found, key=lambda deviation: deviation.path))


def _block_absent(document: CaseDocument, path: str) -> bool:
    components = path.split(".")
    return any(
        value_at(document, ".".join(components[:depth])) is None
        for depth in range(1, len(components))
    )
