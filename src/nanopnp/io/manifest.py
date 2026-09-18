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
from nanopnp.io.defaults import ContributedDeviation, Deviation, deviations

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
    warm_start: Mapping[str, Canonicalisable] | None = None,
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
    warm_start
        The FR-24 record of where Newton started: whether a converged neighbour
        supplied the initial state or the run climbed the ladder cold, which
        artefact it came from, and which operator keys the two runs differed in
        (the section 5.3.2 warm-start NOTE). Every solve records one -- a run
        outside a sweep records ``cold`` with its reason -- so ``None`` here
        means *no solve ran at all*, which is what the group then says.
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
    """Return the Stabilisation group: the mode that produced the number (section 6.4).

    Both the requested mode and the mode read back off the converged model are
    recorded. The reference COMSOL model ran with streamline and crosswind
    stabilisation on and ours does not, so a number whose mode is unrecorded is
    not comparable to it (section 6.4, section 7.4); a number whose recorded mode
    disagrees with the requested one is worse, and this group is where that shows.

    The mode name is not the whole operator, so its tuning constants and their
    provenance travel with it: ``reference`` at ``C_cw = 1`` and at ``C_cw = 0.35``
    are different discretisations under one name. And the two numbers section 7.4
    subtracts are here rather than in the solver group, because they are readings
    *of* the stabilisation: what it contributed to the current (NUM-11, NUM-13),
    and the cell Peclet number that says whether the mesh needed it (NUM-12).

    Parameters
    ----------
    document
        The case, for the requested mode.
    solved
        The mode read back off the converged model, ``LadderResult.stabilisation``.
    parameters, provenance
        The mode's own tuning constants and their sources.
    currents_A
        ``2 pi F z_i S_I S_i(psi)`` per species: what the stabilisation itself
        contributed to the reported current. ``None`` when no solution was
        extracted, which is a different fact from a contribution of zero -- and
        zero is exactly what ``none`` contributes, so the two must not collapse.
    peclet
        The NUM-12 measurement on the converged top rung, likewise ``None`` rather
        than zero when nothing was measured.
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
    """Return the Deviations group's payload for an already-computed diff.

    Shared by :func:`deviations_group` and :meth:`Manifest.groups`, which hold
    the same fact two different ways: one has the case document and diffs it
    itself, the other already carries the diff on ``self.deviations``. Without
    this the two would render the same group by two independent literal dicts,
    free to drift the moment one is edited and the other is not.

    ``count`` is the total. A reader asking whether a run departed from the
    validated model must not have to know that departures arrive by two routes.
    """
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
    """Return the Deviations group: every departure from the validated default.

    The enumeration of switches lives in :mod:`nanopnp.io.defaults`, which is the
    manifest's authority on what the validated default *is* (PHY-22, PHY-23).

    Parameters
    ----------
    document
        The case, diffed against the validated default.
    contributed
        Departures a *stage* found in its inputs rather than in the case — a
        smoothed dielectric field, an ion-exclusion material on the supplied
        mesh. No switch selects either, so nothing in the diff can see them.
    """
    return _deviations_payload(deviations(document), contributed)


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
    contributed_deviations
        Departures the stages found in their inputs; see :func:`deviations_group`.
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
    stabilisation_parameters: Mapping[str, Canonicalisable] | None = None,
    stabilisation_provenance: Mapping[str, Canonicalisable] | None = None,
    stabilisation_currents_A: Mapping[str, Canonicalisable] | None = None,
    peclet: Mapping[str, Canonicalisable] | None = None,
    warm_start: Mapping[str, Canonicalisable] | None = None,
    wall_distance: Mapping[str, Canonicalisable] | None = None,
    contributed_deviations: tuple[ContributedDeviation, ...] = (),
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
        ``nanopnp.mesh.ingest.IngestedMesh.summary()``: the counts and name
        tables, the mesh's content hash, the VER-10 quality statistics, the
        source file and its digest, and the vocabulary mapping that was applied
        to it. That last one is why the whole group comes from stage 6 rather
        than from the NGSolve mesh: which of the file's groups became ``wall``
        is not recoverable from the solved mesh, and two runs that differ only
        in it are two different runs (section 5.3.3). Size-field settings join
        it when the mesher lands in v0.9.
    charge
        The Charge group: ``nanopnp.charge.stage.ResolvedFields.summary()`` — each
        supplied field's header, grid descriptor and digest, and for the charge
        the decomposed PHY-19 report. ``None`` when the run carried no field,
        which is a different fact from a field that carried no charge.
    electrolyte
        The resolved electrolyte.
    clamp_activations
        PHY-13 clamp activations counted over a sampled solution.
    ladder
        ``LadderResult.summary()``.
    stabilisation
        The mode read back off the converged model, ``LadderResult.stabilisation``.
    stabilisation_parameters, stabilisation_provenance
        The mode's tuning constants and their sources; see
        :func:`stabilisation_group`.
    stabilisation_currents_A
        Each species' stabilisation contribution to the current, from
        ``QuantitiesOfInterest.stabilisation_currents_A``.
    peclet
        The NUM-12 measurement on the converged top rung, from
        ``LadderResult.peclet``.
    warm_start
        The FR-24 warm-start record; see :func:`solver_group`.
    wall_distance
        The NUM-34 measurement of the discrete distance field this run read:
        its minimum over the fluid, where that minimum occurred, and the
        fraction of samples below zero. It joins the *mesh* group rather than
        the solver's because it is a statement about the resolution of the mesh
        at the wall, and NUM-34 requires it recorded whether or not it passed.
        ``None`` when no wall correction was active, which is a different fact
        from a field that was measured and found admissible.
    contributed_deviations
        Departures a stage found in its inputs; see :func:`deviations_group`.
    """
    return Manifest(
        case_text=case_text,
        case_hash=case_hash,
        inputs=input_group(case_hash=case_hash, files=input_files, upstream=upstream),
        environment=environment(),
        geometry_and_mesh=(
            {
                **dict(mesh),
                **({} if wall_distance is None else {"wall_distance": dict(wall_distance)}),
            }
            if mesh is not None
            else not_run("no mesh was built or supplied to this run")
        ),
        charge=(
            dict(charge)
            if charge is not None
            else not_run(
                "this run supplied neither inputs.charge nor inputs.eps_r, so stage 7 did not "
                "run; the pipeline that would produce them (FR-12 to FR-15) lands in v0.9"
            )
        ),
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


def read(path: Path) -> dict[str, Canonicalisable]:
    """Return a written manifest, parsed.

    Provided so that a test, a sweep collector or a reader of an archived run does
    not have to know that the file is JSON.
    """
    parsed: dict[str, Canonicalisable] = json.loads(path.read_text(encoding="utf-8"))
    return parsed
