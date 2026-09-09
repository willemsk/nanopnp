"""The correction-model registry (FR-16, ADR-005, section 5.4.2).

A correction model is named by string in the case file and resolved here. Its
coefficients live in a versioned data file under ``data/corrections``; adding an
electrolyte is therefore a data file, never a code change.

Disabling a correction selects the registered ``none`` model rather than taking
a code branch (PHY-22). That is what makes classical PNP-NS a *configuration* of
ePNP-NS (PHY-21) and what makes correction-by-correction ablation a sweep rather
than a rebuild.

Every model returns the **dimensionless** factor ``f_c(c_bar) * f_w(d_bar)``.
The reference value ``X0`` that it multiplies belongs to the electrolyte, not to
the correction, so that ``none`` reproduces ``X = X0`` exactly.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import cache
from typing import Literal, Protocol, TypeAlias

from nanopnp.core.paths import available_corrections
from nanopnp.materials.corrections import (
    CorrectionDocument,
    FitBlock,
    PropertyBlock,
    load_corrections,
)
from nanopnp.materials.forms import NUMPY_OPS, MathOps, Numeric, get_form

PropertyKind: TypeAlias = Literal["diffusivity", "mobility", "viscosity", "density", "permittivity"]
"""The five corrected properties of PHY-11."""

SPECIES_PROPERTIES: frozenset[str] = frozenset({"diffusivity", "mobility"})
"""Properties whose coefficients are per ion; the rest belong to the solvent."""


class CorrectionModel(Protocol):
    """One property's correction, as section 5.4.2 requires it.

    Implementations are immutable and carry their own provenance, so that a
    result can record which parameter file and which model version produced it
    (FR-25).
    """

    @property
    def name(self) -> str:
        """Registered name of the model."""
        ...

    @property
    def parameters(self) -> Mapping[str, float]:
        """Fit coefficients in force, flattened for reporting."""
        ...

    @property
    def provenance(self) -> Mapping[str, str]:
        """Where the coefficients came from."""
        ...

    def evaluate(
        self, c_avg_M: Numeric, wall_distance_nm: Numeric, ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        """Return the dimensionless correction factor.

        Parameters
        ----------
        c_avg_M
            Correction driver ``<c>`` in mol/L, the unit the fits are stated in.
            The suffix is part of the name because this is *not* the solver's
            SI unit: passing mol/m^3 here would silently clamp to the 5.3 M cap.
        wall_distance_nm
            Distance to the nearest pore boundary in nm (PHY-02), likewise the
            unit the fits are stated in rather than the SI one.
        ops
            Operation namespace: NumPy for diagnostics and tests, NGSolve for
            assembly.
        """
        ...


@dataclass(frozen=True)
class NoCorrection:
    """The ``none`` model: the property keeps its reference value everywhere.

    Selecting this for every property, together with ``beta_i = 0``, recovers
    classical PNP-NS exactly (PHY-21).
    """

    property_kind: PropertyKind
    species: str | None = None

    @property
    def name(self) -> str:  # noqa: D102 - documented on the protocol
        return "none"

    @property
    def parameters(self) -> Mapping[str, float]:  # noqa: D102
        return {}

    @property
    def provenance(self) -> Mapping[str, str]:  # noqa: D102
        return {"model": "none", "note": "correction disabled; factor is identically 1"}

    def evaluate(  # noqa: D102
        self, c_avg_M: Numeric, wall_distance_nm: Numeric, ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        del c_avg_M, wall_distance_nm, ops
        return 1.0


@dataclass(frozen=True)
class FittedCorrection:
    """A correction read from a versioned parameter file.

    The concentration and wall parts are independently switchable, matching the
    case-file vocabulary ``{model: ..., wall: true, concentration: true}``.
    """

    name: str
    property_kind: PropertyKind
    species: str | None
    concentration_form: str | None
    concentration_params: Mapping[str, float]
    wall_form: str | None
    wall_params: Mapping[str, float]
    validity_M: tuple[float, float]
    use_concentration: bool = True
    use_wall: bool = True
    source: str = ""
    _extra_provenance: Mapping[str, str] = field(default_factory=dict)

    @property
    def parameters(self) -> Mapping[str, float]:  # noqa: D102
        flat: dict[str, float] = {}
        if self.use_concentration:
            flat.update({f"fc.{k}": v for k, v in self.concentration_params.items()})
        if self.use_wall:
            flat.update({f"fw.{k}": v for k, v in self.wall_params.items()})
        return flat

    @property
    def provenance(self) -> Mapping[str, str]:  # noqa: D102
        # FR-25 requires every switch set away from the validated default to be
        # recorded. Reporting the form a file *offers* rather than the one in
        # force would make an ablated run indistinguishable from the full one.
        record = {
            "model": self.name,
            "property": self.property_kind,
            "source": self.source,
            "concentration_form": self._active_form(
                self.concentration_form, self.use_concentration
            ),
            "wall_form": self._active_form(self.wall_form, self.use_wall),
            "concentration_enabled": str(self.use_concentration).lower(),
            "wall_enabled": str(self.use_wall).lower(),
            "validity_M": f"{self.validity_M[0]:g}-{self.validity_M[1]:g}",
        }
        if self.species is not None:
            record["species"] = self.species
        record.update(self._extra_provenance)
        return record

    @staticmethod
    def _active_form(form: str | None, enabled: bool) -> str:
        """Return the form actually evaluated, or ``"off"`` if it is switched out."""
        return form if enabled and form is not None else "off"

    def evaluate(  # noqa: D102
        self, c_avg_M: Numeric, wall_distance_nm: Numeric, ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        factor: Numeric = 1.0
        if self.use_concentration and self.concentration_form is not None:
            # PHY-13: the fits hold to 5.3 M and every property is capped at its
            # value there. Clamping the driver is how that cap is applied, and it
            # also keeps the half-integer powers away from negative arguments.
            lower, upper = self.validity_M
            clamped = ops.clip(c_avg_M, lower, upper)
            factor = get_form(self.concentration_form)(self.concentration_params, clamped, ops)
        if self.use_wall and self.wall_form is not None:
            # PHY-02: the wall fits are stated for d >= 0, and the ion form
            # ``1 - exp(-P1 (d + P2))`` has its root at ``d = -P2`` rather than
            # decaying to zero -- so a negative sample does not attenuate D_i
            # and mu_i, it reverses their sign. A distance is non-negative by
            # definition, so a negative sample is a discretisation artefact
            # whose nearest admissible value is zero. Clamped here, on the
            # driver, so that a new electrolyte's wall fit inherits it by
            # shipping a YAML file; the *factor* is deliberately not clamped,
            # because a factor floored at zero is a degenerate operator rather
            # than an attenuated one. NUM-34, not this floor, decides whether
            # a field that needed it is admissible at all.
            floored = ops.clip(wall_distance_nm, 0.0, None)
            factor = factor * get_form(self.wall_form)(self.wall_params, floored, ops)
        return factor


ModelBuilder: TypeAlias = Callable[[PropertyKind, str | None, bool, bool], CorrectionModel]
"""Builds one property's model: ``(property, species, concentration, wall)``."""

_REGISTRY: dict[str, ModelBuilder] = {}


def register(name: str, builder: ModelBuilder) -> None:
    """Register a correction model under ``name``.

    Raises
    ------
    ValueError
        If the name is already registered, which would silently change the
        meaning of existing case files.
    """
    if name in _REGISTRY:
        raise ValueError(f"correction model {name!r} is already registered")
    _REGISTRY[name] = builder


def registered_models() -> tuple[str, ...]:
    """Return every selectable model name, sorted.

    That is the explicitly registered builders plus every parameter file
    installed under ``data/corrections``: a new electrolyte becomes selectable
    by shipping its YAML, with no edit to this module (FR-16, ADR-005).
    """
    return tuple(sorted(set(_REGISTRY) | set(available_corrections())))


def _resolve(name: str) -> ModelBuilder:
    """Return the builder for ``name``, registering a file-backed one on demand.

    Raises
    ------
    KeyError
        If neither a builder nor a parameter file of that name exists; the
        message lists the names that are selectable.
    """
    builder = _REGISTRY.get(name)
    if builder is not None:
        return builder
    if name in available_corrections():
        builder = _file_backed_builder(name)
        _REGISTRY[name] = builder
        return builder
    known = ", ".join(registered_models())
    raise KeyError(f"unknown correction model {name!r}; registered models are {known}")


def create(
    name: str,
    property_kind: PropertyKind,
    species: str | None = None,
    *,
    concentration: bool = True,
    wall: bool = True,
) -> CorrectionModel:
    """Build the model registered as ``name`` for one property.

    Parameters
    ----------
    name
        Registered model name, ``"none"`` to disable the correction.
    property_kind
        Which property the model is being built for.
    species
        Ion name for ``diffusivity`` and ``mobility``; ``None`` otherwise.
    concentration, wall
        Whether the respective part of the correction is active.

    Raises
    ------
    KeyError
        If no such model is registered; the message lists the known names.
    ValueError
        If ``species`` is given for a solvent property or omitted for an ionic
        one.
    """
    if (species is not None) != (property_kind in SPECIES_PROPERTIES):
        expected = "an ion name" if property_kind in SPECIES_PROPERTIES else "no species"
        raise ValueError(f"property {property_kind!r} takes {expected}, got species={species!r}")
    return _resolve(name)(property_kind, species, concentration, wall)


def _build_none(
    property_kind: PropertyKind, species: str | None, concentration: bool, wall: bool
) -> CorrectionModel:
    del concentration, wall
    return NoCorrection(property_kind=property_kind, species=species)


@cache
def _document(model_name: str) -> CorrectionDocument:
    """Return the validated parameter file, read once per model name."""
    return load_corrections(model_name)


def validity_range(document: CorrectionDocument) -> tuple[float, float]:
    """Return a parameter file's concentration validity range, in mol/L.

    The range is a required field of the schema and a property of the fits in
    *that* file: silently borrowing NaCl's 0-5.3 M would extrapolate another
    electrolyte past its own limit with no gate failure (PHY-13, QR-12).
    """
    return document.concentration_validity_M


def _property_node(
    document: CorrectionDocument, kind: PropertyKind, species: str | None
) -> PropertyBlock:
    """Return the parameter block for one property.

    Raises
    ------
    KeyError
        If the file carries no coefficients for that species.
    """
    if kind not in SPECIES_PROPERTIES:
        solvent: dict[str, PropertyBlock] = {
            "viscosity": document.solvent.viscosity,
            "density": document.solvent.density,
            "permittivity": document.solvent.permittivity,
        }
        return solvent[kind]
    table = document.species
    if species not in table:
        known = ", ".join(sorted(table))
        raise KeyError(f"no species {species!r} in the parameter file; it has {known}")
    ion = table[species]
    return ion.diffusivity if kind == "diffusivity" else ion.mobility


def _file_backed_builder(model_name: str) -> ModelBuilder:
    """Return a builder reading its coefficients from a packaged parameter file."""

    def build(
        property_kind: PropertyKind, species: str | None, concentration: bool, wall: bool
    ) -> CorrectionModel:
        document = _document(model_name)
        node = _property_node(document, property_kind, species)
        fc = node.fc
        # Diffusivity and mobility share one ion wall function (PHY-11); the
        # solvent properties carry their own, or none at all.
        if property_kind in SPECIES_PROPERTIES:
            fw: FitBlock | None = document.ion_wall_function
        else:
            fw = node.fw
        return FittedCorrection(
            name=model_name,
            property_kind=property_kind,
            species=species,
            concentration_form=None if fc is None else fc.form,
            concentration_params={} if fc is None else fc.coefficients,
            wall_form=None if fw is None else fw.form,
            wall_params={} if fw is None else fw.coefficients,
            validity_M=validity_range(document),
            use_concentration=concentration,
            use_wall=wall,
            source=document.name,
        )

    return build


register("none", _build_none)
