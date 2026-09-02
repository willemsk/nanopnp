"""Loading and validation of ePNP-NS correction parameter files.

A correction model is data, not code (FR-16, ADR-005): the fit coefficients live
in versioned YAML under ``data/corrections`` and are named from the case file by
string. This module reads a file and validates it through a typed schema; the
evaluation of the correction forms belongs to the model classes of section 5.4.2.

The schema is the one Phase-0 serialisation boundary given a Pydantic model
rather than a raw ``dict`` (CLAUDE.md: "Pydantic models at every serialisation
boundary"). Before it, a renamed or missing coefficient key surfaced as a
``KeyError`` deep in assembly; now a fit block is checked against the coefficients
its form actually reads (:data:`~nanopnp.materials.forms.FORM_PARAMETERS`) and the
offending key is named at load, the diagnostic IF-03 sets as the house standard.
This model is also the template the Phase-1 case-file schema (FR-26/VER-09) copies.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from nanopnp.core.paths import correction_file
from nanopnp.materials.forms import FORM_PARAMETERS, FORMS

SCHEMA: str = "nanopnp/corrections/v1"
"""Schema identifier every correction file must declare."""

NON_COEFFICIENT_KEYS: frozenset[str] = frozenset({"r_squared"})
"""Numeric keys a fit block may carry that are metadata, not fit coefficients.

``r_squared`` is a goodness-of-fit float that no correction form reads; keeping
it out of the coefficient set is what stops it being validated against, or
reported as, a fit coefficient (FR-25).
"""


class _Strict(BaseModel):
    """Base for the structural blocks: unknown keys are rejected, naming them."""

    model_config = ConfigDict(extra="forbid")


class FitBlock(BaseModel):
    """One ``f_c`` or ``f_w`` fit block: a form and the coefficients it reads.

    Free-form metadata (``r_squared``, ``check``, ``note``, ``applies_to``,
    ``rationale`` and the like) is permitted and ignored; the *numeric*
    coefficients are validated against the exact set the named form reads, so a
    renamed or missing key is caught here rather than in assembly.
    """

    model_config = ConfigDict(extra="allow")

    form: str

    @property
    def coefficients(self) -> dict[str, float]:
        """Return the numeric fit coefficients, dropping metadata keys.

        Filtering by type alone is not enough: ``r_squared`` is a float and
        ``bool`` is a subclass of ``int``, so both would be reported as fit
        coefficients in the FR-25 record even though no form reads them.
        """
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
        """Reject an unknown form, or coefficients that do not match it (IF-03).

        Raises
        ------
        ValueError
            If ``form`` is not registered, or if the numeric coefficients present
            are not exactly the ones the form reads; the message names the
            unexpected or missing keys.
        """
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
    """A corrected property: its concentration fit, wall fit and cap.

    Every property carries at most an ``f_c`` and an ``f_w``; the ion diffusivity
    and mobility share the file's single :attr:`CorrectionDocument.ion_wall_function`
    instead of their own ``fw``, so ``fw`` is absent on those and present only on
    the viscosity. ``cap_above_validity`` is the published saturation value; it is
    a regression target the tests gate, not a number the solver reads (the cap is
    applied by clamping the driver).
    """

    fc: FitBlock | None = None
    fw: FitBlock | None = None
    cap_above_validity: float | None = None


class DiffusivityBlock(PropertyBlock):
    """One species' diffusivity: ``D0`` at infinite dilution and its fit."""

    D0: float


class MobilityBlock(PropertyBlock):
    """One species' mobility: the tabulated ``mu0`` (a regression target) and fit.

    ``mu0`` is not read by the solver — PHY-14 derives the mobility from ``D0`` —
    but it is gated against the derived value so a mistranscribed exponent
    (erratum 2) is caught.
    """

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
    """The fixed relative permittivities of the solid domains (PHY-03)."""

    protein: float
    membrane: float


class TransportNumberBlock(BaseModel):
    """The auxiliary transport-number fit, used to re-derive mobilities.

    Not required at solve time (extra keys such as ``note`` are permitted), but
    validated so a file that ships it cannot ship a malformed fit block.
    """

    model_config = ConfigDict(extra="allow")

    t0: float
    fc: FitBlock | None = None


class CorrectionDocument(_Strict):
    """A validated ePNP-NS correction parameter file (schema ``nanopnp/corrections/v1``).

    Every key the loader and the model classes read is a typed field; unknown
    top-level or block keys are rejected, and each fit block is checked against
    the coefficients its form reads. ``schema`` is carried under the alias so the
    reserved name does not shadow ``BaseModel``.
    """

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


def load_corrections(name_or_path: str | Path) -> CorrectionDocument:
    """Load and validate a correction parameter file by registered name or by path.

    Parameters
    ----------
    name_or_path
        Registered model name (e.g. ``"willems2020_nacl"``) or a path to a
        correction YAML file.

    Returns
    -------
    CorrectionDocument
        The validated document.

    Raises
    ------
    ValueError
        If the document declares a schema this version does not understand (the
        message names both the file and the schema found), or if it fails
        structural or coefficient validation.
    """
    path = (
        Path(name_or_path)
        if Path(name_or_path).suffix == ".yaml"
        else correction_file(str(name_or_path))
    )
    with path.open(encoding="utf-8") as handle:
        raw: Mapping[str, object] = yaml.safe_load(handle)
    # The schema is checked before structural validation so a file written to a
    # future schema fails with a message naming the file and the version found,
    # rather than with a wall of field errors against a shape it never claimed.
    schema = raw.get("schema")
    if schema != SCHEMA:
        raise ValueError(f"{path}: expected schema {SCHEMA!r}, found {schema!r}")
    return CorrectionDocument.model_validate(raw)
