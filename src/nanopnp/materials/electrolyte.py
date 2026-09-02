"""The electrolyte: reference properties, correction switches and the driver field.

This is the layer the weak forms ask for ``D_i``, ``mu_i``, ``eta``, ``rho`` and
``eps_r``. It owns the reference values ``X0`` and the choice of correction model
per property, so that turning every correction to ``none`` reproduces classical
PNP-NS exactly (PHY-21) with no second code path.

Units: concentrations enter in mol/m^3, the SI unit the solver works in, and the
correction driver ``<c>`` leaves in mol/L, the unit the fits are stated in. Wall
distances are in nm throughout, likewise following the fits.
"""

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

CONCENTRATION_FLOOR_M = 1e-6
"""Lower clamp on each ``c_i`` before the driver average is taken (PHY-01)."""

MOLAR_PER_SI = 1e-3
"""Conversion from mol/m^3 to mol/L."""


@dataclass(frozen=True)
class CorrectionChoice:
    """One property's entry in the case file's ``corrections`` block.

    ``model`` is a registered name; ``"none"`` disables the correction. The two
    flags switch the concentration and wall parts independently, which is what
    makes an ablation study a configuration sweep (section 7.4).
    """

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
    """Which correction applies to each property (PHY-22).

    Defaults are all-off, so an explicitly constructed electrolyte is classical
    PNP-NS until a model is named. ``for_model`` builds the validated ePNP-NS
    configuration.
    """

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
        """Return the classical PNP-NS configuration: every correction off."""
        return cls()

    def without(self, *properties: str) -> CorrectionSwitches:
        """Return a copy with the named properties disabled, for ablation runs.

        Raises
        ------
        ValueError
            If a name is not one of the switchable properties. A typo would
            otherwise disable nothing and leave the ablation silently comparing a
            configuration against itself, which is exactly the failure PHY-21's
            differential testing exists to avoid.
        """
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
    """``D_i^0`` in m^2/s."""
    steric_diameter: float
    """``a_i`` in m; 0.5 nm for every ion in the reference parameterisation."""
    temperature_K: float = 298.15

    @property
    def mobility_0(self) -> float:
        """``mu_i^0 = D_i^0 / V_T`` in m^2/(V s).

        Derived, never fitted independently (PHY-14). The Nernst-Einstein
        relation holds here and *only* here: at finite concentration ``D`` and
        ``mu`` carry different corrections and the ratio drifts (VER-05).
        """
        return self.diffusivity_0 / thermal_voltage(self.temperature_K)


def _resolve_corrections(
    switches: CorrectionSwitches, species: Sequence[IonSpecies]
) -> dict[str, models.CorrectionModel]:
    """Return the correction model in force for each property, from the switches.

    The single place the switch vocabulary becomes behaviour. Both
    :meth:`Electrolyte.from_parameter_file` and :meth:`Electrolyte.with_switches`
    route through it, so a configuration built either way resolves identically.
    """
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
    """A binary or multi-species electrolyte with its corrections resolved.

    **``corrections`` is the behaviour; ``switches`` is the record of how it was
    built.** Every property accessor reads the resolved model out of
    ``corrections`` and never consults ``switches`` again, so the two must agree
    or the electrolyte reports one configuration and evaluates another. Use
    :meth:`with_switches` to change the configuration; ``dataclasses.replace``
    with a new ``switches`` alone leaves ``corrections`` untouched and is
    refused by :meth:`__post_init__`.
    """

    species: tuple[IonSpecies, ...]
    switches: CorrectionSwitches
    temperature_K: float
    viscosity_0: float
    """``eta^0`` in Pa s."""
    mass_density_0: float
    """``rho^0`` in kg/m^3."""
    permittivity_0: float
    """``eps_r,f^0``, dimensionless."""
    water_steric_diameter: float
    """``a_0`` in m."""
    protein_permittivity: float
    membrane_permittivity: float
    validity_M: tuple[float, float]
    corrections: Mapping[str, models.CorrectionModel]
    """The resolved correction model per property, keyed ``kind`` or ``kind:species``."""
    driver: str = "average"
    """``"average"`` for the PHY-01 arithmetic mean, ``"ionic_strength"`` for
    ``0.5 * sum z_i^2 c_i``. The two coincide for a symmetric 1:1 salt."""
    parameter_file: str = ""

    def __post_init__(self) -> None:
        """Reject a species whose temperature disagrees with the electrolyte's.

        ``mu_i^0`` is derived from ``D_i^0 / V_T(T_i)`` on the species while
        every other property is evaluated at the electrolyte temperature, so a
        mismatch is a silent error in every mobility rather than a failure.

        Raises
        ------
        ValueError
            If any species carries a different temperature.
        """
        mismatched = [ion.name for ion in self.species if ion.temperature_K != self.temperature_K]
        if mismatched:
            raise ValueError(
                f"species {', '.join(mismatched)} carry a temperature different from the "
                f"electrolyte's {self.temperature_K} K; mu_i^0 = D_i^0 / V_T(T) would then be "
                "evaluated at the wrong temperature"
            )
        self._reject_switches_that_disagree_with_the_corrections()

    def _reject_switches_that_disagree_with_the_corrections(self) -> None:
        """Raise if the resolved corrections are not the ones the switches name.

        The failure this exists to stop is entirely silent. ``switches`` is
        reported in the FR-25 provenance and read by ``CoupledModel.provenance``
        to decide whether a run is classical, while ``corrections`` is what the
        forms actually evaluate. A ``replace(electrolyte,
        switches=CorrectionSwitches.classical())`` sets the record without
        touching the behaviour, and the result is a run that calls itself
        PNP-NS, converges, and is ePNP-NS -- which makes the PHY-21 ablation, the
        project's primary differential-testing instrument, silently compare a
        configuration against itself.

        Raises
        ------
        ValueError
            Naming every property whose resolved model disagrees with its
            switch, and pointing at :meth:`with_switches`.
        """
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
            # The concentration and wall parts are independently switchable, and
            # an ablation that turns one off is exactly as silent as turning the
            # whole model off. ``none`` carries neither flag and needs no check.
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
        """Return the same electrolyte with a different correction configuration.

        This is how PHY-21's reduction of ePNP-NS to PNP-NS is expressed: the
        same electrolyte, the same reference properties, every correction
        resolved to the registered ``none`` model. It rebuilds ``corrections``
        from ``switches``, which is the part ``dataclasses.replace`` cannot do.

        Parameters
        ----------
        switches
            The configuration to resolve.
        """
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
        """Build an electrolyte from a registered correction parameter file.

        Parameters
        ----------
        model
            Registered correction model name, also the parameter file to read
            reference values from.
        switches
            Which corrections apply. Defaults to every correction enabled
            against ``model`` — the validated ePNP-NS configuration.
        species
            Ion names to solve for; defaults to every species in the file.
        driver
            ``"average"`` (PHY-01) or ``"ionic_strength"``.

        Raises
        ------
        ValueError
            If ``driver`` is not one of the two named options.
        """
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
        """Return the named species.

        Raises
        ------
        KeyError
            If the electrolyte does not solve for that ion.
        """
        for candidate in self.species:
            if candidate.name == name:
                return candidate
        known = ", ".join(s.name for s in self.species)
        raise KeyError(f"no species {name!r} in this electrolyte; it has {known}")

    def average_concentration(
        self, concentrations: Sequence[Numeric], ops: MathOps = NUMPY_OPS
    ) -> Numeric:
        """Return the correction driver ``<c>`` in mol/L.

        Each ``c_i`` is clamped to ``[1e-6 M, 5.3 M]`` before the average is
        taken (PHY-01). Clamping at the upper end is also how PHY-13's cap is
        applied: every property then evaluates at its 5.3 M value above the fit
        range. The default driver is the arithmetic mean of the ion
        concentrations, *not* the ionic strength — they coincide for a symmetric
        1:1 salt and diverge otherwise.

        Parameters
        ----------
        concentrations
            One entry per species, in mol/m^3, ordered as ``self.species``.
        ops
            Operation namespace.

        Note that the clamp applied here is the one that actually activates: the
        driver returned can never exceed the validity limit, so a diagnostic run
        over driver samples alone would report nothing. Use
        ``report_clamp_activations`` on the *species* concentrations to satisfy
        PHY-13's logging requirement.

        Raises
        ------
        ValueError
            If the number of concentrations does not match the species count.
        """
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
        """Return ``mu_i(<c>, d)`` in m^2/(V s).

        Built as ``D_i^0 / V_T`` times the *mobility* correction, per PHY-14:
        ``mu`` is derived from the diffusivity at infinite dilution and then
        carries its own conductivity-fitted concentration coefficients, which is
        why ``D_i/mu_i`` drifts away from ``kT/e`` with concentration.
        """
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
        """Log every per-species clamp activation and return how many there were.

        PHY-13 requires each activation to be logged with its location and
        property. ``average_concentration`` clamps each ``c_i`` *before* the
        average is taken, so by construction the driver it returns never exceeds
        the limit; the extrapolation has to be detected on the species
        concentrations that went in, which is what this does.

        Parameters
        ----------
        concentrations
            Sampled species concentrations in mol/m^3, ordered as
            ``self.species``, one array or sequence per species.
        coordinates
            Optional sample locations, shared by every species.

        Returns
        -------
        int
            Total number of samples clamped, summed over species.

        Raises
        ------
        ValueError
            If the number of concentrations does not match the species count.
        """
        if len(concentrations) != len(self.species):
            raise ValueError(
                f"expected {len(self.species)} concentrations, got {len(concentrations)}"
            )
        import numpy as np

        limit = self.validity_M[1]
        return sum(
            log_clamp_activations(
                np.asarray(values, dtype=float) * MOLAR_PER_SI,
                label=f"{ion.name} concentration",
                limit=limit,
                coordinates=coordinates,
            )
            for ion, values in zip(self.species, concentrations, strict=True)
        )

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Return what a result manifest must record about the materials (FR-25)."""
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

    PHY-13 requires every clamp activation to be logged with its location and
    property. Evaluation inside the solver is symbolic, so this runs as a
    diagnostic over a sampled solution rather than inside the form itself.

    Parameters
    ----------
    values_M
        Sampled driver concentrations, in mol/L.
    label
        What was clamped, named in the log line.
    limit
        Upper end of the fit validity range, in mol/L. Required rather than
        defaulted: the range belongs to the parameter file, not to this module
        (see ``Electrolyte.validity_M``).
    coordinates
        Optional sample locations, in the same order as ``values_M``.

    Returns
    -------
    int
        Number of samples above ``limit``.
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
        "peak driver %.4g M is outside the fit range.%s",
        label,
        limit,
        exceeded.size,
        float(array[worst]),
        where,
    )
    return int(exceeded.size)
