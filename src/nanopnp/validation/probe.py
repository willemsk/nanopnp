"""The ``nanopnp/probe/v1`` comparison surface: where Tier 3 samples both solutions.

Section 7.4 compares fields "on a common probe grid", and the grid is **ours**.
COMSOL interpolates onto the points this document names, so the comparison does
not depend on the reference's mesh and a re-export cannot silently move the
sample points; the document's content hash is carried in every golden manifest,
so an edited probe grid is refused rather than absorbed.

Three properties of the container are load-bearing.

**A patch is never square.** ``%Data`` rows are ``[i_z, i_r]``, which is
:class:`~nanopnp.density.grid.RadialGrid`'s own layout, and
:func:`~nanopnp.density.grid.read_grid` checks that every row carries one value
per ``r`` sample — which catches a ragged file and *not* a cleanly transposed
square one. Requiring ``n_r != n_z`` on every patch turns that case into a shape
error at ingest, and costs nothing: no physically motivated patch has a reason to
be square.

**A point is retained only with a margin.** NGSolve returns ``0`` outside a
space's ``definedon`` region, silently, so a concentration norm taken over the
membrane is dominated by fabricated zeros and reads as agreement. The mask is
therefore the set of points whose four ``+-margin_nm`` neighbours are *also*
inside the field's materials, which keeps it off the boundary-resolution lottery
and makes a residual disagreement with the golden's ``NaN`` set a real geometry
difference rather than a coin flip.

**The axis is mirrored, not clipped.** A probe point on ``r = 0`` has no
neighbour at ``r = -margin`` in a half-plane mesh, and clipping would drop the
near-axis line — the one place ``rel_l2`` exists to see (section 2 of the WP13
plan). Under the axisymmetric ansatz of PHY-01 the point at ``-d`` *is* the point
at ``+d``, so the radial neighbours are taken at ``abs(r +- margin)``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nanopnp.core.hashing import content_hash
from nanopnp.io.case import CaseValidationError, render_problems

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.core.typing import Expression, Mesh

__all__ = [
    "DEFAULT_MARGIN_NM",
    "PROBE_SCHEMA",
    "ProbeDocument",
    "ProbeGrid",
    "ProbeGridError",
    "ProbePatch",
    "load_probe",
    "loads_probe",
]

PROBE_SCHEMA = "nanopnp/probe/v1"
"""Schema identifier every probe document declares, and the hash's separator."""

DEFAULT_MARGIN_NM = 0.05
"""Margin of the domain mask, in nm.

The reference model's own maximum element size on the pore wall
(``.knowledge/09-comsol-reference-settings.md`` section A.2, node ``size5``). A
mask taken without it is decided, point by point, by which element the mesh's
point search happens to land in; taken with it, a residual disagreement against
the golden's ``NaN`` set is a real difference between our reference geometry and
the one the export was made from.
"""

COMSOL_LENGTH_SCALE_M = 1e-9
"""nm to m: the unit a ``%Grid`` axis line is written in."""


class ProbeGridError(ValueError):
    """A probe grid cannot be built, or cannot be compared against.

    A ``ValueError`` and IF-02's case class, like
    :class:`~nanopnp.sweep.plan.SweepPlanError`: every message names the patch,
    the field or the point that was wrong, and the fix is an edit to the probe
    document or to the export, never a retry (QR-12).
    """


class _Strict(BaseModel):
    """Base for every block: unknown keys are rejected, and named in the error."""

    model_config = ConfigDict(extra="forbid")


class ProbePatch(_Strict):
    """One tensor-product block of sample points, in nm.

    Parameters
    ----------
    name
        The patch's name. It reaches the export contract's file names, the
        golden manifest and every diagnostic, so it is part of the interface and
        not a comment.
    r_nm, z_nm
        ``(min, max)`` of the sampled box, inclusive at both ends.
    n_r, n_z
        Sample counts along each axis. They must differ; see the module
        docstring.

    Notes
    -----
    Points flatten in ``[i_z, i_r]`` C order, so
    :meth:`~nanopnp.density.grid.RadialGrid.values` ``.ravel()`` of a table read
    from the author's export lands on this patch's points without a transpose
    anywhere in between.
    """

    name: str
    r_nm: tuple[float, float]
    z_nm: tuple[float, float]
    n_r: int
    n_z: int

    @model_validator(mode="after")
    def _ascending_and_not_square(self) -> ProbePatch:
        """Reject an empty box, a single-sample axis, or a square patch."""
        for axis, (low, high) in (("r", self.r_nm), ("z", self.z_nm)):
            if not high > low:
                raise ValueError(
                    f"patch {self.name!r} declares {axis}_nm = ({low}, {high}); a patch's bounds "
                    "run from its minimum to its maximum and must be distinct"
                )
        for axis, count in (("r", self.n_r), ("z", self.n_z)):
            if count < 2:
                raise ValueError(
                    f"patch {self.name!r} declares n_{axis} = {count}; a tensor-product axis "
                    "needs at least two samples, since one sample fixes no spacing"
                )
        if self.n_r == self.n_z:
            raise ValueError(
                f"patch {self.name!r} is square, n_r = n_z = {self.n_r}. A COMSOL %Data block is "
                "written one row per z sample and one value per r sample, so a transposed read of "
                "a square table has the right shape and the wrong field everywhere — and agrees "
                "exactly wherever r = z. Give the patch different sample counts; no physically "
                "motivated patch needs equal ones"
            )
        return self

    @property
    def spacing_nm(self) -> tuple[float, float]:
        """``(dr, dz)`` of this patch's uniform spacing."""
        return (
            (self.r_nm[1] - self.r_nm[0]) / (self.n_r - 1),
            (self.z_nm[1] - self.z_nm[0]) / (self.n_z - 1),
        )

    @property
    def weight_nm2(self) -> float:
        """``dr dz``: the midpoint-rule weight every point of this patch carries."""
        dr, dz = self.spacing_nm
        return dr * dz

    @property
    def count(self) -> int:
        """Number of points this patch contributes."""
        return self.n_r * self.n_z

    def axes_nm(self) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(r_axis, z_axis)`` in nm, ascending and uniformly spaced."""
        import numpy as np

        return (
            np.linspace(self.r_nm[0], self.r_nm[1], self.n_r, dtype=np.float64),
            np.linspace(self.z_nm[0], self.z_nm[1], self.n_z, dtype=np.float64),
        )

    def points_nm(self) -> np.ndarray:
        """Return this patch's points as ``(count, 2)`` in ``[i_z, i_r]`` order."""
        import numpy as np

        r_axis, z_axis = self.axes_nm()
        r_grid, z_grid = np.meshgrid(r_axis, z_axis, indexing="xy")
        return np.column_stack((r_grid.ravel(), z_grid.ravel()))

    def summary(self) -> dict[str, object]:
        """Return this patch as the document's hash and the manifest record it."""
        return {
            "name": self.name,
            "r_nm": list(self.r_nm),
            "z_nm": list(self.z_nm),
            "n_r": self.n_r,
            "n_z": self.n_z,
        }


class ProbeDocument(_Strict):
    """A validated probe grid (schema ``nanopnp/probe/v1``).

    Parameters
    ----------
    schema_id
        Carried under the ``schema`` alias so the reserved name does not shadow
        ``BaseModel``, exactly as :class:`~nanopnp.io.case.CaseDocument` does.
    name
        The grid's name; part of the export contract's file names.
    margin_nm
        Mask margin; see :data:`DEFAULT_MARGIN_NM`.
    patches
        The blocks of sample points, in order. That order is the flattening
        order of every array compared against this grid.
    """

    schema_id: str = Field(alias="schema")
    name: str
    margin_nm: float = DEFAULT_MARGIN_NM
    patches: list[ProbePatch]

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _one_patch_at_least_with_distinct_names(self) -> ProbeDocument:
        """Reject an empty grid, a non-positive margin or two patches of one name."""
        if not self.patches:
            raise ValueError(f"probe grid {self.name!r} declares no patches, so it samples nothing")
        if not self.margin_nm > 0.0:
            raise ValueError(
                f"probe grid {self.name!r} declares margin_nm = {self.margin_nm}; the mask margin "
                "is what keeps the domain mask off the boundary-resolution lottery and must be "
                "positive"
            )
        seen: dict[str, None] = {}
        for patch in self.patches:
            if patch.name in seen:
                raise ValueError(
                    f"probe grid {self.name!r} declares two patches named {patch.name!r}; the "
                    "patch name is the export contract's file name and must be unique"
                )
            seen[patch.name] = None
        self._check_disjoint()
        return self

    def _check_disjoint(self) -> None:
        """Reject two patches that sample the same point.

        The norms of section 2 of the WP13 plan weight each point by its own
        patch's ``dr dz``, which is a midpoint rule *within* a patch. A point
        carried by two patches would enter both sums, giving it a weight no
        patch declares and one nobody reading the document could predict. Two
        patches may be adjacent or nested in extent; they may not share a point.
        """
        import numpy as np

        points = np.vstack([patch.points_nm() for patch in self.patches])
        # Rounded to 1e-9 nm before the uniqueness test: the axes are built by
        # ``linspace``, so two patches meant to share a coordinate agree to
        # round-off rather than exactly.
        unique, counts = np.unique(np.round(points, 9), axis=0, return_counts=True)
        shared = counts > 1
        if bool(shared.any()):
            worst = unique[int(np.argmax(shared))]
            raise ValueError(
                f"probe grid {self.name!r} samples {int(shared.sum())} point(s) twice, one at "
                f"(r, z) = ({worst[0]:.6g}, {worst[1]:.6g}) nm. Each point's norm weight is its "
                "own patch's dr dz, so a shared point would enter the sum twice at a weight no "
                "patch declares; patches may nest or abut, but must not share a point"
            )

    def patch(self, name: str) -> ProbePatch:
        """Return one patch by name.

        Raises
        ------
        ProbeGridError
            If no patch carries that name; the message lists the ones that do.
        """
        for patch in self.patches:
            if patch.name == name:
                return patch
        known = ", ".join(repr(entry.name) for entry in self.patches)
        raise ProbeGridError(f"probe grid {self.name!r} has no patch {name!r}; it has {known}")

    @property
    def count(self) -> int:
        """Total number of probe points across every patch."""
        return sum(patch.count for patch in self.patches)

    def points_nm(self) -> np.ndarray:
        """Return every probe point as ``(count, 2)``, patch by patch in order."""
        import numpy as np

        return np.vstack([patch.points_nm() for patch in self.patches])

    def weights_nm2(self) -> np.ndarray:
        """Return each point's midpoint-rule weight ``dr dz``, in nm^2.

        Uniform within a patch and different between patches, which is what lets
        a 0.005 nm near-axis line and a 1 nm reservoir block enter one norm
        without the fine patch dominating it by sample count alone.
        """
        import numpy as np

        return np.concatenate(
            [np.full(patch.count, patch.weight_nm2, dtype=np.float64) for patch in self.patches]
        )

    def patch_of_point(self) -> tuple[str, ...]:
        """Return the owning patch's name for each point, in flattening order."""
        names: list[str] = []
        for patch in self.patches:
            names.extend([patch.name] * patch.count)
        return tuple(names)

    def summary(self) -> dict[str, object]:
        """Return the document's record, for the hash and the manifest (FR-25)."""
        return {
            "name": self.name,
            "margin_nm": self.margin_nm,
            "patches": [patch.summary() for patch in self.patches],
        }

    @property
    def hash(self) -> str:
        """Content hash of this probe grid; the ``probe_hash`` of every golden."""
        return content_hash(PROBE_SCHEMA, self.summary())

    def write_comsol_axes(self) -> str:
        """Return the ``%Grid`` axis lines the author pastes into COMSOL.

        One block per patch: the file name the export contract expects, then the
        ``r`` and ``z`` axes in **metres**, which is the unit a ``%Grid`` header
        carries and the unit :func:`~nanopnp.density.grid.read_grid` converts
        back from. Emitting them from the document rather than having the author
        type extents is the point: a hand-entered axis is a silently moved
        sample point, and the ``probe_hash`` in the manifest would not catch it
        because the document did not change.
        """
        lines = [
            f"# Probe grid {self.name!r} ({PROBE_SCHEMA}), hash {self.hash}",
            "# Axes in metres, as a %Grid header carries them. One COMSOL Grid",
            "# evaluation per patch per field; see docs/validation/comsol-export-contract.md.",
        ]
        for patch in self.patches:
            r_axis, z_axis = patch.axes_nm()
            lines.append("")
            lines.append(f"# patch {patch.name!r}: n_r = {patch.n_r}, n_z = {patch.n_z}")
            lines.append(" ".join(f"{value * COMSOL_LENGTH_SCALE_M:.17g}" for value in r_axis))
            lines.append(" ".join(f"{value * COMSOL_LENGTH_SCALE_M:.17g}" for value in z_axis))
        return "\n".join(lines) + "\n"


def loads_probe(text: str, *, source: str = "<string>") -> ProbeDocument:
    """Validate a probe document from YAML text.

    Parameters
    ----------
    text
        The document.
    source
        Name used in diagnostics.

    Raises
    ------
    CaseValidationError
        If the schema string is wrong or the document does not validate — the
        same exception, and the same IF-02 exit class, as a bad case or sweep
        file, all three being IF-03 configuration documents a person writes.
    """
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise CaseValidationError(f"{source} is not valid YAML: {error}") from None
    if not isinstance(parsed, dict):
        found = type(parsed).__name__
        raise CaseValidationError(
            f"{source} holds a {found} at the top level, not a probe document"
        )
    declared = parsed.get("schema")
    if declared != PROBE_SCHEMA:
        raise CaseValidationError(
            f"{source} declares schema {declared!r}; this build reads {PROBE_SCHEMA!r}"
        )
    try:
        return ProbeDocument.model_validate(parsed)
    except ValidationError as error:
        raise CaseValidationError(render_problems(source, error), error) from None


def load_probe(path: str | Path) -> ProbeDocument:
    """Read and validate a probe document.

    Parameters
    ----------
    path
        The YAML probe file.

    Returns
    -------
    ProbeDocument
        Validated, and carrying the :attr:`~ProbeDocument.hash` every golden
        manifest declares.
    """
    source = Path(path)
    return loads_probe(source.read_text(encoding="utf-8"), source=str(source))


@dataclass(frozen=True)
class ProbeGrid:
    """A probe document bound to a mesh: the points, and which of them each field keeps.

    Parameters
    ----------
    document
        The grid that was sampled.
    points_nm
        ``(n, 2)`` in the document's flattening order.
    weights_nm2
        ``(n,)`` midpoint weights.
    masks
        Field name to a boolean ``(n,)`` array: ``True`` where the point and all
        four of its ``+-margin_nm`` neighbours lie in that field's materials.
    dropped
        Field name to the number of points the margin rule removed that the bare
        point test would have kept. Recorded because it is the number that says
        whether the margin is doing anything, and a reader who never sees it
        cannot tell a well-placed grid from one hugging the wall.

    Notes
    -----
    Built through :meth:`on_mesh`. The masks are a property of the *geometry*,
    not of a solution, so one grid serves every rung of the attribution ladder —
    which is what makes the ladder's telescoping identity meaningful.
    """

    document: ProbeDocument
    points_nm: np.ndarray
    weights_nm2: np.ndarray
    masks: Mapping[str, np.ndarray]
    dropped: Mapping[str, int]

    @classmethod
    def on_mesh(
        cls, document: ProbeDocument, mesh: Mesh, domains: Mapping[str, str | None]
    ) -> ProbeGrid:
        """Return ``document``'s points with one mask per field of ``domains``.

        Parameters
        ----------
        document
            The probe grid.
        mesh
            The deployed mesh, in nm coordinates.
        domains
            Field name to the material-name regular expression that field is
            solved on — :attr:`nanopnp.physics.models.Field.domain` — or
            ``None`` for the whole of Omega. Taken from the model rather than
            restated in the probe document, so a probe grid cannot disagree with
            the physics about where a field exists.

        Raises
        ------
        ProbeGridError
            If a patch, grown by the margin, leaves the mesh's bounding box, or
            if a regular expression matches no material of this mesh. Both are
            configuration errors that would otherwise present as a mask of
            zeros, which reads as "this field is nowhere" rather than as "this
            grid is in the wrong place" (QR-12).
        """
        import numpy as np

        points = document.points_nm()
        cls._check_within(document, mesh)
        margin = document.margin_nm
        masks: dict[str, np.ndarray] = {}
        dropped: dict[str, int] = {}
        for field, pattern in domains.items():
            indicator = cls._indicator(mesh, pattern, field)
            bare = cls._inside(mesh, indicator, points)
            keep = bare.copy()
            for offset in ((margin, 0.0), (-margin, 0.0), (0.0, margin), (0.0, -margin)):
                shifted = points + np.asarray(offset, dtype=np.float64)
                # PHY-01: the half-plane's r = -d is the same point as r = +d,
                # so the axial neighbour is mirrored rather than clipped away.
                shifted[:, 0] = np.abs(shifted[:, 0])
                keep &= cls._inside(mesh, indicator, shifted)
            masks[field] = keep
            dropped[field] = int(np.count_nonzero(bare & ~keep))
        return cls(
            document=document,
            points_nm=points,
            weights_nm2=document.weights_nm2(),
            masks=masks,
            dropped=dropped,
        )

    @staticmethod
    def _check_within(document: ProbeDocument, mesh: Mesh) -> None:
        """Refuse a patch that, grown by the margin, leaves the mesh's bounding box."""
        import numpy as np

        vertices = np.array([vertex.point for vertex in mesh.vertices], dtype=np.float64)
        low, high = vertices.min(axis=0), vertices.max(axis=0)
        margin = document.margin_nm
        for patch in document.patches:
            # The radial lower bound is mirrored, not grown: r = 0 is the axis
            # and its neighbour at -margin is the point at +margin.
            wanted = (
                (max(patch.r_nm[0] - margin, 0.0), patch.r_nm[1] + margin),
                (patch.z_nm[0] - margin, patch.z_nm[1] + margin),
            )
            for axis, (index, (want_low, want_high)) in zip("rz", enumerate(wanted), strict=True):
                if want_low < low[index] or want_high > high[index]:
                    raise ProbeGridError(
                        f"patch {patch.name!r} of probe grid {document.name!r} needs "
                        f"{axis} in [{want_low:.6g}, {want_high:.6g}] nm once grown by the "
                        f"{margin:g} nm mask margin, and this mesh spans "
                        f"[{low[index]:.6g}, {high[index]:.6g}] nm. A probe point outside the "
                        "mesh has no material, so the field's mask would silently lose it"
                    )

    @staticmethod
    def _indicator(mesh: Mesh, pattern: str | None, field: str) -> Expression:
        """Return a piecewise-constant 1/0 coefficient for one field's materials.

        Piecewise constant on purpose: evaluating it anywhere strictly inside an
        element returns that element's own value exactly, so the mask is a
        statement about which element a point is in and never about an
        interpolant between two.
        """
        import ngsolve as ngs

        names = mesh.GetMaterials()
        if pattern is None:
            return ngs.CF(1.0)
        mask = mesh.Materials(pattern).Mask()
        keep = [name for name, flag in zip(names, mask, strict=True) if flag]
        if not keep:
            raise ProbeGridError(
                f"field {field!r} is declared on materials {pattern!r}, which matches none of "
                f"this mesh's {', '.join(repr(name) for name in names)}. Every probe point would "
                "be masked out and the field would read as absent rather than as misconfigured"
            )
        return mesh.MaterialCF(dict.fromkeys(keep, 1.0), default=0.0)

    @staticmethod
    def _inside(mesh: Mesh, indicator: Expression, points: np.ndarray) -> np.ndarray:
        """Return whether each point lies in the indicator's materials.

        A point outside the mesh entirely raises out of NGSolve's point search
        rather than returning a value, so the batch evaluation falls back to a
        per-point one and records the miss as "outside", which is what it is.
        The bounding-box gate above is what makes that path rare enough to cost
        nothing.
        """
        import numpy as np

        try:
            sampled = np.asarray(indicator(mesh(points[:, 0], points[:, 1])), dtype=np.float64)
        except Exception:  # NGSolve raises a bare NgException for a point it cannot find
            values = np.zeros(points.shape[0], dtype=np.float64)
            for index, (r_nm, z_nm) in enumerate(points):
                try:
                    values[index] = float(indicator(mesh(r_nm, z_nm)))
                except Exception:  # outside the mesh is outside every material
                    continue
            sampled = values
        return sampled.reshape(points.shape[0]) > 0.5
