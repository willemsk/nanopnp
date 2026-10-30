"""Stage 7 of §5.2: the fixed-charge and dielectric fields (FR-13, FR-14, FR-27, IF-01)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from nanopnp.charge.deposit import (
    DEPOSIT_PAYLOAD,
    SOLID_SHARE_MIN,
    UNCOVERED_TOL,
    Deposit,
    DepositedCharge,
    check_solid_share,
    deposit,
)
from nanopnp.charge.dielectric import (
    DERIVED_CONSTANTS,
    DERIVED_SOURCE,
    DerivedSolidFraction,
    MaterialMean,
    SolidFractionField,
    derive_solid_fraction,
    derived_summary,
    load_solid_fraction,
    water_facing,
)
from nanopnp.charge.dielectric import summary as solid_fraction_summary
from nanopnp.charge.fields import (
    CANONICAL_UNITS,
    DEFAULT_AXIS_CUTOFF_NM,
    FIELD_SCHEMA,
    PLANE_SMOOTHING_NM,
    ChargeField,
    ChargeFieldError,
    ConservationReport,
    FieldDocument,
    FieldDocumentError,
    check_conservation,
    check_deposit_conservation,
    conservation,
    deposit_conservation,
    load_document,
    load_field,
)
from nanopnp.charge.kernel import (
    KERNEL_ID,
    PATCH_HALF_WIDTHS,
    PLANE_COUNT,
    KernelLattice,
    SourceAtoms,
    check_charged,
    kernel_parameters,
    source_atoms,
    sum_kernel,
)
from nanopnp.charge.protonation import PAYLOAD_NAME as PROTONATION_PAYLOAD
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.hashing import Canonicalisable, file_hash
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.density.grid import read_grid, write_grid
from nanopnp.geometry.region import PAYLOAD_NAME as REGION_PAYLOAD
from nanopnp.geometry.region import (
    RegionRecord,
    build_region,
    distance_to_segments,
    protein_water_edges,
    read_region,
)
from nanopnp.io.artefact import Artefact, ChargeGridArtefact, FieldsArtefact, StageInputs
from nanopnp.io.case import UnsupportedCaseSection, stored_artefact_refused
from nanopnp.io.defaults import ContributedDeviation
from nanopnp.io.store import atomic_write_bytes
from nanopnp.io.workspace import scratch_directory
from nanopnp.mesh.ingest import IngestedMesh, MeshStage, deployed_mesh
from nanopnp.numerics.measures import AXISYMMETRIC, Measures

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.core.typing import Expression, Mesh
    from nanopnp.density.grid import RadialGrid
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.io.store import Store

logger = logging.getLogger(__name__)

CHARGE_PAYLOAD = "charge"
"""The payload key of the charge's lattice ``.npz``: the archival copy of a supplied
field, or the export lattice of a deposited one."""

CHARGE_DOCUMENT_PAYLOAD = "charge_document"
"""The payload key of a deposited charge's ``nanopnp/field/v0.5`` document."""

LATTICE_PAYLOAD = "lattice"
"""The charge-grid artefact's payload key: the export lattice as ``.npz``."""

CHARGE_DOCUMENT = "charge.yaml"
CHARGE_GRID_FILE = "charge.npz"
DEPOSIT_FILE = "deposit.npz"

EPS_R_PAYLOAD = "eps_r"
"""The payload key of the solid fraction's lattice ``.npz``: a supplied field's archival
copy, or the lattice of a derived one."""

EPS_R_FILE = "eps_r.npz"

DEPOSIT_PROVENANCE = "nanopnp stage 7: PHY-16 steps 4-6, deposited (WP28)"
"""``provenance.source`` of the exported field document."""


def smoothed_dielectric_deviations(*, smoothed: bool) -> tuple[ContributedDeviation, ...]:
    """Return the deviation a supplied smoothed dielectric field contributes, if any.

    Parameters
    ----------
    smoothed
        Whether a dielectric field replaces the per-domain constants.
    """
    if not smoothed:
        return ()
    return (
        ContributedDeviation(
            source="inputs.eps_r",
            description=(
                "a smoothed dielectric field, where PHY-20's validated model assigns "
                "eps_r per domain as a constant (section 4.4 NOTE). No case-file switch "
                "selects it: a switch that could disagree with the presence of the input "
                "would be a second source of truth"
            ),
        ),
    )


@dataclass(frozen=True)
class ResolvedFields:
    """The supplied fields, gated, and what the gates measured.

    Parameters
    ----------
    charge
        The fixed-charge field, or None if the case has none.
    eps_r
        The solid-fraction field, or None if the case has none.
    """

    charge: ChargeField | DepositedCharge | None
    conservation: ConservationReport | None
    eps_r: SolidFractionField | DerivedSolidFraction | None
    material_means: tuple[MaterialMean, ...]

    def parameters(self) -> dict[str, Canonicalisable]:
        """Return what keys the artefact: each field's contents and declarations, not its bytes."""
        entries: dict[str, Canonicalisable] = {}
        for name, field in (("charge", self.charge), ("eps_r", self.eps_r)):
            if field is None or isinstance(field, DepositedCharge | DerivedSolidFraction):
                continue
            entry: dict[str, Canonicalisable] = {
                "quantity": field.document.quantity,
                "units": field.document.units,
                "axis_cutoff_nm": field.document.axis_cutoff_nm,
                "q_net_e": field.document.q_net_e,
                "grid": field.grid.descriptor(),
                "grid_digest": field.grid.digest(),
            }
            if isinstance(field, ChargeField):
                # The rule the solve assembles the source with (PHY-19): a change
                # of it moves the converged charge.
                entry["quadrature_order"] = field.quadrature_order
            entries[name] = entry
        return entries

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the manifest's Charge group for this run."""
        record: dict[str, Canonicalisable] = {}
        if isinstance(self.charge, DepositedCharge):
            record["charge"] = {"source": "deposited", **self.charge.deposit.summary()}
        elif self.charge is not None:
            record["charge"] = {
                **self.charge.document.summary(),
                "document": self.charge.source.name,
                "document_sha256": file_hash(self.charge.source),
                "grid": self.charge.grid.descriptor(),
                "grid_digest": self.charge.grid.digest(),
                "conservation": (
                    self.conservation.summary() if self.conservation is not None else None
                ),
            }
        if isinstance(self.eps_r, DerivedSolidFraction):
            record["eps_r"] = derived_summary(self.eps_r, self.material_means)
        elif self.eps_r is not None:
            # Through ``charge.dielectric.summary`` rather than beside it: a second
            # literal dict here is a second place for the dielectric's FR-25
            # record to drift, and it already had — the copy written here carried
            # no ``interpolation`` key while the one under test did.
            record["eps_r"] = {
                **solid_fraction_summary(self.eps_r, self.material_means),
                "document": self.eps_r.source.name,
                "document_sha256": file_hash(self.eps_r.source),
            }
        return record

    def deviations(self) -> tuple[ContributedDeviation, ...]:
        """Return the deviations from the validated model these fields carry."""
        return smoothed_dielectric_deviations(smoothed=isinstance(self.eps_r, SolidFractionField))


def _field_path(supplied: object, *, key: str) -> Path:
    path = getattr(supplied, "path", None)
    if path is None:
        raise stored_artefact_refused(key)
    if not Path(path).is_file():
        # Quoted rather than ``!r``, which doubles a Windows path's separators.
        raise FileNotFoundError(f"inputs.{key}.path '{path}' does not exist")
    return Path(path)


def _element_order(resolved: ResolvedCase) -> int:
    return int(resolved.model_options.get("order", AXISYMMETRIC.element_order))


def gate_parameters(resolved: ResolvedCase, fields: ResolvedFields) -> dict[str, Canonicalisable]:
    """Return what the gates are evaluated at, for the stage-7 key."""
    gates: dict[str, Canonicalisable] = {"element_order": _element_order(resolved)}
    if fields.eps_r is not None or resolved.derives_eps_r:
        gates["solids"] = sorted(resolved.document.physics.solid_permittivities)
    return gates


def read_fields(resolved: ResolvedCase) -> ResolvedFields:
    """Read the fields a case supplies, without gating them on the mesh."""
    charge = (
        None if resolved.charge is None else load_field(_field_path(resolved.charge, key="charge"))
    )
    eps_r = (
        None
        if resolved.eps_r is None
        else load_solid_fraction(_field_path(resolved.eps_r, key="eps_r"))
    )
    if resolved.generates_mesh and resolved.membrane is not None:
        centre = resolved.membrane.centre_z_nm
        for key, field in (("charge", charge), ("eps_r", eps_r)):
            if field is not None and field.document.model_frame_centre_z_nm is not None:
                declared = field.document.model_frame_centre_z_nm
                if declared != centre:
                    offset = centre - declared
                    raise FieldDocumentError(
                        f"inputs.{key} declares model_frame_centre_z_nm {declared:g} nm and "
                        f"geometry.membrane.centre_z_nm is {centre:g} nm: the field was written in "
                        f"another model frame than the mesh stage 5 generates, so every feature "
                        f"would sit {offset:+g} nm along z from where it was written "
                        f"(section 5.3.1 NOTE on inputs.charge, inputs.eps_r); export the field "
                        f"from this case, or correct the declaration"
                    )
    return ResolvedFields(charge=charge, conservation=None, eps_r=eps_r, material_means=())


def gate_fields(
    resolved: ResolvedCase,
    supplied: ResolvedFields,
    mesh: Mesh,
    *,
    measures: Measures = AXISYMMETRIC,
    cancel: CancelToken | None = None,
    progress: Progress | None = None,
) -> ResolvedFields:
    """Assemble and gate fields that read_fields already read.

    Parameters
    ----------
    mesh
        The deployed mesh; the conservation check is evaluated here and nowhere else.
    """
    charge = supplied.charge
    report_: ConservationReport | None = None
    # A deposited charge was gated by the stage that deposited it, against its
    # source atoms; only a supplied one is gated here.
    if isinstance(charge, ChargeField):
        check_cancelled(cancel, "the charge conservation gate")
        report(progress, 0.2, "assembling the fixed charge and checking its conservation")
        report_ = check_conservation(conservation(charge, mesh, measures))
        logger.info(
            "fixed charge %r: Q_grid %.6g e, Q_mesh %.6g e, consumer leg %.3g, producer leg %s",
            charge.document.name,
            report_.q_grid_C / ELEMENTARY_CHARGE,
            report_.q_mesh_C / ELEMENTARY_CHARGE,
            report_.consumer_error,
            "not run" if report_.producer_error is None else f"{report_.producer_error:.3g}",
        )

    eps_r = supplied.eps_r
    means: tuple[MaterialMean, ...] = ()
    # A derived chi was gated by the stage that derived it, on this mesh.
    if isinstance(eps_r, SolidFractionField):
        check_cancelled(cancel, "the dielectric range gate")
        report(progress, 0.6, f"checking the dielectric field from {eps_r.source.name}")
        eps_r.check_range()
        check_cancelled(cancel, "the dielectric registration gate")
        report(progress, 0.8, "checking the solid fraction against the mesh materials")
        means = eps_r.check_materials(
            mesh,
            measures,
            solids=resolved.document.physics.solid_permittivities,
        )
    report(progress, 1.0, "the supplied fields passed their gates")
    return ResolvedFields(charge=charge, conservation=report_, eps_r=eps_r, material_means=means)


def load_fields(
    resolved: ResolvedCase,
    mesh: Mesh,
    *,
    measures: Measures = AXISYMMETRIC,
    cancel: CancelToken | None = None,
    progress: Progress | None = None,
) -> ResolvedFields:
    """Read, assemble and gate the fields a case supplies."""
    report(progress, 0.0, "reading the supplied fields")
    return gate_fields(
        resolved,
        read_fields(resolved),
        mesh,
        measures=measures,
        cancel=cancel,
        progress=progress,
    )


def held_solids(resolved: ResolvedCase) -> tuple[str, ...]:
    """Return the solids a derived chi holds at 1: every one but protein."""
    return tuple(sorted(set(resolved.document.physics.solid_permittivities) - {"protein"}))


def derived_parameters(resolved: ResolvedCase) -> dict[str, Canonicalisable]:
    """Return the stage-7 fields entry of a derived chi."""
    return {
        "source": DERIVED_SOURCE,
        "transition_nm": resolved.dielectric_transition_nm,
        "held_at_one": list(held_solids(resolved)),
        "constants": dict(DERIVED_CONSTANTS),
    }


def _missing_derived(resolved: ResolvedCase) -> KeyError:
    return KeyError(
        f"case {resolved.name!r} derives its solid fraction in stage 7 ('charge') from "
        "charge.dielectric_transition_nm, and this stage was handed no stage-7 artefact holding "
        "it; run the pipeline through 'charge' first. A consumer reads the derived chi and never "
        "solves with a sharp permittivity in its place (WP30 D5)"
    )


def derived_solid_fraction(
    resolved: ResolvedCase, artefact: Artefact | None, mesh: Mesh
) -> DerivedSolidFraction:
    """Return the derived chi of a case, read from stage 7 and bound to mesh."""
    if artefact is None or EPS_R_PAYLOAD not in artefact.payload:
        raise _missing_derived(resolved)
    return DerivedSolidFraction(
        grid=read_grid(Path(artefact.payload[EPS_R_PAYLOAD]), format="npz"),
        transition_nm=resolved.dielectric_transition_nm,
        held=held_solids(resolved),
        mesh=mesh,
    )


def check_water_facing(record: RegionRecord, segments: np.ndarray) -> None:
    """Abort unless the water-facing pieces are the region's protein-to-water boundary."""
    import numpy as np

    edges = np.asarray(protein_water_edges(build_region(record)), dtype=np.float64)
    expected = float(np.hypot(*(edges[:, 1] - edges[:, 0]).T).sum()) if edges.size else 0.0
    found = float(np.hypot(*(segments[:, 1] - segments[:, 0]).T).sum()) if segments.size else 0.0
    if not abs(found - expected) <= 1e-9 * max(1.0, expected):
        raise ChargeFieldError(
            "the water-facing profile is not the region's protein-to-water boundary",
            f"W is {found:.9g} nm long and the region's protein-to-water edges {expected:.9g} nm "
            "(section 4.4 NOTE on the derived solid fraction)",
        )
    if not segments.size:
        return
    midpoints = 0.5 * (segments[:, 0] + segments[:, 1])
    off = distance_to_segments(midpoints, edges)
    worst = int(np.argmax(off))
    if not off[worst] <= 1e-9:
        raise ChargeFieldError(
            "the water-facing profile is not the region's protein-to-water boundary",
            f"a piece of W has its midpoint {float(off[worst]):.3e} nm off every protein edge "
            "facing the electrolyte or the shell (section 4.4 NOTE on the derived solid fraction)",
            f"(r, z) = ({float(midpoints[worst, 0]):.4f}, {float(midpoints[worst, 1]):.4f}) nm",
        )


def derive_fields(
    resolved: ResolvedCase,
    record: RegionRecord,
    mesh: Mesh,
    *,
    measures: Measures,
    cancel: CancelToken | None = None,
    progress: Progress | None = None,
) -> tuple[DerivedSolidFraction, tuple[MaterialMean, ...]]:
    """Derive chi from stage 5's record, bind it to mesh and gate it."""
    started = time.perf_counter()
    check_cancelled(cancel, "deriving the solid fraction")
    report(progress, 0.0, "deriving the solid fraction from the profile")
    points = record.points()
    membrane = record.membrane
    shape = {
        "half_thickness_nm": membrane.half_thickness_nm,
        "inner_trans_nm": membrane.inner_trans_nm,
        "inner_cis_nm": membrane.inner_cis_nm,
    }
    water, _ = water_facing(points, **shape)
    check_water_facing(record, water)
    grid = derive_solid_fraction(points, transition_nm=resolved.dielectric_transition_nm, **shape)
    seconds = time.perf_counter() - started
    field = DerivedSolidFraction(
        grid=grid,
        transition_nm=resolved.dielectric_transition_nm,
        held=held_solids(resolved),
        mesh=mesh,
    )
    check_cancelled(cancel, "the derived solid fraction's gates")
    report(progress, 0.5, "checking the derived solid fraction against the mesh materials")
    field.check_range()
    means = field.check_materials(
        mesh, measures, solids=resolved.document.physics.solid_permittivities
    )
    logger.info(
        "derived chi: delta %g nm on a %d x %d lattice in %.3f s; means %s",
        resolved.dielectric_transition_nm,
        grid.shape[1],
        grid.shape[0],
        seconds,
        ", ".join(f"{mean.material} {mean.mean:.4f}" for mean in means),
    )
    return field, means


def frame_shift_nm(resolved: ResolvedCase) -> float:
    """Return the shift into the model frame, in nm."""
    if resolved.generates_mesh and resolved.membrane is not None:
        return float(resolved.membrane.centre_z_nm)
    return 0.0


def charge_grid_key(resolved: ResolvedCase, protonation: Artefact) -> ChargeGridArtefact:
    """Return the export lattice's key: the protonation artefact and the kernel's settings."""
    return ChargeGridArtefact(
        parameters=kernel_parameters(
            sharpness=resolved.smearing.sharpness,
            spacing_nm=resolved.smearing.grid_spacing_nm,
            shift_z_nm=frame_shift_nm(resolved),
        ),
        protonation_hash=protonation.hash,
    )


def produced_parameters(resolved: ResolvedCase) -> dict[str, Canonicalisable]:
    """Return the stage-7 fields entry of a deposited charge."""
    return {"source": "deposited", "order": _element_order(resolved), "kernel": KERNEL_ID}


def produced_gates(resolved: ResolvedCase) -> dict[str, Canonicalisable]:
    """Return what a deposited charge's gates are evaluated at, for the stage-7 key."""
    return {
        "planes": PLANE_COUNT,
        "plane_smoothing_nm": PLANE_SMOOTHING_NM,
        "solids": sorted(resolved.document.physics.solid_permittivities),
        "solid_share_min": SOLID_SHARE_MIN,
        "uncovered_tol": UNCOVERED_TOL,
    }


def _missing_stage(resolved: ResolvedCase) -> KeyError:
    return KeyError(
        f"case {resolved.name!r} deposits its fixed charge in stage 7 ('charge'), and this stage "
        "was handed no stage-7 artefact to read it from; run the pipeline through 'charge' "
        "first. A consumer reads the deposited charge and never solves a producer case "
        "uncharged (WP28 D9)"
    )


def deposited_charge(
    resolved: ResolvedCase, artefact: Artefact | None, mesh: Mesh
) -> DepositedCharge:
    """Return the deposited charge of a producer case, bound to mesh."""
    if artefact is None or DEPOSIT_PAYLOAD not in artefact.payload:
        raise _missing_stage(resolved)
    return DepositedCharge.bind(Deposit.read(Path(artefact.payload[DEPOSIT_PAYLOAD])), mesh)


def case_fields(
    resolved: ResolvedCase,
    supplied: ResolvedFields | None,
    charge_artefact: Artefact | None,
    mesh: Mesh,
    *,
    measures: Measures = AXISYMMETRIC,
    cancel: CancelToken | None = None,
) -> ResolvedFields:
    """Return the fields a solve, a restore or an export assembles, on mesh."""
    fields = (
        ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
        if supplied is None
        else gate_fields(resolved, supplied, mesh, measures=measures, cancel=cancel)
    )
    if resolved.deposits_charge:
        fields = replace(fields, charge=deposited_charge(resolved, charge_artefact, mesh))
    if resolved.derives_eps_r:
        # Gated by stage 7 on this mesh, whose hash keys that artefact.
        # Its means come from that gate's record, so that a solve's record of
        # this chi does not claim no material was measured.
        fields = replace(
            fields,
            eps_r=derived_solid_fraction(resolved, charge_artefact, mesh),
            material_means=_recorded_means(charge_artefact),
        )
    return fields


def _recorded_means(artefact: Artefact | None) -> tuple[MaterialMean, ...]:
    record = artefact.summary.get(EPS_R_PAYLOAD) if artefact is not None else None
    recorded = record.get("material_means") if isinstance(record, dict) else None
    if not isinstance(recorded, list):
        return ()
    return tuple(
        MaterialMean(
            material=str(entry["material"]),
            mean=float(entry["mean"]),
            branch=str(entry["branch"]),
        )
        for entry in recorded
        if isinstance(entry, dict)
    )


def require_charge_artefact(resolved: ResolvedCase, artefact: Artefact | None) -> None:
    """Refuse a producer or deriving case handed no stage-7 artefact."""
    if resolved.deposits_charge and artefact is None:
        raise _missing_stage(resolved)
    if resolved.derives_eps_r and artefact is None:
        raise _missing_derived(resolved)


def fixed_charge_density(
    resolved: ResolvedCase,
    supplied: ResolvedFields | None,
    charge_artefact: Artefact | None,
    mesh: Mesh,
) -> Expression | None:
    """Return the volume charge density a run carried, on mesh, or None."""
    if resolved.deposits_charge:
        return deposited_charge(resolved, charge_artefact, mesh).volume_density_C_m3()
    if supplied is None or supplied.charge is None:
        return None
    return supplied.charge.volume_density_C_m3()


def _field_document(lattice: KernelLattice, data: Path) -> FieldDocument:
    grid = lattice.grid
    return FieldDocument.model_validate(
        {
            "schema": FIELD_SCHEMA,
            "name": "deposited fixed charge",
            "quantity": "areal_charge_density",
            "units": "C/m^2",
            "provenance": {
                "source": DEPOSIT_PROVENANCE,
                "notes": (
                    f"{KERNEL_ID}, {lattice.atoms.count} charged atoms over "
                    f"{lattice.atoms.frames} frames, spacing {lattice.spacing_nm:g} nm, model "
                    f"frame shifted by {lattice.atoms.shift_z_nm:g} nm"
                ),
            },
            "data": {"path": data.name, "format": "npz", "sha256": file_hash(data)},
            "grid": {
                "origin_nm": list(grid.origin_nm),
                "spacing_nm": list(grid.spacing_nm),
                "shape": list(grid.shape),
            },
            "axis_cutoff_nm": DEFAULT_AXIS_CUTOFF_NM,
            "q_net_e": lattice.atoms.q_net_e(),
            "model_frame_centre_z_nm": lattice.atoms.shift_z_nm,
        }
    )


def _document_text(document: FieldDocument) -> str:
    return yaml.safe_dump(
        document.model_dump(mode="json", by_alias=True, exclude_none=True), sort_keys=False
    )


def write_field_document(lattice: KernelLattice, data: Path, path: Path) -> Path:
    """Write the export lattice's field document to path, naming data beside it."""
    path.write_text(_document_text(_field_document(lattice, data)), encoding="utf-8")
    return path


def export_charge(artefact: Artefact, path: Path) -> tuple[Path, ...]:
    """Write stage 7's charge to path in the format its suffix names; return the files."""
    if CHARGE_PAYLOAD not in artefact.payload:
        raise KeyError(
            "stage 7's artefact carries no charge lattice: the run supplied inputs.eps_r or "
            "derived its solid fraction from charge.dielectric_transition_nm, and has no charge"
        )
    source = Path(artefact.payload[CHARGE_PAYLOAD])
    if path.suffix.lower() != ".yaml":
        grid = read_grid(source, format="npz")
        partial = path.with_name(f".{path.stem}.partial{path.suffix}")
        try:
            write_grid(grid, partial)
            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)
        return (path,)
    if CHARGE_DOCUMENT_PAYLOAD not in artefact.payload:
        raise KeyError(
            "stage 7's artefact carries no field document: its charge was supplied through "
            "inputs.charge, whose own document is the one to keep"
        )
    data = path.with_suffix(".npz")
    stored = load_document(Path(artefact.payload[CHARGE_DOCUMENT_PAYLOAD]))
    if stored.data is None:  # the stage writes ``data:``, never ``form:``
        raise KeyError("stage 7's field document names no data file to export beside it")
    document = stored.model_copy(
        update={"data": stored.data.model_copy(update={"path": Path(data.name)})}
    )
    # Each file through a sibling and a rename, as every other export is written
    # (cli/export.py): a failure leaves the file that was there, never a torn one.
    atomic_write_bytes(data, source.read_bytes())
    atomic_write_bytes(path, _document_text(document).encode("utf-8"))
    return (data, path)


@dataclass(frozen=True)
class StoredLattice:
    """The charge lattice stage 7's artefact carries, as it is stored."""

    grid: RadialGrid
    quantity: str
    units: str

    def weights_m(self) -> tuple[np.ndarray, np.ndarray]:
        """Return the trapezoid weights along z and r, in metres."""
        import numpy as np

        weights_z = self.grid.trapezium_weights("z") * 1e-9
        weights_r = self.grid.trapezium_weights("r") * 1e-9
        if self.quantity != "areal_charge_density":
            weights_r = weights_r * (2.0 * np.pi * self.grid.r_nm * 1e-9)
        return weights_z, weights_r


def stored_lattice(artefact: Artefact) -> StoredLattice | None:
    """Return the charge lattice a stage-7 artefact carries, or None."""
    if CHARGE_PAYLOAD not in artefact.payload:
        return None
    grid = read_grid(Path(artefact.payload[CHARGE_PAYLOAD]), format="npz")
    if CHARGE_DOCUMENT_PAYLOAD in artefact.payload:
        quantity = load_document(Path(artefact.payload[CHARGE_DOCUMENT_PAYLOAD])).quantity
    else:
        record = artefact.summary.get("charge")
        if not isinstance(record, dict) or not isinstance(record.get("quantity"), str):
            raise KeyError("stage 7's artefact carries a charge lattice but records no quantity")
        quantity = str(record["quantity"])
    return StoredLattice(grid=grid, quantity=quantity, units=CANONICAL_UNITS[quantity])


def _region(resolved: ResolvedCase, inputs: StageInputs) -> Artefact | None:
    return inputs.require("region") if resolved.derives_eps_r else None


def _derived_entries(
    resolved: ResolvedCase, region: Artefact | None
) -> tuple[dict[str, Canonicalisable], dict[str, str]]:
    if region is None:
        return {}, {}
    return {"eps_r": derived_parameters(resolved)}, {"region": region.hash}


class FieldStage:
    """Stage 7: a deposited or supplied charge, and a supplied or derived dielectric, gated."""

    name = "charge"

    def __init__(
        self,
        *,
        workspace: Path | None = None,
        overwrite_workspace: bool = False,
        store: Store | None = None,
    ) -> None:
        self._workspace = Path(workspace) if workspace is not None else None
        self._overwrite = overwrite_workspace
        self._store = store

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def deviations(self, inputs: StageInputs) -> tuple[ContributedDeviation, ...]:
        """Return the departures the supplied fields contribute."""
        fields = inputs.require(self.name).parameters["fields"]
        assert isinstance(fields, dict)  # FieldsArtefact writes it as one
        # A derived chi is the switch charge.dielectric_transition_nm, which the
        # case-file diff already records; only a supplied one is told here.
        entry = fields.get("eps_r")
        supplied = isinstance(entry, dict) and entry.get("source") != DERIVED_SOURCE
        return smoothed_dielectric_deviations(smoothed=supplied)

    def key(self, inputs: StageInputs) -> FieldsArtefact:
        """Return the artefact key, without depositing or gating anything."""
        resolved, ingested, mesh_artefact = self._prepare(inputs, ingest_mesh=False)
        del ingested
        supplied = read_fields(resolved)
        if resolved.deposits_charge:
            return self._produced_artefact(resolved, supplied, inputs, mesh_artefact.hash)
        return self.artefact(
            supplied, mesh_artefact.hash, resolved=resolved, region=_region(resolved, inputs)
        )

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> FieldsArtefact:
        """Deposit or read the fields, gate them, archive them, and emit the artefact."""
        check_cancelled(cancel, "reading the fields")
        resolved, ingested, mesh_artefact = self._prepare(inputs, ingest_mesh=True)
        assert ingested is not None  # ``ingest_mesh=True`` admits no other case
        region = _region(resolved, inputs)
        derived: tuple[DerivedSolidFraction, tuple[MaterialMean, ...]] | None = None
        if region is not None:
            record = read_region(Path(region.payload[REGION_PAYLOAD]))
            # An idealised pore cannot derive a dielectric: the case refuses its transition.
            assert isinstance(record, RegionRecord)
            derived = derive_fields(
                resolved,
                record,
                ingested.mesh,
                measures=self._measures(resolved),
                cancel=cancel,
            )
        if not resolved.deposits_charge:
            fields = load_fields(
                resolved,
                ingested.mesh,
                measures=self._measures(resolved),
                cancel=cancel,
                progress=progress,
            )
            if derived is not None:
                fields = replace(fields, eps_r=derived[0], material_means=derived[1])
            check_cancelled(cancel, "writing the archival field copies")
            payload = self._write(fields)
            report(progress, 1.0, "the fields passed their gates")
            return self.artefact(
                fields, mesh_artefact.hash, resolved=resolved, payload=payload, region=region
            )
        return self._produce(
            resolved,
            inputs,
            ingested,
            mesh_artefact,
            derived=derived,
            progress=progress,
            cancel=cancel,
        )

    def artefact(
        self,
        fields: ResolvedFields,
        mesh_hash: str,
        *,
        resolved: ResolvedCase,
        payload: dict[str, Path] | None = None,
        region: Artefact | None = None,
    ) -> FieldsArtefact:
        """Return the artefact for already-loaded supplied fields, with or without payload."""
        derived, upstream = _derived_entries(resolved, region)
        return FieldsArtefact(
            fields={**fields.parameters(), **derived},
            gates=gate_parameters(resolved, fields),
            mesh_hash=mesh_hash,
            upstream=upstream,
            payload=payload or {},
            summary=fields.summary(),
        )

    def _produced_artefact(
        self,
        resolved: ResolvedCase,
        supplied: ResolvedFields,
        inputs: StageInputs,
        mesh_hash: str,
        *,
        payload: dict[str, Path] | None = None,
        summary: dict[str, Canonicalisable] | None = None,
    ) -> FieldsArtefact:
        protonation = inputs.require("protonation")
        grid_key = charge_grid_key(resolved, protonation)
        derived, region = _derived_entries(resolved, _region(resolved, inputs))
        return FieldsArtefact(
            fields={**supplied.parameters(), "charge": produced_parameters(resolved), **derived},
            gates={**gate_parameters(resolved, supplied), **produced_gates(resolved)},
            mesh_hash=mesh_hash,
            upstream={"protonation": protonation.hash, "charge_grid": grid_key.hash, **region},
            payload=payload or {},
            summary=summary or {},
        )

    def _produce(
        self,
        resolved: ResolvedCase,
        inputs: StageInputs,
        ingested: IngestedMesh,
        mesh_artefact: Artefact,
        *,
        derived: tuple[DerivedSolidFraction, tuple[MaterialMean, ...]] | None,
        progress: Progress | None,
        cancel: CancelToken | None,
    ) -> FieldsArtefact:
        started = time.perf_counter()
        protonation = inputs.require("protonation")
        table = ProtonationTable.read(Path(protonation.payload[PROTONATION_PAYLOAD]))
        atoms = source_atoms(
            table, sharpness=resolved.smearing.sharpness, shift_z_nm=frame_shift_nm(resolved)
        )
        data = ingested.data
        mesh = ingested.mesh
        measures = self._measures(resolved)
        solids = tuple(sorted(resolved.document.physics.solid_permittivities))
        # Before the sum: the frame check reads only the atoms and the mesh, so a
        # structure in another frame than its mesh is refused without first paying
        # for every frame's kernel sum. With no charged atom at all it would
        # report a share of nothing, so that cause is refused first.
        check_charged(atoms)
        check_cancelled(cancel, "the solid-share gate")
        report(progress, 0.0, "checking that the atoms sit in the mesh's solids")
        share_started = time.perf_counter()
        share = check_solid_share(atoms, data, solids, cell_nm=resolved.smearing.grid_spacing_nm)
        checked = time.perf_counter()

        directory = self._directory()
        grid_artefact, lattice, cached = self._lattice(
            resolved, protonation, atoms, directory, progress=progress, cancel=cancel
        )
        summed = time.perf_counter()
        report(progress, 0.6, f"depositing on P{measures.element_order}")
        found = deposit(lattice.grid, data, measures.element_order, cancel=cancel)
        charge = DepositedCharge.bind(found, mesh)
        deposited = time.perf_counter()
        check_cancelled(cancel, "the conservation gates")
        report(progress, 0.8, "checking the deposited charge's conservation")
        conserved = check_deposit_conservation(
            deposit_conservation(atoms, lattice.grid, charge.volume_density_C_m3(), mesh, measures)
        )
        logger.info(
            "deposited charge: Q_net %.6g e, producer leg %.3g, consumer leg %.3g, worst plane "
            "%.3g (lattice) and %.3g (mesh), solid share %.3f",
            atoms.q_net_e(),
            conserved.producer_error,
            conserved.consumer_error,
            conserved.worst_plane("grid")[1],
            conserved.worst_plane("mesh")[1],
            share.share,
        )

        supplied = read_fields(resolved)
        eps_r: SolidFractionField | DerivedSolidFraction | None = supplied.eps_r
        means: tuple[MaterialMean, ...] = ()
        if derived is not None:
            eps_r, means = derived[0], derived[1]
        elif isinstance(eps_r, SolidFractionField):
            check_cancelled(cancel, "the dielectric gates")
            report(progress, 0.9, f"checking the dielectric field from {eps_r.source.name}")
            gated = gate_fields(resolved, supplied, mesh, measures=measures, cancel=cancel)
            eps_r, means = gated.eps_r, gated.material_means
        fields = ResolvedFields(charge=None, conservation=None, eps_r=eps_r, material_means=means)
        gated_at = time.perf_counter()

        check_cancelled(cancel, "writing the deposit")
        lattice_file = Path(grid_artefact.payload[LATTICE_PAYLOAD])
        payload = {
            CHARGE_PAYLOAD: lattice_file,
            CHARGE_DOCUMENT_PAYLOAD: write_field_document(
                lattice, lattice_file, directory / CHARGE_DOCUMENT
            ),
            DEPOSIT_PAYLOAD: found.write(directory / DEPOSIT_FILE),
        }
        if eps_r is not None:
            payload[EPS_R_PAYLOAD] = write_grid(eps_r.grid, directory / EPS_R_FILE, format="npz")
        record: dict[str, Canonicalisable] = {
            **fields.summary(),
            "charge": {
                "source": "deposited",
                "q_net_e": atoms.q_net_e(),
                "order": found.order,
                "document": CHARGE_DOCUMENT,
                "lattice": {**dict(grid_artefact.summary), "cached": cached},
                "deposit": found.summary(),
                "solid_share": share.summary(),
                "material_charge_e": dict(found.material_charges_e(data)),
                "conservation": conserved.summary(),
            },
        }
        # The log, not the record: a summary that moved with the clock would give
        # every charged run its own manifest. The stage's total
        # stays in the run record's per-stage seconds; the parts ride on the log
        # record as ``timings``, for a benchmark's handler to collect.
        timings = {
            "sum": (share_started - started) + (summed - checked),
            "deposit": deposited - summed,
            "gates": (checked - share_started) + (gated_at - deposited),
        }
        logger.info(
            "stage 7 timings: sum %.3f s, deposit %.3f s, gates %.3f s",
            timings["sum"],
            timings["deposit"],
            timings["gates"],
            extra={"timings": timings},
        )
        report(progress, 1.0, "the deposited charge passed its gates")
        return self._produced_artefact(
            resolved, supplied, inputs, mesh_artefact.hash, payload=payload, summary=record
        )

    def _lattice(
        self,
        resolved: ResolvedCase,
        protonation: Artefact,
        atoms: SourceAtoms,
        directory: Path,
        *,
        progress: Progress | None,
        cancel: CancelToken | None,
    ) -> tuple[Artefact, KernelLattice, bool]:
        key = charge_grid_key(resolved, protonation)
        stored = self._store.get(key.schema, key.hash) if self._store is not None else None
        if stored is not None:
            grid = read_grid(Path(stored.payload[LATTICE_PAYLOAD]), format="npz")
            lattice = KernelLattice(
                grid=grid,
                atoms=atoms,
                spacing_nm=resolved.smearing.grid_spacing_nm,
                half_widths=PATCH_HALF_WIDTHS,
                renormalised=True,
                raw_deviation=(0.0, 0),
            )
            report(progress, 0.55, "the export lattice was in the store")
            return stored, lattice, True
        lattice = sum_kernel(
            atoms,
            resolved.smearing.grid_spacing_nm,
            cancel=cancel,
            progress=None if progress is None else (lambda f, m: progress(0.05 + 0.5 * f, m)),
        )
        written = write_grid(lattice.grid, directory / CHARGE_GRID_FILE, format="npz")
        produced: Artefact = ChargeGridArtefact(
            parameters=key.parameters,
            protonation_hash=protonation.hash,
            payload={LATTICE_PAYLOAD: written},
            summary=lattice.summary(),
        )
        if self._store is not None:
            produced = self._store.put(produced)
        return produced, lattice, False

    def _measures(self, resolved: ResolvedCase) -> Measures:
        return AXISYMMETRIC.at_order(_element_order(resolved))

    def _prepare(
        self, inputs: StageInputs, *, ingest_mesh: bool
    ) -> tuple[ResolvedCase, IngestedMesh | None, Artefact]:
        resolved = inputs.resolved
        if (
            resolved.charge is None
            and resolved.eps_r is None
            and not resolved.deposits_charge
            and not resolved.derives_eps_r
        ):
            raise UnsupportedCaseSection(
                f"case {resolved.name!r} supplies neither inputs.charge nor inputs.eps_r, "
                "deposits no charge and derives no solid fraction: it carries no structure: "
                "section and no inputs.pqr, and charge.dielectric_transition_nm is 0, so "
                "stage 7 has nothing to read (FR-12 to FR-15)"
            )
        mesh = inputs.upstream.get("mesh")
        ingested: IngestedMesh | None = None
        if ingest_mesh or mesh is None:
            ingested = deployed_mesh(resolved, mesh)
        if mesh is None:
            assert ingested is not None  # ingested above precisely for this
            mesh = MeshStage().artefact(ingested)
        return resolved, ingested, mesh

    def _directory(self) -> Path:
        return scratch_directory(self._workspace, self.name, overwrite=self._overwrite)

    def _write(self, fields: ResolvedFields) -> dict[str, Path]:
        directory = self._directory()
        payload: dict[str, Path] = {}
        if isinstance(fields.charge, ChargeField):
            payload["charge"] = write_grid(
                fields.charge.grid, directory / "charge.npz", format="npz"
            )
        if fields.eps_r is not None:
            payload[EPS_R_PAYLOAD] = write_grid(
                fields.eps_r.grid, directory / EPS_R_FILE, format="npz"
            )
        return payload
