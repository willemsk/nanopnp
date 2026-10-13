"""Loading and validation of ePNP-NS correction parameter files."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from nanopnp.core.paths import correction_file
from nanopnp.materials.forms import FORM_PARAMETERS, FORMS

SCHEMA: str = "nanopnp/corrections/v0.5"

NON_COEFFICIENT_KEYS: frozenset[str] = frozenset({"r_squared"})


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FitBlock(BaseModel):
    """One ``f_c`` or ``f_w`` fit block: a form and the coefficients it reads."""

    model_config = ConfigDict(extra="allow")

    form: str

    @property
    def coefficients(self) -> dict[str, float]:
        """Return the numeric fit coefficients, dropping metadata keys and booleans."""
        extra = self.model_extra or {}
        return {
            key: float(value)
            for key, value in extra.items()
            if isinstance(value, int | float)
            and not isinstance(value, bool)
            and key not in NON_COEFFICIENT_KEYS
        }

    @model_validator(mode="after")
    def _check_coefficients(self) -> FitBlock:
        if self.form not in FORMS:
            known = ", ".join(sorted(FORMS))
            raise ValueError(f"unknown correction form {self.form!r}; registered forms are {known}")
        present = set(self.coefficients)
        expected = FORM_PARAMETERS[self.form]
        unknown = sorted(present - expected)
        missing = sorted(expected - present)
        if unknown or missing:
            wants = ", ".join(sorted(expected))
            problems = []
            if unknown:
                problems.append(f"unexpected coefficient(s) {', '.join(unknown)}")
            if missing:
                problems.append(f"missing coefficient(s) {', '.join(missing)}")
            raise ValueError(
                f"form {self.form!r} takes exactly {wants}, but the fit block has "
                f"{'; '.join(problems)}"
            )
        return self


class PropertyBlock(_Strict):
    """A corrected property: its concentration fit, wall fit and cap."""

    fc: FitBlock | None = None
    fw: FitBlock | None = None
    cap_above_validity: float | None = None


class _IonPropertyBlock(PropertyBlock):
    @model_validator(mode="after")
    def _no_own_wall_fit(self) -> _IonPropertyBlock:
        if self.fw is not None:
            raise ValueError(
                "an ion diffusivity or mobility takes the file's ion_wall_function; a "
                "per-species fw here would be accepted and never applied"
            )
        return self


class DiffusivityBlock(_IonPropertyBlock):
    """One species' diffusivity: ``D0`` at infinite dilution and its fit."""

    D0: float


class MobilityBlock(_IonPropertyBlock):
    """One species' mobility: the tabulated ``mu0`` and fit; ``mu0`` is a regression target only."""

    mu0: float


class ViscosityBlock(PropertyBlock):
    """The solvent viscosity: ``eta0`` and its concentration and wall fits."""

    eta0: float


class DensityBlock(PropertyBlock):
    """The solvent mass density: ``rho0`` and its concentration fit."""

    rho0: float


class PermittivityBlock(PropertyBlock):
    """The solvent relative permittivity: ``eps_r0`` and its concentration fit."""

    eps_r0: float


class SpeciesBlock(_Strict):
    """One ionic species: valence, its two transport properties and steric size."""

    z: int
    diffusivity: DiffusivityBlock
    mobility: MobilityBlock
    steric_diameter_nm: float


class SolventBlock(_Strict):
    """The solvent: its steric size and the three solvent-property blocks."""

    water_steric_diameter_nm: float
    viscosity: ViscosityBlock
    density: DensityBlock
    permittivity: PermittivityBlock


class DielectricsBlock(_Strict):
    """The fixed relative permittivities of the solid domains."""

    protein: float
    membrane: float


class TransportNumberBlock(BaseModel):
    """The auxiliary transport-number fit, validated but not required at solve time."""

    model_config = ConfigDict(extra="allow")

    t0: float
    fc: FitBlock | None = None


class CorrectionDocument(_Strict):
    """A validated correction parameter file; unknown keys are rejected."""

    schema_id: str = Field(alias="schema")
    name: str
    electrolyte: str
    temperature_K: float
    concentration_validity_M: tuple[float, float]
    species: dict[str, SpeciesBlock]
    solvent: SolventBlock
    ion_wall_function: FitBlock
    dielectrics: DielectricsBlock
    notes: str | None = None
    transport_number_Na: TransportNumberBlock | None = None


@lru_cache(maxsize=32)
def _parse(text: str) -> Mapping[str, object]:
    raw: Mapping[str, object] = yaml.safe_load(text)
    return raw


def _fresh(node: object) -> object:
    if isinstance(node, dict):
        return {key: _fresh(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_fresh(value) for value in node]
    if isinstance(node, (str, int, float, bool, type(None))):
        return node
    if isinstance(node, set):
        return {_fresh(value) for value in node}
    return copy.deepcopy(node)


def load_corrections(name_or_path: str | Path) -> CorrectionDocument:
    """Load and validate a correction parameter file, by registered name or by path.

    Raises
    ------
    ValueError
        If the schema is not understood or validation fails.
    """
    path = (
        Path(name_or_path)
        if Path(name_or_path).suffix == ".yaml"
        else correction_file(str(name_or_path))
    )
    # copied: the extra="allow" blocks keep their extra values by reference
    raw = cast("Mapping[str, object]", _fresh(_parse(path.read_text(encoding="utf-8"))))
    # before validation, so a future schema fails naming the file and version found
    schema = raw.get("schema")
    if schema != SCHEMA:
        raise ValueError(f"{path}: expected schema {SCHEMA!r}, found {schema!r}")
    return CorrectionDocument.model_validate(raw)
