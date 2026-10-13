"""The correction-model registry (FR-16, ADR-005, section 5.4.2)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
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

SPECIES_PROPERTIES: frozenset[str] = frozenset({"diffusivity", "mobility"})


class CorrectionModel(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def parameters(self) -> Mapping[str, float]: ...

    @property
    def provenance(self) -> Mapping[str, str]: ...

    def evaluate(
        self, c_avg_M: Numeric, wall_distance_nm: Numeric, ops: MathOps = NUMPY_OPS
    ) -> Numeric: ...


@dataclass(frozen=True)
class NoCorrection:
    property_kind: PropertyKind
    species: str | None = None

    @property
    def name(self) -> str:
        return "none"

    @property
    def parameters(self) -> Mapping[str, float]:
        return {}

    @property
    def provenance(self) -> Mapping[str, str]:
        return {"model": "none", "note": "correction disabled; factor is identically 1"}

    def evaluate(
        self, c_avg_M: Numeric, wall_distance_nm: Numeric, ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        del c_avg_M, wall_distance_nm, ops
        return 1.0


@dataclass(frozen=True)
class FittedCorrection:
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
    def parameters(self) -> Mapping[str, float]:
        flat: dict[str, float] = {}
        if self.use_concentration:
            flat.update({f"fc.{k}": v for k, v in self.concentration_params.items()})
        if self.use_wall:
            flat.update({f"fw.{k}": v for k, v in self.wall_params.items()})
        return flat

    @property
    def provenance(self) -> Mapping[str, str]:
        # the form in force, not the one the file offers, or an ablated run looks full
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
        return form if enabled and form is not None else "off"

    def evaluate(
        self, c_avg_M: Numeric, wall_distance_nm: Numeric, ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        factor: Numeric = 1.0
        if self.use_concentration and self.concentration_form is not None:
            # clamping the driver applies the cap and keeps sqrt away from negatives
            lower, upper = self.validity_M
            clamped = ops.clip(c_avg_M, lower, upper)
            factor = get_form(self.concentration_form)(self.concentration_params, clamped, ops)
        if self.use_wall and self.wall_form is not None:
            # a negative distance sample reverses D_i's sign (SPECIFICATION PHY-02); the
            # driver is floored, not the factor, which would be a degenerate operator
            floored = ops.clip(wall_distance_nm, 0.0, None)
            factor = factor * get_form(self.wall_form)(self.wall_params, floored, ops)
        return factor


ModelBuilder: TypeAlias = Callable[[PropertyKind, str | None, bool, bool], CorrectionModel]

_REGISTRY: dict[str, ModelBuilder] = {}


def register(name: str, builder: ModelBuilder) -> None:
    if name in _REGISTRY:
        raise ValueError(f"correction model {name!r} is already registered")
    _REGISTRY[name] = builder


def registered_models() -> tuple[str, ...]:
    return tuple(sorted(set(_REGISTRY) | set(available_corrections())))


def _resolve(name: str) -> ModelBuilder:
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
    if (species is not None) != (property_kind in SPECIES_PROPERTIES):
        expected = "an ion name" if property_kind in SPECIES_PROPERTIES else "no species"
        raise ValueError(f"property {property_kind!r} takes {expected}, got species={species!r}")
    return _resolve(name)(property_kind, species, concentration, wall)


def _build_none(
    property_kind: PropertyKind, species: str | None, concentration: bool, wall: bool
) -> CorrectionModel:
    del concentration, wall
    return NoCorrection(property_kind=property_kind, species=species)


def _document(model_name: str) -> CorrectionDocument:
    return load_corrections(model_name)


def validity_range(document: CorrectionDocument) -> tuple[float, float]:
    return document.concentration_validity_M


def applied_parts(model_name: str, property_kind: PropertyKind) -> frozenset[str]:
    if model_name == "none":
        return frozenset()
    document = _document(model_name)
    parts: set[str] = set()
    if property_kind in SPECIES_PROPERTIES:
        has_fc = any(
            (ion.diffusivity.fc if property_kind == "diffusivity" else ion.mobility.fc) is not None
            for ion in document.species.values()
        )
        if has_fc:
            parts.add("concentration")
        if document.ion_wall_function is not None:
            parts.add("wall")
    else:
        solvent = {
            "viscosity": document.solvent.viscosity,
            "density": document.solvent.density,
            "permittivity": document.solvent.permittivity,
        }
        node = solvent[property_kind]
        if node.fc is not None:
            parts.add("concentration")
        if node.fw is not None:
            parts.add("wall")
    return frozenset(parts)


def applies_part(model_name: str, property_kind: PropertyKind, part: str) -> bool:
    return part in applied_parts(model_name, property_kind)


def _property_node(
    document: CorrectionDocument, kind: PropertyKind, species: str | None
) -> PropertyBlock:
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

    def build(
        property_kind: PropertyKind, species: str | None, concentration: bool, wall: bool
    ) -> CorrectionModel:
        document = _document(model_name)
        node = _property_node(document, property_kind, species)
        fc = node.fc
        # diffusivity and mobility share one ion wall function (PHY-11)
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
