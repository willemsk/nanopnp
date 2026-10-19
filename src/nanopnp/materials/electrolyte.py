"""The electrolyte: reference properties, correction switches and the driver field."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from nanopnp.core.constants import thermal_voltage
from nanopnp.materials import models
from nanopnp.materials.corrections import load_corrections
from nanopnp.materials.forms import NUMPY_OPS, MathOps, Numeric

logger = logging.getLogger(__name__)

# Each c_i is floored here before the driver average: SPECIFICATION.md PHY-01.
CONCENTRATION_FLOOR_M = 1e-6

MOLAR_PER_SI = 1e-3


@dataclass(frozen=True)
class CorrectionChoice:
    """One property's entry in the case file's ``corrections`` block."""

    model: str = "none"
    concentration: bool = True
    wall: bool = True

    def build(
        self, kind: models.PropertyKind, species: str | None = None
    ) -> models.CorrectionModel:
        """Resolve this choice to a correction model."""
        return models.create(
            self.model,
            kind,
            species,
            concentration=self.concentration,
            wall=self.wall,
        )


@dataclass(frozen=True)
class CorrectionSwitches:
    """Which correction applies to each property; all off until a model is named."""

    diffusivity: CorrectionChoice = CorrectionChoice()
    mobility: CorrectionChoice = CorrectionChoice()
    viscosity: CorrectionChoice = CorrectionChoice()
    permittivity: CorrectionChoice = CorrectionChoice()
    density: CorrectionChoice = CorrectionChoice()
    steric: bool = False

    @classmethod
    def for_model(cls, model: str) -> CorrectionSwitches:
        """Return every correction enabled against one named model."""
        choice = CorrectionChoice(model=model)
        return cls(
            diffusivity=choice,
            mobility=choice,
            viscosity=choice,
            permittivity=choice,
            density=choice,
            steric=True,
        )

    @classmethod
    def classical(cls) -> CorrectionSwitches:
        """Return the classical configuration: every correction off."""
        return cls()

    def without(self, *properties: str) -> CorrectionSwitches:
        """Return a copy with the named properties disabled; ValueError for an unknown name."""
        known = {"diffusivity", "mobility", "viscosity", "permittivity", "density", "steric"}
        unknown = sorted(set(properties) - known)
        if unknown:
            raise ValueError(
                f"no correction property {', '.join(unknown)}; the switchable properties are "
                f"{', '.join(sorted(known))}"
            )
        disabled = set(properties)
        off = CorrectionChoice()
        return replace(
            self,
            diffusivity=off if "diffusivity" in disabled else self.diffusivity,
            mobility=off if "mobility" in disabled else self.mobility,
            viscosity=off if "viscosity" in disabled else self.viscosity,
            permittivity=off if "permittivity" in disabled else self.permittivity,
            density=off if "density" in disabled else self.density,
            steric=False if "steric" in disabled else self.steric,
        )


@dataclass(frozen=True)
class IonSpecies:
    """One solved ionic species and its infinite-dilution properties."""

    name: str
    valence: int
    diffusivity_0: float
    steric_diameter: float
    temperature_K: float = 298.15

    @property
    def mobility_0(self) -> float:
        """``mu_i^0 = D_i^0 / V_T`` in m^2/(V s): derived, never fitted."""
        return self.diffusivity_0 / thermal_voltage(self.temperature_K)


def _resolve_corrections(
    switches: CorrectionSwitches, species: Sequence[IonSpecies]
) -> dict[str, models.CorrectionModel]:
    resolved: dict[str, models.CorrectionModel] = {
        "viscosity": switches.viscosity.build("viscosity"),
        "density": switches.density.build("density"),
        "permittivity": switches.permittivity.build("permittivity"),
    }
    for ion in species:
        resolved[f"diffusivity:{ion.name}"] = switches.diffusivity.build("diffusivity", ion.name)
        resolved[f"mobility:{ion.name}"] = switches.mobility.build("mobility", ion.name)
    return resolved


@dataclass(frozen=True)
class Electrolyte:
    """A binary or multi-species electrolyte with its corrections resolved."""

    species: tuple[IonSpecies, ...]
    switches: CorrectionSwitches
    temperature_K: float
    viscosity_0: float
    mass_density_0: float
    permittivity_0: float
    water_steric_diameter: float
    protein_permittivity: float
    membrane_permittivity: float
    validity_M: tuple[float, float]
    corrections: Mapping[str, models.CorrectionModel]
    driver: str = "average"
    parameter_file: str = ""

    def __post_init__(self) -> None:
        mismatched = [ion.name for ion in self.species if ion.temperature_K != self.temperature_K]
        if mismatched:
            raise ValueError(
                f"species {', '.join(mismatched)} carry a temperature different from the "
                f"electrolyte's {self.temperature_K} K; mu_i^0 = D_i^0 / V_T(T) would then be "
                "evaluated at the wrong temperature"
            )
        self._reject_switches_that_disagree_with_the_corrections()

    def _reject_switches_that_disagree_with_the_corrections(self) -> None:
        expected = {
            "viscosity": self.switches.viscosity,
            "density": self.switches.density,
            "permittivity": self.switches.permittivity,
        }
        for ion in self.species:
            expected[f"diffusivity:{ion.name}"] = self.switches.diffusivity
            expected[f"mobility:{ion.name}"] = self.switches.mobility

        disagreements: list[str] = []
        for key, choice in expected.items():
            resolved = self.corrections.get(key)
            if resolved is None:
                disagreements.append(f"{key}: no correction resolved at all")
                continue
            if resolved.name != choice.model:
                disagreements.append(
                    f"{key}: switches say {choice.model!r}, corrections hold {resolved.name!r}"
                )
                continue
            # ``none`` carries neither flag and needs no check
            for part, wanted in (("concentration", choice.concentration), ("wall", choice.wall)):
                actual = getattr(resolved, f"use_{part}", wanted)
                if actual != wanted:
                    disagreements.append(
                        f"{key}: switches say {part}={wanted}, corrections hold {part}={actual}"
                    )
        if disagreements:
            raise ValueError(
                "this electrolyte's switches and its resolved corrections disagree, so it "
                "would report one configuration and evaluate another:\n  "
                + "\n  ".join(disagreements)
                + "\nUse Electrolyte.with_switches() to change the configuration; "
                "dataclasses.replace(..., switches=...) changes only the record."
            )

    def with_switches(self, switches: CorrectionSwitches) -> Electrolyte:
        """Return the same electrolyte with a different correction configuration."""
        return replace(
            self, switches=switches, corrections=_resolve_corrections(switches, self.species)
        )

    @classmethod
    def from_parameter_file(
        cls,
        model: str = "willems2020_nacl",
        *,
        switches: CorrectionSwitches | None = None,
        species: Sequence[str] | None = None,
        driver: str = "average",
    ) -> Electrolyte:
        """Build an electrolyte from a registered correction parameter file."""
        if driver not in {"average", "ionic_strength"}:
            raise ValueError(f"unknown correction driver {driver!r}; use average or ionic_strength")
        document = load_corrections(model)
        active = CorrectionSwitches.for_model(model) if switches is None else switches
        temperature_K = document.temperature_K
        names = tuple(species) if species is not None else tuple(document.species)
        ions = tuple(
            IonSpecies(
                name=name,
                valence=document.species[name].z,
                diffusivity_0=document.species[name].diffusivity.D0,
                steric_diameter=document.species[name].steric_diameter_nm * 1e-9,
                temperature_K=temperature_K,
            )
            for name in names
        )
        solvent = document.solvent
        resolved = _resolve_corrections(active, ions)
        return cls(
            species=ions,
            switches=active,
            temperature_K=temperature_K,
            viscosity_0=solvent.viscosity.eta0,
            mass_density_0=solvent.density.rho0,
            permittivity_0=solvent.permittivity.eps_r0,
            water_steric_diameter=solvent.water_steric_diameter_nm * 1e-9,
            protein_permittivity=document.dielectrics.protein,
            membrane_permittivity=document.dielectrics.membrane,
            validity_M=models.validity_range(document),
            driver=driver,
            parameter_file=model,
            corrections=resolved,
        )

    def correction(
        self, kind: models.PropertyKind, species: str | None = None
    ) -> models.CorrectionModel:
        """Return the correction model in force for one property."""
        key = kind if species is None else f"{kind}:{species}"
        return self.corrections[key]

    def ion(self, name: str) -> IonSpecies:
        """Return the named species; KeyError if the electrolyte does not solve for that ion."""
        for candidate in self.species:
            if candidate.name == name:
                return candidate
        known = ", ".join(s.name for s in self.species)
        raise KeyError(f"no species {name!r} in this electrolyte; it has {known}")

    def average_concentration(
        self, concentrations: Sequence[Numeric], ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        """Return the correction driver ``<c>`` in mol/L: the mean clamped ion concentration."""
        if len(concentrations) != len(self.species):
            raise ValueError(
                f"expected {len(self.species)} concentrations, got {len(concentrations)}"
            )
        lower, upper = CONCENTRATION_FLOOR_M, self.validity_M[1]
        clamped = [ops.clip(c * MOLAR_PER_SI, lower, upper) for c in concentrations]
        if self.driver == "ionic_strength":
            weighted = [
                0.5 * ion.valence**2 * c for ion, c in zip(self.species, clamped, strict=True)
            ]
            return sum(weighted[1:], start=weighted[0])
        total = sum(clamped[1:], start=clamped[0])
        return total / len(clamped)

    def diffusivity(
        self,
        species: str,
        c_avg_M: Numeric,
        wall_distance_nm: Numeric,
        ops: MathOps = NUMPY_OPS,
    ) -> Numeric:
        """Return ``D_i(<c>, d)`` in m^2/s."""
        ion = self.ion(species)
        factor = self.correction("diffusivity", species).evaluate(c_avg_M, wall_distance_nm, ops)
        return ion.diffusivity_0 * factor

    def mobility(
        self,
        species: str,
        c_avg_M: Numeric,
        wall_distance_nm: Numeric,
        ops: MathOps = NUMPY_OPS,
    ) -> Numeric:
        """Return ``mu_i(<c>, d)`` in m^2/(V s): ``D_i^0 / V_T`` times the mobility correction."""
        ion = self.ion(species)
        factor = self.correction("mobility", species).evaluate(c_avg_M, wall_distance_nm, ops)
        return ion.mobility_0 * factor

    def viscosity(
        self, c_avg_M: Numeric, wall_distance_nm: Numeric, ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        """Return ``eta(<c>, d)`` in Pa s."""
        return self.viscosity_0 * self.correction("viscosity").evaluate(
            c_avg_M, wall_distance_nm, ops
        )

    def mass_density(
        self, c_avg_M: Numeric, wall_distance_nm: Numeric = 0.0, ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        """Return ``rho(<c>)`` in kg/m^3; there is no wall correction on density."""
        return self.mass_density_0 * self.correction("density").evaluate(
            c_avg_M, wall_distance_nm, ops
        )

    def relative_permittivity(
        self, c_avg_M: Numeric, wall_distance_nm: Numeric = 0.0, ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        """Return the electrolyte ``eps_r,f(<c>)``; there is no wall correction."""
        factor = self.correction("permittivity").evaluate(c_avg_M, wall_distance_nm, ops)
        return self.permittivity_0 * factor

    def report_clamp_activations(
        self,
        concentrations: Sequence[Numeric],
        *,
        coordinates: Sequence[tuple[float, ...]] | None = None,
    ) -> int:
        """Log every species and driver clamp activation and return the total count.

        Parameters
        ----------
        coordinates
            Optional sample locations, shared by every species.
        """
        if len(concentrations) != len(self.species):
            raise ValueError(
                f"expected {len(self.species)} concentrations, got {len(concentrations)}"
            )
        import numpy as np

        limit = self.validity_M[1]
        samples = [np.asarray(values, dtype=float) for values in concentrations]
        species_count = sum(
            log_clamp_activations(
                values * MOLAR_PER_SI,
                label=f"{ion.name} concentration",
                limit=limit,
                coordinates=coordinates,
            )
            for ion, values in zip(self.species, samples, strict=True)
        )
        driver_label = f"correction driver ({self.driver.replace('_', ' ')})"
        driver_count = log_clamp_activations(
            self.average_concentration(samples),
            label=driver_label,
            limit=limit,
            coordinates=coordinates,
        )
        return species_count + driver_count

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Return what a result manifest must record about the materials."""
        return {
            "parameter_file": self.parameter_file,
            "temperature_K": self.temperature_K,
            "driver": self.driver,
            "species": [ion.name for ion in self.species],
            "steric": self.switches.steric,
            "validity_M": list(self.validity_M),
            "corrections": {
                key: dict(model.provenance) for key, model in sorted(self.corrections.items())
            },
        }


def log_clamp_activations(
    values_M: Numeric,
    *,
    label: str,
    limit: float,
    coordinates: Sequence[tuple[float, ...]] | None = None,
) -> int:
    """Log where the concentration fits were extrapolated past their validity range.

    Parameters
    ----------
    values_M
        Sampled driver concentrations, in mol/L.
    limit
        Upper end of the fit validity range, in mol/L.
    """
    import numpy as np

    array = np.asarray(values_M, dtype=float)
    exceeded = np.flatnonzero(array > limit)
    if exceeded.size == 0:
        return 0
    worst = int(exceeded[np.argmax(array[exceeded])])
    where = "" if coordinates is None else f" worst at {coordinates[worst]}"
    logger.warning(
        "%s: concentration correction clamped at %.3g M for %d sample(s); "
        "peak concentration %.4g M is outside the fit range.%s",
        label,
        limit,
        exceeded.size,
        float(array[worst]),
        where,
    )
    return int(exceeded.size)
