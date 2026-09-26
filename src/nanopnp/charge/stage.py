"""Stage 7 of §5.2: the external fixed-charge and dielectric fields (FR-27, IF-01).

The consumer path of the charge stage. Its producer half — PDB2PQR, protonation,
per-atom smearing and the azimuthal projection — is v0.9; what runs here is
everything downstream of the grid: read the header document, read the data,
interpolate onto the deployed mesh, and gate.

The stage takes ``("case", "mesh")`` and not the case alone, which the §5.1
pipeline diagram does not show and §5.2's stage-7 row now does: PHY-19's
assertion is evaluated **on the deployed finite-element mesh**, not on the source
grid, so a field is not admissible in the abstract but only against the mesh it
will be assembled on. That is also why the mesh's content hash is an input of the
artefact: the same field on a different mesh is a different gate result.

Cancellation is checked between the two fields and before each set of gates,
which is where the seconds are: the mesh integrals of :func:`conservation` are
the only expensive thing this stage does.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.fields import (
    ChargeField,
    ConservationReport,
    check_conservation,
    conservation,
    load_field,
)
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.hashing import Canonicalisable, file_hash
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.density.grid import write_grid
from nanopnp.io.artefact import Artefact, FieldsArtefact, StageInputs
from nanopnp.io.case import UnsupportedCaseSection, resolve
from nanopnp.io.defaults import ContributedDeviation
from nanopnp.materials.fields import (
    MaterialMean,
    SolidFractionField,
    load_solid_fraction,
)
from nanopnp.materials.fields import summary as solid_fraction_summary
from nanopnp.mesh.ingest import IngestedMesh, MeshStage, deployed_mesh
from nanopnp.physics.measures import AXISYMMETRIC, Measures

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Mesh
    from nanopnp.io.case import ResolvedCase

logger = logging.getLogger(__name__)

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the archival native copies are written to."""


def smoothed_dielectric_deviations(*, smoothed: bool) -> tuple[ContributedDeviation, ...]:
    """Return the FR-25 deviation a supplied ``inputs.eps_r`` contributes, if any.

    Module-level, and taking a boolean rather than the fields, because two
    callers need the same sentence from different things in hand:
    :meth:`ResolvedFields.deviations` has the loaded fields, and
    :meth:`FieldStage.deviations` has only the stage-7 artefact — whose
    ``fields`` parameter names ``eps_r`` exactly when one was supplied, so the
    driver need not re-read the field table (tens of megabytes) to learn what
    the artefact already records.

    Parameters
    ----------
    smoothed
        Whether the run supplies a dielectric field in place of PHY-20's
        per-domain constants.
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

    Returned instead of the bare coefficient functions because the artefact and
    the FR-25 manifest both need what the gates already computed — the
    conservation legs, the ring maximum, the per-material means — and recomputing
    them would mean integrating over the mesh twice and could give two different
    answers.

    Parameters
    ----------
    charge
        The fixed-charge field, or ``None`` if the case supplies none.
    conservation
        Its PHY-19 report; ``None`` with no charge field.
    eps_r
        The solid-fraction field, or ``None``.
    material_means
        The mean of ``chi`` over each material, empty with no dielectric field.
    """

    charge: ChargeField | None
    conservation: ConservationReport | None
    eps_r: SolidFractionField | None
    material_means: tuple[MaterialMean, ...]

    def parameters(self) -> dict[str, Canonicalisable]:
        """Return what keys the artefact: each field's contents and declarations.

        The grid's digest rather than its values, and the header's *physical*
        declarations rather than the file's bytes: the same table written as
        ``.npz`` and as OpenDX is one entry, and a table whose values moved is
        another (§5.3.2).
        """
        entries: dict[str, Canonicalisable] = {}
        for name, field in (("charge", self.charge), ("eps_r", self.eps_r)):
            if field is None:
                continue
            entries[name] = {
                "quantity": field.document.quantity,
                "units": field.document.units,
                "axis_cutoff_nm": field.document.axis_cutoff_nm,
                "q_net_e": field.document.q_net_e,
                "grid": field.grid.descriptor(),
                "grid_digest": field.grid.digest(),
            }
        return entries

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the manifest's Charge group for this run (FR-25, §5.3.3)."""
        record: dict[str, Canonicalisable] = {}
        if self.charge is not None:
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
        if self.eps_r is not None:
            # Through ``materials.fields.summary`` rather than beside it: a second
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
        """Return the deviations from the validated model these fields carry.

        A smoothed dielectric is a deviation because PHY-20 gives the validated
        model sharp per-domain constants, and no case-file switch selects it, so
        :func:`nanopnp.io.defaults.deviations` cannot see it and must be told
        (§5.3.3, FR-25).

        The other stage-contributed deviation, an ``exclusion`` material on the
        supplied mesh, belongs to :meth:`nanopnp.mesh.ingest.IngestedMesh.deviations`
        and not here: a run may carry that mesh and no field at all, and a Stern
        layer that went unrecorded because stage 7 had nothing to read would be
        exactly the silent departure FR-25 exists to prevent.
        """
        return smoothed_dielectric_deviations(smoothed=self.eps_r is not None)


def _field_path(supplied: object, *, key: str) -> Path:
    """Return the header document a case names, checked.

    Raises
    ------
    UnsupportedCaseSection
        If the field is named by store hash rather than by path (``resolve``
        refuses that earlier; this is the guard for a stage invoked directly).
    FileNotFoundError
        If the document is not there.
    """
    path = getattr(supplied, "path", None)
    if path is None:
        raise UnsupportedCaseSection(
            f"inputs.{key}: artefact: names a field in the store, which the charge pipeline of "
            f"v0.9 fills; supply inputs.{key}: path: instead"
        )
    if not Path(path).is_file():
        # Quoted rather than ``!r``, which doubles a Windows path's separators.
        raise FileNotFoundError(f"inputs.{key}.path '{path}' does not exist")
    return Path(path)


def read_fields(resolved: ResolvedCase) -> ResolvedFields:
    """Read the fields a case supplies, **without** gating them.

    What :meth:`FieldStage.key` needs: the artefact's key is each grid's digest
    and its header's declarations, none of which involves the mesh, and a cache
    key that could only be computed by running the stage would not be a cache key
    (§5.3.2). Every gate is in :func:`load_fields`, which is what actually runs.

    Raises
    ------
    nanopnp.charge.fields.FieldDocumentError
        If a document is invalid or describes different data than it names.
    """
    charge = (
        None if resolved.charge is None else load_field(_field_path(resolved.charge, key="charge"))
    )
    eps_r = (
        None
        if resolved.eps_r is None
        else load_solid_fraction(_field_path(resolved.eps_r, key="eps_r"))
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
    """Assemble and gate fields :func:`read_fields` already read (PHY-18, PHY-19, VER-30).

    Split from the reading so that a caller holding the fields — the solve stage,
    which reads them to key its own artefact — gates the grids it has rather than
    reading them a second time. The reference table is 77 MB of text, and a
    second parse of it is a second chance to disagree as well as a second minute.

    Parameters
    ----------
    resolved
        The resolved case, which names the solid permittivities the dielectric
        blend registers against.
    supplied
        The ungated fields, as :func:`read_fields` returns them.
    mesh
        The deployed mesh. PHY-19's assertion is evaluated here and nowhere else.
    measures
        The quadrature policy of the solve the fields will enter, so that the
        conservation number is the conservation of the charge the solver carries.
    cancel, progress
        Checked and reported between the two fields and their gates.

    Returns
    -------
    ResolvedFields
        The fields and everything the gates measured.

    Raises
    ------
    nanopnp.charge.fields.ChargeFieldError
        On any gate failure, naming the gate, the quantity and its location.
    """
    charge = supplied.charge
    report_: ConservationReport | None = None
    if charge is not None:
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
    if eps_r is not None:
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
    """Read, assemble and gate the fields a case supplies.

    :func:`read_fields` followed by :func:`gate_fields`; see those two for the
    parameters and for what each raises.
    """
    report(progress, 0.0, "reading the supplied fields")
    return gate_fields(
        resolved,
        read_fields(resolved),
        mesh,
        measures=measures,
        cancel=cancel,
        progress=progress,
    )


class FieldStage:
    """Stage 7: supplied field documents to gated, content-addressed fields."""

    name = "charge"

    def __init__(self, *, workspace: Path | None = None) -> None:
        """Build the stage.

        Parameters
        ----------
        workspace
            Directory the archival native copies are written to before the store
            copies them in. Defaults to a fresh directory under the store root,
            as :class:`~nanopnp.mesh.ingest.MeshStage` does.
        """
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def deviations(self, inputs: StageInputs) -> tuple[ContributedDeviation, ...]:
        """Return the departures the supplied fields contribute (FR-25).

        Called by the driver *after* this stage's artefact is in hand and with
        that artefact under ``inputs.upstream["charge"]``, so the answer comes
        from the ``fields`` parameter the artefact already records rather than
        from a second read of the field tables. The same sentence
        :meth:`ResolvedFields.deviations` returns, from the same helper.
        """
        fields = inputs.require(self.name).parameters["fields"]
        assert isinstance(fields, dict)  # FieldsArtefact writes it as one
        return smoothed_dielectric_deviations(smoothed="eps_r" in fields)

    def key(self, inputs: StageInputs) -> FieldsArtefact:
        """Return the artefact key these fields will produce, without gating them.

        Reads the grids, because their digests *are* the key, and does not
        integrate over the mesh: the gate is what :meth:`run` adds. Nor does it
        ingest the mesh where stage 6 handed its artefact down — the key needs
        that artefact's hash and nothing else, and reading and quality-gating a
        mesh to answer "is this already in the store?" is the whole cost the
        cache exists to avoid.
        """
        resolved, ingested, mesh_artefact = self._prepare(inputs, ingest_mesh=False)
        del ingested
        return self.artefact(read_fields(resolved), mesh_artefact.hash)

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> FieldsArtefact:
        """Read, gate and archive the supplied fields, and emit the artefact.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true. No artefact is written.
        nanopnp.io.case.UnsupportedCaseSection
            If the case supplies no field at all, which describes no work for
            this stage rather than an empty result.
        """
        check_cancelled(cancel, "reading the supplied fields")
        resolved, ingested, mesh_artefact = self._prepare(inputs, ingest_mesh=True)
        assert ingested is not None  # ``ingest_mesh=True`` admits no other case
        fields = load_fields(
            resolved,
            ingested.mesh,
            measures=self._measures(resolved),
            cancel=cancel,
            progress=progress,
        )
        check_cancelled(cancel, "writing the archival field copies")
        payload = self._write(fields)
        report(progress, 1.0, "the supplied fields passed their gates")
        return self.artefact(fields, mesh_artefact.hash, payload=payload)

    def artefact(
        self,
        fields: ResolvedFields,
        mesh_hash: str,
        *,
        payload: dict[str, Path] | None = None,
    ) -> FieldsArtefact:
        """Return the artefact for already-loaded fields, with or without payload.

        Public for the same reason :meth:`nanopnp.mesh.ingest.MeshStage.artefact`
        is: stage 10 has the :class:`ResolvedFields` in hand and needs its key,
        and two loadings of one file are two chances to disagree.
        """
        return FieldsArtefact(
            fields=fields.parameters(),
            mesh_hash=mesh_hash,
            payload=payload or {},
            summary=fields.summary(),
        )

    def _measures(self, resolved: ResolvedCase) -> Measures:
        """Return the quadrature policy the solve will assemble at."""
        order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
        return replace(AXISYMMETRIC, element_order=order)

    def _prepare(
        self, inputs: StageInputs, *, ingest_mesh: bool
    ) -> tuple[ResolvedCase, IngestedMesh | None, Artefact]:
        """Resolve the case, ingest the mesh, and refuse a case with no fields.

        Parameters
        ----------
        ingest_mesh
            Whether the caller needs the geometry itself and not only its hash.
            :meth:`run` does, and gets it; :meth:`key` does not, and the mesh is
            then ingested only where no upstream artefact names its hash.
        """
        resolved = resolve(inputs.case)
        if resolved.charge is None and resolved.eps_r is None:
            raise UnsupportedCaseSection(
                f"case {resolved.name!r} supplies neither inputs.charge nor inputs.eps_r, so "
                "stage 7 has nothing to read; the producer pipeline that would build them is v0.9 "
                "(SPECIFICATION.md section 3, FR-12 to FR-15)"
            )
        mesh = inputs.upstream.get("mesh")
        ingested: IngestedMesh | None = None
        if ingest_mesh or mesh is None:
            ingested = deployed_mesh(resolved, mesh)
        if mesh is None:
            assert ingested is not None  # ingested above precisely for this
            mesh = MeshStage().artefact(ingested)
        return resolved, ingested, mesh

    def _write(self, fields: ResolvedFields) -> dict[str, Path]:
        """Write each field's grid in the native format and return the payload map.

        Written in ``.npz`` from the *loaded* grid, so the archived copy is in
        canonical SI units and needs no header to be read back — which is what
        makes it an archive rather than a second copy of the input.
        """
        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix="fields-", dir=root))
        directory.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Path] = {}
        for name, field in (("charge", fields.charge), ("eps_r", fields.eps_r)):
            if field is not None:
                payload[name] = write_grid(field.grid, directory / f"{name}.npz", format="npz")
        return payload
