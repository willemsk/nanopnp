"""The charge tab's view-model: stage 7 as it lands, its pictures, and its records.

§8.1's third GUI increment, and Phase 3 criterion 6: build stages 1 to 7 from the
shell, and show the charge, its conservation report and the protonation table per
frame. Everything the tab decides lives here, and nothing here imports PySide6,
NGSolve, PDB2PQR, PROPKA or NumPy at module scope, for the reason
:mod:`nanopnp.gui.geometry` gives: a rule written in a widget is asserted on two
of the seven matrix jobs.

**Every number is read from a stage's own artefact** (WP31 D1). The walk's
:class:`~nanopnp.core.stages.ArtefactHook` reports ``protonation`` and ``charge``
as it reports every stage, and the views read ``Store(store).get(schema, hash)``:
the lattice and the conservation record from stage 7's ``nanopnp/fields/v2``,
the table from the ``protonation`` artefact. The internal ``charge-grid`` and
``protonation-frame`` caches are never read, because WP28 D9 makes stage 7's
artefact the one place a consumer reads the charge from.

**The model frame, and the charge as stored** (D4, D5). The lattice, the atoms,
the deposit and the planes are all in the model frame, and every caption says so.
The map is the areal density ``sigma = 2 pi r rho`` the lattice holds, in the
quantity and unit its ``nanopnp/field/v1`` vocabulary names: the charge per unit
meridional area, so it shows where the charge lies; ``rho`` would overweight the
axis by ``1/r``.

**The picture keeps the charge** (D6, the WP31 plan's Design section 1). A
lattice of a thousand nodes a side is reduced to at most :data:`MAX_PIXELS` by
trapezoid-weighted block means, never by striding: a field whose sign changes
every 0.035 nm would alias under decimation, which is VAL-15's failure
transplanted into a display. ``sum_p mean_p A_p`` is the record's ``q_grid`` to
round-off, whatever the block size and however the last block is cut.

**A stored report always passed** (D10, QR-12): stage 7 aborts on a failed gate,
so what the conservation view can show is the margin, each leg's value against
the tolerance its own record carries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

from nanopnp.charge.protonation import PAYLOAD_NAME as PROTONATION_PAYLOAD
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.charge.stage import StoredLattice, stored_lattice
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.gui.geometry import MODEL_FRAME, ImageModel, StageList, stored_artefact
from nanopnp.gui.render import ChargeQuantity
from nanopnp.io.case import resolve
from nanopnp.io.run import UnknownStageError, selected_stages

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping

    import numpy as np

    from nanopnp.gui.solver import Produced
    from nanopnp.io.case import CaseDocument

__all__ = [
    "BUILD_UPTO",
    "CHARGE_STAGES",
    "MAX_PIXELS",
    "BuildOffer",
    "ChargeMap",
    "ChargeView",
    "ConservationView",
    "Leg",
    "ProtonationFrame",
    "ProtonationView",
    "ResidueRow",
    "block_size",
    "build_offer",
    "charge_image",
    "charge_stages",
    "load_charge",
    "load_protonation",
]

CHARGE_STAGES: tuple[str, ...] = ("protonation", "charge")
"""The two halves of stage 7: the ones the charge tab lists, in the order a walk runs them."""

BUILD_UPTO = "charge"
"""Where **Build charge** stops: the command line's ``run --upto charge`` (WP31 D2)."""

MAX_PIXELS = 1024
"""The most pixels the charge map has along either axis (D6)."""


# -- building --------------------------------------------------------------------


@dataclass(frozen=True)
class BuildOffer:
    """Whether **Build charge** is offered, and if not, why (D2).

    Parameters
    ----------
    offered
        Whether the case walks stage 7.
    reason
        Empty when offered; otherwise the driver's or the loader's own sentence.
    """

    offered: bool
    reason: str = ""


def build_offer(document: CaseDocument) -> BuildOffer:
    """Return whether a walk through ``charge`` has anything to build, in the driver's words.

    :func:`~nanopnp.io.run.selected_stages` is asked for a walk through
    ``charge``, so its refusal of a case that gives stage 7 nothing to read is
    the reason shown, and the shell does not restate its rule (WP24). A case
    that does not resolve is refused with the loader's diagnostic.
    """
    try:
        resolved = resolve(document)
    except (ValueError, NotImplementedError) as error:
        return BuildOffer(offered=False, reason=str(error))
    try:
        selected_stages(resolved, BUILD_UPTO)
    except UnknownStageError as error:
        # Its ``__str__`` is the sentence as written, without ``KeyError``'s quoting.
        return BuildOffer(offered=False, reason=str(error))
    return BuildOffer(offered=True)


def charge_stages(document: CaseDocument) -> StageList:
    """Return the halves of stage 7 a walk through ``charge`` runs, as a stage list.

    ``protonation`` runs only for a case that deposits its charge (WP28 D8); a
    case supplying ``inputs.charge`` or ``inputs.eps_r`` walks ``charge`` alone.

    Raises
    ------
    nanopnp.io.case.CaseValidationError
        If the case does not resolve.
    nanopnp.io.run.UnknownStageError
        If the case walks no stage 7; :func:`build_offer` says so first.
    """
    walked = selected_stages(resolve(document), BUILD_UPTO)
    return StageList(planned=tuple(name for name in walked if name in CHARGE_STAGES))


# -- the charge map --------------------------------------------------------------


def block_size(shape: tuple[int, int], limit: int = MAX_PIXELS) -> int:
    """Return the smallest ``k`` that leaves at most ``limit`` blocks along either axis (D6).

    ``ceil(n / limit)`` for the longer axis ``n``: then ``ceil(n / k) <= limit``,
    and ``k - 1`` would leave more than ``limit``.
    """
    return max(1, math.ceil(max(shape) / limit))


def _block_starts(values: np.ndarray, block: int) -> tuple[np.ndarray, np.ndarray]:
    """Return where each block starts along ``z`` and along ``r``.

    Blocks start every ``block`` nodes along each axis; the last is cut short
    where the axis is not a multiple of it.
    """
    import numpy as np

    return np.arange(0, values.shape[0], block), np.arange(0, values.shape[1], block)


def _block_sums(
    values: np.ndarray, weights_z: np.ndarray, weights_r: np.ndarray, block: int
) -> tuple[np.ndarray, np.ndarray]:
    """Return each block's weighted sum and its area."""
    import numpy as np

    starts_z, starts_r = _block_starts(values, block)
    weighted = values * weights_z[:, None] * weights_r[None, :]
    sums = np.add.reduceat(np.add.reduceat(weighted, starts_z, axis=0), starts_r, axis=1)
    areas = np.outer(np.add.reduceat(weights_z, starts_z), np.add.reduceat(weights_r, starts_r))
    return sums, areas


def _plain_means(values: np.ndarray, block: int) -> np.ndarray:
    """Return each block's unweighted mean: what a block of zero weight is drawn at."""
    import numpy as np

    starts_z, starts_r = _block_starts(values, block)
    counts = np.outer(
        np.diff(np.append(starts_z, values.shape[0])), np.diff(np.append(starts_r, values.shape[1]))
    )
    plain: np.ndarray = (
        np.add.reduceat(np.add.reduceat(values, starts_z, axis=0), starts_r, axis=1) / counts
    )
    return plain


@dataclass(frozen=True)
class ChargeMap:
    """The export lattice as a picture, and the charge the picture carries (D5, D6, D8, D9).

    Parameters
    ----------
    image
        Block means in the model frame, on a diverging scale ``[-limit, limit]``.
    block
        ``k``: each pixel is the trapezoid-weighted mean of up to ``k x k`` nodes.
    areas
        ``A_p``, each pixel's summed weight, in m^2 for an areal density (m^3 for a
        volume density, whose weights carry ``2 pi r``).
    integral_C
        ``sum_p mean_p A_p``, in coulombs: the record's ``q_grid`` to round-off.
    limit
        ``L``, the largest magnitude drawn, which the scale is symmetric about.
    quantity, units
        The lattice's ``nanopnp/field/v1`` quantity and canonical unit.
    planes
        The recorded worst planes, ``(label, z_nm)``, in the model frame.
    """

    image: ImageModel
    block: int
    areas: np.ndarray
    integral_C: float
    limit: float
    quantity: str
    units: str
    planes: tuple[tuple[str, float], ...] = ()

    @property
    def integral_e(self) -> float:
        """The picture's charge in e."""
        return self.integral_C / ELEMENTARY_CHARGE

    def plane_row(self, z_nm: float) -> int:
        """Return the display row whose pixel contains ``z``, where a plane's marker is drawn."""
        return self.image.pixel_of(float(self.image.x_nm[0]), z_nm)[1]


def charge_image(
    lattice: StoredLattice,
    *,
    block: int | None = None,
    planes: tuple[tuple[str, float], ...] = (),
) -> ChargeMap:
    """Return the lattice as a picture that carries its charge (D5, D6, D8).

    Parameters
    ----------
    lattice
        Stage 7's lattice, as :func:`~nanopnp.charge.stage.stored_lattice` reads it.
    block
        ``k``; by default :func:`block_size` of the lattice.
    planes
        Markers to draw, ``(label, z_nm)``, read from the conservation record.

    Notes
    -----
    A pixel is drawn ``k h`` wide, centred where a full block of nodes is: at
    ``k = 1`` that is WP24's node-centred convention, and a partial last block is
    drawn at a full block's width. That is a display convention; the integral
    uses each block's own summed weight ``A_p``.
    """
    import numpy as np

    grid = lattice.grid
    k = block_size(grid.values.shape) if block is None else int(block)
    if k < 1:
        raise ValueError(f"a block is at least one node wide, not {k}")
    weights_z, weights_r = lattice.weights_m()
    sums, areas = _block_sums(grid.values, weights_z, weights_r, k)
    carried = areas > 0.0
    means = np.divide(sums, areas, out=np.zeros_like(sums), where=carried)
    if not carried.all():
        # A block whose weight is zero (the axis column of a volume density, whose
        # weight carries r) carries no charge; it is drawn at its plain mean. Only
        # then is the lattice summed a second time.
        means = np.where(carried, means, _plain_means(grid.values, k))
    finite = means[np.isfinite(means)]
    limit = float(np.max(np.abs(finite))) if finite.size else 0.0
    shown = limit if limit > 0.0 else 1.0
    step_r, step_z = grid.spacing_nm
    origin_r, origin_z = grid.origin_nm
    columns, rows = means.shape[1], means.shape[0]
    x_nm = origin_r + 0.5 * (k - 1) * step_r + k * step_r * np.arange(columns)
    z_nm = origin_z + 0.5 * (k - 1) * step_z + k * step_z * np.arange(rows)
    name = lattice.quantity.replace("_", " ")
    image = ImageModel(
        values=means,
        x_nm=x_nm,
        z_nm=z_nm,
        scale=(-shown, shown),
        title=(
            f"stage 7: {name} ({lattice.units}), {k} x {k} node blocks, scale ±{limit:.3g} "
            f"{lattice.units}, {MODEL_FRAME}"
        ),
        x_label="r (nm)",
        frame=MODEL_FRAME,
        palette="diverging",
    )
    return ChargeMap(
        image=image,
        block=k,
        areas=areas,
        integral_C=float(np.sum(sums)),
        limit=limit,
        quantity=lattice.quantity,
        units=lattice.units,
        planes=planes,
    )


# -- the conservation report -----------------------------------------------------


@dataclass(frozen=True)
class Leg:
    """One leg of the conservation report, as the record holds it (D10).

    Parameters
    ----------
    name
        The leg, named as the record names it.
    value
        Its relative error, or ``None`` when it was not run.
    tolerance
        The budget the record carries beside it, or ``None`` where it carries none.
    reason
        Why it was not run, from the record; empty when it was.
    location
        Where it was measured, for a per-plane leg.
    """

    name: str
    value: float | None
    tolerance: float | None
    reason: str = ""
    location: str = ""

    @property
    def run(self) -> bool:
        """Whether the record holds a value for this leg."""
        return self.value is not None

    @property
    def ratio(self) -> float | None:
        """``|value| / tolerance``: the share of the budget used, or ``None``."""
        if self.value is None or self.tolerance is None or self.tolerance == 0.0:
            return None
        return abs(self.value) / self.tolerance


def _number(value: object) -> float | None:
    """Return a record entry as a float, or ``None`` where it is not a number."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _leg(name: str, entry: object, *, location: str = "") -> Leg:
    """Return one leg from its record entry: a value and a tolerance, or a status and a reason."""
    if not isinstance(entry, dict):
        return Leg(name=name, value=None, tolerance=None, reason="not recorded")
    if "relative_error" not in entry:
        return Leg(
            name=name,
            value=None,
            tolerance=None,
            reason=str(entry.get("reason", entry.get("status", "not run"))),
        )
    return Leg(
        name=name,
        value=_number(entry["relative_error"]),
        tolerance=_number(entry.get("tolerance")),
        location=location,
    )


@dataclass(frozen=True)
class ConservationView:
    """Stage 7's conservation record: its legs against their budgets, and its figures (D10).

    Parameters
    ----------
    source
        ``deposited`` (the producer path) or ``supplied`` (the consumer path).
    legs
        Producer, consumer and quadrature, then the per-plane legs.
    figures
        The record's charges and diagnostics, by the record's own names, in e or
        nm: ``q_net_e``, ``q_grid_e``, ``q_mesh_e``, ``axis_guard_deficit_e``,
        the boundary ring, and on a deposit ``material_charge_e`` and the solid
        share.
    planes
        The worst planes, ``(label, z_nm)``, for the charge map to mark (D9).
    """

    source: Literal["deposited", "supplied"]
    legs: tuple[Leg, ...]
    figures: Mapping[str, object]
    planes: tuple[tuple[str, float], ...]

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> ConservationView:
        """Read the view from ``summary["charge"]``, in either of its two forms.

        Raises
        ------
        KeyError
            If the record carries no conservation report.
        """
        report = record.get("conservation")
        if not isinstance(report, dict):
            raise KeyError("stage 7's charge record carries no conservation report")
        deposited = record.get("source") == "deposited"
        legs = [
            _leg("producer", report.get("producer")),
            _leg("consumer", report.get("consumer")),
            _leg("quadrature agreement", report.get("quadrature_agreement")),
        ]
        per_plane = report.get("per_plane")
        plane = per_plane if isinstance(per_plane, dict) else {}
        planes: list[tuple[str, float]] = []
        sides = (("lattice", "grid_"), ("mesh", "mesh_")) if deposited else (("mesh", ""),)
        for side, prefix in sides:
            z = _number(plane.get(f"{prefix}worst_plane_z_nm"))
            error = plane.get(f"{prefix}worst_relative_error")
            entry = {"relative_error": error, "tolerance": plane.get("tolerance")}
            location = "" if z is None else f"z = {z:.4g} nm"
            legs.append(_leg(f"worst plane ({side})", entry, location=location))
            if z is not None and math.isfinite(z):
                planes.append((f"worst plane ({side})", z))
        figures: dict[str, object] = {
            key: report.get(key)
            for key in ("q_net_e", "q_grid_e", "q_mesh_e", "axis_guard_deficit_e")
        }
        figures["boundary_ring"] = report.get("boundary_ring")
        if deposited:
            figures["material_charge_e"] = record.get("material_charge_e")
            figures["solid_share"] = record.get("solid_share")
        return cls(
            source="deposited" if deposited else "supplied",
            legs=tuple(legs),
            figures=figures,
            planes=tuple(planes),
        )


# -- stage 7 ---------------------------------------------------------------------


@dataclass(frozen=True)
class ChargeView:
    """What stage 7's artefact shows: the map, the report and the dielectric (D3).

    Parameters
    ----------
    charge
        The lattice's picture, or ``None`` for a case that carries no charge.
    conservation
        Its conservation record, or ``None`` likewise.
    dielectric
        One line per entry of the dielectric record, or the statement that the
        dielectric is the material split when the case has neither a supplied
        nor a derived ``chi``.
    quantities
        What the deployed-field pane may ask the render child for: ``charge``
        when stage 7 recorded a charge, ``chi`` when it recorded a solid
        fraction. Read from the record, so a sharp dielectric is never offered
        as a picture of zeros (D3, D7).
    """

    charge: ChargeMap | None
    conservation: ConservationView | None
    dielectric: tuple[str, ...]
    quantities: tuple[ChargeQuantity, ...] = ()
    frame: str = MODEL_FRAME


def _dielectric(summary: Mapping[str, object]) -> tuple[str, ...]:
    """Return the dielectric record as lines, or the material split it falls back to."""
    record = summary.get("eps_r")
    if not isinstance(record, dict):
        return (
            "no solid fraction: the dielectric is the material split, each material at its "
            "physics.solid_permittivities constant (PHY-20)",
        )
    lines = [f"source: {record.get('source', 'supplied')}"]
    for key in ("transition_nm", "held_at_one", "name"):
        if key in record:
            lines.append(f"{key}: {record[key]}")
    means = record.get("material_means")
    if isinstance(means, list):
        for entry in means:
            if isinstance(entry, dict):
                lines.append(
                    f"mean chi over {entry.get('material')}: {entry.get('mean')} "
                    f"({entry.get('branch')})"
                )
    return tuple(lines)


def load_charge(event: Produced, *, block: int | None = None) -> ChargeView:
    """Read stage 7's artefact from the store into what the tab shows (D1).

    Called off the Qt thread: the reference lattice is about 15 million nodes.

    Raises
    ------
    FileNotFoundError
        If the artefact has left the store since it was reported.
    ValueError
        If the event is not stage 7's.
    """
    if event.name != BUILD_UPTO:
        raise ValueError(f"stage {event.name!r} is not stage 7 ({BUILD_UPTO!r})")
    artefact = stored_artefact(event)
    summary = dict(artefact.summary)
    record = summary.get("charge")
    conservation = ConservationView.from_record(record) if isinstance(record, dict) else None
    lattice = stored_lattice(artefact)
    charge = (
        None
        if lattice is None
        else charge_image(
            lattice, block=block, planes=conservation.planes if conservation is not None else ()
        )
    )
    quantities: list[ChargeQuantity] = []
    if isinstance(record, dict):
        quantities.append("charge")
    if isinstance(summary.get("eps_r"), dict):
        quantities.append("chi")
    return ChargeView(
        charge=charge,
        conservation=conservation,
        dielectric=_dielectric(summary),
        quantities=tuple(quantities),
    )


# -- the protonation table -------------------------------------------------------


@dataclass(frozen=True)
class ResidueRow:
    """One titratable group, or on a supplied PQR one residue, in one frame (D11).

    Parameters
    ----------
    chain, residue
        The residue: stage 1's chain key, and ``NAME resid`` with its insertion code.
    group
        PROPKA's group label, or empty for a supplied PQR's residue.
    pka
        The group's pKa in this frame, or ``None`` where it was not computed.
    applied_e
        The charge the residue carries in the table.
    expected_e
        The charge PROPKA's group states give it at the pH, or ``None``.
    unapplied
        Whether the two differ, as the table records it.
    """

    chain: str
    residue: str
    group: str
    pka: float | None
    applied_e: float
    expected_e: float | None
    unapplied: bool


@dataclass(frozen=True)
class ProtonationFrame:
    """One frame of the table: its ``Q_net`` and its rows."""

    index: int
    q_net_e: float
    rows: tuple[ResidueRow, ...]


RecordedWarning: TypeAlias = tuple[str, int]
"""A PDB2PQR or PROPKA warning and how many times it was raised."""


def _float_or_none(value: float) -> float | None:
    """Return ``None`` for NaN, the table's marker of a value not computed."""
    return None if math.isnan(value) else float(value)


@dataclass(frozen=True)
class ProtonationView:
    """The protonation artefact: the frames, their charges, and the recorded diagnostics (D11).

    Parameters
    ----------
    table
        The payload, read through :class:`~nanopnp.charge.protonation.ProtonationTable`.
    summary
        The artefact's record.
    """

    table: ProtonationTable
    summary: Mapping[str, object]

    @classmethod
    def build(cls, table: ProtonationTable, summary: Mapping[str, object]) -> ProtonationView:
        """Return the view, after checking the table's unapplied states against the record.

        Raises
        ------
        ValueError
            If the residues the table flags as unapplied in some frame are not the
            ones the record lists: the two were written together, so a disagreement
            is a table and a record of different runs.
        """
        view = cls(table=table, summary=summary)
        # Summed here, on the loader's thread, and kept: the pane reads it on
        # every frame it shows, and the 2WCD table is 50 frames of ~30,000 atoms.
        _ = view.q_net_e
        flagged = view.unapplied_residues()
        recorded = {
            (str(entry.get("chain")), str(entry.get("residue")))
            for entry in summary.get("unapplied", []) or []  # type: ignore[attr-defined]
            if isinstance(entry, dict)
        }
        if flagged != recorded:
            raise ValueError(
                "the protonation table's unapplied states are not the ones its record lists: "
                f"the table flags {sorted(flagged)} and the record {sorted(recorded)}"
            )
        return view

    @property
    def frames(self) -> int:
        """Number of frames."""
        return self.table.frames

    @cached_property
    def q_net_e(self) -> tuple[float, ...]:
        """``Q_net`` per frame, summed from the table's atoms once and kept."""
        return tuple(float(value) for value in self.table.q_net_e())

    @property
    def titrated(self) -> bool:
        """Whether PROPKA ran: the table carries its groups."""
        return len(self.table.group_type) > 0

    @property
    def pka_status(self) -> str:
        """``computed``, or why no pKa is shown, from the record's source."""
        if self.titrated:
            return "computed"
        source = self.summary.get("source")
        titration = self.summary.get("titration")
        return f"not run: source {source}, titration {titration}"

    def _residue(self, column: int) -> tuple[str, str]:
        """Return ``(chain, NAME resid icode)`` of one residue."""
        table = self.table
        return (
            str(table.residue_chain[column]),
            f"{table.residue_name[column]} {int(table.residue_resid[column])}"
            f"{table.residue_icode[column]}",
        )

    def unapplied_residues(self) -> set[tuple[str, str]]:
        """Return the residues the table flags as unapplied in any frame."""
        return {
            self._residue(column)
            for column in range(self.table.unapplied.shape[1])
            if bool(self.table.unapplied[:, column].any())
        }

    def frame(self, index: int) -> ProtonationFrame:
        """Return one frame's rows: one per PROPKA group, or one per residue without them.

        Raises
        ------
        IndexError
            If the frame is not in the table.
        """
        if not 0 <= index < self.frames:
            raise IndexError(f"frame {index} is not in a table of {self.frames} frames")
        table = self.table
        rows: list[ResidueRow] = []

        def row(column: int, *, group: str, pka: float | None) -> ResidueRow:
            chain, residue = self._residue(column)
            return ResidueRow(
                chain=chain,
                residue=residue,
                group=group,
                pka=pka,
                applied_e=float(table.residue_charge_e[index, column]),
                expected_e=_float_or_none(float(table.expected_charge_e[index, column])),
                unapplied=bool(table.unapplied[index, column]),
            )

        if self.titrated:
            for group in range(len(table.group_type)):
                rows.append(
                    row(
                        int(table.group_residue[group]),
                        group=str(table.group_label[group]) or str(table.group_type[group]),
                        pka=_float_or_none(float(table.group_pka[index, group])),
                    )
                )
        else:
            rows.extend(
                row(column, group="", pka=None) for column in range(len(table.residue_name))
            )
        return ProtonationFrame(index=index, q_net_e=self.q_net_e[index], rows=tuple(rows))

    @property
    def chain_differences(self) -> tuple[Mapping[str, object], ...]:
        """The residues whose charge differs between identical chains, as recorded."""
        found = self.summary.get("chain_differences") or []
        return tuple(entry for entry in found if isinstance(entry, dict))  # type: ignore[attr-defined]

    @property
    def warnings(self) -> tuple[RecordedWarning, ...]:
        """PDB2PQR's and PROPKA's warnings with their counts, as recorded."""
        found = self.summary.get("warnings")
        if not isinstance(found, dict):
            return ()
        return tuple((str(message), int(count)) for message, count in sorted(found.items()))

    @property
    def settings(self) -> tuple[str, ...]:
        """The record's source, settings and ``variant`` beside ``Q_net`` (OPN-04), as lines."""
        return tuple(
            f"{key}: {self.summary.get(key)}"
            for key in ("source", "forcefield", "ph", "titration", "variant")
        )


def load_protonation(event: Produced) -> ProtonationView:
    """Read the protonation artefact from the store into what its pane shows (D1, D11).

    Called off the Qt thread (WP24 D11): the 2WCD table holds 50 frames of some
    30,000 atoms.

    Raises
    ------
    FileNotFoundError
        If the artefact has left the store since it was reported.
    ValueError
        If the event is not the protonation stage's, or its table and record disagree.
    """
    if event.name != CHARGE_STAGES[0]:
        raise ValueError(f"stage {event.name!r} is not {CHARGE_STAGES[0]!r}")
    artefact = stored_artefact(event)
    table = ProtonationTable.read(Path(artefact.payload[PROTONATION_PAYLOAD]))
    return ProtonationView.build(table, dict(artefact.summary))
