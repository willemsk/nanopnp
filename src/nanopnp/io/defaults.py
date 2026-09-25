"""The validated default configuration, and what it means to deviate from it.

Section 5.3.3 requires the provenance manifest to record "every switch set away
from the validated default", and PHY-22 fixes what those defaults are. This
module holds them as a case document and the diff as a walk over an enumerated
set of paths.

It is not a ``model_dump(exclude_defaults=True)``. The pydantic field defaults of
:class:`~nanopnp.io.case.CorrectionsSpec` are ``model: none`` — the *classical*
configuration, because ``CorrectionSwitches()`` constructs every correction off —
so a default-diff would report the validated ePNP-NS configuration as nine
deviations and classical PNP-NS as none, exactly backwards.

What keeps the enumeration honest is not the walk but the test:
``tests/tier1/test_manifest.py`` enumerates every switch-typed field in the
schema tree and asserts each one appears either in :data:`SWITCH_PATHS` or in
:data:`CONFIGURATION_PATHS` with a reason. A switch added in a later work package
without a validated default fails Tier 1 rather than silently vanishing from the
manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeAlias

from nanopnp.io.artefact import CASE_SCHEMA
from nanopnp.io.case import CaseDocument, UnknownCasePathError
from nanopnp.io.case import value_at as case_value_at

SwitchValue: TypeAlias = Any
"""The value of one switch: a ``bool``, a correction model name, a solver
strategy, or a numeric threshold such as ``max_distance_nm``. The schema
constrains each field, but a walk over dotted paths sees the union of them,
so the alias names what the value *is* where the checker can only say ``Any``
(the house convention of :mod:`nanopnp.core.typing`)."""

SWITCH_PATHS: tuple[str, ...] = (
    # PHY-21: the named physics model.
    "physics.model",
    # PHY-22: the five property corrections, each with its two independently
    # switchable parts, and the steric flux.
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
    # PHY-22, PHY-23: the flow terms and the opt-in dielectric-gradient forces.
    "physics.flow",
    "physics.variable_density",
    "physics.inertia",
    "physics.dielectric_gradient_forces",
    # Section 6.2: the conditions the reference model applied on the walls.
    "boundary_conditions.walls.ion_flux",
    "boundary_conditions.walls.slip",
    # FR-15, PHY-20: the exclusion offset and the dielectric transition width,
    # both 0 in the validated model (section 5.3.1 NOTE on the v2 keys that
    # change a number). Floats, so the walk does not type them as switches;
    # they are classified here by hand.
    "charge.exclusion_offset_nm",
    "charge.dielectric_transition_nm",
    # NUM-11, NUM-16, NUM-18, PHY-02, CON-11.
    "numerics.stabilisation",
    "numerics.continuation",
    "numerics.nonlinear.strategy",
    "numerics.nonlinear.damping",
    "numerics.wall_distance.sources",
    "numerics.linear.solver",
)
"""Every switch with a validated default, by dotted path into the case document."""

MODEL_SWITCH_PATHS: frozenset[str] = frozenset(
    {
        "physics.flow",
        "physics.variable_density",
        "physics.inertia",
        "physics.dielectric_gradient_forces",
        "electrolyte.corrections.steric.model",
    }
)
"""The subset of :data:`SWITCH_PATHS` a :class:`~nanopnp.physics.models.CoupledModel`
carries itself.

``physics/`` must not import ``io/`` (section 5.4.1), so ``CoupledModel._deviations``
enumerates these independently and ``tests/tier1/test_manifest.py`` asserts the two
agree on exactly this set. It is the overlap, not the whole: the correction models,
the solver settings and the boundary conditions are the case's, not the model's."""

CONFIGURATION_PATHS: dict[str, str] = {
    "boundary_conditions.ground": (
        "which electrode is grounded is the operating point, not a model switch; it is "
        "recorded in the resolved case rather than as a deviation"
    ),
    "numerics.mesh.backend": (
        "mesh generation is v0.9 and is recorded in the Geometry and mesh group of the "
        "manifest (section 5.3.3); it changes the discretisation, not the model"
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
    "geometry.density.kernel": "v0.9; resolve() refuses a case carrying a geometry: section",
    "geometry.contour.smoothing": "v0.9; resolve() refuses a case carrying a geometry: section",
    "geometry.analyte.shape": "v0.9; resolve() refuses a case carrying a geometry: section",
    "charge.titration": "v0.9; resolve() refuses a case carrying a charge: section",
}
"""Switch-typed fields that are deliberately *not* deviations, each with its reason.

A field here is one a run may set freely without the manifest calling it a
deviation from the validated model. The reason is required, and the Tier-1
enumeration test refuses a field that is in neither this mapping nor
:data:`SWITCH_PATHS` — which is what stops "not a deviation" from becoming a
place to put switches nobody wanted to think about.
"""

_VALIDATED_DEFAULTS: dict[str, Any] = {
    "schema": CASE_SCHEMA,
    "name": "validated-default",
    # The operating point below is arbitrary and is never read: only the paths of
    # SWITCH_PATHS are compared against this document. It is here because a case
    # document cannot be constructed without one.
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
    # Present at its defaults so that every switch path reads off this document;
    # a case without a charge: block reads the same values (see deviations()).
    "charge": {"exclusion_offset_nm": 0.0, "dielectric_transition_nm": 0.0},
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
"""The validated ePNP-NS configuration of PHY-21 and PHY-22, as a case document.

Every correction on against ``willems2020_nacl``, both parts of each; the steric
flux on; variable-density flow and inertia on; the dielectric-gradient forces off
(PHY-23); unstabilised (NUM-11); the NUM-16 Newton policy; the NUM-18 ladder; the
PHY-02 distance field measured from the pore wall alone; UMFPACK (CON-11 as
amended); no exclusion shell and a sharp material permittivity (FR-15, PHY-20).

It carries a ``charge:`` block, which :func:`~nanopnp.io.case.resolve` refuses in
this release: the document is read path by path and never resolved.
"""


@dataclass(frozen=True)
class Deviation:
    """One switch set away from the validated default (FR-25, section 5.3.3)."""

    path: str
    validated: SwitchValue
    value: SwitchValue

    def __str__(self) -> str:
        """Render the deviation as the manifest and the log report it."""
        return f"{self.path}: {self.value!r}, validated default {self.validated!r}"

    def summary(self) -> dict[str, Any]:
        """Return the manifest's record of this deviation."""
        return {"path": self.path, "value": self.value, "validated_default": self.validated}


@dataclass(frozen=True)
class ContributedDeviation:
    """A deviation from the validated model that no case-file switch selects.

    Some departures are not configuration. An ingested mesh carrying the
    ``exclusion`` material puts a Stern layer in a model that has none, and a
    supplied ``inputs.eps_r`` smooths a permittivity PHY-20 assigns as a constant
    per domain; both are set by the *input*, not by a switch, so the diff of
    :func:`deviations` cannot see either and the stage that read them must say so
    (FR-25, §5.3.3).

    Deliberately not given a fabricated dotted path. A path implies a key a
    reader could set, and inventing one would make the manifest describe a case
    file that does not exist.

    Parameters
    ----------
    source
        What carries the deviation: ``inputs.eps_r``, ``mesh material
        'exclusion'``.
    description
        What departs from the validated model, and which clause says so.
    """

    source: str
    description: str

    def __str__(self) -> str:
        """Render the deviation as the manifest and the log report it."""
        return f"{self.source}: {self.description}"

    def summary(self) -> dict[str, Any]:
        """Return the manifest's record of this deviation."""
        return {"source": self.source, "description": self.description}


class UnknownSwitchPathError(KeyError):
    """A dotted path does not name a field of the case document."""


def value_at(document: CaseDocument, path: str) -> SwitchValue:
    """Return the value a dotted path names in a case document.

    A thin translation over :func:`nanopnp.io.case.value_at`, which walks the
    *schema* first and only then the document. One walker rather than two: the
    enumeration here and the sweep axes of FR-24 name paths in the same
    vocabulary, and two implementations of "what does this path mean" could
    disagree about a field this module then reported as never deviating.

    Raises
    ------
    UnknownSwitchPathError
        If any component is not a field of the block it is read from. Kept as
        this module's own exception rather than propagating the case-level one:
        the switch paths are a frozen enumeration checked by VER-24 in both
        directions, so an unknown one here means *this build* is inconsistent,
        which is why :data:`nanopnp.cli.errors.EXCLUDED` leaves it unclassified.
    """
    try:
        return case_value_at(document, path)
    except UnknownCasePathError as error:
        raise UnknownSwitchPathError(str(error)) from None


def deviations(document: CaseDocument) -> tuple[Deviation, ...]:
    """Return every switch this case sets away from the validated default.

    Sorted by path, so that two runs of the same configuration produce identical
    manifests and a diff of two manifests is readable. A switch under an
    optional block the case does not carry reads as its validated default: the
    block's absence selects nothing (section 5.3.1 NOTE on the v2 keys).
    """
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
    """Return whether a block on the way to ``path`` is absent from ``document``.

    Asked of every proper prefix, each of which the schema declares, so a path
    the schema does not know still fails loudly in :func:`value_at` rather than
    reading as absent.
    """
    components = path.split(".")
    return any(
        value_at(document, ".".join(components[:depth])) is None
        for depth in range(1, len(components))
    )
