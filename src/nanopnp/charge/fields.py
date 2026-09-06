"""Supplied fixed-charge and solid-fraction fields, and the conservation gate.

The consumer half of FR-14: the solver reads a field somebody else produced, in
the shape §5.3.1's NOTE fixes — a pydantic-validated header document,
``schema: nanopnp/field/v1``, naming the quantity, its units, the grid, the axis
cutoff of PHY-18, the declared ``Q_net`` where the producer knows one, and the
data file. The header is what makes an OpenDX file usable at all: OpenDX has
nowhere to record a ``Q_net`` or a unit, so a bare grid cannot say which of the
three quantities it is, and the difference between them is a factor of ``2*pi*r``
(§4.4 NOTE).

The document lives here rather than in ``density/`` because §5.1 gives
``density/`` the grid IO and this is a description of a *physical field* — which
is also why :mod:`nanopnp.materials.fields` imports it rather than defining a
second header for the solid fraction. One header shape for every quantity keeps
the gates in one place.

**The conservation check is two checks.** Under the axisymmetric volume element
the Jacobian and PHY-16 step 6's ``1/(2*pi*r)`` cancel identically, so the
global check is blind to how ``r`` enters (§4.4 NOTE). It is therefore reported
and gated as a producer leg — the planar integral of the source grid against the
declared ``Q_net`` — and a consumer leg — the integral over the deployed mesh
against that planar integral. A single number against ``Q_net`` attributes
nothing, which is exactly why the reference's own 1.25 % gap is uninterpretable
(OPN-06).

Four more things are measured because each can consume the QR-03 budget on its
own, and none of them is visible in the total: the quadrature agreement between
the ``Measures`` order and three orders above it, which is what says whether the
deployed mesh resolves the field at all; the boundary-ring maximum, which bounds
what the interpolant's zero padding threw away; the axis-guard deficit, which is
the charge PHY-18 deletes; and the ramped per-``z``-plane cumulative, which
localises a failure the total can hide.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

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

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Callable, Mapping, Sequence

    import numpy as np

    from nanopnp.core.scaling import Scales
    from nanopnp.physics.measures import Measures

FIELD_SCHEMA = "nanopnp/field/v1"
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
    # nothing to say so (`.knowledge/04` §7 G5, settled on the delivered table).
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

CONSERVATION_TOL = 1.0e-3
"""QR-03's budget on each leg of the conservation check."""

QUADRATURE_REFINEMENT = 3
"""Quadrature orders the agreement check adds on top of the assembly order.

Added to the bonus the assembly already carries, not passed as ``extra_order``
on its own: :meth:`~nanopnp.physics.measures.Measures.bonus_order` takes
``max(extra, 3)`` on a singular form, so ``extra_order=3`` on the ``1/r`` field
of PHY-16 step 6 evaluates at *exactly* the same order as ``extra_order=0`` and
the two integrals agree to the last bit [tested]. A gate that passes because its
two sides are the same computation is worse than no gate.
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


class FieldDocumentError(ValueError):
    """A field document is not one, or does not describe the data it names."""


class ChargeFieldError(ValueError):
    """A supplied field failed one of the gates of PHY-19, QR-03 or §5.3.1.

    Parameters
    ----------
    gate
        Which gate failed, named as the manifest and the log name it.
    quantity
        The offending value, rendered.
    location
        Where it is, in ``(r, z)`` nm, when the gate has a location; ``None``
        for a global one.
    """

    def __init__(self, gate: str, quantity: str, location: str | None = None) -> None:
        where = f" at {location}" if location is not None else ""
        super().__init__(f"{gate}: {quantity}{where}")
        self.gate = gate
        self.quantity = quantity
        self.location = location


# -- the header document ------------------------------------------------------


class _Strict(BaseModel):
    """Base for every block: unknown keys are rejected, and named in the error."""

    model_config = ConfigDict(extra="forbid")


class GridSpec(_Strict):
    """The grid descriptor the header declares, checked against the data.

    Optional, and checked rather than used: a descriptor that disagrees with the
    file is a header describing a different grid, which is the failure a
    provenance record must not have.
    """

    origin_nm: tuple[float, float]
    spacing_nm: tuple[float, float]
    shape: tuple[int, int]


class DataSpec(_Strict):
    """The data file a header refers to, and how to read it."""

    path: Path
    format: str | None = None
    sha256: str | None = None


class FormSpec(_Strict):
    """A named analytic form standing in for a data file (FR-16 generalised).

    A field is data, named, with provenance. A free-text expression evaluated at
    solve time would be arbitrary code whose provenance is a string; a registered
    form with typed parameters is neither.
    """

    name: str
    parameters: dict[str, float] = Field(default_factory=dict)
    origin_nm: tuple[float, float]
    spacing_nm: tuple[float, float]
    shape: tuple[int, int]


class FieldProvenance(_Strict):
    """Where a field came from (FR-25)."""

    source: str
    citation: str | None = None
    notes: str | None = None


class FieldDocument(_Strict):
    """A supplied field's header (``nanopnp/field/v1``, §5.3.1 NOTE).

    Raises
    ------
    ValueError
        At construction, if the units do not belong to the quantity, or if the
        document names neither or both of ``data:`` and ``form:``.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_id: str = Field(alias="schema")
    name: str
    quantity: str
    units: str
    provenance: FieldProvenance
    data: DataSpec | None = None
    form: FormSpec | None = None
    grid: GridSpec | None = None
    axis_cutoff_nm: float = DEFAULT_AXIS_CUTOFF_NM
    q_net_e: float | None = None

    @model_validator(mode="after")
    def _check(self) -> FieldDocument:
        """Check the schema, the units and the single source of the values."""
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
        """The declared net charge in coulombs, or ``None`` if none was declared."""
        return None if self.q_net_e is None else self.q_net_e * ELEMENTARY_CHARGE

    @property
    def unit_factor(self) -> float:
        """The factor from the declared units onto the canonical SI unit."""
        return QUANTITIES[self.quantity][self.units]

    def summary(self) -> dict[str, object]:
        """Return what the FR-25 manifest records about this header."""
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
    """Read and validate a field header document.

    Raises
    ------
    FileNotFoundError
        If the file is not there.
    FieldDocumentError
        If it is not valid YAML, or fails validation. The message names every
        offending key, as IF-03 requires of every schema in §5.3.
    """
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
    document
        The validated header.
    base
        Directory a relative ``data.path`` is resolved against — the document's
        own directory, so that a field travels as a pair of files.

    Raises
    ------
    FieldDocumentError
        If the declared grid descriptor disagrees with the data file, or if the
        data file's recorded digest does not match its contents.
    GridFormatError
        If the data cannot be read in the format it names.
    """
    import numpy as np

    if document.form is not None:
        grid = create_form(document.form)
    else:
        assert document.data is not None  # the validator admits no third case
        path = document.data.path
        resolved = path if path.is_absolute() else base / path
        grid = read_grid(resolved, format=document.data.format)
        if document.data.sha256 is not None:
            from nanopnp.core.hashing import file_hash

            digest = file_hash(resolved)
            if digest != document.data.sha256:
                raise FieldDocumentError(
                    f"{resolved.name!r} hashes to {digest} and the document declares "
                    f"{document.data.sha256}; the header describes different bytes"
                )
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


# -- the analytic form registry -----------------------------------------------

FormBuilder: TypeAlias = "Callable[[np.ndarray, np.ndarray, Mapping[str, float]], np.ndarray]"
"""A named form: the two axes in nm and its parameters, to SI values ``[i_z, i_r]``."""

_FORMS: dict[str, FormBuilder] = {}


def register_form(name: str, builder: FormBuilder) -> None:
    """Register an analytic field form under ``name``.

    Raises
    ------
    ValueError
        If the name is already registered, which would silently change the
        meaning of existing field documents.
    """
    if name in _FORMS:
        raise ValueError(f"field form {name!r} is already registered")
    _FORMS[name] = builder


def registered_forms() -> tuple[str, ...]:
    """Return every registered form name, sorted."""
    return tuple(sorted(_FORMS))


def create_form(spec: FormSpec) -> RadialGrid:
    """Return the grid a :class:`FormSpec` describes, in canonical SI units.

    Raises
    ------
    FieldDocumentError
        If the form is not registered, or if it was given a parameter it does
        not take or left one it needs unset. Both messages name the parameters.
    """
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
    """Return a constant field: ``value`` everywhere on the box."""
    import numpy as np

    return np.full((z_nm.size, r_nm.size), float(parameters["value"]), dtype=np.float64)


def _gaussian_ring(
    r_nm: np.ndarray, z_nm: np.ndarray, parameters: Mapping[str, float]
) -> np.ndarray:
    """Return the reference model's own smearing kernel, as one ring of charge.

    ``charge_e / (pi w^2) * exp(-((r - r0)^2 + (z - z0)^2) / w^2)`` in C m^-2,
    with ``w`` in metres, so its planar integral over the whole plane is exactly
    ``charge_e`` elementary charges (`.knowledge/04` §3). That exactness is the
    point: it gives the Tier-2 conservation benchmark a ``Q_net`` known in closed
    form rather than one measured by the code under test.
    """
    import numpy as np

    r0 = float(parameters["centre_r_nm"])
    z0 = float(parameters["centre_z_nm"])
    width_m = float(parameters["width_nm"]) * 1e-9
    charge_C = float(parameters["charge_e"]) * ELEMENTARY_CHARGE
    dr = (r_nm[None, :] - r0) * 1e-9
    dz = (z_nm[:, None] - z0) * 1e-9
    return charge_C / (np.pi * width_m**2) * np.exp(-(dr**2 + dz**2) / width_m**2)


def _slab(r_nm: np.ndarray, z_nm: np.ndarray, parameters: Mapping[str, float]) -> np.ndarray:
    """Return ``value`` inside an ``(r, z)`` box and zero outside it.

    The sharp solid fraction of §4.4's NOTE, which must reproduce PHY-20's
    piecewise assignment exactly, lives here.
    """
    import numpy as np

    inside_r = (r_nm[None, :] >= parameters["r_min_nm"]) & (r_nm[None, :] <= parameters["r_max_nm"])
    inside_z = (z_nm[:, None] >= parameters["z_min_nm"]) & (z_nm[:, None] <= parameters["z_max_nm"])
    return np.where(inside_r & inside_z, float(parameters["value"]), 0.0)


register_form("uniform", _uniform)
register_form("gaussian_ring", _gaussian_ring)
register_form("slab", _slab)


# -- the assembled field ------------------------------------------------------


@dataclass(frozen=True)
class ChargeField:
    """A supplied fixed-charge field, ready to be assembled onto a mesh.

    Parameters
    ----------
    document
        The validated header.
    grid
        Its grid, values in the canonical SI unit of the quantity.
    source
        The header document's path, for provenance.
    """

    document: FieldDocument
    grid: RadialGrid
    source: Path

    def __post_init__(self) -> None:
        """Refuse a quantity that is not a charge.

        Raises
        ------
        FieldDocumentError
            If the document carries a solid fraction. That is the dielectric's
            field (:mod:`nanopnp.materials.fields`), and assembling it as a
            charge would put a dimensionless number where C m^-3 belongs.
        """
        if self.document.quantity not in CHARGE_QUANTITIES:
            raise FieldDocumentError(
                f"inputs.charge names quantity {self.document.quantity!r}; a fixed-charge field is "
                f"one of {', '.join(sorted(CHARGE_QUANTITIES))}. A solid fraction is the "
                "dielectric field of §4.4 and belongs under inputs.eps_r"
            )

    @property
    def is_areal(self) -> bool:
        """Whether the ``1/(2*pi*r)`` projection and the axis guard apply (PHY-18)."""
        return self.document.quantity == "areal_charge_density"

    def volume_density_C_m3(self) -> Expression:
        """Return the SI volume charge density as a coefficient function.

        PHY-16 step 6, verbatim: ``if(r < 0.01[nm], 0, rhoq_pore(r, z)/(2 pi r))``
        for an areal density, and the interpolant itself for a volume density —
        which is why the quantity is declared rather than inferred. Applying the
        projection twice, or not at all, is invisible in the conservation check
        (§4.4 NOTE).
        """
        import ngsolve as ngs

        interpolant = coefficient(self.grid)
        if not self.is_areal:
            return interpolant
        cutoff = self.document.axis_cutoff_nm
        # ``ngs.x`` is r in nm; the projection needs it in metres.
        projected = interpolant / (2.0 * ngs.pi * ngs.x * 1e-9)
        return ngs.IfPos(ngs.x - cutoff, projected, 0.0)

    def assemble(self, scales: Scales) -> Expression:
        """Return the dimensionless ``rho~_pore`` the weak form takes (NUM-09).

        Parameters
        ----------
        scales
            The model's scale set; :attr:`~nanopnp.core.scaling.Scales.charge_density_C_m3`
            is the one this divides by.
        """
        return self.volume_density_C_m3() / scales.charge_density_C_m3

    def guard_deficit_C(self) -> float:
        """Return the charge the PHY-18 axis guard deletes, in coulombs.

        Computed on the grid samples inside the guard radius rather than assumed
        negligible: the innermost ClyA atoms sit at ``r >~ 1.6 nm`` and the strip
        sees ``exp(-354)`` of peak, but a different structure — or an analyte on
        the axis — makes it real, and a deficit nobody measured is a deficit
        nobody can rule out.
        """
        if not self.is_areal:
            return 0.0
        return self.grid.integral(
            weights={"r": self.grid.truncated_weights("r", self.document.axis_cutoff_nm)}
        )

    def planar_integral_C(self) -> float:
        """Return ``Q_grid``: the source grid's own charge, in coulombs.

        The planar integral for an areal density, because the ``2*pi*r`` cancels
        (§4.4 NOTE); the radially weighted one for a volume density, which gets
        no such cancellation and whose check therefore *does* exercise the
        Jacobian.
        """
        return self.grid.integral(radial=not self.is_areal)

    def mesh_integral_C(self, mesh: Mesh, measures: Measures, *, refined: bool = False) -> float:
        """Return ``Q_mesh``: the assembled density integrated over the mesh.

        The ``2*pi`` is restored here, once and in this layer.
        :meth:`~nanopnp.physics.measures.Measures.integrate` applies the ``r``
        weight of the axisymmetric forms and not the ``2*pi``, which cancels from
        both sides of every weak form and does not cancel from a charge; the
        Phase-0 rule names ``io/``, ``sweep/`` and ``gui/`` as the layers that
        must not re-apply it, and those consume a QoI rather than produce one.

        Parameters
        ----------
        mesh
            The deployed mesh, in nm.
        measures
            The quadrature policy. Its order is the one the solve assembles at,
            which is what makes this the conservation of the charge the solver
            actually carries.
        refined
            Evaluate :data:`QUADRATURE_REFINEMENT` orders above the assembly
            order, for the agreement check. See that constant for why the
            refinement is computed from the bonus rather than passed as it.
        """
        import math

        extra_order = 0
        if refined:
            extra_order = measures.bonus_order(singular=self.is_areal) + QUADRATURE_REFINEMENT
        integral_nm = measures.integrate(
            self.volume_density_C_m3(),
            mesh,
            singular=self.is_areal,
            extra_order=extra_order,
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
        """Return the mesh-side cumulative below each plane, ramped (§4.4 NOTE)."""
        import math

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
                    singular=self.is_areal,
                    what=f"the cumulative fixed charge below z = {plane:g} nm",
                )
            )
        return tuple(values)

    def grid_cumulative_C(
        self, planes_nm: Sequence[float], *, ramp_nm: float = DEFAULT_RAMP_NM
    ) -> tuple[float, ...]:
        """Return the grid-side cumulative below each plane, ramped identically."""
        return self.grid.cumulative(planes_nm, ramp_nm=ramp_nm, radial=not self.is_areal)


def load_field(path: str | Path) -> ChargeField:
    """Read a field document and its grid, and return the charge field.

    Raises
    ------
    FieldDocumentError
        If the document is invalid, disagrees with its data, or names a quantity
        that is not a charge.
    GridFormatError
        If the data file cannot be read.
    """
    source = Path(path)
    document = load_document(source)
    return ChargeField(
        document=document, grid=load_grid(document, base=source.parent), source=source
    )


# -- the conservation report ---------------------------------------------------


@dataclass(frozen=True)
class ConservationReport:
    """What PHY-19's assertion measured, decomposed (§4.4 NOTE, QR-03).

    Parameters
    ----------
    q_net_C, q_grid_C, q_mesh_C
        The producer's declared charge, the source grid's own planar integral,
        and the integral over the deployed mesh. ``q_net_C`` is ``None`` when the
        producer declared none, and the producer leg is then not run.
    q_mesh_refined_C
        The same mesh integral :data:`QUADRATURE_REFINEMENT` orders higher.
    guard_deficit_C
        The charge the PHY-18 axis guard deletes.
    ring, interior_maximum
        The grid's boundary-ring maximum and its interior maximum, in the
        quantity's own units.
    planes_nm, grid_cumulative_C, mesh_cumulative_C, ramp_nm
        The per-plane check: the planes, both sides, and the ramp width both
        were evaluated with.
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
        """The magnitude every absolute tolerance is taken against.

        ``|Q_net|`` when the producer declared one, and ``|Q_grid|`` otherwise:
        skipping the whole assertion because its reference is absent is how a
        conservation failure reaches a published number (§4.4 NOTE).
        """
        return abs(self.q_net_C if self.q_net_C is not None else self.q_grid_C)

    @property
    def producer_error(self) -> float | None:
        """``(Q_grid - Q_net) / |Q_net|``, or ``None`` if none was declared."""
        if self.q_net_C is None:
            return None
        return (self.q_grid_C - self.q_net_C) / abs(self.q_net_C)

    @property
    def consumer_error(self) -> float:
        """``(Q_mesh - Q_grid) / |Q_grid|``: interpolation, quadrature, footprint."""
        return (self.q_mesh_C - self.q_grid_C) / abs(self.q_grid_C)

    @property
    def quadrature_error(self) -> float:
        """``|Q_mesh(order) - Q_mesh(order + 3)| / reference``."""
        return abs(self.q_mesh_C - self.q_mesh_refined_C) / self.reference_C

    @property
    def ring_ratio(self) -> float:
        """The boundary ring against the grid's interior maximum."""
        return self.ring.value / self.interior_maximum if self.interior_maximum else 0.0

    @property
    def worst_plane(self) -> tuple[float, float]:
        """The plane with the largest cumulative disagreement, and that error."""
        if not self.planes_nm:
            return (float("nan"), 0.0)
        errors = [
            (abs(mesh - grid) / self.reference_C, plane)
            for plane, grid, mesh in zip(
                self.planes_nm, self.grid_cumulative_C, self.mesh_cumulative_C, strict=True
            )
        ]
        error, plane = max(errors)
        return (plane, error)

    def summary(self) -> dict[str, object]:
        """Return the manifest's record of this check (FR-25, §5.3.3)."""
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
    """Return a ladder of ``z`` planes spanning the grid, ends excluded.

    The ends carry no information — the cumulative is 0 below the first and
    ``Q_grid`` above the last, both of which the global check already tests.
    """
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
    """Measure PHY-19's assertion on the deployed mesh, without gating it.

    Separate from :func:`check_conservation` so that a caller can record the
    numbers for a field that fails — which is what a diagnostic run needs, and
    what makes the failure attributable.
    """
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


def check_conservation(report: ConservationReport) -> ConservationReport:
    """Gate a conservation report, aborting on the first failure (QR-12).

    The order is deliberate: the truncation and quadrature gates come first
    because each explains a conservation failure, and reporting "charge is not
    conserved" when the real fact is "this grid was cut short" or "this mesh
    cannot resolve this field" names the wrong culprit.

    Returns
    -------
    ConservationReport
        ``report`` itself, so a caller can gate and record in one expression.

    Raises
    ------
    ChargeFieldError
        Naming the gate, the offending quantity and, where there is one, its
        location.
    """
    if report.ring_ratio > RING_TOL:
        raise ChargeFieldError(
            "the supplied grid is truncated",
            f"its boundary ring reaches {report.ring.value:.6g} against an interior maximum of "
            f"{report.interior_maximum:.6g}, a ratio of {report.ring_ratio:.3g} against the "
            f"{RING_TOL:g} this gate allows. The interpolant is zero outside the grid box, so "
            "this charge would be discarded silently; PHY-16 step 4 asks for >= 4 sigma beyond "
            "the structure",
            f"(r, z) = ({report.ring.r_nm:.4g}, {report.ring.z_nm:.4g}) nm",
        )
    if report.quadrature_error > QUADRATURE_TOL:
        raise ChargeFieldError(
            "the deployed mesh under-resolves the supplied field",
            f"the charge integral moves by {report.quadrature_error:.3g} of the reference charge "
            f"between the assembly order and three orders above it, against the "
            f"{QUADRATURE_TOL:g} this gate allows. The conservation check below it is a "
            "quadrature-resolution check on this mesh, so its number cannot be defended",
        )
    producer = report.producer_error
    if producer is not None and abs(producer) > CONSERVATION_TOL:
        raise ChargeFieldError(
            "the supplied field does not carry the charge it declares (producer leg, QR-03)",
            f"its grid integrates to {report.q_grid_C / ELEMENTARY_CHARGE:.6g} e against a "
            f"declared q_net_e of {report.q_net_C / ELEMENTARY_CHARGE if report.q_net_C else 0:.6g}"
            f", a relative error of {producer:.3g} against {CONSERVATION_TOL:g}. This leg is the "
            "producer's: smearing, projection and the annular volumes",
        )
    if abs(report.consumer_error) > CONSERVATION_TOL:
        raise ChargeFieldError(
            "the assembled charge is not conserved on the deployed mesh (consumer leg, QR-03)",
            f"the mesh carries {report.q_mesh_C / ELEMENTARY_CHARGE:.6g} e against the grid's "
            f"{report.q_grid_C / ELEMENTARY_CHARGE:.6g} e, a relative error of "
            f"{report.consumer_error:.3g} against {CONSERVATION_TOL:g}. This leg is the "
            "consumer's: interpolation, quadrature, the mesh's coverage of the grid and the axis "
            f"guard, which deletes {report.guard_deficit_C / ELEMENTARY_CHARGE:.3g} e",
        )
    plane, plane_error = report.worst_plane
    if plane_error > CONSERVATION_TOL:
        raise ChargeFieldError(
            "the cumulative charge disagrees with the source grid at a z plane (PHY-19)",
            f"the mesh carries {plane_error:.3g} of the reference charge more or less than the "
            f"grid below this plane, against {CONSERVATION_TOL:g}. A globally satisfied check can "
            "hide compensating local errors, which is what this one is for",
            f"z = {plane:.4g} nm",
        )
    return report
