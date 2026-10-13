"""The ``nanopnp/probe/v0.5`` comparison surface: where Tier 3 samples both solutions."""

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

PROBE_SCHEMA = "nanopnp/probe/v0.5"

DEFAULT_MARGIN_NM = 0.05

COMSOL_LENGTH_SCALE_M = 1e-9


class ProbeGridError(ValueError): ...


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProbePatch(_Strict):
    name: str
    r_nm: tuple[float, float]
    z_nm: tuple[float, float]
    n_r: int
    n_z: int

    @model_validator(mode="after")
    def _ascending_and_not_square(self) -> ProbePatch:
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
        return (
            (self.r_nm[1] - self.r_nm[0]) / (self.n_r - 1),
            (self.z_nm[1] - self.z_nm[0]) / (self.n_z - 1),
        )

    @property
    def weight_nm2(self) -> float:
        dr, dz = self.spacing_nm
        return dr * dz

    @property
    def count(self) -> int:
        return self.n_r * self.n_z

    def axes_nm(self) -> tuple[np.ndarray, np.ndarray]:
        import numpy as np

        return (
            np.linspace(self.r_nm[0], self.r_nm[1], self.n_r, dtype=np.float64),
            np.linspace(self.z_nm[0], self.z_nm[1], self.n_z, dtype=np.float64),
        )

    def points_nm(self) -> np.ndarray:
        import numpy as np

        r_axis, z_axis = self.axes_nm()
        r_grid, z_grid = np.meshgrid(r_axis, z_axis, indexing="xy")
        return np.column_stack((r_grid.ravel(), z_grid.ravel()))

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "r_nm": list(self.r_nm),
            "z_nm": list(self.z_nm),
            "n_r": self.n_r,
            "n_z": self.n_z,
        }


class ProbeDocument(_Strict):
    schema_id: str = Field(alias="schema")
    name: str
    margin_nm: float = DEFAULT_MARGIN_NM
    patches: list[ProbePatch]

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="after")
    def _one_patch_at_least_with_distinct_names(self) -> ProbeDocument:
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
        for patch in self.patches:
            if patch.name == name:
                return patch
        known = ", ".join(repr(entry.name) for entry in self.patches)
        raise ProbeGridError(f"probe grid {self.name!r} has no patch {name!r}; it has {known}")

    @property
    def count(self) -> int:
        return sum(patch.count for patch in self.patches)

    def points_nm(self) -> np.ndarray:
        import numpy as np

        return np.vstack([patch.points_nm() for patch in self.patches])

    def weights_nm2(self) -> np.ndarray:
        import numpy as np

        return np.concatenate(
            [np.full(patch.count, patch.weight_nm2, dtype=np.float64) for patch in self.patches]
        )

    def patch_of_point(self) -> tuple[str, ...]:
        names: list[str] = []
        for patch in self.patches:
            names.extend([patch.name] * patch.count)
        return tuple(names)

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "margin_nm": self.margin_nm,
            "patches": [patch.summary() for patch in self.patches],
        }

    @property
    def hash(self) -> str:
        return content_hash(PROBE_SCHEMA, self.summary())

    def write_comsol_axes(self) -> str:
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
    source = Path(path)
    return loads_probe(source.read_text(encoding="utf-8"), source=str(source))


@dataclass(frozen=True)
class ProbeGrid:
    document: ProbeDocument
    points_nm: np.ndarray
    weights_nm2: np.ndarray
    masks: Mapping[str, np.ndarray]
    bare: Mapping[str, np.ndarray]
    dropped: Mapping[str, int]

    def band(self, field: str) -> np.ndarray:
        import numpy as np

        band: np.ndarray = np.asarray(self.bare[field], dtype=bool) & ~np.asarray(
            self.masks[field], dtype=bool
        )
        return band

    @classmethod
    def on_mesh(
        cls, document: ProbeDocument, mesh: Mesh, domains: Mapping[str, str | None]
    ) -> ProbeGrid:
        import numpy as np

        points = document.points_nm()
        cls._check_within(document, mesh)
        margin = document.margin_nm
        masks: dict[str, np.ndarray] = {}
        bares: dict[str, np.ndarray] = {}
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
            bares[field] = bare
            dropped[field] = int(np.count_nonzero(bare & ~keep))
        return cls(
            document=document,
            points_nm=points,
            weights_nm2=document.weights_nm2(),
            masks=masks,
            bare=bares,
            dropped=dropped,
        )

    @staticmethod
    def _check_within(document: ProbeDocument, mesh: Mesh) -> None:
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
                if not want_low >= low[index] or not want_high <= high[index]:
                    raise ProbeGridError(
                        f"patch {patch.name!r} of probe grid {document.name!r} needs "
                        f"{axis} in [{want_low:.6g}, {want_high:.6g}] nm once grown by the "
                        f"{margin:g} nm mask margin, and this mesh spans "
                        f"[{low[index]:.6g}, {high[index]:.6g}] nm. A probe point outside the "
                        "mesh has no material, so the field's mask would silently lose it"
                    )

    @staticmethod
    def _indicator(mesh: Mesh, pattern: str | None, field: str) -> Expression:
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
        import numpy as np
        from netgen.meshing import NgException

        try:
            sampled = np.asarray(indicator(mesh(points[:, 0], points[:, 1])), dtype=np.float64)
        except NgException:  # NGSolve raises a bare NgException for a point it cannot find
            values = np.zeros(points.shape[0], dtype=np.float64)
            for index, (r_nm, z_nm) in enumerate(points):
                try:
                    values[index] = float(indicator(mesh(r_nm, z_nm)))
                except NgException as error:
                    # Outside the mesh is outside every material; any other
                    # failure is a defect, and reading it as "outside" would
                    # empty the mask and report agreement over nothing.
                    if "not in mesh" not in str(error):
                        raise
            sampled = values
        return sampled.reshape(points.shape[0]) > 0.5
