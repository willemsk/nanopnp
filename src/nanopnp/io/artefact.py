"""Content-addressed stage artefacts (SPECIFICATION.md section 5.3.2)."""

from __future__ import annotations

import base64
import html
import io
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, content_hash, file_hash, short

if TYPE_CHECKING:  # pragma: no cover - annotations only; io must not import at runtime
    from matplotlib.figure import Figure

    from nanopnp.io.case import CaseDocument
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.materials.electrolyte import Electrolyte

CASE_SCHEMA = "nanopnp/case/v0.5"


STRUCTURE_SCHEMA = "nanopnp/structure/v0.5"

DENSITY_SCHEMA = "nanopnp/density/v0.5"

REDUCED_SCHEMA = "nanopnp/reduced/v0.5"

PROFILE_ARTEFACT_SCHEMA = "nanopnp/profile/v0.5"

REGION_SCHEMA = "nanopnp/region/v0.5"

MATERIALS_SCHEMA = "nanopnp/materials/v0.5"

MESH_ARTEFACT_SCHEMA = "nanopnp/mesh/v0.5"

PROTONATION_SCHEMA = "nanopnp/protonation/v0.5"

PROTONATION_FRAME_SCHEMA = "nanopnp/protonation-frame/v0.5"

CHARGE_GRID_SCHEMA = "nanopnp/charge-grid/v0.5"

FIELDS_SCHEMA = "nanopnp/fields/v0.5"

SOLUTION_SCHEMA = "nanopnp/solution/v0.5"

QOI_SCHEMA = "nanopnp/qoi/v0.5"

REPORT_SCHEMA = "nanopnp/report/v0.5"

SWEEP_SCHEMA = "nanopnp/sweep/v0.5"


def summary_html(rows: Mapping[str, Canonicalisable], *, limit: int = 40) -> str:
    """Return a two-column HTML table of ``rows``, long values cut and the rest counted."""
    shown = list(rows.items())[:limit]
    body = "".join(
        f"<tr><td>{html.escape(str(key))}</td><td>{html.escape(str(value)[:120])}</td></tr>"
        for key, value in shown
    )
    more = f"<p>and {len(rows) - limit} more</p>" if len(rows) > limit else ""
    return f"<table>{body}</table>{more}"


def figure_html(figure: Figure) -> str:
    """Return ``figure`` as an HTML image tag holding an embedded PNG."""
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f'<img src="data:image/png;base64,{encoded}" style="max-width:100%">'


def timestamp() -> str:
    """Return the current UTC time, ISO 8601 to the second; never part of the hash."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Artefact:
    """One stage output, addressed by the hash of what produced it.

    Parameters
    ----------
    inputs
        Upstream artefact hashes and input-file digests, by name; files by content, not path.
    payload
        Heavy data on disk, by name; outside the digest.
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
        """The content hash: schema, parameters and input hashes."""
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
        """Return the digest of every payload file, recomputed from disk."""
        return {name: file_hash(path) for name, path in sorted(self.payload.items())}

    @property
    def hand_substituted(self) -> bool:
        """Whether the stored bytes disagree with the record; a hand edit or corruption."""
        if self.recorded_hash is not None and self.recorded_hash != self.hash:
            return True
        return bool(self.recorded_payload) and self.recorded_payload != self.payload_hashes()

    def _repr_mimebundle_(self, include: object = None, exclude: object = None) -> dict[str, str]:
        # Imported here: the exit-code table names MissingExtraError, and classifying an
        # exception must not load the module of the class it names.
        from nanopnp.core.stages import MissingExtraError, draw

        held = ", ".join(sorted(self.payload)) or "none"
        text = (
            f"{self.schema} {self.short_hash}: {len(self.summary)} summary entries; payload {held}"
        )
        try:
            figure = draw(self)
        except MissingExtraError:
            return {"text/plain": text}
        body = f"<h4>{html.escape(self.schema)} {self.short_hash}</h4>{summary_html(self.summary)}"
        if figure is not None:
            body += figure_html(figure)
        return {"text/plain": text, "text/html": body}

    def meta(self) -> dict[str, Canonicalisable]:
        """Return the ``meta.json`` record of this artefact."""
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
    """Stage 9: a validated case document, hashed over its validated dump."""

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
    """Stage 1: the aligned ensemble, keyed on the structure block and its files' bytes."""

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
    """Stage 2: the density map, keyed on the density geometry, the radius set and stage 1."""

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
    """Stage 3: the (r, z) reduction, keyed on n, the bin width, its two methods and stage 2."""

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
    """Stage 4: the conditioned contour, keyed on the contour block and the grid spacing."""

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
    """Stage 8: the resolved material coefficient set, keyed on its electrolyte and corrections."""

    def __init__(
        self,
        electrolyte: Electrolyte,
        *,
        concentration_M: float,
        correction_file_hash: str,
        other_correction_file_hashes: Mapping[str, str] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        others = other_correction_file_hashes or {}
        super().__init__(
            schema=MATERIALS_SCHEMA,
            parameters={
                "electrolyte": dict(electrolyte.provenance),
                "concentration_M": concentration_M,
            },
            inputs={
                "corrections": correction_file_hash,
                **{f"corrections:{name}": digest for name, digest in sorted(others.items())},
            },
            summary=summary or {},
        )


class RegionArtefact(Artefact):
    """Stage 5: the tagged region, keyed on the membrane, reservoir, constants and profile."""

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
    """Stage 6: a mesh that has passed the mesh gates, in the vocabulary.

    Parameters
    ----------
    content_hash
        A supplied mesh's canonical content hash; exactly one of this and ``region`` is given.
    region
        A generated mesh's stage-5 key.
    sizing
        A generated mesh's resolved size fields; None for a supplied one.
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


class ProtonationArtefact(Artefact):
    """Stage 7, first half: the protonation artefact, keyed on its parameters or file."""

    def __init__(
        self,
        *,
        parameters: Mapping[str, Canonicalisable],
        inputs: Mapping[str, str],
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=PROTONATION_SCHEMA,
            parameters=dict(parameters),
            inputs=dict(inputs),
            payload=dict(payload or {}),
            summary=summary or {},
        )


class ChargeGridArtefact(Artefact):
    """Stage 7's export lattice, keyed on the protonation artefact and the kernel."""

    def __init__(
        self,
        *,
        parameters: Mapping[str, Canonicalisable],
        protonation_hash: str,
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=CHARGE_GRID_SCHEMA,
            parameters=dict(parameters),
            inputs={"protonation": protonation_hash},
            payload=dict(payload or {}),
            summary=summary or {},
        )


class FieldsArtefact(Artefact):
    """Stage 7: the external fields, keyed on their grid digests and the mesh."""

    def __init__(
        self,
        *,
        fields: Mapping[str, Canonicalisable],
        gates: Mapping[str, Canonicalisable],
        mesh_hash: str,
        upstream: Mapping[str, str] | None = None,
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        super().__init__(
            schema=FIELDS_SCHEMA,
            parameters={
                "fields": dict(sorted(fields.items())),
                "gates": dict(sorted(gates.items())),
            },
            inputs={"mesh": mesh_hash, **dict(upstream or {})},
            payload=dict(payload or {}),
            summary=summary or {},
        )


class SolutionArtefact(Artefact):
    """Stage 10: the converged field set and the record of reaching it."""

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
    """Stage 11: the scalars extracted from one converged solution."""

    def __init__(
        self,
        *,
        case_hash: str,
        solution_hash: str,
        outputs: tuple[str, ...],
        indicator_band_nm: tuple[float, float] | None,
        check_routes: bool,
        extension_shell_nm: tuple[float, float] | None = None,
        payload: Mapping[str, Path] | None = None,
        summary: Mapping[str, Canonicalisable] | None = None,
    ) -> None:
        parameters: dict[str, Canonicalisable] = {"outputs": list(outputs)}
        # Absent for a model without transport (no indicator); every other model's key is unchanged.
        if indicator_band_nm is not None:
            parameters["indicator_band_nm"] = list(indicator_band_nm)
        parameters["check_routes"] = check_routes
        # Absent rather than null: "no force extracted" and "one, over no shell" are different runs.
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
    """Stage 12: what the run wrote, and the hashes of what it was written from."""

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
    """The collected dataset over the members of one sweep; keyed on the plan, not the members."""

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
    """What a stage is handed: the resolved case, its upstream artefacts and its options."""

    resolved: ResolvedCase
    upstream: Mapping[str, Artefact] = field(default_factory=dict)
    options: Mapping[str, Canonicalisable] = field(default_factory=dict)

    def require(self, name: str) -> Artefact:
        """Return an upstream artefact by name; KeyError if it was not supplied."""
        try:
            return self.upstream[name]
        except KeyError:
            present = ", ".join(sorted(self.upstream)) or "nothing"
            raise KeyError(
                f"this stage needs the {name!r} artefact; the inputs carry {present}"
            ) from None
