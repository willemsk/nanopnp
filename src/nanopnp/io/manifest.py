"""The provenance manifest of SPECIFICATION.md section 5.3.3 (FR-25, IF-08)."""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field
from importlib import metadata
from typing import TYPE_CHECKING

from nanopnp.core.hashing import (
    Canonicalisable,
    canonical,
    content_hash,
    decode_floats,
    file_hash,
)
from nanopnp.core.paths import available_corrections, correction_file
from nanopnp.io.artefact import timestamp
from nanopnp.io.defaults import ContributedDeviation, Deviation, deviations
from nanopnp.io.store import atomic_write_bytes

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping
    from pathlib import Path

    from nanopnp.io.artefact import Artefact
    from nanopnp.io.case import CaseDocument
    from nanopnp.materials.electrolyte import Electrolyte

MANIFEST_SCHEMA = "nanopnp/manifest/v0.5"

MANIFEST_FILENAME = "manifest.json"

CASE_FILENAME = "case.yaml"

DEVIATIONS_GROUP = "deviations"

GROUPS: tuple[str, ...] = (
    "inputs",
    "environment",
    "geometry_and_mesh",
    "charge",
    "materials",
    "solver",
    "stabilisation",
    DEVIATIONS_GROUP,
)

DISTRIBUTIONS: tuple[str, ...] = (
    # By distribution name, not import name (they differ for PyYAML, MDAnalysis, GridDataFormats,
    # scikit-image and PySide6): importlib.metadata keys on the distribution.
    "nanopnp",
    "ngsolve",
    "numpy",
    "scipy",
    "PyYAML",
    "pydantic",
    "meshio",
    "h5py",
    "sympy",
    # Optional extras are reported as None rather than omitted, so "not installed" differs from
    # "this release did not know to look".
    "MDAnalysis",
    "GridDataFormats",
    "scikit-image",
    "shapely",
    "pdb2pqr",
    "propka",
    "PySide6",
    "gmsh",
)


class ManifestHashError(ValueError):
    """A manifest read back does not reproduce the hash it records."""


def not_run(reason: str) -> dict[str, Canonicalisable]:
    """Return the record of a field group that no stage in this run contributed."""
    return {"status": "not run", "reason": reason}


def _version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def environment() -> dict[str, Canonicalisable]:
    """Return the Environment group: distribution, interpreter and platform versions."""
    return {
        "packages": {name: _version(name) for name in DISTRIBUTIONS},
        "python": {
            "version": sys.version.split()[0],
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
    }


def input_group(
    *,
    case_hash: str,
    files: Mapping[str, Path] | None = None,
    upstream: Mapping[str, Artefact] | None = None,
) -> dict[str, Canonicalisable]:
    """Return the Inputs group: the content hash of every input, and each file's path."""
    return {
        "case": case_hash,
        "files": {
            role: {"path": str(path), "sha256": file_hash(path)}
            for role, path in sorted((files or {}).items())
        },
        "artefacts": {
            stage: {
                "schema": artefact.schema,
                "hash": artefact.hash,
                "hand_substituted": artefact.hand_substituted,
            }
            for stage, artefact in sorted((upstream or {}).items())
        },
    }


def materials_group(
    electrolyte: Electrolyte,
    *,
    clamp_activations: int | None = None,
) -> dict[str, Canonicalisable]:
    """Return the Materials group: correction models, file hashes and clamp counts.

    Parameters
    ----------
    clamp_activations
        Samples outside the fits' validity range; None if no solution was sampled.
    """
    provenance = dict(electrolyte.provenance)
    name = str(provenance.get("parameter_file", "") or "")
    # Every file the models read, as MaterialsStage keys them; a correction model may name another.
    named = {model.name for model in electrolyte.corrections.values()}
    read = sorted(({name} if name else set()) | (named & set(available_corrections())))
    files: dict[str, Canonicalisable] = {}
    for each in read:
        try:
            path = correction_file(each)
        except FileNotFoundError:
            files[each] = None
        else:
            files[each] = file_hash(path)
    provenance["parameter_file_hashes"] = files
    provenance["clamp_activations"] = (
        clamp_activations
        if clamp_activations is not None
        else not_run("no solution was sampled for clamp activations (PHY-13)")
    )
    return provenance


def solver_group(
    document: CaseDocument,
    *,
    ladder: Mapping[str, Canonicalisable] | None = None,
    warm_start: Mapping[str, Canonicalisable] | None = None,
) -> dict[str, Canonicalisable]:
    """Return the Solver group: model, element orders, continuation and settings, as run.

    Parameters
    ----------
    warm_start
        Where Newton started; None if no solve ran.
    """
    numerics = document.numerics
    return {
        "warm_start": (
            dict(warm_start)
            if warm_start is not None
            else not_run("no solve ran, so Newton had no starting point to record")
        ),
        "model": document.physics.model,
        "physics_switches": document.physics.model_dump(mode="json"),
        "elements": numerics.elements.model_dump(mode="json"),
        "continuation": numerics.continuation,
        "nonlinear": numerics.nonlinear.model_dump(mode="json"),
        "linear": numerics.linear.model_dump(mode="json"),
        "wall_distance": numerics.wall_distance.model_dump(mode="json"),
        "run": dict(ladder) if ladder is not None else not_run("no solve ran"),
    }


def stabilisation_group(
    document: CaseDocument,
    *,
    solved: str | None = None,
    parameters: Mapping[str, Canonicalisable] | None = None,
    provenance: Mapping[str, Canonicalisable] | None = None,
    currents_A: Mapping[str, Canonicalisable] | None = None,
    peclet: Mapping[str, Canonicalisable] | None = None,
) -> dict[str, Canonicalisable]:
    """Return the Stabilisation group: the requested and the read-back mode.

    Parameters
    ----------
    currents_A
        Stabilisation's contribution to the current; None when no solution was extracted, not zero.
    peclet
        Cell Peclet number on the top rung; None when unmeasured.
    """
    requested = document.numerics.stabilisation
    return {
        "requested": requested,
        "mode": solved if solved is not None else requested,
        "matches_requested": solved is None or solved == requested,
        "parameters": None if parameters is None else dict(parameters),
        "parameter_provenance": None if provenance is None else dict(provenance),
        "stabilisation_current_A": None if currents_A is None else dict(currents_A),
        "max_cell_peclet": None if peclet is None else peclet.get("maximum"),
        "peclet": None if peclet is None else dict(peclet),
    }


def _deviations_payload(
    found: tuple[Deviation, ...],
    contributed: tuple[ContributedDeviation, ...] = (),
) -> dict[str, Canonicalisable]:
    return {
        "count": len(found) + len(contributed),
        "switches": [deviation.summary() for deviation in found],
        "contributed": [deviation.summary() for deviation in contributed],
    }


def deviations_group(
    document: CaseDocument,
    *,
    contributed: tuple[ContributedDeviation, ...] = (),
) -> dict[str, Canonicalisable]:
    """Return the Deviations group: every departure from the validated default."""
    return _deviations_payload(deviations(document), contributed)


@dataclass(frozen=True)
class Manifest:
    """The eight-group provenance record of one run."""

    case_text: str
    case_hash: str
    inputs: Mapping[str, Canonicalisable]
    environment: Mapping[str, Canonicalisable]
    geometry_and_mesh: Mapping[str, Canonicalisable]
    charge: Mapping[str, Canonicalisable]
    materials: Mapping[str, Canonicalisable]
    solver: Mapping[str, Canonicalisable]
    stabilisation: Mapping[str, Canonicalisable]
    deviations: tuple[Deviation, ...] = ()
    contributed_deviations: tuple[ContributedDeviation, ...] = ()
    created_at: str = field(default_factory=timestamp)

    def groups(self) -> dict[str, Canonicalisable]:
        """Return the eight field groups, keyed as :data:`GROUPS` names them."""
        return {
            "inputs": dict(self.inputs),
            "environment": dict(self.environment),
            "geometry_and_mesh": dict(self.geometry_and_mesh),
            "charge": dict(self.charge),
            "materials": dict(self.materials),
            "solver": dict(self.solver),
            "stabilisation": dict(self.stabilisation),
            "deviations": _deviations_payload(self.deviations, self.contributed_deviations),
        }

    @property
    def hash(self) -> str:
        """Content hash over the case and the eight groups, excluding the timestamp."""
        return content_hash(
            MANIFEST_SCHEMA,
            {"case": self.case_hash, "groups": self.groups()},
        )

    def document(self) -> dict[str, Canonicalisable]:
        """Return the manifest as it is serialised."""
        return {
            "schema": MANIFEST_SCHEMA,
            "created_at": self.created_at,
            "hash": self.hash,
            "case": {"hash": self.case_hash, "text": self.case_text},
            **self.groups(),
        }

    @classmethod
    def from_document(cls, document: Mapping[str, Canonicalisable]) -> Manifest:
        """Rebuild a manifest from its serialised document.

        Raises
        ------
        ManifestHashError
            The document is not a manifest of this schema, or its groups do not hash to its hash.
        """
        parsed = decode_floats(dict(document))
        decoded: dict[str, Canonicalisable] = parsed if isinstance(parsed, dict) else {}
        if decoded.get("schema") != MANIFEST_SCHEMA:
            found = decoded.get("schema")
            raise ManifestHashError(
                f"the document declares schema {found!r}; this build reads {MANIFEST_SCHEMA!r}, "
                "and recomputes the hash only under it"
            )
        try:
            case = decoded["case"]
            block = decoded[DEVIATIONS_GROUP]
            manifest = cls(
                case_text=str(case["text"]),
                case_hash=str(case["hash"]),
                inputs=decoded["inputs"],
                environment=decoded["environment"],
                geometry_and_mesh=decoded["geometry_and_mesh"],
                charge=decoded["charge"],
                materials=decoded["materials"],
                solver=decoded["solver"],
                stabilisation=decoded["stabilisation"],
                deviations=tuple(
                    Deviation(
                        path=str(entry["path"]),
                        validated=entry["validated_default"],
                        value=entry["value"],
                    )
                    for entry in block["switches"]
                ),
                contributed_deviations=tuple(
                    ContributedDeviation(
                        source=str(entry["source"]), description=str(entry["description"])
                    )
                    for entry in block["contributed"]
                ),
                created_at=str(decoded["created_at"]),
            )
            computed = manifest.hash
        except KeyError as error:
            raise ManifestHashError(
                f"the document lacks the manifest field {error}, so its hash cannot be recomputed"
            ) from None
        except (TypeError, ValueError) as error:
            raise ManifestHashError(
                f"the document holds a manifest field of the wrong shape ({error}), so its hash "
                "cannot be recomputed"
            ) from None
        recorded = decoded.get("hash")
        if recorded != computed:
            raise ManifestHashError(
                f"the document records hash {str(recorded)[:12]} but its case and groups hash to "
                f"{computed[:12]}: it was edited after the run wrote it, and is not that "
                "run's record"
            )
        return manifest

    def write(self, directory: Path) -> Path:
        """Write the manifest and case file into a run directory; return the manifest path."""
        directory.mkdir(parents=True, exist_ok=True)
        # Atomic: job-array members sharing a case write one run directory.
        # Verbatim: the recorded case sha256 is of the source file's bytes.
        atomic_write_bytes(directory / CASE_FILENAME, self.case_text.encode("utf-8"))
        path = directory / MANIFEST_FILENAME
        atomic_write_bytes(path, canonical(self.document()) + b"\n")
        return path


def build(
    document: CaseDocument,
    *,
    case_text: str,
    case_hash: str,
    input_files: Mapping[str, Path] | None = None,
    upstream: Mapping[str, Artefact] | None = None,
    mesh: Mapping[str, Canonicalisable] | None = None,
    structure: Mapping[str, Canonicalisable] | None = None,
    density: Mapping[str, Canonicalisable] | None = None,
    reduction: Mapping[str, Canonicalisable] | None = None,
    contour: Mapping[str, Canonicalisable] | None = None,
    region: Mapping[str, Canonicalisable] | None = None,
    charge: Mapping[str, Canonicalisable] | None = None,
    protonation: Mapping[str, Canonicalisable] | None = None,
    protonation_reason: str | None = None,
    charge_reason: str | None = None,
    electrolyte: Electrolyte | None = None,
    clamp_activations: int | None = None,
    ladder: Mapping[str, Canonicalisable] | None = None,
    stabilisation: str | None = None,
    stabilisation_parameters: Mapping[str, Canonicalisable] | None = None,
    stabilisation_provenance: Mapping[str, Canonicalisable] | None = None,
    stabilisation_currents_A: Mapping[str, Canonicalisable] | None = None,
    peclet: Mapping[str, Canonicalisable] | None = None,
    warm_start: Mapping[str, Canonicalisable] | None = None,
    wall_distance: Mapping[str, Canonicalisable] | None = None,
    contributed_deviations: tuple[ContributedDeviation, ...] = (),
) -> Manifest:
    """Assemble a manifest from the run's outputs; absent stage outputs are recorded as not run.

    Parameters
    ----------
    charge
        The resolved fields' summary; None when the run carried no field.
    """
    return Manifest(
        case_text=case_text,
        case_hash=case_hash,
        inputs=input_group(case_hash=case_hash, files=input_files, upstream=upstream),
        environment=environment(),
        geometry_and_mesh=_geometry_group(
            mesh,
            wall_distance,
            structure=structure,
            density=density,
            reduction=reduction,
            contour=contour,
            region=region,
        ),
        charge=_charge_group(charge, protonation, protonation_reason, charge_reason),
        materials=(
            materials_group(electrolyte, clamp_activations=clamp_activations)
            if electrolyte is not None
            else not_run("no electrolyte was resolved")
        ),
        solver=solver_group(document, ladder=ladder, warm_start=warm_start),
        stabilisation=stabilisation_group(
            document,
            solved=stabilisation,
            parameters=stabilisation_parameters,
            provenance=stabilisation_provenance,
            currents_A=stabilisation_currents_A,
            peclet=peclet,
        ),
        deviations=deviations(document),
        contributed_deviations=contributed_deviations,
    )


def _charge_group(
    charge: Mapping[str, Canonicalisable] | None,
    protonation: Mapping[str, Canonicalisable] | None,
    reason: str | None,
    charge_reason: str | None = None,
) -> dict[str, Canonicalisable]:
    group = (
        dict(charge)
        if charge is not None
        else not_run(
            charge_reason
            or "this run supplied neither inputs.charge nor inputs.eps_r and deposited no charge"
        )
    )
    group["protonation"] = (
        dict(protonation)
        if protonation is not None
        else not_run(reason or "the protonation stage did not run")
    )
    return group


def _geometry_group(
    mesh: Mapping[str, Canonicalisable] | None,
    wall_distance: Mapping[str, Canonicalisable] | None,
    **stages: Mapping[str, Canonicalisable] | None,
) -> dict[str, Canonicalisable]:
    if mesh is None:
        group = not_run("no mesh was built or supplied to this run")
    else:
        group = {
            **dict(mesh),
            **({} if wall_distance is None else {"wall_distance": dict(wall_distance)}),
        }
    for name, record in stages.items():
        if record is not None:
            group[name] = dict(record)
    return group


def read(path: Path) -> dict[str, Canonicalisable]:
    """Return a written manifest, parsed."""
    parsed: dict[str, Canonicalisable] = json.loads(path.read_text(encoding="utf-8"))
    return parsed
