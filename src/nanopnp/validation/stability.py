"""The number-stability golden: one walk's numbers against the meshes they were recorded on."""

from __future__ import annotations

import importlib
import json
import math
import platform
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA = "nanopnp/golden/stability/v0.5"

SAME_MESH_TOLERANCE = 1e-8

SAFETY_FACTOR = 10.0

CEILING = 1e-3

REFERENCE_ENVIRONMENT = "linux-x86_64/X86_V3"


class MeshEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    values: dict[str, str]
    seen_on: list[str] = Field(default_factory=list)

    def floats(self) -> dict[str, float]:
        return {name: float.fromhex(value) for name, value in self.values.items()}


class WalkGolden(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_mesh: str
    moved_tolerance: float | None
    meshes: dict[str, MeshEntry]


class StabilityGolden(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_: Literal["nanopnp/golden/stability/v0.5"] = Field(alias="schema")
    same_mesh_tolerance: float
    safety_factor: float
    ceiling: float
    reference_environment: str
    walks: dict[str, WalkGolden]

    @classmethod
    def read(cls, path: Path) -> StabilityGolden:
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def empty(cls) -> StabilityGolden:
        return cls.model_validate(
            {
                "schema": SCHEMA,
                "same_mesh_tolerance": SAME_MESH_TOLERANCE,
                "safety_factor": SAFETY_FACTOR,
                "ceiling": CEILING,
                "reference_environment": REFERENCE_ENVIRONMENT,
                "walks": {},
            }
        )

    def write(self, path: Path) -> None:
        document = self.model_dump(by_alias=True)
        document["walks"] = {
            walk: {**entry, "meshes": dict(sorted(entry["meshes"].items()))}
            for walk, entry in sorted(document["walks"].items())
        }
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def environment() -> str:
    # NumPy publishes these only on its private extension module; numpy.show_runtime
    # reads them from there too. Imported here, not at module scope (CLAUDE.md).
    umath = importlib.import_module("numpy._core._multiarray_umath")
    features: dict[str, bool] = umath.__cpu_features__
    enabled = [target for target in umath.__cpu_dispatch__ if features.get(target)]
    level = (enabled or list(umath.__cpu_baseline__) or ["none"])[-1]
    return f"{sys.platform}-{platform.machine()}/{level}"


def relative_drift(value: float, reference: float) -> float:
    return abs(value - reference) / abs(reference)


def spread(walk: WalkGolden) -> float:
    reference = walk.meshes[walk.reference_mesh].floats()
    return max(
        (
            relative_drift(value, reference[name])
            for entry in walk.meshes.values()
            for name, value in entry.floats().items()
        ),
        default=0.0,
    )


def moved_tolerance(walk: WalkGolden, golden: StabilityGolden) -> float | None:
    if len(walk.meshes) < 2:
        return None
    return max(golden.safety_factor * spread(walk), golden.same_mesh_tolerance)


@dataclass(frozen=True)
class Verdict:
    walk: str
    mode: Literal["same-mesh", "mesh-moved", "missing"]
    tolerance: float | None
    drifts: dict[str, float]
    failure: str | None


def entry_for(walk: str, mesh_hash: str, values: Mapping[str, float], where: str) -> str:
    record = {
        "schema": SCHEMA,
        "walk": walk,
        "mesh_hash": mesh_hash,
        "environment": where,
        "values": {name: float(value).hex() for name, value in sorted(values.items())},
    }
    return json.dumps(record, indent=2, sort_keys=True)


def compare(
    golden: StabilityGolden,
    walk: str,
    mesh_hash: str,
    values: Mapping[str, float],
    where: str,
) -> Verdict:
    printed = entry_for(walk, mesh_hash, values, where)
    record = golden.walks.get(walk)
    if record is None:
        return Verdict(
            walk,
            "missing",
            None,
            {},
            f"no number-stability golden for walk {walk!r}; after checking these values, "
            f"fold this record in with merge_number_stability.py:\n{printed}",
        )
    known = record.meshes.get(mesh_hash)
    if known is not None:
        mode: Literal["same-mesh", "mesh-moved"] = "same-mesh"
        tolerance = golden.same_mesh_tolerance
        reference = known.floats()
    elif where == golden.reference_environment:
        return Verdict(
            walk,
            "missing",
            None,
            {},
            f"{walk} on the reference environment {where}: the deployed mesh moved "
            f"({mesh_hash}, not one of the golden's {len(record.meshes)}), and here a "
            "change of mesh is a change of the code, not of the platform; investigate the "
            "mesh, then revert, or rule it and re-pin (section 8.2.7 G10)\n" + printed,
        )
    elif record.moved_tolerance is None:
        return Verdict(
            walk,
            "missing",
            None,
            {},
            f"{walk} on {where}: mesh {mesh_hash} is not in the golden, and the walk has one "
            "recorded mesh, so no measured spread to hold an unseen mesh to. After checking "
            "these values, fold this record in with merge_number_stability.py:\n" + printed,
        )
    else:
        mode = "mesh-moved"
        tolerance = record.moved_tolerance
        reference = record.meshes[record.reference_mesh].floats()
    if set(values) != set(reference):
        return Verdict(
            walk,
            mode,
            tolerance,
            {},
            f"{walk}: the walk computes {sorted(values)}, the golden holds {sorted(reference)}",
        )
    drifts = {name: relative_drift(values[name], reference[name]) for name in sorted(values)}
    misses = [
        f"{name}: {values[name]!r} against {reference[name]!r}, drift {drift:.3e}"
        for name, drift in drifts.items()
        if not abs(values[name] - reference[name]) <= tolerance * abs(reference[name])
    ]
    failure = None
    if misses:
        question = (
            "on a recorded mesh, so a change moved a number"
            if mode == "same-mesh"
            else f"on an unseen mesh {mesh_hash}, beyond the spread measured between meshes"
        )
        failure = (
            f"{walk} on {where} moved beyond {tolerance:.3g} relative {question} (section "
            "8.2.7 G10): investigate, then revert, or rule it a deliberate fix that amends "
            "its clause and re-pins the golden in the same commit\n"
            + "\n".join(misses)
            + "\n"
            + printed
        )
    return Verdict(walk, mode, tolerance, drifts, failure)


class FoldError(ValueError): ...


def fold(
    golden: StabilityGolden, record: Mapping[str, object], *, replace: bool = False
) -> StabilityGolden:
    if record.get("schema") != SCHEMA:
        raise FoldError(f"record schema {record.get('schema')!r}, not {SCHEMA!r}")
    walk = str(record["walk"])
    mesh_hash = str(record["mesh_hash"])
    where = str(record["environment"])
    values = dict(record["values"])  # type: ignore[call-overload]
    zero = sorted(
        name
        for name, value in values.items()
        if float.fromhex(value) == 0.0 or not math.isfinite(float.fromhex(value))
    )
    if zero:
        raise FoldError(f"{walk}: {zero} are zero or not finite; a golden cannot hold them")
    existing = golden.walks.get(walk)
    meshes = dict(existing.meshes) if existing else {}
    known = meshes.get(mesh_hash)
    if known is not None and not replace:
        # Another environment on a recorded mesh: it must hold that mesh's values at
        # round-off, and the values first recorded stay the ones asserted.
        recorded = known.floats()
        moved = sorted(
            name
            for name, value in values.items()
            if name not in recorded
            or not abs(float.fromhex(value) - recorded[name])
            <= golden.same_mesh_tolerance * abs(recorded[name])
        )
        if moved or set(recorded) != set(values):
            raise FoldError(
                f"{walk} mesh {mesh_hash}: {moved or 'the quantities'} differ beyond "
                f"{golden.same_mesh_tolerance:g}; pass --replace to re-pin"
            )
        values = dict(known.values)
    seen = sorted({*(known.seen_on if known else []), where})
    meshes[mesh_hash] = MeshEntry(values=values, seen_on=seen)
    if existing is None or where == golden.reference_environment:
        reference = mesh_hash
    else:
        reference = existing.reference_mesh
    if any(set(entry.values) != set(values) for entry in meshes.values()):
        raise FoldError(f"{walk}: its meshes hold different quantities")
    draft = WalkGolden(reference_mesh=reference, moved_tolerance=None, meshes=meshes)
    tolerance = moved_tolerance(draft, golden)
    if tolerance is not None and tolerance > golden.ceiling:
        raise FoldError(
            f"{walk}: mesh {mesh_hash} drifts {spread(draft):.3e} from the reference mesh, "
            f"which argues a mesh-moved tolerance of {tolerance:.3e}, above the ceiling "
            f"{golden.ceiling:g}; that is not a mesh wobble, investigate it"
        )
    walks = dict(golden.walks)
    walks[walk] = draft.model_copy(update={"moved_tolerance": tolerance})
    return golden.model_copy(update={"walks": walks})
