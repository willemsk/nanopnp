"""The attribution ladder: which part of a discrepancy could be a defect (VAL-01, VAL-04)."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from nanopnp.core.hashing import Canonicalisable, canonical, content_hash, decode_floats
from nanopnp.validation.compare import (
    COMPARED_QUANTITIES,
    FieldComparison,
    QoIComparison,
    check_mask_agreement,
    field_error,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.case import FieldValue
    from nanopnp.validation.comsol import Golden
    from nanopnp.validation.probe import ProbeGrid

__all__ = [
    "ATTRIBUTION_SCHEMA",
    "DELTA_LABELS",
    "IDENTITY_TOLERANCE",
    "LADDER",
    "Attribution",
    "AttributionReport",
    "LadderError",
    "Rung",
    "RungOutcome",
    "attribute",
    "read_report",
    "reference_error",
    "write_report",
]

ATTRIBUTION_SCHEMA = "nanopnp/attribution/v0.5"

IDENTITY_TOLERANCE = 1e-14

Verdict = Literal["reference-limited", "attributed", "reference-unbounded"]


class LadderError(ValueError):
    """Raised when the ladder's rungs cannot be attributed against each other."""


@dataclass(frozen=True)
class Rung:
    """One configuration of the ladder, as dotted case-file assignments.

    Parameters
    ----------
    what
        One line on what this rung measures, printed in the report.
    """

    index: int
    name: str
    stabilisation: str
    velocity_element: str
    pressure_element: str
    what: str

    def assignments(self) -> dict[str, FieldValue]:
        """Return this rung as the sweep document's assignment mapping."""
        return {
            "numerics.stabilisation": self.stabilisation,
            "numerics.elements.u": self.velocity_element,
            "numerics.elements.p": self.pressure_element,
        }

    def summary(self) -> dict[str, Canonicalisable]:
        """Return this rung's record for the report."""
        return {
            "index": self.index,
            "name": self.name,
            "stabilisation": self.stabilisation,
            "elements": {"u": self.velocity_element, "p": self.pressure_element},
            "what": self.what,
        }


LADDER: tuple[Rung, ...] = (
    Rung(
        index=0,
        name="production",
        stabilisation="none",
        velocity_element="P2",
        pressure_element="P1",
        what="our production default: Taylor-Hood, unstabilised (NUM-11)",
    ),
    Rung(
        index=1,
        name="supg",
        stabilisation="supg",
        velocity_element="P2",
        pressure_element="P1",
        what="transport stabilisation only; second order on this pair (WP12: 2.012)",
    ),
    Rung(
        index=2,
        name="reference-taylor-hood",
        stabilisation="reference",
        velocity_element="P2",
        pressure_element="P1",
        what="transport and flow GLS on an inf-sup-stable pair (WP12: 0.984)",
    ),
    Rung(
        index=3,
        name="reference-equal-order",
        stabilisation="reference",
        velocity_element="P1",
        pressure_element="P1",
        what="the reference's own discretisation "
        "(knowledge/09-comsol-reference-settings/04-physics-settings.md, E rows 1, 2, 4)",
    ),
)

DELTA_LABELS: tuple[str, ...] = ("total", "transport", "flow", "pair")


@dataclass(frozen=True)
class RungOutcome:
    """One rung, compared against one golden.

    Parameters
    ----------
    golden_hash, probe_hash, case_hash
        Provenance the ladder gates on; rungs that differ in any are not comparable.
    stabilisation_currents_A
        Per-species stabilisation contribution from this run alone, beside the deltas.
    zero_reference
        Our value of each quantity whose golden value is exactly zero, which has no relative error.
    """

    rung: Rung
    golden_hash: str
    probe_hash: str
    case_hash: str
    fields: tuple[FieldComparison, ...]
    quantities: tuple[QoIComparison, ...]
    stabilisation_currents_A: Mapping[str, float] | None = None
    zero_reference: Mapping[str, float] = field(default_factory=dict)

    def field_errors(self) -> dict[str, float]:
        """Return ``rel_L2_r`` per field."""
        return {entry.field: entry.rel_L2_r for entry in self.fields}

    def quantity_errors(self) -> dict[str, float]:
        """Return the magnitude of the relative error per quantity."""
        return {entry.name: abs(entry.relative) for entry in self.quantities}

    def point_counts(self) -> dict[str, int]:
        """Return the number of retained probe points per field."""
        return {entry.field: entry.points for entry in self.fields}

    def summary(self) -> dict[str, Canonicalisable]:
        """Return this rung's record for the report."""
        return {
            "rung": self.rung.summary(),
            "golden_hash": self.golden_hash,
            "probe_hash": self.probe_hash,
            "case_hash": self.case_hash,
            "fields": [entry.summary() for entry in self.fields],
            "quantities": [entry.summary() for entry in self.quantities],
            "stabilisation_currents_A": (
                None
                if self.stabilisation_currents_A is None
                else dict(self.stabilisation_currents_A)
            ),
            "zero_reference": dict(self.zero_reference),
        }


@dataclass(frozen=True)
class Attribution:
    """The five deltas for one field or one quantity.

    Parameters
    ----------
    errors
        ``(E_0, E_1, E_2, E_3)``, one per rung of ``LADDER``.
    reference_error
        VAL-04's ``Delta_ref`` for this key, or ``None`` if no refinement pair was given.
    """

    key: str
    kind: Literal["field", "quantity"]
    errors: tuple[float, float, float, float]
    reference_error: float | None = None

    @property
    def total(self) -> float:
        """Return ``Delta_total = E_0``: what the shipped default does."""
        return self.errors[0]

    @property
    def transport(self) -> float:
        """Return ``Delta_transport = E_1 - E_0``: the transport stabilisation."""
        return self.errors[1] - self.errors[0]

    @property
    def flow(self) -> float:
        """Return ``Delta_flow = E_2 - E_1``: the flow GLS term on a Taylor-Hood pair."""
        return self.errors[2] - self.errors[1]

    @property
    def pair(self) -> float:
        """Return ``Delta_pair = E_3 - E_2``: P2/P1 to P1/P1."""
        return self.errors[3] - self.errors[2]

    @property
    def residual(self) -> float:
        """Return ``Delta_resid = E_3``: the like-for-like number, the only possible defect."""
        return self.errors[3]

    def identity_residual(self) -> float:
        """Return the telescoped sum minus ``Delta_resid``, zero to round-off by construction."""
        return self.total + self.transport + self.flow + self.pair - self.residual

    def verdict(self) -> Verdict:
        """Return what this residual can honestly be called; see ``Verdict``."""
        if self.reference_error is None:
            return "reference-unbounded"
        return "reference-limited" if self.residual < self.reference_error else "attributed"

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the five deltas and the verdict, for the report."""
        return {
            "key": self.key,
            "kind": self.kind,
            "E": list(self.errors),
            "delta_total": self.total,
            "delta_transport": self.transport,
            "delta_flow": self.flow,
            "delta_pair": self.pair,
            "delta_resid": self.residual,
            "identity_residual": self.identity_residual(),
            "delta_ref": self.reference_error,
            "verdict": self.verdict(),
        }


@dataclass(frozen=True)
class AttributionReport:
    """One case's ladder: four rungs, five deltas per key, and a verdict.

    Parameters
    ----------
    golden_source
        ``"comsol"`` or ``"self"``; a self-golden tests the machinery only.
    unavailable_fields, unavailable_quantities
        What the golden did not carry, reported rather than skipped.
    zero_reference_quantities
        Our value of each quantity whose golden value is exactly zero.
    """

    case: str
    golden_source: str
    golden_hash: str
    probe_hash: str
    case_hash: str
    refinement: str
    rungs: tuple[RungOutcome, ...]
    attributions: tuple[Attribution, ...]
    unavailable_fields: tuple[str, ...] = ()
    unavailable_quantities: tuple[str, ...] = ()
    zero_reference_quantities: Mapping[str, float] = field(default_factory=dict)

    def attribution(self, key: str) -> Attribution:
        """Return one key's attribution.

        Raises
        ------
        LadderError
            If no attribution carries that key.
        """
        for entry in self.attributions:
            if entry.key == key:
                return entry
        listed = ", ".join(repr(entry.key) for entry in self.attributions) or "nothing"
        raise LadderError(f"this report attributes {listed}, not {key!r}")

    def check_identity(self, tolerance: float = IDENTITY_TOLERANCE) -> None:
        """Abort where a telescoped sum does not return its own ``Delta_resid``.

        Raises
        ------
        LadderError
            Naming the key and the residual. A non-finite residual fails too.
        """
        for entry in self.attributions:
            residual = entry.identity_residual()
            # Relative to the largest E_k: an E_k is a relative error and is not
            # bounded by 1, and the round-off of the telescoped sum grows with it.
            scale = max(1.0, *(abs(value) for value in entry.errors))
            if not math.isfinite(residual) or abs(residual) > tolerance * scale:
                raise LadderError(
                    f"the ladder identity fails for {entry.kind} {entry.key!r}: "
                    f"delta_total + delta_transport + delta_flow + delta_pair - delta_resid = "
                    f"{residual:.3e}, against a tolerance of {tolerance:g}. The four deltas "
                    "telescope by construction, so this is a defect in how they were formed — "
                    f"or one of the rung errors {list(entry.errors)} is not finite, which is the "
                    "same statement about a rung that measured nothing"
                )

    @property
    def hash(self) -> str:
        """Return the content hash over the report's record."""
        return content_hash(ATTRIBUTION_SCHEMA, self.summary())

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the whole report, for the JSON artefact and the manifest."""
        return {
            "schema": ATTRIBUTION_SCHEMA,
            "case": self.case,
            "golden_source": self.golden_source,
            "golden_hash": self.golden_hash,
            "probe_hash": self.probe_hash,
            "case_hash": self.case_hash,
            "refinement": self.refinement,
            "ladder": [rung.summary() for rung in self.rungs],
            "attributions": [entry.summary() for entry in self.attributions],
            "unavailable_fields": list(self.unavailable_fields),
            "unavailable_quantities": list(self.unavailable_quantities),
            "zero_reference_quantities": dict(self.zero_reference_quantities),
        }

    def markdown(self) -> str:
        """Return the report a person reads, deltas first and provenance last."""
        lines = [
            f"# Tier-3 attribution — {self.case}",
            "",
            f"**Golden source: `{self.golden_source}`.**"
            + (
                "  A self-golden tests the harness and nothing else; no number below is a"
                " statement about the reference implementation."
                if self.golden_source == "self"
                else ""
            ),
            "",
            f"Refinement `{self.refinement}`; golden `{self.golden_hash[:12]}`, "
            f"probe `{self.probe_hash[:12]}`, case `{self.case_hash[:12]}`.",
            "",
            "## Deltas",
            "",
            "| key | kind | Δ_total | Δ_transport | Δ_flow | Δ_pair | Δ_resid | Δ_ref | verdict |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for entry in self.attributions:
            reference = "—" if entry.reference_error is None else f"{entry.reference_error:.4e}"
            lines.append(
                f"| `{entry.key}` | {entry.kind} | {entry.total:.4e} | {entry.transport:+.4e} | "
                f"{entry.flow:+.4e} | {entry.pair:+.4e} | {entry.residual:.4e} | {reference} | "
                f"{entry.verdict()} |"
            )
        lines += [
            "",
            "## The ladder",
            "",
            "| rung | stabilisation | u/p | what |",
            "|---|---|---|---|",
        ]
        for outcome in self.rungs:
            rung = outcome.rung
            lines.append(
                f"| {rung.index} `{rung.name}` | `{rung.stabilisation}` | "
                f"{rung.velocity_element}/{rung.pressure_element} | {rung.what} |"
            )
        lines += [
            "",
            "## `stabilisation_currents_A` — a different quantity",
            "",
            "Section 6.7 extracts this from a *single* run as the stabilisation form evaluated",
            "against the indicator. `Δ_transport` is a difference of two runs' distances from a",
            "third object. They measure the same physics and they are not the same number.",
            "",
            "| rung | stabilisation_currents_A |",
            "|---|---|",
        ]
        for outcome in self.rungs:
            currents = outcome.stabilisation_currents_A
            shown = (
                "not measured"
                if currents is None
                else ", ".join(
                    f"`{name}` {value:.4e} A" for name, value in sorted(currents.items())
                )
            )
            lines.append(f"| {outcome.rung.index} `{outcome.rung.name}` | {shown} |")
        if self.unavailable_fields or self.unavailable_quantities:
            lines += [
                "",
                "## Not compared",
                "",
                "The golden does not carry these, so they are recorded as unavailable rather",
                "than skipped silently.",
                "",
                "- fields: " + (", ".join(f"`{name}`" for name in self.unavailable_fields) or "—"),
                "- quantities: "
                + (", ".join(f"`{name}`" for name in self.unavailable_quantities) or "—"),
            ]
        if self.zero_reference_quantities:
            lines += [
                "",
                "## Zero reference",
                "",
                "Golden is zero; relative error undefined. Our absolute value is shown.",
                "",
                *(
                    f"- `{name}`: ours {value:.4e}, golden 0"
                    for name, value in sorted(self.zero_reference_quantities.items())
                ),
            ]
        return "\n".join(lines) + "\n"


def reference_error(coarse: Golden, fine: Golden, grid: ProbeGrid) -> dict[str, float]:
    """Return VAL-04's ``Delta_ref`` per field: the reference's own discretisation error.

    Parameters
    ----------
    grid
        The probe grid the rungs were compared on; its margin band is dropped.

    Raises
    ------
    LadderError
        If the goldens are not two distinct refinements of one case on one probe grid.
    """
    import numpy as np

    if coarse.manifest.case_hash != fine.manifest.case_hash:
        raise LadderError(
            f"the refinement pair answers two different cases: {coarse.manifest.case_hash[:12]} "
            f"and {fine.manifest.case_hash[:12]}. Delta_ref is the reference's discretisation "
            "error on one case, not the difference between two"
        )
    if coarse.manifest.probe_hash != fine.manifest.probe_hash:
        raise LadderError(
            "the refinement pair was exported onto two different probe grids "
            f"({coarse.manifest.probe_hash[:12]} and {fine.manifest.probe_hash[:12]}); their "
            "difference would be a difference of sample points"
        )
    if coarse.manifest.refinement == fine.manifest.refinement:
        raise LadderError(
            f"both goldens declare refinement {coarse.manifest.refinement!r}. Delta_ref needs the "
            "published mesh and one uniform refinement of it; two of one level measure nothing"
        )
    errors: dict[str, float] = {}
    for name in sorted(set(coarse.values) & set(fine.values) & set(grid.masks)):
        # The two exports must agree about where the field exists, band
        # included: that is a statement about the two models, and the band is
        # dropped only from the norm.
        defined = fine.defined(name)
        check_mask_agreement(name, defined, coarse.defined(name), grid)
        keep = defined & np.asarray(grid.masks[name], dtype=bool)
        comparison = field_error(
            name,
            np.asarray(coarse.values[name], dtype=np.float64),
            np.asarray(fine.values[name], dtype=np.float64),
            grid,
            keep,
        )
        errors[name] = comparison.rel_L2_r
    for name in COMPARED_QUANTITIES:
        rough, refined = getattr(coarse.quantities, name), getattr(fine.quantities, name)
        if rough is None or refined is None or float(refined) == 0.0:
            continue
        errors[name] = abs(float(rough) - float(refined)) / abs(float(refined))
    return errors


def attribute(
    outcomes: Sequence[RungOutcome],
    *,
    case: str,
    golden: Golden,
    reference_errors: Mapping[str, float] | None = None,
    sampled_fields: Sequence[str] | None = None,
) -> AttributionReport:
    """Build the report from four rung outcomes, gating their provenance first.

    Parameters
    ----------
    reference_errors
        VAL-04's ``Delta_ref`` per key, or ``None`` if no refinement pair was supplied.
    sampled_fields
        Every field we sampled on the probe grid; needed to name the unavailable ones.

    Raises
    ------
    LadderError
        If the rungs do not share a golden, a probe grid and a case, or retained different
        numbers of probe points for one field.
    """
    if len(outcomes) != len(LADDER):
        raise LadderError(
            f"the ladder has {len(LADDER)} rungs and {len(outcomes)} outcome(s) were given. "
            "Every delta is a difference of two adjacent rungs, so a missing one does not make "
            "the remaining deltas mean less — it makes them mean something else"
        )
    for outcome, rung in zip(outcomes, LADDER, strict=True):
        if outcome.rung != rung:
            raise LadderError(
                f"outcome {outcome.rung.index} is rung {outcome.rung.name!r} where the ladder's "
                f"rung {rung.index} is {rung.name!r}; the deltas are named for their position"
            )
    _check_shared_provenance(outcomes)
    _check_shared_masks(outcomes)

    attributions: list[Attribution] = []
    for kind, errors_of in (("field", "field_errors"), ("quantity", "quantity_errors")):
        per_rung = [getattr(outcome, errors_of)() for outcome in outcomes]
        for key in sorted(set(per_rung[0]).intersection(*(set(entry) for entry in per_rung[1:]))):
            attributions.append(
                Attribution(
                    key=key,
                    kind="field" if kind == "field" else "quantity",
                    errors=(
                        per_rung[0][key],
                        per_rung[1][key],
                        per_rung[2][key],
                        per_rung[3][key],
                    ),
                    reference_error=None if reference_errors is None else reference_errors.get(key),
                )
            )
    report = AttributionReport(
        case=case,
        golden_source=golden.source,
        golden_hash=golden.hash,
        probe_hash=golden.manifest.probe_hash,
        case_hash=golden.manifest.case_hash,
        refinement=golden.manifest.refinement,
        rungs=tuple(outcomes),
        attributions=tuple(attributions),
        unavailable_fields=golden.unavailable(
            sorted(outcomes[0].field_errors()) if sampled_fields is None else sampled_fields
        ),
        unavailable_quantities=tuple(
            name
            for name in COMPARED_QUANTITIES
            if name not in outcomes[0].quantity_errors() and name not in outcomes[0].zero_reference
        ),
        zero_reference_quantities=dict(outcomes[0].zero_reference),
    )
    report.check_identity()
    return report


def _check_shared_provenance(outcomes: Sequence[RungOutcome]) -> None:
    first = outcomes[0]
    for name in ("golden_hash", "probe_hash", "case_hash"):
        expected = getattr(first, name)
        for outcome in outcomes[1:]:
            found = getattr(outcome, name)
            if found != expected:
                raise LadderError(
                    f"rung {outcome.rung.index} ({outcome.rung.name!r}) carries {name} "
                    f"{found[:12]} where rung {first.rung.index} ({first.rung.name!r}) carries "
                    f"{expected[:12]}. The deltas are differences of distances to one object; "
                    "against two objects they are not deltas of anything"
                )


def _check_shared_masks(outcomes: Sequence[RungOutcome]) -> None:
    first = outcomes[0].point_counts()
    for outcome in outcomes[1:]:
        counts = outcome.point_counts()
        for key, expected in first.items():
            found = counts.get(key)
            if found is not None and found != expected:
                raise LadderError(
                    f"rung {outcome.rung.index} ({outcome.rung.name!r}) took field {key!r} over "
                    f"{found} probe points and rung {outcomes[0].rung.index} took it over "
                    f"{expected}. The mask is a property of the geometry and not of a "
                    "configuration, so two rungs cannot honestly differ in it"
                )


def write_report(report: AttributionReport, directory: str | Path) -> tuple[Path, Path]:
    """Write the report as JSON and as markdown, and return both paths."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    document = target / f"{report.case}.attribution.json"
    document.write_bytes(canonical({"attribution_hash": report.hash, **report.summary()}))
    readable = target / f"{report.case}.attribution.md"
    readable.write_text(report.markdown(), encoding="utf-8")
    return document, readable


def read_report(path: str | Path) -> dict[str, Canonicalisable]:
    """Return a written report's record, floats restored."""
    decoded = decode_floats(json.loads(Path(path).read_text(encoding="utf-8")))
    if not isinstance(decoded, dict):
        raise LadderError(f"{path} does not hold an attribution report object")
    return decoded
