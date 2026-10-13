"""The charge tab's view-model: stage 7 as it lands, its pictures, and its records."""

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
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import (
    UnknownStageError,
    selected_stages,
)

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

BUILD_UPTO = "charge"

MAX_PIXELS = 1024


@dataclass(frozen=True)
class BuildOffer:
    offered: bool
    reason: str = ""


def build_offer(document: CaseDocument) -> BuildOffer:
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
    walked = selected_stages(resolve(document), BUILD_UPTO)
    return StageList(planned=tuple(name for name in walked if name in CHARGE_STAGES))


def block_size(shape: tuple[int, int], limit: int = MAX_PIXELS) -> int:
    return max(1, math.ceil(max(shape) / limit))


def _block_starts(values: np.ndarray, block: int) -> tuple[np.ndarray, np.ndarray]:
    import numpy as np

    return np.arange(0, values.shape[0], block), np.arange(0, values.shape[1], block)


def _block_sums(
    values: np.ndarray, weights_z: np.ndarray, weights_r: np.ndarray, block: int
) -> tuple[np.ndarray, np.ndarray]:
    import numpy as np

    starts_z, starts_r = _block_starts(values, block)
    weighted = values * weights_z[:, None] * weights_r[None, :]
    sums = np.add.reduceat(np.add.reduceat(weighted, starts_z, axis=0), starts_r, axis=1)
    areas = np.outer(np.add.reduceat(weights_z, starts_z), np.add.reduceat(weights_r, starts_r))
    return sums, areas


def _plain_means(values: np.ndarray, block: int) -> np.ndarray:
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
        return self.integral_C / ELEMENTARY_CHARGE

    def plane_row(self, z_nm: float) -> int:
        return self.image.pixel_of(float(self.image.x_nm[0]), z_nm)[1]


def charge_image(
    lattice: StoredLattice,
    *,
    block: int | None = None,
    planes: tuple[tuple[str, float], ...] = (),
) -> ChargeMap:
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
        # A zero-weight block (the axis column of a volume density) carries no charge and is drawn
        # at its plain mean; only then is the lattice summed a second time.
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


@dataclass(frozen=True)
class Leg:
    name: str
    value: float | None
    tolerance: float | None
    reason: str = ""
    location: str = ""

    @property
    def run(self) -> bool:
        return self.value is not None

    @property
    def ratio(self) -> float | None:
        if self.value is None or self.tolerance is None or self.tolerance == 0.0:
            return None
        return abs(self.value) / self.tolerance


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _leg(name: str, entry: object, *, location: str = "") -> Leg:
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
    source: Literal["deposited", "supplied"]
    legs: tuple[Leg, ...]
    figures: Mapping[str, object]
    planes: tuple[tuple[str, float], ...]

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> ConservationView:
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


@dataclass(frozen=True)
class ChargeView:
    charge: ChargeMap | None
    conservation: ConservationView | None
    dielectric: tuple[str, ...]
    quantities: tuple[ChargeQuantity, ...] = ()
    frame: str = MODEL_FRAME


def _dielectric(summary: Mapping[str, object]) -> tuple[str, ...]:
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


# Called off the Qt thread: the reference lattice is about 15 million nodes.
def load_charge(event: Produced, *, block: int | None = None) -> ChargeView:
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


@dataclass(frozen=True)
class ResidueRow:
    chain: str
    residue: str
    group: str
    pka: float | None
    applied_e: float
    expected_e: float | None
    unapplied: bool


@dataclass(frozen=True)
class ProtonationFrame:
    index: int
    q_net_e: float
    rows: tuple[ResidueRow, ...]


RecordedWarning: TypeAlias = tuple[str, int]


def _float_or_none(value: float) -> float | None:
    return None if math.isnan(value) else float(value)


@dataclass(frozen=True)
class ProtonationView:
    table: ProtonationTable
    summary: Mapping[str, object]

    @classmethod
    def build(cls, table: ProtonationTable, summary: Mapping[str, object]) -> ProtonationView:
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
        return self.table.frames

    @cached_property
    def q_net_e(self) -> tuple[float, ...]:
        return tuple(float(value) for value in self.table.q_net_e())

    @property
    def titrated(self) -> bool:
        return len(self.table.group_type) > 0

    @property
    def pka_status(self) -> str:
        if self.titrated:
            return "computed"
        source = self.summary.get("source")
        titration = self.summary.get("titration")
        return f"not run: source {source}, titration {titration}"

    def _residue(self, column: int) -> tuple[str, str]:
        table = self.table
        return (
            str(table.residue_chain[column]),
            f"{table.residue_name[column]} {int(table.residue_resid[column])}"
            f"{table.residue_icode[column]}",
        )

    def unapplied_residues(self) -> set[tuple[str, str]]:
        return {
            self._residue(column)
            for column in range(self.table.unapplied.shape[1])
            if bool(self.table.unapplied[:, column].any())
        }

    def frame(self, index: int) -> ProtonationFrame:
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
        found = self.summary.get("chain_differences") or []
        return tuple(entry for entry in found if isinstance(entry, dict))  # type: ignore[attr-defined]

    @property
    def warnings(self) -> tuple[RecordedWarning, ...]:
        found = self.summary.get("warnings")
        if not isinstance(found, dict):
            return ()
        return tuple((str(message), int(count)) for message, count in sorted(found.items()))

    @property
    def settings(self) -> tuple[str, ...]:
        return tuple(
            f"{key}: {self.summary.get(key)}"
            for key in ("source", "forcefield", "ph", "titration", "variant")
        )


def load_protonation(event: Produced) -> ProtonationView:
    if event.name != CHARGE_STAGES[0]:
        raise ValueError(f"stage {event.name!r} is not {CHARGE_STAGES[0]!r}")
    artefact = stored_artefact(event)
    table = ProtonationTable.read(Path(artefact.payload[PROTONATION_PAYLOAD]))
    return ProtonationView.build(table, dict(artefact.summary))
