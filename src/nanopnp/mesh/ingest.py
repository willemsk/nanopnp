"""Stage 6 of section 5.2: reading a supplied mesh, tagging it, gating it (IF-06, QR-12)."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import file_hash
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.geometry.region import PAYLOAD_NAME, read_region
from nanopnp.io.artefact import MeshArtefact
from nanopnp.io.case import SuppliedArtefact, stored_artefact_refused
from nanopnp.io.defaults import ContributedDeviation
from nanopnp.io.vocabulary import (
    POTENTIAL,
    VELOCITY,
    VELOCITY_AXIS,
)
from nanopnp.io.workspace import scratch_directory
from nanopnp.mesh.adapter import MeshData, detect_format, read, write_msh41
from nanopnp.mesh.primitives import (
    ELECTROLYTE_DOMAINS,
    PERMITTIVITY_EXEMPT,
)
from nanopnp.mesh.quality import QualityReport, check_quality, check_radii, element_quality
from nanopnp.mesh.sizing import SIZES, resolve_wall_size

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Mesh
    from nanopnp.io.artefact import Artefact, StageInputs
    from nanopnp.io.resolved import ResolvedCase

logger = logging.getLogger(__name__)

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
outer edge of the shell — the conventional hydrodynamic shear plane — and
ion-free water, ``eps_r,f^0``, for Poisson, which is what
:meth:`nanopnp.physics.models.CoupledModel.permittivity` gives every material off
the fluid with no entry of its own. It is therefore exempt from
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
"""The domains Poisson alone is solved on (PHY-03).

Each needs a ``physics.solid_permittivities`` entry except the members of
:data:`~nanopnp.mesh.primitives.PERMITTIVITY_EXEMPT`, which take the fluid's
``eps_r`` deliberately; :func:`check_solid_permittivities` is where that
distinction is enforced.
"""


# Characters a flat name alternation cannot contain; see :func:`_options`.
_METACHARACTERS: frozenset[str] = frozenset(".*+?[](){}^$\\")


class MeshVocabularyError(ValueError):
    """A supplied mesh's groups and the names this run selects on do not line up."""


@dataclass(frozen=True)
class Requirement:
    """One name selection the run makes, and the names that would satisfy it."""

    purpose: str
    pattern: str
    options: tuple[str, ...]

    def satisfied_by(self, names: frozenset[str]) -> bool:
        """Return whether any of :attr:`options` is among ``names``."""
        return bool(set(self.options) & names)


@dataclass(frozen=True)
class RequiredNames:
    """Every name selection the run makes, split by namespace."""

    materials: tuple[Requirement, ...]
    boundaries: tuple[Requirement, ...]

    @property
    def names(self) -> frozenset[str]:
        """Every name any requirement mentions, in either namespace."""
        return frozenset(
            option
            for requirement in (*self.materials, *self.boundaries)
            for option in requirement.options
        )

    def unsatisfied(
        self, materials: frozenset[str], boundaries: frozenset[str]
    ) -> tuple[Requirement, ...]:
        """Return the requirements that neither name table supplies."""
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
    parts = tuple(part.strip() for part in pattern.split("|"))
    if not parts or any(not part or set(part) & _METACHARACTERS for part in parts):
        raise MeshVocabularyError(
            f"{pattern!r} is not a flat alternation of boundary or material names; the ingestion "
            "gate can only say which names a run selects on when the pattern is one"
        )
    return parts


# What the diagnostic says each essential set is for, keyed by field (physics.models' vocabulary),
# not by model; a key missing here, such as a species' concentration, is described generically.
_ESSENTIAL_PURPOSES: dict[str, str] = {
    POTENTIAL: "the essential potential (PHY-09)",
    VELOCITY: "no-slip (NUM-06)",
    VELOCITY_AXIS: "the axis, carrying u_r = 0 and nothing else (NUM-06)",
}


def required_names(resolved: ResolvedCase) -> RequiredNames:
    """Return every name selection ``resolved`` makes on its mesh."""
    materials = (
        Requirement(
            purpose="the fluid domains Nernst-Planck and the flow are solved on (PHY-03)",
            pattern=ELECTROLYTE_DOMAINS,
            options=_options(ELECTROLYTE_DOMAINS),
        ),
    )

    # Read off the built model, not its name (section 5.4.3 NOTE); the potential only where
    # the model reports it.
    essential = dict(resolved.essential_boundaries)
    potential = essential.pop(POTENTIAL, None)
    boundaries: list[Requirement] = []
    if potential is not None:
        boundaries.append(
            Requirement(
                purpose=_ESSENTIAL_PURPOSES[POTENTIAL],
                pattern=potential,
                options=_options(potential),
            )
        )
    # The bias is applied between two named electrodes, so each is required on its own.
    driven = next(iter({"cis", "trans"} - {resolved.ground}))
    for name, role in ((resolved.ground, "grounded"), (driven, "driven")):
        boundaries.append(
            Requirement(
                purpose=f"the {role} electrode, boundary_conditions.ground",
                pattern=name,
                options=(name,),
            )
        )
    for key, pattern in essential.items():
        boundaries.append(
            Requirement(
                purpose=_ESSENTIAL_PURPOSES.get(key, f"the essential condition on {key} (PHY-09)"),
                pattern=pattern,
                options=_options(pattern),
            )
        )

    # Required even with every wall correction off, so an ablation passes no gate the
    # validated configuration fails.
    if resolved.declaration.wall_distance:
        boundaries.append(
            Requirement(
                purpose="the PHY-02 wall-distance sources, numerics.wall_distance.sources",
                pattern=resolved.wall_distance_sources,
                options=_options(resolved.wall_distance_sources),
            )
        )
    return RequiredNames(materials=materials, boundaries=tuple(boundaries))


def _looks_reversed(groups: dict[str, str]) -> bool:
    if not groups:
        return False
    return all(key in VOCABULARY for key in groups) and not any(
        value in VOCABULARY for value in groups.values()
    )


def _mapped(
    table: tuple[str, ...], groups: dict[str, str], vocabulary: frozenset[str], label: str
) -> tuple[dict[str, str], list[str], list[str]]:
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
    """Map a mesh's own group names onto the project vocabulary.

    Parameters
    ----------
    groups
        ``{group name in the file: vocabulary name}``; many-to-one is allowed.

    Raises
    ------
    MeshVocabularyError
        If the mapping looks reversed, names an absent group, or leaves one unclaimed.
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
    """Abort unless ``data`` supplies every selection ``required`` makes.

    Raises
    ------
    MeshVocabularyError
        Naming each unsatisfied requirement and the names the mesh does carry.
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
    data: MeshData,
    solid_permittivities: dict[str, float],
    *,
    where: str,
    model: str | None = None,
    solids: bool = True,
) -> None:
    """Abort unless every solid domain of ``data`` has a permittivity.

    Members of ``PERMITTIVITY_EXEMPT`` take the fluid's ``eps_r`` deliberately.

    Parameters
    ----------
    solids
        Whether the model carries solid materials. If not, any solid domain aborts.

    Raises
    ------
    MeshVocabularyError
        Naming every solid material with no entry, or the model and its solid domains.
    """
    if not solids:
        present = sorted(name for name in data.materials if name not in FLUID_MATERIALS)
        if present:
            raise MeshVocabularyError(
                f"{where} carries the solid {'domains' if len(present) > 1 else 'domain'} "
                f"{', '.join(repr(name) for name in present)}, and physics.model {model!r} "
                "cannot be posed on a mesh with a solid domain: it carries no solid materials, "
                "and its screening term would treat the solid as electrolyte (PHY-21 NOTE)"
            )
        return
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


def exclusion_deviations(materials: Iterable[str]) -> tuple[ContributedDeviation, ...]:
    """Return the deviation an ``exclusion`` material contributes, if any."""
    if not set(materials) & PERMITTIVITY_EXEMPT:
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


@dataclass(frozen=True)
class IngestedMesh:
    """A supplied mesh that has passed every gate, with what the gates measured."""

    data: MeshData
    quality: QualityReport
    source: Path
    source_hash: str
    applied: dict[str, str]

    @property
    def content_hash(self) -> str:
        """The mesh's identity: its vertices, connectivity and tags."""
        return self.data.content_hash

    @cached_property
    def mesh(self) -> Mesh:
        """The NGSolve mesh, built once on first use."""
        from nanopnp.mesh.adapter import to_ngsolve

        return to_ngsolve(self.data)

    def deviations(self) -> tuple[ContributedDeviation, ...]:
        """Return the departures from the validated model this mesh carries.

        An ``exclusion`` material adds an ion-exclusion shell that ePNP-NS does not have.
        """
        return exclusion_deviations(self.data.materials)

    def summary(self) -> dict[str, object]:
        """Return what the manifest's geometry-and-mesh group records."""
        return {
            "source": self.source.name,
            "source_sha256": self.source_hash,
            "content_hash": self.content_hash,
            **self.data.summary(),
            "groups": dict(sorted(self.applied.items())),
            "quality": self.quality.summary(),
        }


def _source_path(supplied: SuppliedArtefact) -> Path:
    if supplied.path is None:
        raise stored_artefact_refused("mesh")
    if not supplied.path.is_file():
        # Quoted rather than ``!r``, which doubles a Windows path's separators.
        raise FileNotFoundError(f"inputs.mesh.path '{supplied.path}' does not exist")
    return supplied.path


def ingest(supplied: SuppliedArtefact, resolved: ResolvedCase) -> IngestedMesh:
    """Read, map and gate the mesh a case supplies.

    Raises
    ------
    MeshVocabularyError
        On any naming failure.
    MeshQualityError
        On a sliver, an inverted element or a negative radius.
    """
    path = _source_path(supplied)
    where = f"the mesh {path.name!r}"
    data = read(path, format=detect_format(path, supplied.format))

    mapped, applied = apply_groups(data, dict(supplied.groups))
    check_names(mapped, required_names(resolved), where=where)
    check_solid_permittivities(
        mapped,
        dict(resolved.document.physics.solid_permittivities),
        where=where,
        model=resolved.model,
        solids=resolved.declaration.solids,
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


MESH_PAYLOAD = "mesh"
"""The stage-6 artefact's payload key: the archival, or generated, MSH 4.1 file."""


def deployed_mesh(resolved: ResolvedCase, generated: Artefact | None) -> IngestedMesh:
    """Return the mesh a run solves on: the supplied mesh, else the stage-6 payload.

    Raises
    ------
    KeyError
        If the case generates its mesh and no stage-6 artefact is given.
    """
    if resolved.mesh is not None:
        return ingest(resolved.mesh, resolved)
    if generated is None or MESH_PAYLOAD not in generated.payload:
        raise KeyError(
            f"case {resolved.name!r} generates its mesh, and this stage was handed no stage-6 "
            "mesh artefact to read it from; run the pipeline through 'mesh' first. A consumer "
            "reads the generated mesh and never regenerates it"
        )
    return ingest(SuppliedArtefact(path=generated.payload[MESH_PAYLOAD], format="msh41"), resolved)


class MeshStage:
    """Stage 6: a supplied mesh file, or stage 5's region, to a tagged, gated mesh."""

    name = "mesh"

    def __init__(self, *, workspace: Path | None = None) -> None:
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def deviations(self, inputs: StageInputs) -> tuple[ContributedDeviation, ...]:
        """Return the departures a supplied mesh contributes, from its artefact's materials."""
        materials = inputs.require(self.name).parameters["materials"]
        assert isinstance(materials, list)  # MeshArtefact writes it as one
        return exclusion_deviations(str(name) for name in materials)

    def key(self, inputs: StageInputs) -> MeshArtefact:
        """Return the artefact key this mesh will produce, without writing it."""
        resolved = inputs.resolved
        if resolved.generates_mesh:
            return self._recipe(inputs, resolved)
        return self.artefact(self._ingest(inputs))

    def _recipe(
        self,
        inputs: StageInputs,
        resolved: ResolvedCase,
        *,
        payload: dict[str, Path] | None = None,
        summary: dict[str, object] | None = None,
    ) -> MeshArtefact:
        from nanopnp.mesh.generate import sizing_parameters

        region = inputs.require("region")
        record = read_region(region.payload[PAYLOAD_NAME])
        wall = resolve_wall_size(
            resolved.document, permittivity_0=resolved.electrolyte.permittivity_0
        )
        return MeshArtefact(
            region=region.hash,
            materials=tuple(sorted(record.face_areas_nm2)),
            boundaries=tuple(sorted(record.edge_counts)),
            groups={},
            sizing=sizing_parameters(
                wall,
                SIZES.scaled(wall.size_scale),
                resolved.document.numerics.mesh.backend,
                exclusion=record.exclusion is not None,
            ),
            payload=payload,
            summary=summary,
        )

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> MeshArtefact:
        """Ingest the mesh, write the archival copy and emit the stage-6 artefact.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true; no artefact is written.
        """
        resolved = inputs.resolved
        if resolved.generates_mesh:
            return self._generate(inputs, resolved, progress=progress, cancel=cancel)
        check_cancelled(cancel, "reading the mesh")
        report(progress, 0.0, "reading and gating the mesh")
        ingested = self._ingest(inputs)

        check_cancelled(cancel, "writing the archival mesh")
        report(progress, 0.6, "writing the archival MSH 4.1 copy")
        payload = self._write(ingested)
        report(progress, 1.0, f"{ingested.data.element_count} elements, gates passed")
        return self.artefact(ingested, payload=payload)

    def _generate(
        self,
        inputs: StageInputs,
        resolved: ResolvedCase,
        *,
        progress: Progress | None,
        cancel: CancelToken | None,
    ) -> MeshArtefact:
        from nanopnp.mesh.generate import generate

        check_cancelled(cancel, "meshing the region")
        report(progress, 0.0, "meshing the region")
        record = read_region(inputs.require("region").payload[PAYLOAD_NAME])
        generated = generate(record, resolved, self._directory())
        found = (set(generated.ingested.data.materials), set(generated.ingested.data.boundaries))
        wanted = (set(record.face_areas_nm2), set(record.edge_counts))
        if found != wanted:
            raise MeshVocabularyError(
                f"the generated mesh carries the domains {sorted(found[0])} and the boundaries "
                f"{sorted(found[1])}, and its region named {sorted(wanted[0])} and "
                f"{sorted(wanted[1])}; the mesher lost or invented a name (VER-27)"
            )
        report(
            progress,
            1.0,
            f"{generated.ingested.data.element_count} elements generated, gates passed",
        )
        return self._recipe(
            inputs,
            resolved,
            payload={MESH_PAYLOAD: generated.ingested.source},
            summary=generated.summary(),
        )

    def _ingest(self, inputs: StageInputs) -> IngestedMesh:
        resolved = inputs.resolved
        assert resolved.mesh is not None  # only reached for a supplied mesh
        return ingest(resolved.mesh, resolved)

    def artefact(
        self, ingested: IngestedMesh, *, payload: dict[str, Path] | None = None
    ) -> MeshArtefact:
        """Return the artefact for an already-gated mesh, with or without its payload."""
        return MeshArtefact(
            content_hash=ingested.content_hash,
            materials=ingested.data.materials,
            boundaries=ingested.data.boundaries,
            groups=ingested.applied,
            payload=payload or {},
            summary=ingested.summary(),
        )

    def _write(self, ingested: IngestedMesh) -> dict[str, Path]:
        directory = self._directory()
        return {MESH_PAYLOAD: write_msh41(ingested.data, directory / "mesh.msh")}

    def _directory(self) -> Path:
        return scratch_directory(self._workspace, "mesh")
