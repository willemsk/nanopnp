"""Content-addressed stage artefacts (SPECIFICATION.md section 5.3.2)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, content_hash, file_hash, short

if TYPE_CHECKING:  # pragma: no cover - annotations only; io must not import at runtime
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


def timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Artefact:
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
        return content_hash(self.schema, self.parameters, self.inputs)

    @property
    def short_hash(self) -> str:
        return short(self.hash)

    @property
    def slug(self) -> str:
        return self.schema.replace("/", "-")

    def payload_hashes(self) -> dict[str, str]:
        return {name: file_hash(path) for name, path in sorted(self.payload.items())}

    @property
    def hand_substituted(self) -> bool:
        if self.recorded_hash is not None and self.recorded_hash != self.hash:
            return True
        return bool(self.recorded_payload) and self.recorded_payload != self.payload_hashes()

    def meta(self) -> dict[str, Canonicalisable]:
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
    resolved: ResolvedCase
    upstream: Mapping[str, Artefact] = field(default_factory=dict)
    options: Mapping[str, Canonicalisable] = field(default_factory=dict)

    def require(self, name: str) -> Artefact:
        try:
            return self.upstream[name]
        except KeyError:
            present = ", ".join(sorted(self.upstream)) or "nothing"
            raise KeyError(
                f"this stage needs the {name!r} artefact; the inputs carry {present}"
            ) from None
