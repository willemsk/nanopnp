"""The attribution ladder: which part of a discrepancy could be a defect (VAL-01, VAL-04).

Section 7.4 says the acceptance targets apply "only once the matching stabilised
mode of section 6.4 exists and the meshes have been convergence-matched", and
that until both hold "differences are recorded and attributed rather than gated
on". This module is the attribution.

Let ``E_k`` be a configuration's relative distance from the golden on the probe
grid (:mod:`nanopnp.validation.compare`). Four configurations:

===  ========================  ===================  =====================================
 k   ``numerics.stabilisation``  ``u`` / ``p``      What it is
===  ========================  ===================  =====================================
 0   ``none``                  P2 / P1              our production default (NUM-11)
 1   ``supg``                  P2 / P1              transport stabilisation only
 2   ``reference``             P2 / P1              transport **and** flow GLS
 3   ``reference``             P1 / P1              the reference's own discretisation
===  ========================  ===================  =====================================

and the reported deltas

    Delta_total     = E_0        our shipped default's distance from the reference
    Delta_transport = E_1 - E_0  the transport stabilisation, measured at second order
    Delta_flow      = E_2 - E_1  the flow GLS term added on a Taylor-Hood pair
    Delta_pair      = E_3 - E_2  the element pair, P2/P1 to P1/P1
    Delta_resid     = E_3        the like-for-like residual, the only possible defect

**Why four rungs and not three.** The phase plan specified ``none`` ->
``reference`` -> ``reference``+P1/P1, calling the first delta ``Delta_stab``.
WP12 then measured, on the VER-11 benchmark pore, an MMS L2 convergence rate of
**0.984** for ``reference`` on a Taylor-Hood pair against **2.012** for ``supg``
on the same meshes and the same manufactured solution. A full order, lost in the
flow operator: the GLS term's pressure-test content is what makes P1/P1 legal,
and on a pair that is already inf-sup stable it is a first-order perturbation of
a second-order discretisation. Without the ``supg`` rung the middle delta is the
sum of two different things and attributes neither.

**What each delta may be called.** ``Delta_resid`` is the like-for-like number
and the one section 7.4's targets apply to. ``Delta_transport`` is the transport
stabilisation's contribution *to the distance from the golden*; it is **not**
``stabilisation_currents_A``, which section 6.7 extracts from a single run as the
stabilisation form evaluated against the indicator. WP12 measured those two
agreeing to 1.55e-3 of the current on its benchmark, which is evidence that both
measure the same physics, not licence to print one as the other. The report
carries both, under distinct names.

**What the identity does and does not catch.** ``Delta_total + Delta_transport +
Delta_flow + Delta_pair = Delta_resid`` telescopes for *any* four numbers, so it
cannot detect a rung run against a stale golden — see :meth:`Attribution.residual`
and :func:`attribute`, which gates the provenance separately and is what actually
does that job.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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

ATTRIBUTION_SCHEMA = "nanopnp/attribution/v1"
"""Schema identifier of the report, and the separator of its content hash."""

IDENTITY_TOLERANCE = 1e-14
"""Absolute tolerance on the telescoped sum.

The identity is exact in real arithmetic, so what is left is the round-off of
four additions of numbers of order one: about 1e-16. Asserting at 1e-14 leaves
two orders of headroom and still fails on any real slip in forming the deltas.
"""

Verdict = Literal["reference-limited", "attributed", "reference-unbounded"]
"""What a comparison's residual can honestly be called.

``reference-limited`` — ``Delta_resid < Delta_ref``, so our residual is below the
reference's own discretisation error and the comparison has reached the limit of
what the reference can say. Section 7.4's NOTE requires exactly this word: "a
comparison whose residual falls below that bound SHALL be reported as
*reference-limited* rather than as agreement".

``attributed`` — ``Delta_resid >= Delta_ref``: the residual is larger than the
reference's own error, so it is ours to explain.

``reference-unbounded`` — VAL-04's refinement pair was not supplied for this
case, so RSK-09 is unbounded here and neither word above is available.
"""


class LadderError(ValueError):
    """The ladder's rungs cannot be attributed against each other.

    A ``ValueError`` and IF-02's case class. Every message names the rung and
    the thing that differed, because the failure it guards against — four rungs
    compared against different goldens, or on different masks — produces five
    finite deltas and one plausible wrong conclusion (QR-12).
    """


@dataclass(frozen=True)
class Rung:
    """One configuration of the ladder, as dotted case-file assignments.

    Parameters
    ----------
    index
        Position in :data:`LADDER`; the ``rung`` axis of the sweep document
        enumerates these in order.
    name
        Short name, used in the sweep document, the report and every diagnostic.
    stabilisation
        ``numerics.stabilisation``.
    velocity_element, pressure_element
        ``numerics.elements.u`` and ``.p``. ``phi`` and ``c`` stay at P2
        throughout, which is the reference's own choice
        (``.knowledge/09-comsol-reference-settings.md`` section C.2).
    what
        One line on what this rung measures, printed in the report so a reader
        need not reconstruct the ladder from the assignments.
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
        what="the reference's own discretisation (.knowledge/09 C.2, E rows 1, 2, 4)",
    ),
)
"""The four rungs, in the order a reader should read them.

``supg.permits_equal_order`` is ``False``, so rung 1 is P2/P1 by construction and
not by choice; :func:`nanopnp.io.case.resolve` refuses it at equal order.
"""

DELTA_LABELS: tuple[str, ...] = ("total", "transport", "flow", "pair")
"""The four reported deltas, in the order they telescope."""


@dataclass(frozen=True)
class RungOutcome:
    """One rung, compared against one golden.

    Parameters
    ----------
    rung
        Which rung this is.
    golden_hash, probe_hash, case_hash
        The provenance the ladder gates on: four rungs that do not share all
        three were not compared against the same object, and their deltas are
        differences between distances to different things.
    fields, quantities
        The comparisons, as :mod:`nanopnp.validation.compare` produced them.
    stabilisation_currents_A
        Section 6.7's per-species stabilisation contribution, from *this run
        alone*. Carried beside ``Delta_transport`` and never as it.
    """

    rung: Rung
    golden_hash: str
    probe_hash: str
    case_hash: str
    fields: tuple[FieldComparison, ...]
    quantities: tuple[QoIComparison, ...]
    stabilisation_currents_A: Mapping[str, float] | None = None

    def field_errors(self) -> dict[str, float]:
        """Return ``rel_L2_r`` per field: the VAL-01 quantity, and ``E_k``'s source."""
        return {entry.field: entry.rel_L2_r for entry in self.fields}

    def quantity_errors(self) -> dict[str, float]:
        """Return ``|relative|`` per quantity: the VAL-02 quantity.

        The magnitude, where :class:`~nanopnp.validation.compare.QoIComparison`
        keeps the sign. ``E_k`` is a *distance*, so the ladder telescopes
        magnitudes; the signed value stays on the comparison, where a reader
        looking for the direction of a discrepancy will find it.
        """
        return {entry.name: abs(entry.relative) for entry in self.quantities}

    def point_counts(self) -> dict[str, int]:
        """Return the number of retained probe points per field."""
        return {entry.field: entry.points for entry in self.fields}

    def summary(self) -> dict[str, Canonicalisable]:
        """Return this rung's record for the report (FR-25)."""
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
        }


@dataclass(frozen=True)
class Attribution:
    """The five deltas for one field or one quantity.

    Parameters
    ----------
    key
        The field or quantity name.
    kind
        ``"field"`` or ``"quantity"``.
    errors
        ``(E_0, E_1, E_2, E_3)``, one per rung of :data:`LADDER`.
    reference_error
        VAL-04's ``Delta_ref`` for this key, or ``None`` where the refinement
        pair was not supplied.
    """

    key: str
    kind: Literal["field", "quantity"]
    errors: tuple[float, float, float, float]
    reference_error: float | None = None

    @property
    def total(self) -> float:
        """``Delta_total = E_0``: what our shipped default does."""
        return self.errors[0]

    @property
    def transport(self) -> float:
        """``Delta_transport = E_1 - E_0``: the transport stabilisation."""
        return self.errors[1] - self.errors[0]

    @property
    def flow(self) -> float:
        """``Delta_flow = E_2 - E_1``: the flow GLS term on a Taylor-Hood pair."""
        return self.errors[2] - self.errors[1]

    @property
    def pair(self) -> float:
        """``Delta_pair = E_3 - E_2``: P2/P1 to P1/P1."""
        return self.errors[3] - self.errors[2]

    @property
    def residual(self) -> float:
        """``Delta_resid = E_3``: the like-for-like number, and the only possible defect."""
        return self.errors[3]

    def identity_residual(self) -> float:
        """Return the telescoped sum minus ``Delta_resid``.

        Zero to round-off by construction. Asserted anyway, at
        :data:`IDENTITY_TOLERANCE`, because it costs nothing and fails on a slip
        in forming the deltas — but it is *not* what catches a rung compared
        against a stale golden, which telescopes just as cleanly. That is
        :func:`attribute`'s provenance gate.
        """
        return self.total + self.transport + self.flow + self.pair - self.residual

    def verdict(self) -> Verdict:
        """Return what this residual can honestly be called; see :data:`Verdict`."""
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
    case
        The frozen case's name.
    golden_source
        ``"comsol"`` or ``"self"``. Printed by every consumer: a ladder run
        against a self-golden tests the machinery and nothing else.
    golden_hash, probe_hash, case_hash, refinement
        The provenance every rung shared.
    rungs
        The four outcomes, in :data:`LADDER` order.
    attributions
        One per field and per quantity, sorted by kind then key.
    unavailable_fields, unavailable_quantities
        What the golden did not carry. Reported rather than skipped: the open
        question of whether the reference model exports ``p`` at all is answered
        at export time, and a report that quietly covered four fields instead of
        five would answer it wrongly.
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

    def attribution(self, key: str) -> Attribution:
        """Return one key's attribution.

        Raises
        ------
        LadderError
            If no attribution carries that key; the message lists the ones that
            do.
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
            Naming the key and the residual. See
            :meth:`Attribution.identity_residual` for what this does and does
            not establish.

        Notes
        -----
        A non-finite residual fails too, and explicitly: an ``E_k`` of ``inf`` —
        which :mod:`nanopnp.validation.compare` returns where the golden is zero
        everywhere and we are not — telescopes to ``nan``, and ``abs(nan) >
        tolerance`` is ``False``. Left to the magnitude test alone the one rung
        that says nothing would be the one rung that passes.
        """
        for entry in self.attributions:
            residual = entry.identity_residual()
            if not math.isfinite(residual) or abs(residual) > tolerance:
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
        """Content hash over the report's record."""
        return content_hash(ATTRIBUTION_SCHEMA, self.summary())

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the whole report, for the JSON artefact and the manifest (FR-25)."""
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
        return "\n".join(lines) + "\n"


def reference_error(coarse: Golden, fine: Golden, grid: ProbeGrid) -> dict[str, float]:
    """Return VAL-04's ``Delta_ref`` per field: the reference's own discretisation error.

    ``Delta_ref = ||g_fine - g_coarse|| / ||g_fine||`` in the same *r*-weighted
    norm every other number here is taken in, so the comparison against
    ``Delta_resid`` is between two of one quantity.

    Parameters
    ----------
    coarse, fine
        The same case on the published mesh and on one uniform refinement of it.
    grid
        The probe grid both were exported onto.

    Returns
    -------
    dict of str to float
        Per field carried by both, plus one entry per scalar quantity both
        report, keyed as :data:`~nanopnp.validation.compare.COMPARED_QUANTITIES`
        names it.

    Raises
    ------
    LadderError
        If the two goldens are not two refinements of one case on one probe
        grid, or if they carry the same refinement label. Mixing the levels
        inverts ``Delta_ref``'s meaning, which is the one thing it cannot
        survive.
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
    for name in sorted(set(coarse.values) & set(fine.values)):
        keep = fine.defined(name)
        check_mask_agreement(name, keep, coarse.defined(name), grid)
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
    outcomes
        One per rung of :data:`LADDER`, in that order.
    case
        The frozen case's name.
    golden
        The golden every rung was compared against; its manifest supplies the
        report's provenance and its ``source`` the warning every consumer prints.
    reference_errors
        VAL-04's ``Delta_ref`` per key, from :func:`reference_error`, or ``None``
        where the refinement pair was not supplied for this case. Absent, every
        verdict is ``reference-unbounded`` — RSK-09 is simply not bounded here,
        and saying so is the honest report.
    sampled_fields
        Every field *we* sampled on the probe grid, from
        :func:`~nanopnp.validation.compare.sample_on_probe`. It is what
        ``unavailable_fields`` is the complement of, and it cannot be recovered
        from ``outcomes``: a rung's comparisons are already the intersection of
        our fields with the golden's, so asking the golden which of *those* it
        lacks always answers "none" and a report built that way would say a
        golden carrying no ``pressure`` covered it.

    Returns
    -------
    AttributionReport
        With :meth:`~AttributionReport.check_identity` already run.

    Raises
    ------
    LadderError
        If the rungs are not :data:`LADDER`, if they do not share a golden, a
        probe grid and a case, or if two of them retained different numbers of
        probe points for one field. That last one is the gate the arithmetic
        identity cannot be: two rungs masked differently are two distances to
        two different objects, and their difference is not a delta.
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
            name for name in COMPARED_QUANTITIES if name not in outcomes[0].quantity_errors()
        ),
    )
    report.check_identity()
    return report


def _check_shared_provenance(outcomes: Sequence[RungOutcome]) -> None:
    """Abort unless every rung was compared against the same object.

    This is the gate the plan attributed to the telescoping identity. The
    identity cannot do it: ``E_0 + (E_1 - E_0) + (E_2 - E_1) + (E_3 - E_2) =
    E_3`` holds for any four numbers, so a rung compared against a re-exported
    golden telescopes exactly as cleanly as one compared against the right one.
    Comparing the hashes is what catches it.
    """
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
    """Abort unless every rung took its norms over the same probe points."""
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
    """Write the report as JSON and as markdown, and return both paths.

    JSON through :func:`~nanopnp.core.hashing.canonical`, as every other artefact
    record is written, so the file the nightly job uploads and the bytes the
    report hashes are one thing.
    """
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    document = target / f"{report.case}.attribution.json"
    document.write_bytes(canonical({"attribution_hash": report.hash, **report.summary()}))
    readable = target / f"{report.case}.attribution.md"
    readable.write_text(report.markdown(), encoding="utf-8")
    return document, readable


def read_report(path: str | Path) -> dict[str, Canonicalisable]:
    """Return a written report's record, floats restored.

    The report is a record rather than an object with behaviour, so it comes
    back as the mapping it was written as: every consumer of a Tier-3 run reads
    the deltas and the verdict, and none of them re-runs the ladder.
    """
    decoded = decode_floats(json.loads(Path(path).read_text(encoding="utf-8")))
    if not isinstance(decoded, dict):
        raise LadderError(f"{path} does not hold an attribution report object")
    return decoded
