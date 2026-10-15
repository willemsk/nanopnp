"""Supplied fixed-charge and solid-fraction fields, and the conservation gate."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, TypeAlias

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.typing import Expression, Mesh
from nanopnp.density.grid import (
    RadialGrid,
    RingMaximum,
    coefficient,
    read_grid,
)
from nanopnp.numerics.measures import FixedCharge

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Callable, Mapping, Sequence

    import numpy as np

    from nanopnp.charge.kernel import SourceAtoms
    from nanopnp.core.scaling import Scales
    from nanopnp.numerics.measures import Measures

FIELD_SCHEMA = "nanopnp/field/v0.5"
"""Schema identifier every supplied field document declares (§5.3.1)."""

FIELD_FORMAT = "field1"
"""``inputs.charge.format`` naming the header document rather than the data."""

Quantity: TypeAlias = Literal["areal_charge_density", "volume_charge_density", "solid_fraction"]
"""The three quantities a supplied field may carry (§5.3.1 NOTE)."""

QUANTITIES: dict[str, dict[str, float]] = {
    # Quantity -> accepted unit -> factor onto the canonical SI unit. Declared
    # rather than inferred: the reference's own table stores the charge sum
    # *without* ``e`` (units m^-2) and its COMSOL assembly multiplies by
    # ``e_const``, so a table read as C m^-2 would be wrong by 1.6e-19 with
    # nothing to say so
    # (`knowledge/04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md` G5,
    # settled on the delivered table).
    "areal_charge_density": {"C/m^2": 1.0, "e/m^2": ELEMENTARY_CHARGE},
    "volume_charge_density": {"C/m^3": 1.0, "e/m^3": ELEMENTARY_CHARGE},
    "solid_fraction": {"1": 1.0},
}
"""Accepted units per quantity, against the factor onto the canonical SI unit."""

CANONICAL_UNITS: dict[str, str] = {
    "areal_charge_density": "C/m^2",
    "volume_charge_density": "C/m^3",
    "solid_fraction": "1",
}
"""The SI unit each quantity is held in once loaded."""

REFUSED_QUANTITIES: dict[str, str] = {
    name: (
        "an absolute relative-permittivity field cannot carry PHY-11's concentration dependence: "
        "eps_w = eps_r,f0 * eps_r,f^c(<c>) and <c> is solved for, so a static field would silently "
        "disable the permittivity correction while the run continued to report ePNP-NS. Supply a "
        "solid fraction chi in [0, 1] instead and the solver blends "
        "eps_r = chi * eps_p + (1 - chi) * eps_r,f(<c>) (§4.4 NOTE, PHY-12, PHY-20)"
    )
    for name in ("relative_permittivity", "permittivity", "eps_r", "epsilon_r", "dielectric")
}
"""Quantities refused with their own diagnostic rather than as unknown names.

An absolute ``eps_r`` field is the mistake §4.4's NOTE exists to prevent, and
"not one of the three accepted names" would be a true diagnostic that teaches a
reader nothing about why.
"""

CHARGE_QUANTITIES: frozenset[str] = frozenset({"areal_charge_density", "volume_charge_density"})
"""The quantities :class:`ChargeField` accepts; the third is the dielectric's."""

DEFAULT_AXIS_CUTOFF_NM = 0.01
"""PHY-18's axis guard: ``r < 0.01 nm -> 0``, as the reference model applies it."""

FIELD_QUADRATURE_ORDER = 8
"""Explicit integration rule order evaluated by the source and every conservation leg."""

CONSERVATION_TOL = 1.0e-3
"""QR-03's budget on each leg of the conservation check."""

QUADRATURE_REFINEMENT = 3
"""Quadrature orders the agreement check adds on top of the assembly order.

Added to the explicit rule the source is assembled with
(:data:`FIELD_QUADRATURE_ORDER`), so the refined leg is a genuinely different
rule. Passing it as ``extra_order`` beside ``singular`` would not be:
:meth:`~nanopnp.numerics.measures.Measures.bonus_order` takes ``max(extra, 3)`` on
a singular form, so ``extra_order=3`` on the ``1/r`` field of PHY-16 step 6
evaluates at *exactly* the same order as ``extra_order=0`` and the two integrals
agree to the last bit [tested]. A gate that passes because its two sides are the
same computation is worse than no gate.
"""

QUADRATURE_TOL = 1.0e-4
"""Budget on the order / order + 3 agreement of the mesh integral.

A tenth of QR-03's, because this is not a physical error but a statement about
whether the deployed mesh resolves the field: without it the gate reports a
number it cannot defend. NUM-07's order floor is about ``1/r`` and says nothing
about a Gaussian of width 0.085 nm on 0.05 nm elements.
"""

RING_TOL = 1.0e-4
"""Budget on the boundary ring against the grid's interior maximum.

The interpolant is padded to zero outside its box, which hides truncation; this
is the gate that refuses to hide it. PHY-16 step 4's ">= 4 sigma beyond the
protein" delivers ``exp(-16) = 1.1e-7`` of peak, three decades of headroom, and
the reference grid clears it by twenty [tested].
"""

DEFAULT_RAMP_NM = 0.2
"""Width of the per-plane ramp of §4.4's NOTE, in nm.

Two to four times the element size at the reference pore wall, which is the
condition for the mesh side's quadrature error to be negligible while the ramp
stays far below the ~14 nm over which the cumulative varies.
"""

DEFAULT_PLANE_COUNT = 12
"""Planes the per-``z`` cumulative is evaluated at when a caller names none."""

NEUTRAL_Q_NET_E = 1e-6
"""``|Q_net|`` at or below which a deposited charge is net-neutral, in e.

The protonation gate holds every frame's ``Q_net`` to within this of an integer
(``charge.protonation.Q_NET_TOLERANCE_E``), so a frame mean this small is a
zero summed in floating point: ``fsum`` of CHARMM's decimal charges is ~1e-17 e,
not 0, and every relative leg against it is round-off over round-off.
"""

PLANE_SMOOTHING_NM = 0.5
"""``s`` of the producer path's per-plane weight ``1/2 erfc((z - p)/s)``, in nm.

The consumer path keeps its 0.2 nm ramp. A polynomial of the deposit's order
approximates this smooth weight to about ``0.064 h^3 |W'''|`` on an element of
size ``h``, 6e-4 on ClyA's 0.1 nm protein elements, where the ramp's kinks leave
``h/(16 s) = 0.03`` (§4.4 NOTE on the producer path).
"""


class FieldDocumentError(ValueError):
    """A field document is not one, or does not describe the data it names."""


class ChargeFieldError(ValueError):
    """A supplied field failed one of the charge gates."""

    def __init__(self, gate: str, quantity: str, location: str | None = None) -> None:
        where = f" at {location}" if location is not None else ""
        super().__init__(f"{gate}: {quantity}{where}")
        self.gate = gate
        self.quantity = quantity
        self.location = location


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GridSpec(_Strict):
    """The grid descriptor the header declares, checked against the data."""

    origin_nm: tuple[float, float]
    spacing_nm: tuple[float, float]
    shape: tuple[int, int]


class DataSpec(_Strict):
    """The data file a header refers to, and how to read it."""

    path: Path
    format: str | None = None
    sha256: str | None = None


class FormSpec(_Strict):
    """A named analytic form standing in for a data file, with typed parameters."""

    name: str
    parameters: dict[str, float] = Field(default_factory=dict)
    origin_nm: tuple[float, float]
    spacing_nm: tuple[float, float]
    shape: tuple[int, int]


class FieldProvenance(_Strict):
    """Where a field came from, for the manifest."""

    source: str
    citation: str | None = None
    notes: str | None = None


class FieldDocument(_Strict):
    """A supplied field's header document."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_id: str = Field(alias="schema")
    name: str
    quantity: str
    units: str
    provenance: FieldProvenance
    data: DataSpec | None = None
    form: FormSpec | None = None
    grid: GridSpec | None = None
    # Finite, or every ``> tol`` conservation test downstream passes on NaN.
    axis_cutoff_nm: float = Field(default=DEFAULT_AXIS_CUTOFF_NM, allow_inf_nan=False)
    q_net_e: float | None = Field(default=None, allow_inf_nan=False)
    model_frame_centre_z_nm: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def _check(self) -> FieldDocument:
        problems: list[str] = []
        if self.schema_id != FIELD_SCHEMA:
            problems.append(f"schema is {self.schema_id!r} and must be {FIELD_SCHEMA!r}")
        refusal = REFUSED_QUANTITIES.get(self.quantity)
        if refusal is not None:
            raise ValueError(f"quantity {self.quantity!r} is refused: {refusal}")
        accepted = QUANTITIES.get(self.quantity)
        if accepted is None:
            raise ValueError(
                f"quantity {self.quantity!r} is not one this release reads; the quantities are "
                f"{', '.join(sorted(QUANTITIES))}"
            )
        if self.units not in accepted:
            problems.append(
                f"units {self.units!r} do not belong to quantity {self.quantity!r}; the accepted "
                f"units are {', '.join(sorted(accepted))}"
            )
        if (self.data is None) == (self.form is None):
            problems.append(
                "a field document names exactly one of data: (a file on disk) and form: (a "
                "registered analytic form)"
            )
        if self.form is not None and self.units != CANONICAL_UNITS[self.quantity]:
            problems.append(
                f"an analytic form produces SI values, so units must be "
                f"{CANONICAL_UNITS[self.quantity]!r} and not {self.units!r}"
            )
        if self.axis_cutoff_nm < 0.0:
            problems.append(f"axis_cutoff_nm is {self.axis_cutoff_nm} and cannot be negative")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    @property
    def q_net_C(self) -> float | None:
        """Return the declared net charge in coulombs, or None if none was declared."""
        return None if self.q_net_e is None else self.q_net_e * ELEMENTARY_CHARGE

    @property
    def unit_factor(self) -> float:
        """Return the factor from the declared units onto the SI unit."""
        return QUANTITIES[self.quantity][self.units]

    def summary(self) -> dict[str, object]:
        """Return what the manifest records about this header."""
        return {
            "name": self.name,
            "quantity": self.quantity,
            "units": self.units,
            "canonical_units": CANONICAL_UNITS[self.quantity],
            "axis_cutoff_nm": self.axis_cutoff_nm,
            "q_net_e": self.q_net_e,
            "provenance": self.provenance.model_dump(mode="json"),
            "source": (
                {"file": self.data.path.name}
                if self.data is not None
                else {"form": self.form.name if self.form is not None else "unknown"}
            ),
        }


def load_document(path: str | Path) -> FieldDocument:
    """Read and validate a field header document; refuse invalid YAML or fields."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"no field document at {str(source)!r}")
    try:
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise FieldDocumentError(f"{source.name}: not valid YAML: {error}") from error
    if not isinstance(payload, dict):
        raise FieldDocumentError(
            f"{source.name}: a field document is a mapping, not {type(payload).__name__}"
        )
    try:
        return FieldDocument.model_validate(payload)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in problem['loc']) or '<document>'}: {problem['msg']}"
            for problem in error.errors()
        )
        raise FieldDocumentError(f"{source.name}: {problems}") from error


def load_grid(document: FieldDocument, *, base: Path) -> RadialGrid:
    """Return the grid a document describes, with its values converted to SI.

    Parameters
    ----------
    base
        Directory a relative data.path is resolved against.
    """
    import numpy as np

    if document.form is not None:
        grid = create_form(document.form)
    else:
        assert document.data is not None  # the validator admits no third case
        path = document.data.path
        resolved = path if path.is_absolute() else base / path
        # Ahead of the read, not after it: a declared digest is a statement about
        # the bytes, and checking it costs one pass over the buffer where parsing
        # the 77 MB reference table before refusing it costs a couple of seconds
        # (1.6 s measured for an 84 MB %Grid table).
        if document.data.sha256 is not None:
            from nanopnp.core.hashing import file_hash

            digest = file_hash(resolved)
            if digest != document.data.sha256:
                raise FieldDocumentError(
                    f"{resolved.name!r} hashes to {digest} and the document declares "
                    f"{document.data.sha256}; the header describes different bytes"
                )
        grid = read_grid(resolved, format=document.data.format)
    factor = document.unit_factor
    if factor != 1.0:
        grid = RadialGrid(
            origin_nm=grid.origin_nm,
            spacing_nm=grid.spacing_nm,
            values=grid.values * factor,
        )
    declared = document.grid
    if declared is not None:
        found = (tuple(grid.origin_nm), tuple(grid.spacing_nm), tuple(grid.shape))
        expected = (
            tuple(declared.origin_nm),
            tuple(declared.spacing_nm),
            tuple(declared.shape),
        )
        if found[2] != expected[2] or not np.allclose(found[:2], expected[:2], rtol=0.0, atol=1e-9):
            raise FieldDocumentError(
                f"the document declares grid origin {list(declared.origin_nm)} nm, spacing "
                f"{list(declared.spacing_nm)} nm and shape {list(declared.shape)}, and the data "
                f"has origin {list(grid.origin_nm)} nm, spacing {list(grid.spacing_nm)} nm and "
                f"shape {list(grid.shape)}"
            )
    return grid


FormBuilder: TypeAlias = "Callable[[np.ndarray, np.ndarray, Mapping[str, float]], np.ndarray]"
"""A named form: the two axes in nm and its parameters, to SI values ``[i_z, i_r]``."""

_FORMS: dict[str, FormBuilder] = {}


def register_form(name: str, builder: FormBuilder) -> None:
    """Register an analytic field form under name; refuse a name already taken."""
    if name in _FORMS:
        raise ValueError(f"field form {name!r} is already registered")
    _FORMS[name] = builder


def registered_forms() -> tuple[str, ...]:
    """Return every registered form name, sorted."""
    return tuple(sorted(_FORMS))


def create_form(spec: FormSpec) -> RadialGrid:
    """Return the grid a FormSpec describes, in canonical SI units."""
    import numpy as np

    builder = _FORMS.get(spec.name)
    if builder is None:
        raise FieldDocumentError(
            f"field form {spec.name!r} is not registered; the forms are "
            f"{', '.join(registered_forms()) or 'none'}"
        )
    n_r, n_z = spec.shape
    r_nm = spec.origin_nm[0] + spec.spacing_nm[0] * np.arange(n_r, dtype=np.float64)
    z_nm = spec.origin_nm[1] + spec.spacing_nm[1] * np.arange(n_z, dtype=np.float64)
    try:
        values = builder(r_nm, z_nm, spec.parameters)
    except KeyError as error:
        raise FieldDocumentError(
            f"field form {spec.name!r} needs a parameter {error.args[0]!r} the document does not "
            "set"
        ) from error
    return RadialGrid.from_axes(r_nm, z_nm, values)


def _uniform(r_nm: np.ndarray, z_nm: np.ndarray, parameters: Mapping[str, float]) -> np.ndarray:
    import numpy as np

    return np.full((z_nm.size, r_nm.size), float(parameters["value"]), dtype=np.float64)


def _gaussian_ring(
    r_nm: np.ndarray, z_nm: np.ndarray, parameters: Mapping[str, float]
) -> np.ndarray:
    import numpy as np

    r0 = float(parameters["centre_r_nm"])
    z0 = float(parameters["centre_z_nm"])
    width_m = float(parameters["width_nm"]) * 1e-9
    charge_C = float(parameters["charge_e"]) * ELEMENTARY_CHARGE
    dr = (r_nm[None, :] - r0) * 1e-9
    dz = (z_nm[:, None] - z0) * 1e-9
    return charge_C / (np.pi * width_m**2) * np.exp(-(dr**2 + dz**2) / width_m**2)


def _slab(r_nm: np.ndarray, z_nm: np.ndarray, parameters: Mapping[str, float]) -> np.ndarray:
    import numpy as np

    inside_r = (r_nm[None, :] >= parameters["r_min_nm"]) & (r_nm[None, :] <= parameters["r_max_nm"])
    inside_z = (z_nm[:, None] >= parameters["z_min_nm"]) & (z_nm[:, None] <= parameters["z_max_nm"])
    return np.where(inside_r & inside_z, float(parameters["value"]), 0.0)


register_form("uniform", _uniform)
register_form("gaussian_ring", _gaussian_ring)
register_form("slab", _slab)


@dataclass(frozen=True)
class ChargeField:
    """A supplied fixed-charge field, ready to be assembled onto a mesh."""

    document: FieldDocument
    grid: RadialGrid
    source: Path
    quadrature_order: ClassVar[int] = FIELD_QUADRATURE_ORDER

    def __post_init__(self) -> None:
        if self.document.quantity not in CHARGE_QUANTITIES:
            raise FieldDocumentError(
                f"inputs.charge names quantity {self.document.quantity!r}; a fixed-charge field is "
                f"one of {', '.join(sorted(CHARGE_QUANTITIES))}. A solid fraction is the "
                "dielectric field of §4.4 and belongs under inputs.eps_r"
            )

    @property
    def is_areal(self) -> bool:
        """Return whether the 1/(2 pi r) projection and the axis guard apply."""
        return self.document.quantity == "areal_charge_density"

    def volume_density_C_m3(self) -> Expression:
        """Return the SI volume charge density in C m^-3 as a coefficient function."""
        import ngsolve as ngs

        interpolant = coefficient(self.grid)
        if not self.is_areal:
            return interpolant
        cutoff = self.document.axis_cutoff_nm
        # ``ngs.x`` is r in nm; the projection needs it in metres.
        projected = interpolant / (2.0 * ngs.pi * ngs.x * 1e-9)
        return ngs.IfPos(ngs.x - cutoff, projected, 0.0)

    def fixed_charge_C_m3(self) -> FixedCharge:
        """Return the SI volume density with the rule it is assembled with."""
        return FixedCharge(self.volume_density_C_m3(), self.quadrature_order)

    def assemble(self, scales: Scales) -> FixedCharge:
        """Return the dimensionless rho~_pore the weak form takes, scaled by scales."""
        return self.fixed_charge_C_m3().scaled(1.0 / scales.charge_density_C_m3)

    def guard_deficit_C(self) -> float:
        """Return the charge the axis guard deletes, in coulombs, measured on the grid."""
        if not self.is_areal:
            return 0.0
        return self.grid.integral(
            weights={"r": self.grid.truncated_weights("r", self.document.axis_cutoff_nm)}
        )

    def planar_integral_C(self) -> float:
        """Return the source grid's own charge, Q_grid, in coulombs."""
        if self.is_areal:
            return self.grid.planar_integral()
        return self.grid.integral(radial=True)

    def mesh_integral_C(self, mesh: Mesh, measures: Measures, *, refined: bool = False) -> float:
        """Return the assembled density integrated over the mesh, Q_mesh, in coulombs.

        Parameters
        ----------
        refined
            Also evaluate the refinement orders above the assembly rule.
        """
        rule_order = self.quadrature_order + (QUADRATURE_REFINEMENT if refined else 0)
        integral_nm = measures.integrate(
            self.volume_density_C_m3(),
            mesh,
            rule_order=rule_order,
            what="the assembled fixed charge",
        )
        # nm^3 -> m^3 for the (r dr dz) the measure returned, and the 2 pi the
        # axisymmetric volume element carries.
        return 2.0 * math.pi * 1e-27 * integral_nm

    def mesh_cumulative_C(
        self,
        mesh: Mesh,
        measures: Measures,
        planes_nm: Sequence[float],
        *,
        ramp_nm: float = DEFAULT_RAMP_NM,
    ) -> tuple[float, ...]:
        """Return the mesh-side cumulative charge below each plane, ramped."""
        import ngsolve as ngs

        density = self.volume_density_C_m3()
        values: list[float] = []
        for plane in planes_nm:
            raw = (plane + 0.5 * ramp_nm - ngs.y) / ramp_nm
            weight = ngs.IfPos(raw, ngs.IfPos(raw - 1.0, 1.0, raw), 0.0)
            values.append(
                2.0
                * math.pi
                * 1e-27
                * measures.integrate(
                    density * weight,
                    mesh,
                    rule_order=self.quadrature_order,
                    what=f"the cumulative fixed charge below z = {plane:g} nm",
                )
            )
        return tuple(values)

    def grid_cumulative_C(
        self, planes_nm: Sequence[float], *, ramp_nm: float = DEFAULT_RAMP_NM
    ) -> tuple[float, ...]:
        """Return the grid-side cumulative charge below each plane, ramped alike."""
        return self.grid.cumulative(planes_nm, ramp_nm=ramp_nm, radial=not self.is_areal)


def load_field(path: str | Path) -> ChargeField:
    """Read a field document and its grid, and return the charge field."""
    source = Path(path)
    document = load_document(source)
    return ChargeField(
        document=document, grid=load_grid(document, base=source.parent), source=source
    )


def _relative(deviation: float, reference: float) -> float:
    if reference == 0.0:
        return 0.0 if deviation == 0.0 else float("inf")
    return deviation / reference


@dataclass(frozen=True)
class ConservationReport:
    """The PHY-19 conservation check, decomposed.

    Parameters
    ----------
    q_net_C
        Declared net charge in C, or None when none was declared.
    """

    q_net_C: float | None
    q_grid_C: float
    q_mesh_C: float
    q_mesh_refined_C: float
    guard_deficit_C: float
    ring: RingMaximum
    interior_maximum: float
    planes_nm: tuple[float, ...]
    grid_cumulative_C: tuple[float, ...]
    mesh_cumulative_C: tuple[float, ...]
    ramp_nm: float

    @property
    def reference_C(self) -> float:
        """Return the magnitude every absolute tolerance is taken against."""
        return abs(self.q_net_C if self.q_net_C is not None else self.q_grid_C)

    @property
    def producer_error(self) -> float | None:
        """Return (Q_grid - Q_net) / |Q_net|, or None if none was declared."""
        if self.q_net_C is None:
            return None
        return _relative(self.q_grid_C - self.q_net_C, abs(self.q_net_C))

    @property
    def consumer_error(self) -> float:
        """Return (Q_mesh - Q_grid) / |Q_grid|."""
        return _relative(self.q_mesh_C - self.q_grid_C, abs(self.q_grid_C))

    @property
    def quadrature_error(self) -> float:
        """Return |Q_mesh(order) - Q_mesh(order + 3)| / reference."""
        return _relative(abs(self.q_mesh_C - self.q_mesh_refined_C), self.reference_C)

    @property
    def ring_ratio(self) -> float:
        """Return the boundary ring against the grid's interior maximum."""
        return self.ring.value / self.interior_maximum if self.interior_maximum else 0.0

    @property
    def worst_plane(self) -> tuple[float, float]:
        """Return the plane with the largest cumulative error, and that error; NaN ranks highest."""
        if not self.planes_nm:
            return (float("nan"), 0.0)
        errors = [
            (_relative(abs(mesh - grid), self.reference_C), plane)
            for plane, grid, mesh in zip(
                self.planes_nm, self.grid_cumulative_C, self.mesh_cumulative_C, strict=True
            )
        ]
        error, plane = max(errors, key=lambda item: math.inf if math.isnan(item[0]) else item[0])
        return (plane, error)

    def summary(self) -> dict[str, object]:
        """Return the manifest's record of this check."""
        plane, plane_error = self.worst_plane
        return {
            "q_net_e": None if self.q_net_C is None else self.q_net_C / ELEMENTARY_CHARGE,
            "q_grid_e": self.q_grid_C / ELEMENTARY_CHARGE,
            "q_mesh_e": self.q_mesh_C / ELEMENTARY_CHARGE,
            "producer": (
                {"status": "not run", "reason": "the field document declares no q_net_e"}
                if self.producer_error is None
                else {"relative_error": self.producer_error, "tolerance": CONSERVATION_TOL}
            ),
            "consumer": {
                "relative_error": self.consumer_error,
                "tolerance": CONSERVATION_TOL,
            },
            "quadrature_agreement": {
                "relative_error": self.quadrature_error,
                "tolerance": QUADRATURE_TOL,
            },
            "axis_guard_deficit_e": self.guard_deficit_C / ELEMENTARY_CHARGE,
            "boundary_ring": {**self.ring.summary(), "ratio": self.ring_ratio},
            "per_plane": {
                "ramp_nm": self.ramp_nm,
                "count": len(self.planes_nm),
                "worst_plane_z_nm": plane,
                "worst_relative_error": plane_error,
            },
            "interpolation": "bilinear",
        }


def default_planes(field: ChargeField, count: int = DEFAULT_PLANE_COUNT) -> tuple[float, ...]:
    """Return a ladder of z planes spanning the grid, ends excluded."""
    (_, _), (z_min, z_max) = field.grid.extent_nm
    step = (z_max - z_min) / (count + 1)
    return tuple(z_min + step * (index + 1) for index in range(count))


def conservation(
    field: ChargeField,
    mesh: Mesh,
    measures: Measures,
    *,
    planes_nm: Sequence[float] | None = None,
    ramp_nm: float = DEFAULT_RAMP_NM,
) -> ConservationReport:
    """Measure the conservation check on the deployed mesh, without gating it."""
    planes = tuple(planes_nm) if planes_nm is not None else default_planes(field)
    return ConservationReport(
        q_net_C=field.document.q_net_C,
        q_grid_C=field.planar_integral_C(),
        q_mesh_C=field.mesh_integral_C(mesh, measures),
        q_mesh_refined_C=field.mesh_integral_C(mesh, measures, refined=True),
        guard_deficit_C=field.guard_deficit_C(),
        ring=field.grid.boundary_ring_maximum(),
        interior_maximum=field.grid.interior_maximum(),
        planes_nm=planes,
        grid_cumulative_C=field.grid_cumulative_C(planes, ramp_nm=ramp_nm),
        mesh_cumulative_C=field.mesh_cumulative_C(mesh, measures, planes, ramp_nm=ramp_nm),
        ramp_nm=ramp_nm,
    )


@dataclass(frozen=True)
class DepositConservation:
    """The conservation check for a deposited charge, against the source atoms.

    Parameters
    ----------
    q_net_C
        Declared net charge, in C.
    planes_nm, smoothing_nm
        The planes and the smoothing width of their weight, in nm.
    """

    q_net_C: float
    q_grid_C: float
    q_mesh_C: float
    q_mesh_refined_C: float
    guard_deficit_C: float
    ring: RingMaximum
    interior_maximum: float
    planes_nm: tuple[float, ...]
    smoothing_nm: float
    source_cumulative_C: tuple[float, ...]
    grid_cumulative_C: tuple[float, ...]
    mesh_cumulative_C: tuple[float, ...]

    @property
    def reference_C(self) -> float:
        """Return |Q_net|, the magnitude every relative error is taken against."""
        return abs(self.q_net_C)

    @property
    def producer_error(self) -> float:
        """Return (Q_grid - Q_net) / |Q_net|."""
        return _relative(self.q_grid_C - self.q_net_C, abs(self.q_net_C))

    @property
    def consumer_error(self) -> float:
        """Return (Q_mesh - Q_grid) / |Q_grid|."""
        return _relative(self.q_mesh_C - self.q_grid_C, abs(self.q_grid_C))

    @property
    def quadrature_error(self) -> float:
        """Return |Q_mesh(order) - Q_mesh(order + 3)| / |Q_net|."""
        return _relative(abs(self.q_mesh_C - self.q_mesh_refined_C), self.reference_C)

    @property
    def ring_ratio(self) -> float:
        """Return the lattice's boundary ring against its interior maximum."""
        return self.ring.value / self.interior_maximum if self.interior_maximum else 0.0

    def worst_plane(self, side: str) -> tuple[float, float]:
        """Return the plane where side is furthest from the atoms, and that error."""
        values = self.grid_cumulative_C if side == "grid" else self.mesh_cumulative_C
        if not self.planes_nm:
            return (float("nan"), 0.0)
        errors = [
            (_relative(abs(found - source), self.reference_C), plane)
            for plane, source, found in zip(
                self.planes_nm, self.source_cumulative_C, values, strict=True
            )
        ]
        error, plane = max(errors, key=lambda item: math.inf if math.isnan(item[0]) else item[0])
        return (plane, error)

    def summary(self) -> dict[str, object]:
        """Return the manifest's record of this check."""
        grid_plane, grid_error = self.worst_plane("grid")
        mesh_plane, mesh_error = self.worst_plane("mesh")
        return {
            "q_net_e": self.q_net_C / ELEMENTARY_CHARGE,
            "q_grid_e": self.q_grid_C / ELEMENTARY_CHARGE,
            "q_mesh_e": self.q_mesh_C / ELEMENTARY_CHARGE,
            "producer": {"relative_error": self.producer_error, "tolerance": CONSERVATION_TOL},
            "consumer": {"relative_error": self.consumer_error, "tolerance": CONSERVATION_TOL},
            "quadrature_agreement": {
                "relative_error": self.quadrature_error,
                "tolerance": QUADRATURE_TOL,
            },
            "axis_guard_deficit_e": self.guard_deficit_C / ELEMENTARY_CHARGE,
            "boundary_ring": {**self.ring.summary(), "ratio": self.ring_ratio},
            "per_plane": {
                "reference": "source atoms, in closed form",
                "weight": "1/2 erfc((z - p)/s)",
                "smoothing_nm": self.smoothing_nm,
                "count": len(self.planes_nm),
                "planes_nm": list(self.planes_nm),
                "grid_worst_plane_z_nm": grid_plane,
                "grid_worst_relative_error": grid_error,
                "mesh_worst_plane_z_nm": mesh_plane,
                "mesh_worst_relative_error": mesh_error,
                "tolerance": CONSERVATION_TOL,
            },
            "interpolation": "deposited",
        }


def deposit_conservation(
    atoms: SourceAtoms,
    grid: RadialGrid,
    density_C_m3: Expression,
    mesh: Mesh,
    measures: Measures,
    *,
    planes_nm: Sequence[float] | None = None,
    smoothing_nm: float | None = None,
) -> DepositConservation:
    """Measure the conservation check for a deposited charge, without gating it."""
    import ngsolve as ngs
    import numpy as np
    from scipy.special import erfc

    smoothing = PLANE_SMOOTHING_NM if smoothing_nm is None else smoothing_nm
    planes = tuple(planes_nm) if planes_nm is not None else atoms.planes_nm()

    def mesh_charge(integrand: Expression, *, extra: int = 0, what: str) -> float:
        return (
            2.0
            * math.pi
            * 1e-27
            * measures.integrate(integrand, mesh, extra_order=extra, what=what)
        )

    mesh_cumulative = tuple(
        mesh_charge(
            density_C_m3 * 0.5 * (1.0 - ngs.erf((ngs.y - plane) / smoothing)),
            what=f"the deposited charge below z = {plane:g} nm",
        )
        for plane in planes
    )
    return DepositConservation(
        q_net_C=atoms.q_net_e() * ELEMENTARY_CHARGE,
        q_grid_C=grid.planar_integral(),
        q_mesh_C=mesh_charge(density_C_m3, what="the deposited fixed charge"),
        q_mesh_refined_C=mesh_charge(
            density_C_m3,
            extra=measures.bonus_order() + QUADRATURE_REFINEMENT,
            what="the deposited fixed charge, refined",
        ),
        guard_deficit_C=grid.integral(
            weights={"r": grid.truncated_weights("r", DEFAULT_AXIS_CUTOFF_NM)}
        ),
        ring=grid.boundary_ring_maximum(),
        interior_maximum=grid.interior_maximum(),
        planes_nm=planes,
        smoothing_nm=smoothing,
        source_cumulative_C=tuple(
            value * ELEMENTARY_CHARGE
            for value in atoms.cumulative_e(planes, smoothing_nm=smoothing)
        ),
        grid_cumulative_C=tuple(
            grid.integral(z_weight=0.5 * erfc((np.asarray(grid.z_nm) - plane) / smoothing))
            for plane in planes
        ),
        mesh_cumulative_C=mesh_cumulative,
    )


def check_deposit_conservation(report: DepositConservation) -> DepositConservation:
    """Gate a deposit's conservation report, aborting on the first failure."""
    if not report.reference_C > NEUTRAL_Q_NET_E * ELEMENTARY_CHARGE:
        raise ChargeFieldError(
            "the protonation artefact carries no net charge",
            f"|Q_net| is {report.reference_C / ELEMENTARY_CHARGE:.3g} e, a net-neutral structure "
            f"to within {NEUTRAL_Q_NET_E:g} e, and every leg of this check is relative to it, "
            "so no tolerance means anything (QR-03)",
        )
    if not report.ring_ratio <= RING_TOL:
        raise ChargeFieldError(
            "the export lattice is truncated",
            f"its boundary ring reaches {report.ring_ratio:.3g} of its interior maximum against "
            f"{RING_TOL:g}; the lattice must extend 6 w beyond every atom (PHY-16 step 6)",
            f"(r, z) = ({report.ring.r_nm:.4g}, {report.ring.z_nm:.4g}) nm",
        )
    if not report.quadrature_error <= QUADRATURE_TOL:
        raise ChargeFieldError(
            "the deposited field's integral depends on the quadrature order",
            f"it moves by {report.quadrature_error:.3g} of Q_net between the solve's order and "
            f"three orders above it, against {QUADRATURE_TOL:g}",
        )
    if not abs(report.producer_error) <= CONSERVATION_TOL:
        raise ChargeFieldError(
            "the export lattice does not carry Q_net (producer leg, QR-03)",
            f"it integrates to {report.q_grid_C / ELEMENTARY_CHARGE:.9g} e against Q_net "
            f"{report.q_net_C / ELEMENTARY_CHARGE:.9g} e, a relative error of "
            f"{report.producer_error:.3g} against {CONSERVATION_TOL:g}. This leg is the "
            "kernel's: its per-atom renormalisation and its patches",
        )
    if not abs(report.consumer_error) <= CONSERVATION_TOL:
        raise ChargeFieldError(
            "the deposited charge is not conserved on the deployed mesh (consumer leg, QR-03)",
            f"the mesh carries {report.q_mesh_C / ELEMENTARY_CHARGE:.9g} e against the lattice's "
            f"{report.q_grid_C / ELEMENTARY_CHARGE:.9g} e, a relative error of "
            f"{report.consumer_error:.3g} against {CONSERVATION_TOL:g}. This leg is the "
            "projection's: its r weight and the mesh's coverage of the lattice",
        )
    for side, what in (("grid", "the export lattice"), ("mesh", "the deployed field")):
        plane, error = report.worst_plane(side)
        if not error <= CONSERVATION_TOL:
            raise ChargeFieldError(
                f"the cumulative charge of {what} disagrees with the source atoms at a z plane "
                "(PHY-19)",
                f"{what} carries {error:.3g} of |Q_net| more or less than the atoms below this "
                f"plane, under 1/2 erfc((z - p)/{report.smoothing_nm:g} nm), against "
                f"{CONSERVATION_TOL:g}. A globally conserved charge can hide a compensating "
                "Jacobian error, which is what this check is for",
                f"z = {plane:.4g} nm",
            )
    return report


def check_conservation(report: ConservationReport) -> ConservationReport:
    """Gate a conservation report, aborting on the first failure; return the report."""
    if report.reference_C == 0.0:
        raise ChargeFieldError(
            "the supplied field carries no reference charge",
            "every leg of this check is a relative error and its reference "
            f"({'the declared q_net_e' if report.q_net_C is not None else 'the grid integral'}) "
            "is zero, so no tolerance means anything. A field with no net charge cannot be "
            "gated against QR-03's relative budget: omit q_net_e if the producer declared it "
            "wrongly, or supply a field that carries charge",
        )
    if not report.ring_ratio <= RING_TOL:
        raise ChargeFieldError(
            "the supplied grid is truncated",
            f"its boundary ring reaches {report.ring.value:.6g} against an interior maximum of "
            f"{report.interior_maximum:.6g}, a ratio of {report.ring_ratio:.3g} against the "
            f"{RING_TOL:g} this gate allows. The interpolant is zero outside the grid box, so "
            "this charge would be discarded silently; PHY-16 step 4 asks for >= 4 sigma beyond "
            "the structure",
            f"(r, z) = ({report.ring.r_nm:.4g}, {report.ring.z_nm:.4g}) nm",
        )
    if not report.quadrature_error <= QUADRATURE_TOL:
        raise ChargeFieldError(
            "the deployed mesh under-resolves the supplied field",
            f"the charge integral moves by {report.quadrature_error:.3g} of the reference charge "
            f"between the assembly order and three orders above it, against the "
            f"{QUADRATURE_TOL:g} this gate allows. The conservation check below it is a "
            "quadrature-resolution check on this mesh, so its number cannot be defended",
        )
    producer = report.producer_error
    declared_C = report.q_net_C
    if producer is not None and declared_C is not None and not abs(producer) <= CONSERVATION_TOL:
        raise ChargeFieldError(
            "the supplied field does not carry the charge it declares (producer leg, QR-03)",
            f"its grid integrates to {report.q_grid_C / ELEMENTARY_CHARGE:.6g} e against a "
            f"declared q_net_e of {declared_C / ELEMENTARY_CHARGE:.6g}"
            f", a relative error of {producer:.3g} against {CONSERVATION_TOL:g}. This leg is the "
            "producer's: smearing, projection and the annular volumes",
        )
    if not abs(report.consumer_error) <= CONSERVATION_TOL:
        raise ChargeFieldError(
            "the assembled charge is not conserved on the deployed mesh (consumer leg, QR-03)",
            f"the mesh carries {report.q_mesh_C / ELEMENTARY_CHARGE:.6g} e against the grid's "
            f"{report.q_grid_C / ELEMENTARY_CHARGE:.6g} e, a relative error of "
            f"{report.consumer_error:.3g} against {CONSERVATION_TOL:g}. This leg is the "
            "consumer's: interpolation, quadrature, the mesh's coverage of the grid and the axis "
            f"guard, which deletes {report.guard_deficit_C / ELEMENTARY_CHARGE:.3g} e",
        )
    plane, plane_error = report.worst_plane
    if not plane_error <= CONSERVATION_TOL:
        raise ChargeFieldError(
            "the cumulative charge disagrees with the source grid at a z plane (PHY-19)",
            f"the mesh carries {plane_error:.3g} of the reference charge more or less than the "
            f"grid below this plane, against {CONSERVATION_TOL:g}. A globally satisfied check can "
            "hide compensating local errors, which is what this one is for",
            f"z = {plane:.4g} nm",
        )
    return report
