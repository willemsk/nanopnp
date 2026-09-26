"""Content-addressed stage artefacts (``SPECIFICATION.md`` section 5.3.2).

Every stage output carries a hash over a canonical serialisation of the
parameters that produced it and of the artefacts it consumed. That hash is the
cache key, and because the input hashes are inside the digest, "a
hand-substituted artefact registers as a changed input" is true by construction
rather than by a check somebody must remember to run.

Two digests would be one too many, so there is one: :attr:`Artefact.hash` is
taken over the schema, the parameters and the input hashes, and **not** over the
payload files. That is what makes it computable before the stage runs, which is
what :meth:`nanopnp.io.store.Store.get_or_compute` needs in order to be a cache
at all. The payload is covered instead by recording each file's digest beside
the artefact and recomputing it on load: a mismatch is a hand substitution, which
FR-27 permits and section 5.3.2 requires be recorded rather than aborted.

Artefacts are frozen dataclasses, not pydantic models. They carry
``GridFunction``s and arrays and are not themselves a serialisation boundary;
their ``meta.json`` is, and pydantic stays there.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, content_hash, file_hash, short

if TYPE_CHECKING:  # pragma: no cover - annotations only; io must not import at runtime
    from nanopnp.io.case import CaseDocument
    from nanopnp.materials.electrolyte import Electrolyte

CASE_SCHEMA = "nanopnp/case/v2"
"""Stage 9: the resolved case document (IF-03)."""

CASE_SCHEMA_V1 = "nanopnp/case/v1"
"""The previous case schema, still read: a v1 document loads as its v2 upgrade (IF-03)."""

STRUCTURE_SCHEMA = "nanopnp/structure/v1"
"""Stage 1: the aligned ensemble, with the Cₙ axis on z at r = 0 (FR-01 to FR-03)."""

DENSITY_SCHEMA = "nanopnp/density/v1"
"""Stage 2: the ensemble-mean union density on the canonical 3D grid (FR-04)."""

REDUCED_SCHEMA = "nanopnp/reduced/v1"
"""Stage 3: the (r, z) mean and the Cₙ and raw azimuthal variances (FR-05, FR-06)."""

PROFILE_ARTEFACT_SCHEMA = "nanopnp/profile/v1"
"""Stage 4: the conditioned, gated contour, a ``nanopnp/profile/v1`` document (FR-07, FR-08).

The same string as :data:`nanopnp.mesh.profile.PROFILE_SCHEMA`, repeated rather
than imported for the reason :data:`MESH_ARTEFACT_SCHEMA` gives: the payload *is*
a profile document, which ``inputs.profile`` reads back (WP20 D12).
"""

REGION_SCHEMA = "nanopnp/region/v1"
"""Stage 5: the declarative record of the tagged (r, z) region (FR-09, WP21 D5).

The same string as :data:`nanopnp.geometry.region.REGION_SCHEMA`, repeated for
the reason :data:`MESH_ARTEFACT_SCHEMA` gives.
"""

MATERIALS_SCHEMA = "nanopnp/materials/v1"
"""Stage 8: the resolved material coefficient set."""

MESH_ARTEFACT_SCHEMA = "nanopnp/mesh/v1"
"""Stage 6: a tagged, gated mesh in the boundary vocabulary (IF-06).

The same string as :data:`nanopnp.mesh.adapter.MESH_SCHEMA`, which is the domain
separator of the mesh content hash, and deliberately repeated rather than
imported: ``io`` imports nothing from ``mesh`` at run time (see the module
docstring), and one schema naming one thing in two places is the intent.
"""

FIELDS_SCHEMA = "nanopnp/fields/v1"
"""Stage 7: the supplied fixed-charge and dielectric fields, gated (§5.2)."""

SOLUTION_SCHEMA = "nanopnp/solution/v2"
"""Stage 10: the converged field set and its iteration history.

``v2`` because the payload contract changed: ``v1`` wrote the backend's native
``state.gfu``, ``v2`` writes the self-describing coefficient record of
:mod:`nanopnp.solve.state`. The payload is outside the content hash (see the
module docstring), so a ``v1`` entry left in a store would otherwise be a cache
*hit* whose payload the loader cannot open — which is why section 5.3.2 makes a
changed payload contract a changed schema version.
"""

QOI_SCHEMA = "nanopnp/qoi/v1"
"""Stage 11: the NUM-27 scalar quantities of one converged solution."""

REPORT_SCHEMA = "nanopnp/report/v1"
"""Stage 12: the run record — the export selection and what was written."""

SWEEP_SCHEMA = "nanopnp/sweep/v1"
"""A sweep: its specification document, its plan, and the collected dataset.

One string for the three, because they are one thing described at three moments
— what was asked for, what it enumerates, and what came back — and a sweep is
not a pipeline stage (§5.3.4). A stage keyed on three thousand upstream
artefacts has no meaningful key and no meaningful progress fraction, so the
dataset is an artefact without being the output of a registered stage.
"""


def timestamp() -> str:
    """Return the current UTC time, ISO 8601, to the second.

    Recorded beside the hash and never inside it: a timestamp in the digest would
    make every run a cache miss, which is the point of the cache inverted.
    """
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Artefact:
    """One stage output, addressed by the hash of what produced it.

    Parameters
    ----------
    schema
        The artefact schema, e.g. ``nanopnp/solution/v1``.
    parameters
        Everything about the stage's configuration that changes its output.
    inputs
        Upstream artefact hashes and input-file digests, by name. Files are
        hashed by content and never by path, so a moved file is the same input
        and a case is reproducible on another machine.
    payload
        Heavy data on disk, by name. Outside the digest; see the module
        docstring.
    summary
        Numbers a reader wants without opening the payload — iteration counts,
        wall time, QoIs. Outside the digest, because it describes the output
        rather than determining it.
    created_at, recorded_hash, recorded_payload
        Store bookkeeping, filled in on load and ``None``/empty on a fresh
        artefact.
    """

    schema: str
    parameters: Mapping[str, Canonicalisable]
    inputs: Mapping[str, str] = field(default_factory=dict)
    payload: Mapping[str, Path] = field(default_factory=dict)
    summary: Mapping[str, Canonicalisable] = field(default_factory=dict)
    created_at: str | None = None
    recorded_hash: str | None = None
    recorded_payload: Mapping[str, str] = field(default_factory=dict)

    @property
    def hash(self) -> str:
        """The content hash: schema, parameters and input hashes (section 5.3.2)."""
        return content_hash(self.schema, self.parameters, self.inputs)

    @property
    def short_hash(self) -> str:
        """The display and directory-fan-out prefix of :attr:`hash`."""
        return short(self.hash)

    @property
    def slug(self) -> str:
        """The schema as one path component."""
        return self.schema.replace("/", "-")

    def payload_hashes(self) -> dict[str, str]:
        """Return the digest of every payload file, recomputed from disk.

        Never read from ``meta.json``: the recorded value is what this is checked
        *against*, and trusting it would make hand substitution undetectable.

        Raises
        ------
        FileNotFoundError
            If a payload file named by the artefact is not on disk.
        """
        return {name: file_hash(path) for name, path in sorted(self.payload.items())}

    @property
    def hand_substituted(self) -> bool:
        """Whether this artefact's stored bytes disagree with what was recorded.

        FR-27 permits an artefact to be edited by hand, so this is a fact to be
        recorded in the manifest, not an error. A corrupted file reads the same
        way, which is the honest outcome: the manifest says the bytes are not the
        ones the run produced, and cannot say why.
        """
        if self.recorded_hash is not None and self.recorded_hash != self.hash:
            return True
        return bool(self.recorded_payload) and self.recorded_payload != self.payload_hashes()

    def meta(self) -> dict[str, Canonicalisable]:
        """Return the ``meta.json`` record of this artefact.

        ``created_at`` is beside the hash and outside it; the payload files are
        recorded with their digests so that a later load can detect an edit.
        """
        return {
            "schema": self.schema,
            "hash": self.hash,
            "parameters": dict(self.parameters),
            "inputs": dict(sorted(self.inputs.items())),
            "payload": {
                name: {"file": path.name, "sha256": file_hash(path)}
                for name, path in sorted(self.payload.items())
            },
            "summary": dict(self.summary),
            "created_at": self.created_at or timestamp(),
        }


class CaseArtefact(Artefact):
    """Stage 9: a validated case document, hashed over its validated dump.

    Hashing the dump rather than the file text is what makes FR-26 true rather
    than something FR-26 must be defended against: comments, key order, quoting
    and ``1`` against ``1.0`` all vanish in validation, and every difference that
    survives changes the run.
    """

    def __init__(
        self,
        document: CaseDocument,
        *,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=CASE_SCHEMA,
            parameters=document.model_dump(by_alias=True, mode="json"),
            summary=summary or {},
        )


class StructureArtefact(Artefact):
    """Stage 1: the aligned ensemble, keyed on the ``structure:`` block and its files' bytes.

    The parameters are the resolved ``structure:`` block with each file replaced
    by its content digest (WP18 D11), so a moved file is the same input and an
    edited one is a different key. The key never depends on the payload: the
    aligned coordinates come out of an SVD whose last bits LAPACK may vary across
    platforms, and a key over them would make the cache machine-dependent
    (section 5.3.2). The payload's own digest is recorded beside it and re-checked
    on load, which is VER-23's hand-edit rule.
    """

    def __init__(
        self,
        *,
        parameters: Mapping[str, Canonicalisable],
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=STRUCTURE_SCHEMA,
            parameters=dict(parameters),
            payload=dict(payload or {}),
            summary=summary or {},
        )


class DensityArtefact(Artefact):
    """Stage 2: the density map, keyed on ``geometry.density``, the radius set and stage 1.

    The parameters are the ``geometry.density`` block, the radius set's name and
    file digest, and the two constants that move a number, ε and the logarithm's
    floor (WP19 D11). Stage 1's hash is the one input. The payload's digest is
    recorded beside it and re-checked on load (VER-23).
    """

    def __init__(
        self,
        *,
        parameters: Mapping[str, Canonicalisable],
        inputs: Mapping[str, str],
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=DENSITY_SCHEMA,
            parameters=dict(parameters),
            inputs=dict(inputs),
            payload=dict(payload or {}),
            summary=summary or {},
        )


class ReducedArtefact(Artefact):
    """Stage 3: the (r, z) reduction, keyed on n, the bin width, its two methods and stage 2.

    The parameters are the point group's n, the bin width, and the names of the
    detrending and harmonic-truncation rules, each of which moves a variance
    (WP19 D11). Stage 2's hash is the one input.
    """

    def __init__(
        self,
        *,
        parameters: Mapping[str, Canonicalisable],
        inputs: Mapping[str, str],
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=REDUCED_SCHEMA,
            parameters=dict(parameters),
            inputs=dict(inputs),
            payload=dict(payload or {}),
            summary=summary or {},
        )


class ProfileArtefact(Artefact):
    """Stage 4: the conditioned contour, keyed on ``geometry.contour``, h, its constants and 1, 3.

    The parameters are the ``geometry.contour`` block, the grid spacing h that
    sets the morphology, the resampling and the gate's ``h_c``, every code
    constant that moves a vertex or a verdict, and the radius set the probe
    profile reads (WP20 D13). Stages 1 and 3's hashes are the inputs: stage 3's
    mean is contoured, and stage 1's ensemble gives the probe profile.
    """

    def __init__(
        self,
        *,
        parameters: Mapping[str, Canonicalisable],
        inputs: Mapping[str, str],
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=PROFILE_ARTEFACT_SCHEMA,
            parameters=dict(parameters),
            inputs=dict(inputs),
            payload=dict(payload or {}),
            summary=summary or {},
        )


class MaterialsArtefact(Artefact):
    """Stage 8: the resolved material coefficient set.

    Hashed over the electrolyte's provenance and the digest of the correction
    file it resolved through, so that editing ``data/corrections/*.yaml`` is a
    cache miss. FR-25 asks for the "version of each parameter data file" and
    :class:`~nanopnp.materials.corrections.CorrectionDocument` carries no version
    field; the content hash is the version.
    """

    def __init__(
        self,
        electrolyte: Electrolyte,
        *,
        concentration_M: float,
        correction_file_hash: str,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=MATERIALS_SCHEMA,
            parameters={
                "electrolyte": dict(electrolyte.provenance),
                "concentration_M": concentration_M,
            },
            inputs={"corrections": correction_file_hash},
            summary=summary or {},
        )


class RegionArtefact(Artefact):
    """Stage 5: the tagged region, keyed on the membrane, reservoir, constants and profile.

    The parameters are ``geometry.membrane``, ``geometry.reservoir`` and every
    code constant that moves a vertex of the region or a verdict of its gate
    (WP21 D5). The one input is the profile: stage 4's key, or the canonical
    digest of a supplied profile's validated payload, so a hand edit of a
    supplied profile is a new key (FR-27). The payload is the record, whose
    digest is recorded beside it and re-checked on load.
    """

    def __init__(
        self,
        *,
        parameters: Mapping[str, Canonicalisable],
        inputs: Mapping[str, str],
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=REGION_SCHEMA,
            parameters=dict(parameters),
            inputs=dict(inputs),
            payload=dict(payload or {}),
            summary=summary or {},
        )


class MeshArtefact(Artefact):
    """Stage 6: a mesh that has passed the section 5.2.2 gates, in the vocabulary.

    A **supplied** mesh is keyed on its **contents** — canonical vertices,
    connectivity and tag maps, as :meth:`nanopnp.mesh.adapter.MeshData.content_hash`
    takes them — and not on the bytes of the file it came from. A mesh rewritten
    by another tool with a different header, or with its entity blocks in another
    order, is then one store entry rather than two, while a mesh whose ``wall``
    group gained an edge is a different one. The source file's own digest is
    recorded in the summary, where provenance belongs and where it changes no key.

    A **generated** mesh is keyed on its **recipe**: the stage-5 key as its input,
    and the resolved size fields as the ``sizing`` parameter (WP21 D10). A content
    key would have to mesh before the store could be asked whether it holds the
    mesh, which is seconds per sweep member, and netgen is deterministic within a
    process and platform but not across them (``.knowledge/07`` section 4). The
    content hash is recorded in the summary and the manifest, and the QR-08
    reproduction check compares it (WP21 D13).

    The applied vocabulary mapping is a *parameter*, not a summary field: the
    same file read under two different ``inputs.mesh.groups`` maps is two
    different meshes as far as every downstream selection is concerned, and
    keying them alike would serve one solve's boundary conditions from the
    other's cache entry.

    Parameters
    ----------
    content_hash
        A supplied mesh's canonical content hash; its input.
    region
        A generated mesh's stage-5 key; its input. Exactly one of the two.
    sizing
        A generated mesh's resolved size fields; ``None`` for a supplied one.
    """

    def __init__(
        self,
        *,
        materials: tuple[str, ...],
        boundaries: tuple[str, ...],
        groups: Mapping[str, str],
        content_hash: str | None = None,
        region: str | None = None,
        sizing: Mapping[str, Canonicalisable] | None = None,
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        if (content_hash is None) == (region is None):
            raise ValueError(
                "a mesh artefact is keyed on exactly one of its content (a supplied mesh) and "
                "its region (a generated one)"
            )
        parameters: dict[str, Canonicalisable] = {
            "materials": list(materials),
            "boundaries": list(boundaries),
            "groups": dict(sorted(groups.items())),
        }
        if region is not None:
            parameters["sizing"] = dict(sizing or {})
        super().__init__(
            schema=MESH_ARTEFACT_SCHEMA,
            parameters=parameters,
            inputs={"mesh": content_hash} if content_hash is not None else {"region": str(region)},
            payload=dict(payload or {}),
            summary=summary or {},
        )


class FieldsArtefact(Artefact):
    """Stage 7: the external fields, keyed on their contents and on the mesh.

    Keyed on each field's grid **digest** and on the header's physical
    declarations — quantity, units, axis cutoff, declared ``Q_net`` — and not on
    the bytes of the file they arrived in, exactly as :class:`MeshArtefact` is
    keyed on the mesh's contents. The same table written as ``.npz`` and as
    OpenDX is then one store entry, while a table whose values moved is a
    different one; the source file's own digest is recorded in the summary, where
    provenance belongs and where it changes no key.

    The mesh enters as an *input* hash rather than as a parameter, because
    PHY-19's gate is evaluated on the deployed mesh (§5.2, stage 7): the same
    field on a different mesh is a different conservation result, and keying them
    alike would serve one mesh's gate from the other's cache entry.
    """

    def __init__(
        self,
        *,
        fields: Mapping[str, Canonicalisable],
        mesh_hash: str,
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=FIELDS_SCHEMA,
            parameters={"fields": dict(sorted(fields.items()))},
            inputs={"mesh": mesh_hash},
            payload=dict(payload or {}),
            summary=summary or {},
        )


class SolutionArtefact(Artefact):
    """Stage 10: the converged field set and the record of reaching it.

    The mesh enters as an input hash rather than as a parameter, so a mesh
    supplied by hand (FR-27) changes the key exactly as a regenerated one would.
    """

    def __init__(
        self,
        parameters: Mapping[str, Canonicalisable],
        *,
        inputs: Mapping[str, str],
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=SOLUTION_SCHEMA,
            parameters=dict(parameters),
            inputs=dict(inputs),
            payload=dict(payload or {}),
            summary=summary or {},
        )


class QoIArtefact(Artefact):
    """Stage 11: the NUM-27 scalars extracted from one converged solution.

    The case and the solution enter as input hashes and everything that changes
    a number enters as a parameter: which quantities were asked for, the axial
    band ``grad(psi)`` is supported on, the NUM-28 extension shell when a force
    was asked for, and whether the NUM-26 route check ran.
    The band is a parameter and not a summary field because two extractions that
    differ only in it are two different numbers, and NUM-24's whole claim is that
    they are not — a claim VER-11 tests and this key must not assume.

    No library version appears here. The environment is recorded in the manifest
    beside the artefact; putting it in the key would make the cache
    machine-dependent and every machine a miss.
    """

    def __init__(
        self,
        *,
        case_hash: str,
        solution_hash: str,
        outputs: tuple[str, ...],
        indicator_band_nm: tuple[float, float],
        check_routes: bool,
        extension_shell_nm: tuple[float, float] | None = None,
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        parameters: dict[str, Canonicalisable] = {
            "outputs": list(outputs),
            "indicator_band_nm": list(indicator_band_nm),
            "check_routes": check_routes,
        }
        # Absent rather than null when no force was asked for, matching the
        # convention the other artefacts use for an input a run did not have:
        # "no force was extracted" and "one was, over no shell" are different
        # runs, and a null would read as the second.
        if extension_shell_nm is not None:
            parameters["extension_shell_nm"] = list(extension_shell_nm)
        super().__init__(
            schema=QOI_SCHEMA,
            parameters=parameters,
            inputs={"case": case_hash, "solution": solution_hash},
            payload=dict(payload or {}),
            summary=summary or {},
        )


class ReportArtefact(Artefact):
    """Stage 12: what the run wrote, and what it wrote it from.

    The only parameter is the export selection, because that is the only thing
    about this stage that changes what lands on disk. Its three inputs are the
    hashes of everything the report describes, so a report is never served from
    the cache for a different case, a different solve or a different extraction.
    """

    def __init__(
        self,
        *,
        case_hash: str,
        qoi_hash: str,
        solution_hash: str,
        exports: tuple[str, ...],
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=REPORT_SCHEMA,
            parameters={"exports": list(exports)},
            inputs={"case": case_hash, "qoi": qoi_hash, "solution": solution_hash},
            payload=dict(payload or {}),
            summary=summary or {},
        )


class SweepArtefact(Artefact):
    """The collected dataset over the members of one sweep (FR-24, §5.3.4).

    Keyed on the plan rather than on the members: the plan fixes the base case,
    the axes, the point identities and their order, so two datasets with the
    same key describe the same set of operating points. The *results* are the
    summary, outside the digest, because they are what the artefact describes
    rather than what determines it — and because a sweep whose members are still
    running has a key before it has rows.

    A member's row carries its status and, where it failed, the §3.1 exit class.
    Its quantities are **absent** rather than defaulted on any non-``ok`` row:
    QR-06 requires that a failed member be distinguishable from a refused one
    and from one that was never dispatched, and a zero current is none of those.
    """

    def __init__(
        self,
        *,
        plan_hash: str,
        base_hash: str,
        name: str,
        points: int,
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=SWEEP_SCHEMA,
            parameters={"name": name, "points": points},
            inputs={"plan": plan_hash, "base_case": base_hash},
            payload=dict(payload or {}),
            summary=summary or {},
        )


@dataclass(frozen=True)
class StageInputs:
    """What a stage is handed: the case, its upstream artefacts, and options.

    One type for every stage is what keeps a stage independently invocable
    (FR-27): the CLI, the GUI and the sweep runner all build this and none of
    them needs to know which stage takes what.
    """

    case: CaseDocument
    upstream: Mapping[str, Artefact] = field(default_factory=dict)
    options: Mapping[str, Canonicalisable] = field(default_factory=dict)

    def require(self, name: str) -> Artefact:
        """Return an upstream artefact by name.

        Raises
        ------
        KeyError
            If the stage was invoked without it; the message names what is
            present, because "run this stage alone" is exactly when this happens.
        """
        try:
            return self.upstream[name]
        except KeyError:
            present = ", ".join(sorted(self.upstream)) or "nothing"
            raise KeyError(
                f"this stage needs the {name!r} artefact; the inputs carry {present}"
            ) from None
