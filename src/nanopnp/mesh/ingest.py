"""Stage 6 of section 5.2: reading a supplied mesh, tagging it, gating it (IF-06, QR-12).

Phase 1 solves on a mesh it did not build (section 8.1): ``inputs.mesh`` names a
file, and everything the weak forms need from it arrives as *names*. That is the
whole reason this module exists. Boundary conditions select by regular
expression, and under the ``r``-weighted forms of section 6.2 the natural
condition is the **free** one (NUM-06), so a mesh whose pore wall is called
``Wall``, or ``pore_surface``, or nothing at all assembles cleanly, converges,
and reports a current that is wrong by whatever leaks through a no-flux boundary
that was never imposed. There is no residual for it and no solver diagnostic. The
gate below is the only place that failure can be caught.

**One route in.** Every format :mod:`nanopnp.mesh.adapter` reads lands in one
:class:`~nanopnp.mesh.adapter.MeshData` and every mesh goes through the same
mapping and the same gate, netgen's own ``.vol`` included. A second route that
skipped the gate would be the hole the gate exists to close.

**The vocabulary is fixed and carries no aliases** (section 5.3.1). Two names for
one region means two regular expressions, and the day they diverge the fluid
loses a domain silently — which is the trap
:data:`~nanopnp.mesh.primitives.ELECTROLYTE_DOMAINS` was written to document.
``pore`` is deliberately not a name: it reads as both the lumen fluid and the
dielectric body, and a mesh that uses it disambiguates through the mapping.

**What is required is derived from the resolved case, never listed here.** A
constant list is wrong in both directions: it would demand ``cis``/``trans`` of a
cylinder that has neither, and it would say nothing when a case widens
``numerics.wall_distance.sources`` to a name no group supplies. Deriving it makes
the abort message exactly true — *this run will select on this name, and no group
supplies it*.

The gate, in order (section 5.2.2, QR-12):

1. the file exists and its format is readable;
2. it reads into a :class:`~nanopnp.mesh.adapter.MeshData`;
3. every file group is claimed, and every name the run selects on is supplied;
4. every solid material has a permittivity (PHY-03);
5. ``SICN`` and ``gamma`` per element, and the sign of the Jacobian (VER-10);
6. ``min(r) >= 0`` over the vertices (CON-04);

and only then is the NGSolve mesh built. Steps 3 to 6 are the abort surface and
each names its own gate.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import file_hash
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import MeshArtefact
from nanopnp.io.case import COUPLED_MODELS, UnsupportedCaseSection, resolve
from nanopnp.io.defaults import ContributedDeviation
from nanopnp.mesh.adapter import MeshData, detect_format, read, write_msh41
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS, PERMITTIVITY_EXEMPT
from nanopnp.mesh.quality import QualityReport, check_quality, check_radii, element_quality
from nanopnp.physics.models import DEFAULT_BOUNDARIES

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Mesh
    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.case import ResolvedCase, SuppliedArtefact

logger = logging.getLogger(__name__)

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the archival MSH copy is written to."""

MATERIAL_VOCABULARY: tuple[str, ...] = (
    "analyte",
    "cis",
    "electrolyte",
    "exclusion",
    "membrane",
    "protein",
    "trans",
)
"""Domain names the solver speaks (section 5.3.1).

``protein`` is the pore's dielectric body (section 2.2): a solid Poisson is
solved on and Nernst-Planck and the flow are not. ``cis`` and ``trans`` are
domains *and* boundaries, in two separate namespaces, exactly as
:mod:`nanopnp.mesh.primitives` already names them.

``exclusion`` is the ion-exclusion shell of FR-15, and it is a *configuration* of
the machinery the other names already use rather than a third kind of domain: a
solid for Nernst-Planck and for the flow, so the no-slip surface sits at the
outer edge of the shell — the conventional hydrodynamic shear plane — and the
**fluid's** ``eps_r`` for Poisson, which is what
:meth:`nanopnp.physics.models.CoupledModel.permittivity`'s default already gives
anything with no entry of its own. It is therefore exempt from
:func:`check_solid_permittivities`, and its presence is a deviation from the
validated model: ePNP-NS has no explicit Stern layer (section 5.3.1 NOTE).
"""

BOUNDARY_VOCABULARY: tuple[str, ...] = (
    "analyte",
    "axis",
    "cis",
    "interface",
    "membrane",
    "membrane_outer",
    "trans",
    "wall",
)
"""Boundary-group names the solver speaks (section 5.3.1).

``interface`` is any interior seam nothing selects on. Fragmenting a region
produces one wherever two domains meet without a physical boundary between
them: the two pore-mouth interfaces of
:class:`~nanopnp.mesh.primitives.CylindricalPoreGeometry`, which OCC leaves at
NGSolve's ``default`` and which separate fluid from fluid, and the
protein-to-membrane seam of :mod:`nanopnp.mesh.reference`, which separates one
solid from another. It is in the vocabulary because every group must be claimed
by a name, and calling an interior seam ``wall`` would put it in the PHY-02
distance source set and impose no-slip across the middle of the electrolyte.
"""

VOCABULARY: frozenset[str] = frozenset(MATERIAL_VOCABULARY) | frozenset(BOUNDARY_VOCABULARY)
"""Every name the mapping may produce, across both namespaces."""

FLUID_MATERIALS: frozenset[str] = frozenset(ELECTROLYTE_DOMAINS.split("|"))
"""The domains Nernst-Planck and the flow are solved on (PHY-03).

Split from the regular expression rather than written out, so that widening the
fluid set is one edit in :mod:`nanopnp.mesh.primitives` and not two that can
drift apart.
"""

SOLID_MATERIALS: frozenset[str] = frozenset(MATERIAL_VOCABULARY) - FLUID_MATERIALS
"""The domains Poisson alone is solved on; each needs a permittivity (PHY-03)."""


_METACHARACTERS: frozenset[str] = frozenset(".*+?[](){}^$\\")
"""Characters a flat name alternation cannot contain; see :func:`_options`."""


class MeshVocabularyError(ValueError):
    """A supplied mesh's groups and the names this run selects on do not line up.

    Carried as its own type rather than as a :class:`ValueError` so that a caller
    driving a sweep can tell "this mesh cannot serve this case" from "this file
    is not a mesh".
    """


@dataclass(frozen=True)
class Requirement:
    """One name selection this run will make, and the names that would satisfy it.

    Parameters
    ----------
    purpose
        What the selection is for, quoted in the diagnostic.
    pattern
        The regular expression as the run will use it.
    options
        The alternatives ``pattern`` names. The requirement is **disjunctive**:
        one supplied name satisfies it. ``velocity = "wall|membrane"`` asks for
        no-slip on the pore wall and on the bilayer, and a geometry with no
        bilayer is not thereby wrong; a geometry with *neither* has no no-slip
        surface at all, which is.
    """

    purpose: str
    pattern: str
    options: tuple[str, ...]

    def satisfied_by(self, names: frozenset[str]) -> bool:
        """Return whether any of :attr:`options` is among ``names``."""
        return bool(set(self.options) & names)


@dataclass(frozen=True)
class RequiredNames:
    """Every selection this run makes, split by namespace.

    Returned rather than a bare ``frozenset[str]`` because the two halves of the
    gate need different things from it: the check needs to know which
    alternatives count as one requirement, and the diagnostic needs to say what
    each unsatisfied one was *for*.
    """

    materials: tuple[Requirement, ...]
    boundaries: tuple[Requirement, ...]

    @property
    def names(self) -> frozenset[str]:
        """Every name mentioned by any requirement, in either namespace."""
        return frozenset(
            option
            for requirement in (*self.materials, *self.boundaries)
            for option in requirement.options
        )

    def unsatisfied(
        self, materials: frozenset[str], boundaries: frozenset[str]
    ) -> tuple[Requirement, ...]:
        """Return the requirements neither name table supplies."""
        return tuple(
            [
                requirement
                for requirement in self.materials
                if not requirement.satisfied_by(materials)
            ]
            + [
                requirement
                for requirement in self.boundaries
                if not requirement.satisfied_by(boundaries)
            ]
        )


def _options(pattern: str) -> tuple[str, ...]:
    """Return the alternatives of a flat ``a|b|c`` selection pattern.

    The selection patterns of this codebase are alternations of literal names and
    nothing else, which is what makes the gate expressible; a pattern carrying
    any other regular-expression metacharacter is refused rather than guessed at,
    because a requirement derived from a mis-parsed pattern is a gate that passes
    for the wrong reason.
    """
    parts = tuple(part.strip() for part in pattern.split("|"))
    if not parts or any(not part or set(part) & _METACHARACTERS for part in parts):
        raise MeshVocabularyError(
            f"{pattern!r} is not a flat alternation of boundary or material names; the ingestion "
            "gate can only say which names a run selects on when the pattern is one"
        )
    return parts


def required_names(resolved: ResolvedCase) -> RequiredNames:
    """Return every name selection ``resolved`` will make on its mesh.

    Derived from the resolved case and from the boundary vocabulary the physics
    models are posed on (PHY-09), never from a constant list here — see the module
    docstring.

    Parameters
    ----------
    resolved
        The case as :func:`nanopnp.io.case.resolve` returned it.

    Returns
    -------
    RequiredNames
        The fluid material set, the essential boundaries of the model this case
        names, the two electrodes individually, and the PHY-02 distance sources.
    """
    materials = (
        Requirement(
            purpose="the fluid domains Nernst-Planck and the flow are solved on (PHY-03)",
            pattern=ELECTROLYTE_DOMAINS,
            options=_options(ELECTROLYTE_DOMAINS),
        ),
    )

    boundaries = [
        Requirement(
            purpose="the essential potential (PHY-09)",
            pattern=DEFAULT_BOUNDARIES.potential,
            options=_options(DEFAULT_BOUNDARIES.potential),
        )
    ]
    # The bias is applied between two *named* electrodes -- ``BoundaryCF({ground:
    # 0, driven: V})`` in ``solve/stage.py`` and in the continuation ladder -- so
    # each of them is required on its own, and not merely as an alternative of
    # the pattern above. ``ResolvedCase.ground`` is ``Literal["cis", "trans"]``,
    # so this difference is always a single name and never a choice.
    driven = next(iter({"cis", "trans"} - {resolved.ground}))
    for name, role in ((resolved.ground, "grounded"), (driven, "driven")):
        boundaries.append(
            Requirement(
                purpose=f"the {role} electrode, boundary_conditions.ground",
                pattern=name,
                options=(name,),
            )
        )

    if resolved.model in COUPLED_MODELS:
        for ion in resolved.electrolyte.species:
            pattern = DEFAULT_BOUNDARIES.concentration_boundary(ion.name)
            boundaries.append(
                Requirement(
                    purpose=f"the essential concentration of {ion.name} (PHY-09)",
                    pattern=pattern,
                    options=_options(pattern),
                )
            )
        # ``pnp`` is the one model whose ``flow`` is not in ``model_options``:
        # ``io.case._model_options`` omits it because the builder fixes
        # ``flow=False`` itself, so a bare ``.get("flow", True)`` would demand a
        # no-slip boundary of a model that poses none.
        if resolved.model != "pnp" and resolved.model_options.get("flow", True):
            boundaries.append(
                Requirement(
                    purpose="no-slip (NUM-06)",
                    pattern=DEFAULT_BOUNDARIES.velocity,
                    options=_options(DEFAULT_BOUNDARIES.velocity),
                )
            )
            boundaries.append(
                Requirement(
                    purpose="the axis, carrying u_r = 0 and nothing else (NUM-06)",
                    pattern=DEFAULT_BOUNDARIES.velocity_axis,
                    options=_options(DEFAULT_BOUNDARIES.velocity_axis),
                )
            )

    # Required whether or not this electrolyte's corrections read ``d``: the
    # sources are a case field, and a mesh that cannot supply them is not a mesh
    # this case can run on. An ablation with every wall correction off would
    # otherwise pass a gate the validated configuration fails.
    boundaries.append(
        Requirement(
            purpose="the PHY-02 wall-distance sources, numerics.wall_distance.sources",
            pattern=resolved.wall_distance_sources,
            options=_options(resolved.wall_distance_sources),
        )
    )
    return RequiredNames(materials=materials, boundaries=tuple(boundaries))


def _looks_reversed(groups: dict[str, str]) -> bool:
    """Return whether ``groups`` was written vocabulary-first.

    The one ergonomic cost of keying the mapping on the *file's* names is that a
    reader writing it from the solver's side gets a diagnostic pointing at the
    wrong thing — every group unclaimed, and no hint why. Two lines buy the right
    one.
    """
    if not groups:
        return False
    return all(key in VOCABULARY for key in groups) and not any(
        value in VOCABULARY for value in groups.values()
    )


def _mapped(
    table: tuple[str, ...], groups: dict[str, str], vocabulary: frozenset[str], label: str
) -> tuple[dict[str, str], list[str], list[str]]:
    """Return the mapping applied to one name table, and what went wrong.

    A group whose own name is already a vocabulary name is claimed by that fact
    and needs no entry: the failure this gate exists to catch is a name the solver
    does *not* speak slipping through unnoticed, and a name it does speak is not
    one of those. Everything else must be named in ``groups``.
    """
    applied: dict[str, str] = {}
    unclaimed: list[str] = []
    wrong_namespace: list[str] = []
    for name in table:
        if name in groups:
            target = groups[name]
            if target not in vocabulary:
                wrong_namespace.append(f"{name!r} -> {target!r}, which is not a {label} name")
                continue
            applied[name] = target
        elif name in vocabulary:
            applied[name] = name
        else:
            unclaimed.append(name)
    return applied, unclaimed, wrong_namespace


def apply_groups(data: MeshData, groups: dict[str, str]) -> tuple[MeshData, dict[str, str]]:
    """Map a mesh's own group names onto the vocabulary (section 5.3.1, IF-06).

    Parameters
    ----------
    data
        The mesh as the file carries it.
    groups
        ``inputs.mesh.groups``: ``{group name in the file: vocabulary name}``.
        Many-to-one is expected — a CAD export routinely splits one physical wall
        into several curves — and is merged by
        :meth:`~nanopnp.mesh.adapter.MeshData.renamed`. The mapping is flat while
        the mesh has two namespaces, so a key naming both a domain and a boundary
        group maps both; the target is checked against the namespace it lands in.

    Returns
    -------
    MeshData
        The mesh with both name tables in the vocabulary.
    dict
        The mapping actually applied, ``{file name: vocabulary name}``, including
        the identities. Recorded in the FR-25 manifest, because "which of the
        file's groups became the pore wall" is not recoverable from the result.

    Raises
    ------
    MeshVocabularyError
        If the mapping looks reversed, names a group the file does not carry,
        maps a name into the wrong namespace, or leaves a group unclaimed.
    """
    if _looks_reversed(groups):
        raise MeshVocabularyError(
            "inputs.mesh.groups reads file group -> vocabulary name, and this mapping looks "
            f"written the other way round: every key ({', '.join(sorted(groups))}) is a "
            f"vocabulary name and no value ({', '.join(sorted(set(groups.values())))}) is. The "
            "key is what the mesh file says; the value is what the solver selects on"
        )

    stale = sorted(set(groups) - set(data.materials) - set(data.boundaries))
    if stale:
        raise MeshVocabularyError(
            f"inputs.mesh.groups names {', '.join(repr(name) for name in stale)}, which no group "
            f"in this mesh is called; it carries the domains {list(data.materials)} and the "
            f"boundaries {list(data.boundaries)}"
        )

    material_map, unclaimed_m, wrong_m = _mapped(
        data.materials, groups, frozenset(MATERIAL_VOCABULARY), "domain"
    )
    boundary_map, unclaimed_b, wrong_b = _mapped(
        data.boundaries, groups, frozenset(BOUNDARY_VOCABULARY), "boundary"
    )
    if wrong_m or wrong_b:
        raise MeshVocabularyError(
            "inputs.mesh.groups maps a group into the wrong namespace: "
            + "; ".join(wrong_m + wrong_b)
            + f". The domain names are {list(MATERIAL_VOCABULARY)} and the boundary names are "
            f"{list(BOUNDARY_VOCABULARY)}"
        )
    if unclaimed_m or unclaimed_b:
        parts = []
        if unclaimed_m:
            parts.append(f"domains {', '.join(repr(name) for name in unclaimed_m)}")
        if unclaimed_b:
            parts.append(f"boundaries {', '.join(repr(name) for name in unclaimed_b)}")
        raise MeshVocabularyError(
            f"this mesh carries {' and '.join(parts)} that inputs.mesh.groups does not claim and "
            "that the solver does not speak; every group must map onto one of the vocabulary "
            f"names {sorted(VOCABULARY)}, because a boundary nothing selects on carries the "
            "natural condition and is silently free (NUM-06)"
        )

    applied = {**material_map, **boundary_map}
    return data.renamed(materials=material_map, boundaries=boundary_map), applied


def check_names(data: MeshData, required: RequiredNames, *, where: str) -> None:
    """Abort unless every selection ``required`` makes is supplied by ``data``.

    Parameters
    ----------
    data
        The mesh **after** :func:`apply_groups`, so its names are vocabulary names.
    required
        As :func:`required_names` returned it.
    where
        Named in the diagnostic; the mesh file, ordinarily.

    Raises
    ------
    MeshVocabularyError
        Naming every unsatisfied requirement, what it was for, and the names the
        mesh does carry (QR-12).
    """
    unsatisfied = required.unsatisfied(frozenset(data.materials), frozenset(data.boundaries))
    if not unsatisfied:
        return
    lines = "; ".join(
        f"{requirement.pattern!r} for {requirement.purpose}" for requirement in unsatisfied
    )
    raise MeshVocabularyError(
        f"{where} supplies no group for {lines}. After mapping it carries the domains "
        f"{list(data.materials)} and the boundaries {list(data.boundaries)}. A selection that "
        "matches nothing applies its condition to nothing, and under the r-weighted forms that is "
        "silent (NUM-06, QR-12)"
    )


def check_solid_permittivities(
    data: MeshData, solid_permittivities: dict[str, float], *, where: str
) -> None:
    """Abort unless every solid domain of ``data`` has a permittivity (PHY-03, QR-12).

    Poisson is solved over the whole domain, so a solid with no entry falls back
    to the electrolyte's ``eps_r`` — about 24 times too large in a protein or a
    bilayer, and a plausible wrong answer with no solver diagnostic. The
    exception is :data:`PERMITTIVITY_EXEMPT`, whose members take the fluid's
    ``eps_r`` deliberately.

    On an **ingested** mesh this aborts, where
    :meth:`nanopnp.physics.models.CoupledModel` only warns: the benchmark
    geometries' material names are written by this codebase and covered by tests,
    and an ingested mesh's are not. The asymmetry is section 5.3.1's.

    Parameters
    ----------
    data
        The mesh after :func:`apply_groups`.
    solid_permittivities
        ``physics.solid_permittivities`` from the case.
    where
        Named in the diagnostic.

    Raises
    ------
    MeshVocabularyError
        Naming every solid material with no entry, and the reference values.
    """
    missing = sorted(
        name
        for name in data.materials
        if name not in FLUID_MATERIALS
        and name not in PERMITTIVITY_EXEMPT
        and name not in solid_permittivities
    )
    if not missing:
        return
    raise MeshVocabularyError(
        f"{where} carries the solid {'domains' if len(missing) > 1 else 'domain'} "
        f"{', '.join(repr(name) for name in missing)} with no physics.solid_permittivities entry. "
        "Poisson is solved there too, so the electrolyte's eps_r would stand in at about 24 times "
        "the right value with nothing to say so (PHY-03). PHY-20 gives eps_r = 3.2 for the "
        "membrane and 20 for the protein and the analyte"
    )


@dataclass(frozen=True)
class IngestedMesh:
    """A supplied mesh that has passed every gate, and what the gates measured.

    Returned instead of the bare NGSolve mesh because the artefact and the FR-25
    manifest both need what the gates already computed — the content hash, the
    quality statistics, the mapping actually applied — and recomputing them would
    mean reading the file twice and could give two different answers.

    Parameters
    ----------
    data
        The mapped, gated mesh.
    quality
        The VER-10 report over it.
    source
        The file it came from.
    source_hash
        That file's sha256, recorded for provenance and deliberately *outside*
        the artefact key: a mesh rewritten with a different header is the same
        mesh (section 5.3.2).
    applied
        ``{file group name: vocabulary name}``, identities included.
    """

    data: MeshData
    quality: QualityReport
    source: Path
    source_hash: str
    applied: dict[str, str]

    @property
    def content_hash(self) -> str:
        """The mesh's identity: its canonical vertices, connectivity and tags."""
        return self.data.content_hash

    @cached_property
    def mesh(self) -> Mesh:
        """The NGSolve mesh, built once on first use."""
        from nanopnp.mesh.adapter import to_ngsolve

        return to_ngsolve(self.data)

    def deviations(self) -> tuple[ContributedDeviation, ...]:
        """Return the departures from the validated model this mesh carries.

        One, and no case-file switch selects it: a mesh presenting the
        ``exclusion`` material puts an ion-exclusion shell into a model that has
        none. ePNP-NS carries no explicit Stern layer, so its presence is a
        deviation and is recorded as one (§5.3.1 NOTE, FR-25) — reported from
        here rather than from stage 7 because a run may carry such a mesh and
        supply no field at all.
        """
        if not set(self.data.materials) & PERMITTIVITY_EXEMPT:
            return ()
        return (
            ContributedDeviation(
                source="mesh material 'exclusion'",
                description=(
                    "an ion-exclusion shell, where ePNP-NS carries no explicit Stern layer "
                    "(section 5.3.1 NOTE). The no-slip surface then sits at the outer edge of "
                    "the shell, which is the conventional hydrodynamic shear plane, and the "
                    "PHY-02 distance is measured from there rather than from the dielectric "
                    "contour"
                ),
            ),
        )

    def summary(self) -> dict[str, object]:
        """Return what the manifest's geometry-and-mesh group records (FR-25)."""
        return {
            "source": self.source.name,
            "source_sha256": self.source_hash,
            "content_hash": self.content_hash,
            **self.data.summary(),
            "groups": dict(sorted(self.applied.items())),
            "quality": self.quality.summary(),
        }


def _source_path(supplied: SuppliedArtefact) -> Path:
    """Return the mesh file the case names, checked.

    Raises
    ------
    UnsupportedCaseSection
        If the mesh is named by store hash rather than by path, which needs the
        meshing pipeline of v0.9.
    FileNotFoundError
        If the file is not there.
    """
    if supplied.path is None:
        raise UnsupportedCaseSection(
            "inputs.mesh: artefact: names a mesh in the store, which the meshing "
            "pipeline of v0.9 fills; supply inputs.mesh: path: instead"
        )
    if not supplied.path.is_file():
        raise FileNotFoundError(f"inputs.mesh.path {str(supplied.path)!r} does not exist")
    return supplied.path


def ingest(supplied: SuppliedArtefact, resolved: ResolvedCase) -> IngestedMesh:
    """Read, map and gate the mesh a case supplies (IF-06, QR-12, VER-10, VER-27).

    The six steps of the module docstring, in order. Nothing downstream of this
    function checks a name again.

    Parameters
    ----------
    supplied
        ``inputs.mesh``: the path, the optional declared format, and the mapping.
    resolved
        The resolved case, which is what says which names this run selects on.

    Returns
    -------
    IngestedMesh
        The gated mesh, its quality report and the mapping applied.

    Raises
    ------
    MeshVocabularyError
        On any naming failure (steps 3 and 4).
    nanopnp.mesh.quality.MeshQualityError
        On a sliver, an inverted element or a negative radius (steps 5 and 6).
    """
    path = _source_path(supplied)
    where = f"the mesh {path.name!r}"
    data = read(path, format=detect_format(path, supplied.format))

    mapped, applied = apply_groups(data, dict(supplied.groups))
    check_names(mapped, required_names(resolved), where=where)
    check_solid_permittivities(
        mapped, dict(resolved.document.physics.solid_permittivities), where=where
    )

    quality = element_quality(mapped)
    check_quality(mapped, where=where)
    check_radii(mapped, where=where)

    logger.info(
        "ingested %s: %d elements, %d vertices, min SICN %.4f, min gamma %.4f, domains %s",
        path.name,
        mapped.element_count,
        mapped.vertex_count,
        quality.min_sicn,
        quality.min_gamma,
        ", ".join(mapped.materials),
    )
    return IngestedMesh(
        data=mapped,
        quality=quality,
        source=path,
        source_hash=file_hash(path),
        applied=applied,
    )


class MeshStage:
    """Stage 6: a supplied mesh file to a tagged, gated, content-addressed mesh.

    The artefact's identity is the mesh's **contents** — canonical vertices,
    connectivity and tag maps — and not the file's bytes, so a mesh rewritten by
    another tool with a different header is one store entry rather than two, and a
    mesh whose ``wall`` group gained an edge is a different one. The cost is that
    :meth:`key` has to read and gate the mesh: seconds, against a solve of
    minutes, and the alternative files one mesh under two keys.
    """

    name = "mesh"

    def __init__(self, *, workspace: Path | None = None) -> None:
        """Build the stage.

        Parameters
        ----------
        workspace
            Directory the archival MSH 4.1 copy is written to before the store
            copies it in. Defaults to a fresh directory under the store root.
        """
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> MeshArtefact:
        """Return the artefact key this mesh will produce, without writing it.

        Returns
        -------
        MeshArtefact
            The same schema and parameters :meth:`run` returns, with no payload.
        """
        return self.artefact(self._ingest(inputs))

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> MeshArtefact:
        """Ingest the mesh, write the archival copy and emit the stage-6 artefact.

        Parameters
        ----------
        inputs
            Carries the case; this stage consumes no upstream artefact.
        progress
            Called with a fraction in [0, 1], monotone, ending at 1.
        cancel
            Checked on entry and before the archival write.

        Returns
        -------
        MeshArtefact
            Keyed on the mesh's contents, carrying the MSH 4.1 copy as its
            payload and the quality statistics as its summary.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true. No artefact is written.
        """
        check_cancelled(cancel, "reading the mesh")
        report(progress, 0.0, "reading and gating the mesh")
        ingested = self._ingest(inputs)

        check_cancelled(cancel, "writing the archival mesh")
        report(progress, 0.6, "writing the archival MSH 4.1 copy")
        payload = self._write(ingested)
        report(progress, 1.0, f"{ingested.data.element_count} elements, gates passed")
        return self.artefact(ingested, payload=payload)

    def _ingest(self, inputs: StageInputs) -> IngestedMesh:
        """Resolve the case and run the gate; shared by :meth:`key` and :meth:`run`."""
        resolved = resolve(inputs.case)
        return ingest(resolved.mesh, resolved)

    def artefact(
        self, ingested: IngestedMesh, *, payload: dict[str, Path] | None = None
    ) -> MeshArtefact:
        """Return the artefact for an already-gated mesh, with or without its payload.

        Public because stage 10 has the :class:`IngestedMesh` in hand and needs
        its key: routing that through :meth:`key` would read and gate the same
        file a second time, and two ingestions of one file are two chances to
        disagree.

        Parameters
        ----------
        ingested
            The mesh as :func:`ingest` returned it.
        payload
            The archival copy, when there is one. Outside the digest either way
            (section 5.3.2), so the key is the same with and without it.
        """
        return MeshArtefact(
            content_hash=ingested.content_hash,
            materials=ingested.data.materials,
            boundaries=ingested.data.boundaries,
            groups=ingested.applied,
            payload=payload or {},
            summary=ingested.summary(),
        )

    def _write(self, ingested: IngestedMesh) -> dict[str, Path]:
        """Write the archival MSH 4.1 copy and return the payload map (IF-06).

        Written from the *mapped* mesh, so the archived file speaks the
        vocabulary and needs no mapping to be read back — which is what makes it
        an archive rather than a second copy of the input.
        """
        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix="mesh-", dir=root))
        directory.mkdir(parents=True, exist_ok=True)
        return {"mesh": write_msh41(ingested.data, directory / "mesh.msh")}
