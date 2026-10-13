"""The ``nanopnp/golden/v0.5`` archive: a COMSOL export turned into evidence (VAL-03)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nanopnp.charge.stage import charge_grid_key, derived_parameters, read_fields
from nanopnp.core.hashing import Canonicalisable, canonical, content_hash, decode_floats
from nanopnp.core.stages import create
from nanopnp.density.grid import (
    COMSOL_DATA_HEADER,
    COMSOL_GRID_HEADER,
    COMSOL_LENGTH_SCALE_NM,
    RadialGrid,
    read_grid,
)
from nanopnp.io.artefact import Artefact, StageInputs
from nanopnp.io.case import CaseValidationError, render_problems
from nanopnp.pipeline.run import offered
from nanopnp.validation.probe import ProbeDocument, ProbePatch, load_probe

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.io.resolved import ResolvedCase

__all__ = [
    "ARCHIVE_MANIFEST_NAME",
    "ARCHIVE_NAME",
    "CASE_IDENTITY_SCHEMA",
    "DISCRETISATION_KEYS",
    "GOLDEN_SCHEMA",
    "KERNEL_DISCRETISATION_KEYS",
    "MANIFEST_NAME",
    "MODEL_OPTION_DISCRETISATION_KEYS",
    "PROBE_FIELDS",
    "PROTONATION_VERDICT_KEYS",
    "Golden",
    "GoldenError",
    "GoldenManifest",
    "GoldenQuantities",
    "case_identity",
    "export_golden",
    "field_unit",
    "ingest_golden",
    "load_golden",
    "loads_manifest",
    "table_name",
    "write_comsol_table",
]

GOLDEN_SCHEMA = "nanopnp/golden/v0.5"

MANIFEST_NAME = "manifest.yaml"

ARCHIVE_NAME = "golden.npz"

ARCHIVE_MANIFEST_NAME = "golden.manifest.json"

Refinement = Literal["published", "refined_1"]

GoldenSource = Literal["comsol", "self"]

SignReference = Literal["cis", "trans"]

POTENTIAL_UNIT = "V"
CONCENTRATION_UNIT = "mol/m^3"
VELOCITY_UNIT = "m/s"
PRESSURE_UNIT = "Pa"

PROBE_FIELDS: tuple[str, ...] = (
    "potential",
    "concentration",
    "velocity_r",
    "velocity_z",
    "pressure",
)

CONCENTRATION_PREFIX = "c_"

CASE_IDENTITY_SCHEMA = "nanopnp/golden/case/v0.5"

DISCRETISATION_KEYS: frozenset[str] = frozenset(
    {"stabilisation", "continuation", "newton", "linear_solver"}
)

MODEL_OPTION_DISCRETISATION_KEYS: frozenset[str] = frozenset(
    {"order", "velocity_order", "pressure_order", "stabilisation"}
)

KERNEL_DISCRETISATION_KEYS: frozenset[str] = frozenset({"grid_spacing_nm"})

PROTONATION_VERDICT_KEYS: frozenset[str] = frozenset({"gates"})

AXIS_TOL_NM = 1e-6


class GoldenError(ValueError): ...


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def field_unit(field: str) -> str:
    if field == "potential":
        return POTENTIAL_UNIT
    if field == "pressure":
        return PRESSURE_UNIT
    if field in ("velocity_r", "velocity_z"):
        return VELOCITY_UNIT
    if field.startswith(CONCENTRATION_PREFIX) and len(field) > len(CONCENTRATION_PREFIX):
        return CONCENTRATION_UNIT
    raise GoldenError(
        f"{field!r} is not a field the probe comparison knows. It reads 'potential', 'pressure', "
        "'velocity_r', 'velocity_z' and one 'c_<species>' per species of the case"
    )


def case_identity(resolved: ResolvedCase, *, recorded: Mapping[str, Artefact] | None = None) -> str:
    record: dict[str, object] = {
        key: value
        for key, value in resolved.solve_provenance.items()
        if key not in DISCRETISATION_KEYS
    }
    supplied = record.get("fields")
    if isinstance(supplied, Mapping) and any(supplied.values()):
        contents = read_fields(resolved).parameters()
        record["fields"] = {name: contents.get(name, given) for name, given in supplied.items()}
    options = record.get("model_options")
    if isinstance(options, Mapping):
        record["model_options"] = {
            key: value
            for key, value in sorted(options.items())
            if key not in MODEL_OPTION_DISCRETISATION_KEYS
        }
    record.update(_stage7_recipe(resolved, recorded))
    if resolved.exclusion_offset_nm > 0.0:
        record["exclusion_shell"] = {"offset_nm": resolved.exclusion_offset_nm}
    return content_hash(CASE_IDENTITY_SCHEMA, record)


def _stage7_recipe(
    resolved: ResolvedCase, recorded: Mapping[str, Artefact] | None
) -> dict[str, Canonicalisable]:
    if not (resolved.deposits_charge or resolved.derives_eps_r):
        return {}
    structure = (
        _upstream(resolved, recorded, "structure", {}) if resolved.structure is not None else None
    )
    upstream = {} if structure is None else {"structure": structure}
    described = None if structure is None else dict(structure.parameters)
    recipe: dict[str, Canonicalisable] = {}
    if resolved.deposits_charge:
        protonation = _upstream(resolved, recorded, "protonation", upstream)
        kernel = charge_grid_key(resolved, protonation).parameters
        recipe["deposited_charge"] = {
            "structure": described,
            "protonation": {
                key: value
                for key, value in sorted(protonation.parameters.items())
                if key not in PROTONATION_VERDICT_KEYS
            },
            # The PQR's digest; the structure is represented by its key's parameters.
            "inputs": {
                key: value
                for key, value in sorted(protonation.inputs.items())
                if key != "structure"
            },
            "kernel": {
                key: value
                for key, value in sorted(kernel.items())
                if key not in KERNEL_DISCRETISATION_KEYS
            },
        }
    if resolved.derives_eps_r:
        recipe["derived_eps_r"] = {
            "derivation": derived_parameters(resolved),
            "structure": described,
        }
    return recipe


def _upstream(
    resolved: ResolvedCase,
    recorded: Mapping[str, Artefact] | None,
    name: str,
    upstream: Mapping[str, Artefact],
) -> Artefact:
    if recorded is None:
        return create(name).key(StageInputs(resolved=resolved, upstream=offered(name, upstream)))
    found = recorded.get(name)
    if found is None:
        raise KeyError(
            f"case {resolved.name!r}: the recorded artefacts hold no {name!r} artefact, which its "
            "identity is read from; reopen the run with the store it was made against"
        )
    return found


def table_name(field: str, patch: str) -> str:
    return f"{field}__{patch}.txt"


class FieldDeclaration(_Strict):
    expression: str
    unit: str


class GoldenQuantities(_Strict):
    bias_V: float
    current_A: float
    currents_A: dict[str, float] | None = None
    transport_number: float | None = None
    conductance_S: float | None = None
    eof_m3_s: float | None = None

    def summary(self) -> dict[str, object]:
        return {
            "bias_V": self.bias_V,
            "current_A": self.current_A,
            "currents_A": None if self.currents_A is None else dict(self.currents_A),
            "transport_number": self.transport_number,
            "conductance_S": self.conductance_S,
            "eof_m3_s": self.eof_m3_s,
        }


class GoldenManifest(_Strict):
    schema_id: str = Field(alias="schema")
    case: str
    case_hash: str
    probe: str
    probe_hash: str
    refinement: Refinement
    source: GoldenSource = "comsol"
    comsol_version: str
    model_file: str
    export_date: str
    fields: dict[str, FieldDeclaration]
    current_boundary: str
    current_sign_reference: SignReference
    quantities: GoldenQuantities

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _declared_and_not_blank(self) -> GoldenManifest:
        why = {
            "case_hash": "the WP7 content hash of the frozen case this golden answers; without "
            "it a golden compared against a different case is undetectable",
            "probe_hash": "the content hash of the probe document the export was interpolated "
            "onto; without it an edited probe grid silently moves the sample points",
            "comsol_version": "the version that produced the export (section 7.4 archives the "
            "generating model)",
            "model_file": "the .mph archived beside this golden",
            "export_date": "when the export was taken",
            "current_boundary": "the boundary tds.ntflux_i was evaluated on. It is NOT IN REPORT "
            "(.knowledge/09 section F), so only the author can supply it",
        }
        missing = [name for name in why if not str(getattr(self, name)).strip()]
        if missing:
            listed = "; ".join(f"{name}: {why[name]}" for name in missing)
            raise ValueError(
                f"golden manifest for case {self.case!r} leaves {len(missing)} required "
                f"declaration(s) blank — {listed}"
            )
        if not self.fields:
            raise ValueError(
                f"golden manifest for case {self.case!r} declares no fields, so it archives "
                "nothing VAL-01 can compare"
            )
        if "potential" not in self.fields:
            raise ValueError(
                f"golden manifest for case {self.case!r} declares no 'potential' field. The "
                "potential is solved over the whole of Omega and is the one field every "
                "configuration of the model carries, so a golden without it cannot discharge "
                "VAL-01 at all"
            )
        for name, declaration in sorted(self.fields.items()):
            try:
                expected = field_unit(name)
            except GoldenError as error:
                raise ValueError(str(error)) from None
            if not declaration.expression.strip():
                raise ValueError(
                    f"field {name!r} declares no COMSOL expression; the expression is the only "
                    "record of what was exported that survives the loss of licence access"
                )
            if declaration.unit != expected:
                raise ValueError(
                    f"field {name!r} declares unit {declaration.unit!r} and this build reads "
                    f"{expected!r}. The unit is refused rather than converted: a mol/L export is "
                    "a factor 1000, and scaled silently it reads as a 99.9 % discrepancy — a "
                    "physics failure that is a units failure. Re-export in SI, or correct the "
                    "declaration if the export was already SI"
                )
        return self

    def summary(self) -> dict[str, object]:
        return {
            "schema": self.schema_id,
            "case": self.case,
            "case_hash": self.case_hash,
            "probe": self.probe,
            "probe_hash": self.probe_hash,
            "refinement": self.refinement,
            "source": self.source,
            "comsol_version": self.comsol_version,
            "model_file": self.model_file,
            "export_date": self.export_date,
            "fields": {
                name: {"expression": entry.expression, "unit": entry.unit}
                for name, entry in sorted(self.fields.items())
            },
            "current_boundary": self.current_boundary,
            "current_sign_reference": self.current_sign_reference,
            "quantities": self.quantities.summary(),
        }


def loads_manifest(text: str, *, source: str = "<string>") -> GoldenManifest:
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise CaseValidationError(f"{source} is not valid YAML: {error}") from None
    if not isinstance(parsed, dict):
        found = type(parsed).__name__
        raise CaseValidationError(
            f"{source} holds a {found} at the top level, not a golden manifest"
        )
    declared = parsed.get("schema")
    if declared != GOLDEN_SCHEMA:
        raise CaseValidationError(
            f"{source} declares schema {declared!r}; this build reads {GOLDEN_SCHEMA!r}"
        )
    try:
        return GoldenManifest.model_validate(parsed)
    except ValidationError as error:
        raise CaseValidationError(render_problems(source, error), error) from None


@dataclass(frozen=True)
class Golden:
    manifest: GoldenManifest
    values: Mapping[str, np.ndarray]
    quantities: GoldenQuantities
    current_sign_flipped: bool
    hash: str

    @property
    def source(self) -> GoldenSource:
        return self.manifest.source

    def defined(self, field: str) -> np.ndarray:
        import numpy as np

        array = self.values.get(field)
        if array is None:
            listed = ", ".join(repr(name) for name in sorted(self.values)) or "nothing"
            raise GoldenError(
                f"golden for case {self.manifest.case!r} carries no field {field!r}; it carries "
                f"{listed}"
            )
        return ~np.isnan(array)

    def unavailable(self, expected: Sequence[str]) -> tuple[str, ...]:
        return tuple(sorted(set(expected) - set(self.values)))

    def check_case(self, case_hash: str) -> None:
        if self.manifest.case_hash != case_hash:
            raise GoldenError(
                f"golden for case {self.manifest.case!r} declares case_hash "
                f"{self.manifest.case_hash} and this run's case hashes to {case_hash}. The "
                "golden answers a different case; nothing downstream would notice"
            )

    def check_probe(self, document: ProbeDocument) -> None:
        if self.manifest.probe_hash != document.hash:
            raise GoldenError(
                f"golden for case {self.manifest.case!r} was exported onto probe grid "
                f"{self.manifest.probe!r} ({self.manifest.probe_hash}) and this comparison is "
                f"taken on {document.name!r} ({document.hash}). The two name different sample "
                "points, so every value would be compared at a coordinate it was not taken at"
            )

    def summary(self) -> dict[str, object]:
        return {
            "hash": self.hash,
            "golden_source": self.source,
            "manifest": self.manifest.summary(),
            "current_sign_flipped": self.current_sign_flipped,
            "quantities_section_6_7": self.quantities.summary(),
            "fields": sorted(self.values),
        }


def write_comsol_table(grid: RadialGrid, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [COMSOL_GRID_HEADER]
    for axis in (grid.r_nm, grid.z_nm):
        lines.append(" ".join(f"{value / COMSOL_LENGTH_SCALE_NM:.17g}" for value in axis))
    lines.append(COMSOL_DATA_HEADER)
    # One row per z sample, one value per r sample: the [i_z, i_r] order the
    # container already holds and the reader already expects.
    lines.extend(" ".join(f"{value:.17g}" for value in row) for row in grid.values)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def ingest_golden(
    directory: str | Path,
    *,
    probe: ProbeDocument | str | Path,
    destination: str | Path | None = None,
) -> Path:
    import numpy as np

    source = Path(directory)
    manifest_path = source / MANIFEST_NAME
    if not manifest_path.is_file():
        raise GoldenError(
            f"{source} carries no {MANIFEST_NAME}. An export without its declaration is a pile of "
            "numbers: section 7.4 archives the generating model alongside, and the manifest is "
            "what names it"
        )
    manifest = loads_manifest(manifest_path.read_text(encoding="utf-8"), source=str(manifest_path))
    document = probe if isinstance(probe, ProbeDocument) else load_probe(probe)
    _check_probe(manifest, document, manifest_path)

    values: dict[str, np.ndarray] = {}
    for field in sorted(manifest.fields):
        blocks = [
            _read_patch(source / table_name(field, patch.name), patch, field)
            for patch in document.patches
        ]
        values[field] = np.concatenate(blocks)
    return _write_archive(manifest, values, Path(destination) if destination else source)


def export_golden(
    values: Mapping[str, np.ndarray],
    manifest: GoldenManifest,
    destination: str | Path,
    *,
    tables: ProbeDocument | None = None,
) -> Path:
    import numpy as np

    if manifest.source != "self":
        raise GoldenError(
            f"export_golden writes self-goldens and this manifest declares source "
            f"{manifest.source!r}. A COMSOL golden comes from ingest_golden against delivered "
            "tables, so that the unit, sign and hash declarations are checked against what was "
            "actually exported"
        )
    target = Path(destination)
    if tables is not None:
        _check_probe(manifest, tables, target / ARCHIVE_MANIFEST_NAME)
        for field, array in sorted(values.items()):
            length = int(np.asarray(array).size)
            if length != tables.count:
                raise GoldenError(
                    f"field {field!r} carries {length} values and probe grid {tables.name!r} has "
                    f"{tables.count} points. The arrays are written patch by patch in the "
                    "document's flattening order, so a length that is not the document's would "
                    "split the blocks at the wrong place"
                )
        offset = 0
        for patch in tables.patches:
            block = slice(offset, offset + patch.count)
            offset += patch.count
            r_axis, z_axis = patch.axes_nm()
            for field, array in sorted(values.items()):
                grid = RadialGrid.from_axes(
                    r_axis, z_axis, np.asarray(array)[block].reshape(patch.n_z, patch.n_r)
                )
                write_comsol_table(grid, target / table_name(field, patch.name))
    return _write_archive(manifest, values, target)


def load_golden(path: str | Path) -> Golden:
    import numpy as np

    archive, manifest_path = _archive_paths(Path(path))
    manifest, recorded = _read_archive_manifest(manifest_path)
    with np.load(archive, allow_pickle=False) as loaded:
        values = {name: np.asarray(loaded[name], dtype=np.float64) for name in loaded.files}
    if sorted(values) != sorted(manifest.fields):
        raise GoldenError(
            f"{archive} holds fields {sorted(values)} and {manifest_path.name} declares "
            f"{sorted(manifest.fields)}. The two files are written together by ingest_golden, so "
            "a disagreement means one of them was replaced on its own"
        )
    digest = _golden_hash(manifest, values)
    if recorded is None:
        raise GoldenError(
            f"{manifest_path.name} records no golden_hash. ingest_golden always writes one, so a "
            "manifest without it was edited by hand, and an archive it vouches for cannot be "
            "checked against it"
        )
    if recorded != digest:
        raise GoldenError(
            f"{archive} and {manifest_path.name} hash to {digest} and the manifest records "
            f"{recorded}. The two are written together by ingest_golden over the same bytes, so "
            "a disagreement means the arrays or the declaration changed after the archive was "
            "made — and every number compared against it would be attributed to the provenance "
            "the manifest still states"
        )
    flipped = manifest.current_sign_reference == "trans"
    return Golden(
        manifest=manifest,
        values=values,
        quantities=_referenced_to_cis(manifest.quantities) if flipped else manifest.quantities,
        current_sign_flipped=flipped,
        hash=digest,
    )


def _referenced_to_cis(quantities: GoldenQuantities) -> GoldenQuantities:
    return GoldenQuantities(
        bias_V=quantities.bias_V,
        current_A=-quantities.current_A,
        currents_A=(
            None
            if quantities.currents_A is None
            else {name: -value for name, value in quantities.currents_A.items()}
        ),
        transport_number=quantities.transport_number,
        conductance_S=(None if quantities.conductance_S is None else -quantities.conductance_S),
        eof_m3_s=None if quantities.eof_m3_s is None else -quantities.eof_m3_s,
    )


def _check_probe(manifest: GoldenManifest, document: ProbeDocument, source: Path) -> None:
    if manifest.probe_hash != document.hash:
        raise GoldenError(
            f"{source} declares probe_hash {manifest.probe_hash} for probe {manifest.probe!r}, "
            f"and probe grid {document.name!r} hashes to {document.hash}. The export was "
            "interpolated onto a different set of points; comparing against it would put every "
            "sample in the wrong place while every array kept its shape"
        )


def _read_patch(path: Path, patch: ProbePatch, field: str) -> np.ndarray:
    import numpy as np

    if not path.is_file():
        raise GoldenError(
            f"field {field!r} declares an export and {path} is not there. The contract is one "
            f"{COMSOL_GRID_HEADER} table per field per patch, named "
            f"{table_name(field, patch.name)!r}"
        )
    grid = read_grid(path, format="comsolgrid")
    expected = (patch.n_z, patch.n_r)
    if grid.values.shape != expected:
        raise GoldenError(
            f"{path} holds a {grid.values.shape} table and patch {patch.name!r} is {expected} "
            "(n_z rows of n_r values). A %Data block is one row per z sample, so a transposed "
            "export lands here — which is why no patch is square"
        )
    r_axis, z_axis = patch.axes_nm()
    for name, found, wanted in (("r", grid.r_nm, r_axis), ("z", grid.z_nm, z_axis)):
        worst = float(np.max(np.abs(found - wanted)))
        if not worst <= AXIS_TOL_NM:
            raise GoldenError(
                f"{path}: the {name} axis differs from patch {patch.name!r}'s by up to "
                f"{worst:.6g} nm, against a tolerance of {AXIS_TOL_NM:g} nm. The export was taken "
                "on a grid this probe document does not name, so every value is at a coordinate "
                "the comparison would attribute to another"
            )
    return np.asarray(grid.values, dtype=np.float64).ravel()


def _golden_hash(manifest: GoldenManifest, values: Mapping[str, np.ndarray]) -> str:
    return content_hash(
        GOLDEN_SCHEMA,
        {"manifest": manifest.summary(), "values": {name: values[name] for name in sorted(values)}},
    )


def _write_archive(
    manifest: GoldenManifest, values: Mapping[str, np.ndarray], destination: Path
) -> Path:
    import numpy as np

    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / ARCHIVE_NAME
    arrays = {name: np.asarray(values[name], dtype=np.float64) for name in sorted(values)}
    np.savez_compressed(archive, **arrays)  # type: ignore[arg-type]
    record = {"golden_hash": _golden_hash(manifest, values), **manifest.summary()}
    (destination / ARCHIVE_MANIFEST_NAME).write_bytes(canonical(record))
    return archive


def _archive_paths(path: Path) -> tuple[Path, Path]:
    archive = path / ARCHIVE_NAME if path.is_dir() else path
    manifest = archive.parent / ARCHIVE_MANIFEST_NAME
    for name, wanted in (("archive", archive), ("manifest", manifest)):
        if not wanted.is_file():
            raise GoldenError(
                f"no golden {name} at {wanted}. A golden is the {ARCHIVE_NAME!r} and the "
                f"{ARCHIVE_MANIFEST_NAME!r} written together by ingest_golden; one without the "
                "other cannot state what it holds"
            )
    return archive, manifest


def _read_archive_manifest(path: Path) -> tuple[GoldenManifest, str | None]:
    decoded = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(decoded, dict):
        raise GoldenError(f"{path} does not hold a golden manifest object")
    recorded = decoded.get("golden_hash")
    record = {key: value for key, value in decoded.items() if key != "golden_hash"}
    try:
        return GoldenManifest.model_validate(record), (
            str(recorded) if isinstance(recorded, str) else None
        )
    except ValidationError as error:
        raise CaseValidationError(render_problems(str(path), error), error) from None
