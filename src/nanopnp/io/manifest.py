"""The provenance manifest of ``SPECIFICATION.md`` section 5.3.3 (FR-25, IF-08).

A result whose manifest cannot reconstruct the run is not a result. Section 5.3.3
names eight field groups, and this module assembles them from the provenance the
stages already produce — ``Electrolyte.provenance``, ``LadderResult.summary()``,
``continuation.mesh_report``, ``CoupledModel.provenance["stabilisation"]`` and the
:mod:`nanopnp.io.defaults` deviation diff — rather than inventing a second record
that could disagree with the first.

**Every group is always present.** A group no stage contributed is written as
``{"status": "not run", "reason": ...}``: absence and "did not apply" are
different facts, and a reader of a Phase-1 manifest must be able to tell that the
charge pipeline did not run from the manifest alone, without knowing which
release wrote it.

The case file is embedded verbatim as a string beside its hash. Re-emitting it as
YAML from the parsed document would let the manifest's case and the manifest's
case hash disagree, which is the one failure a provenance record must not have.

Nothing here imports ``ngsolve``: the environment group reads distribution
metadata through :mod:`importlib.metadata`, which never imports the package it
reports on. Importing NGSolve to read its version would cost ~370 ms in every
CLI, GUI and sweep-worker process for a string that is already on disk.
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field
from importlib import metadata
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, canonical, content_hash, file_hash
from nanopnp.core.paths import correction_file
from nanopnp.io.artefact import timestamp
from nanopnp.io.defaults import Deviation, deviations

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping
    from pathlib import Path

    from nanopnp.io.artefact import Artefact
    from nanopnp.io.case import CaseDocument
    from nanopnp.materials.electrolyte import Electrolyte

MANIFEST_SCHEMA = "nanopnp/manifest/v1"
"""Schema string of the manifest document (IF-08)."""

MANIFEST_FILENAME = "manifest.json"
"""Name the manifest is written under inside a run directory."""

CASE_FILENAME = "case.yaml"
"""Name the embedded case text is written beside it under."""

GROUPS: tuple[str, ...] = (
    "inputs",
    "environment",
    "geometry_and_mesh",
    "charge",
    "materials",
    "solver",
    "stabilisation",
    "deviations",
)
"""The eight field groups of section 5.3.3, in the order that table lists them."""

DISTRIBUTIONS: tuple[str, ...] = (
    # Section 2.6, by *distribution* name rather than import name -- they differ
    # for PyYAML, MDAnalysis, GridDataFormats, scikit-image and PySide6, and
    # importlib.metadata keys on the distribution.
    "nanopnp",
    "ngsolve",
    "numpy",
    "scipy",
    "PyYAML",
    "pydantic",
    "meshio",
    "h5py",
    "sympy",
    # Optional extras: absent from a solver-only install, and reported as None
    # rather than omitted so that "not installed" is distinguishable from
    # "this release did not know to look".
    "MDAnalysis",
    "GridDataFormats",
    "scikit-image",
    "shapely",
    "pdb2pqr",
    "PySide6",
    "gmsh",
)
"""Distributions whose versions the manifest records (section 2.6, FR-25)."""


def not_run(reason: str) -> dict[str, Canonicalisable]:
    """Return the record of a field group no stage in this run contributed.

    Parameters
    ----------
    reason
        Why it did not run, in the terms a reader needs: which release owns the
        stage, or which switch turned it off.
    """
    return {"status": "not run", "reason": reason}


def _version(distribution: str) -> str | None:
    """Return an installed distribution's version, or ``None`` if it is absent."""
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def environment() -> dict[str, Canonicalisable]:
    """Return the Environment group: library, interpreter and platform versions.

    Returns
    -------
    dict
        ``packages`` maps every distribution of :data:`DISTRIBUTIONS` to its
        version or to ``None``; ``python`` and ``platform`` record the
        interpreter and the machine (FR-25, section 5.3.3).
    """
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
    """Return the Inputs group: the content hash of every input.

    Parameters
    ----------
    case_hash
        Content hash of the case artefact this run was resolved from.
    files
        Input files by role, hashed by content. The path is recorded beside the
        hash but is not part of it: a moved file is not a changed input.
    upstream
        Upstream artefacts by stage name. Each is recorded with its schema, its
        hash and whether its payload was substituted by hand (section 5.3.2).
    """
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
    """Return the Materials group: correction models, file versions, clamps.

    FR-25 asks for the "version of each parameter data file" and the correction
    documents carry no version field, so the version *is* the content hash of the
    resolved ``data/corrections/<name>.yaml``.

    Parameters
    ----------
    electrolyte
        The resolved electrolyte, whose ``provenance`` names every correction in
        force and the switches applied to it.
    clamp_activations
        How many samples of the solution were outside the fits' validity range
        (PHY-13). ``None`` records that no solution was sampled, which is not the
        same fact as zero activations.
    """
    provenance = dict(electrolyte.provenance)
    name = str(provenance.get("parameter_file", "") or "")
    files: dict[str, Canonicalisable] = {}
    if name:
        try:
            path = correction_file(name)
        except FileNotFoundError:
            files[name] = None
        else:
            files[name] = file_hash(path)
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
) -> dict[str, Canonicalisable]:
    """Return the Solver group: model, element orders, continuation, settings.

    Parameters
    ----------
    document
        The case, which carries what was *asked for*.
    ladder
        ``LadderResult.summary()``, which carries what actually happened: the
        rungs taken, the seconds, the Newton iterations and the minimum damping
        any rung needed. ``None`` when no solve ran.
    """
    numerics = document.numerics
    return {
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
) -> dict[str, Canonicalisable]:
    """Return the Stabilisation group: the mode that produced the number (section 6.4).

    Both the requested mode and the mode read back off the converged model are
    recorded. The reference COMSOL model ran with streamline and crosswind
    stabilisation on and ours does not, so a number whose mode is unrecorded is
    not comparable to it (section 6.4, section 7.4); a number whose recorded mode
    disagrees with the requested one is worse, and this group is where that shows.
    """
    requested = document.numerics.stabilisation
    return {
        "requested": requested,
        "mode": solved if solved is not None else requested,
        "matches_requested": solved is None or solved == requested,
    }


def _deviations_payload(found: tuple[Deviation, ...]) -> dict[str, Canonicalisable]:
    """Return the Deviations group's payload for an already-computed diff.

    Shared by :func:`deviations_group` and :meth:`Manifest.groups`, which hold
    the same fact two different ways: one has the case document and diffs it
    itself, the other already carries the diff on ``self.deviations``. Without
    this the two would render the same group by two independent literal dicts,
    free to drift the moment one is edited and the other is not.
    """
    return {
        "count": len(found),
        "switches": [deviation.summary() for deviation in found],
    }


def deviations_group(document: CaseDocument) -> dict[str, Canonicalisable]:
    """Return the Deviations group: every switch set away from the validated default.

    The enumeration lives in :mod:`nanopnp.io.defaults`, which is the manifest's
    authority on what the validated default *is* (PHY-22, PHY-23).
    """
    return _deviations_payload(deviations(document))


@dataclass(frozen=True)
class Manifest:
    """The eight-group provenance record of one run (FR-25, IF-08, section 5.3.3).

    Parameters
    ----------
    case_text
        The case file verbatim, as it was read. Embedded rather than re-emitted
        so that it cannot disagree with ``case_hash``.
    case_hash
        Content hash of the case artefact.
    inputs, environment, geometry_and_mesh, charge, materials, solver
    stabilisation
        The section 5.3.3 field groups, each a mapping. A group no stage
        contributed carries :func:`not_run`.
    deviations
        Every switch this case set away from the validated default.
    created_at
        UTC timestamp, outside every digest.
    """

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
            "deviations": _deviations_payload(self.deviations),
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

    def write(self, directory: Path) -> Path:
        """Write ``manifest.json`` and ``case.yaml`` into a run directory.

        The case is written from the same string that is embedded in the
        manifest, so the two cannot drift apart.

        Parameters
        ----------
        directory
            Run directory; created if it does not exist.

        Returns
        -------
        Path
            The path of the written manifest.
        """
        directory.mkdir(parents=True, exist_ok=True)
        (directory / CASE_FILENAME).write_text(self.case_text, encoding="utf-8")
        path = directory / MANIFEST_FILENAME
        path.write_bytes(canonical(self.document()) + b"\n")
        return path


def build(
    document: CaseDocument,
    *,
    case_text: str,
    case_hash: str,
    input_files: Mapping[str, Path] | None = None,
    upstream: Mapping[str, Artefact] | None = None,
    mesh: Mapping[str, Canonicalisable] | None = None,
    charge: Mapping[str, Canonicalisable] | None = None,
    electrolyte: Electrolyte | None = None,
    clamp_activations: int | None = None,
    ladder: Mapping[str, Canonicalisable] | None = None,
    stabilisation: str | None = None,
) -> Manifest:
    """Assemble a manifest from whatever the run produced.

    Every argument that names a stage's output is optional, and its absence is
    recorded as :func:`not_run` with the reason rather than dropped. That is what
    lets a Phase-1 run — no structure, no charge pipeline, an externally supplied
    mesh — write a manifest with all eight groups present (FR-25).

    Parameters
    ----------
    document
        The validated case.
    case_text
        The case file verbatim.
    case_hash
        Content hash of the case artefact.
    input_files
        Input files by role, hashed by content.
    upstream
        Upstream artefacts by stage name.
    mesh
        ``continuation.mesh_report(mesh)``: elements, vertices, materials and
        boundaries. Quality statistics and size-field settings join it in WP8.
    charge
        The charge pipeline's record; ``None`` until WP9 builds it.
    electrolyte
        The resolved electrolyte.
    clamp_activations
        PHY-13 clamp activations counted over a sampled solution.
    ladder
        ``LadderResult.summary()``.
    stabilisation
        The mode read back off the converged model, ``LadderResult.stabilisation``.
    """
    return Manifest(
        case_text=case_text,
        case_hash=case_hash,
        inputs=input_group(case_hash=case_hash, files=input_files, upstream=upstream),
        environment=environment(),
        geometry_and_mesh=(
            dict(mesh) if mesh is not None else not_run("no mesh was built or supplied to this run")
        ),
        charge=(
            dict(charge)
            if charge is not None
            else not_run("the charge pipeline (stages 4 and 5, FR-08 to FR-11) lands in v0.9")
        ),
        materials=(
            materials_group(electrolyte, clamp_activations=clamp_activations)
            if electrolyte is not None
            else not_run("no electrolyte was resolved")
        ),
        solver=solver_group(document, ladder=ladder),
        stabilisation=stabilisation_group(document, solved=stabilisation),
        deviations=deviations(document),
    )


def read(path: Path) -> dict[str, Canonicalisable]:
    """Return a written manifest, parsed.

    Provided so that a test, a sweep collector or a reader of an archived run does
    not have to know that the file is JSON.
    """
    parsed: dict[str, Canonicalisable] = json.loads(path.read_text(encoding="utf-8"))
    return parsed
