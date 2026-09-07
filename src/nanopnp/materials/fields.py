"""The supplied dielectric field: a solid fraction, and the blend it drives.

§4.4's NOTE settles what an ``inputs.eps_r`` field is. PHY-20 requires the
transition **to** ``eps_w``, and ``eps_w = eps_r,f0 * eps_r,f^c(<c>)`` is a
function of the solved concentration, so a static ``eps_r`` field cannot express
it: accepting one would silently disable the permittivity correction while the
run continued to report ePNP-NS. A supplied field is therefore a solid fraction
``chi in [0, 1]`` and the permittivity is

``eps_r = chi * eps_p + (1 - chi) * eps_r,f(<c>)``

with the 1-2 Angstrom transition carried by ``chi`` alone. Setting ``chi`` to the
sharp material indicator reproduces PHY-20's piecewise assignment exactly, which
is what makes the smoothed field a refinement of the validated model rather than
a replacement for it — and is the Tier-1 assertion of VER-30.

The header document is :class:`~nanopnp.charge.fields.FieldDocument`, imported
rather than duplicated: one header shape for every quantity keeps the units, the
grid descriptor and the unknown-key rejection in one place, and a second schema
for the dielectric would be a second place for them to drift.

Two gates, both aimed at the failure that actually happens — a field written with
``r`` and ``z`` transposed, or with its sense inverted. Neither is a sampled
check: the range gate is taken on the grid, where it *proves* the mesh statement
rather than testing it at chosen points (see :meth:`SolidFractionField.check_range`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.fields import (
    ChargeFieldError,
    FieldDocument,
    FieldDocumentError,
    load_document,
    load_grid,
)
from nanopnp.core.typing import Expression, Mesh
from nanopnp.density.grid import RadialGrid, coefficient

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Iterable, Sequence

    from nanopnp.physics.measures import Measures

SOLID_FRACTION = "solid_fraction"
"""The one quantity an ``inputs.eps_r`` field may declare (§5.3.1 NOTE)."""

SOLID_MEAN_FLOOR = 0.9
"""Least mean ``chi`` over a material the blend sends to ``eps_p``."""

FLUID_MEAN_CEILING = 0.1
"""Greatest mean ``chi`` over a material the blend sends to ``eps_r,f(<c>)``.

An inverted or grossly misregistered field fails these two by construction,
while a 1-2 Angstrom transition moves neither mean by more than a per cent: the
transition is a shell a couple of element widths thick around a body many
nanometres across.
"""


@dataclass(frozen=True)
class MaterialMean:
    """The mean of ``chi`` over one material, and which branch it should take."""

    material: str
    mean: float
    branch: str
    """``"solid"`` or ``"fluid"``: which side of the blend this material takes."""

    @property
    def within(self) -> bool:
        """Whether the mean is on the side of the threshold its branch requires."""
        if self.branch == "solid":
            return self.mean >= SOLID_MEAN_FLOOR
        return self.mean <= FLUID_MEAN_CEILING

    def summary(self) -> dict[str, object]:
        """Return this mean as plain data, for the FR-25 manifest."""
        return {"material": self.material, "mean": self.mean, "branch": self.branch}


@dataclass(frozen=True)
class SolidFractionField:
    """A supplied solid fraction, ready to blend onto a mesh.

    Parameters
    ----------
    document
        The validated header.
    grid
        Its grid: dimensionless values in ``[0, 1]``.
    source
        The header document's path, for provenance.
    """

    document: FieldDocument
    grid: RadialGrid
    source: Path

    def __post_init__(self) -> None:
        """Refuse a quantity that is not a solid fraction.

        Raises
        ------
        FieldDocumentError
            Naming §4.4's NOTE. An absolute ``eps_r`` never reaches here — the
            header document refuses that quantity by name — so what this catches
            is a *charge* field supplied under ``inputs.eps_r``, which would put
            C m^-2 where a dimensionless fraction belongs.
        """
        if self.document.quantity != SOLID_FRACTION:
            raise FieldDocumentError(
                f"inputs.eps_r names quantity {self.document.quantity!r}; a dielectric field "
                f"supplies {SOLID_FRACTION!r}, a fraction in [0, 1] the solver blends as "
                "eps_r = chi * eps_p + (1 - chi) * eps_r,f(<c>) (§4.4 NOTE)"
            )

    def chi(self) -> Expression:
        """Return the solid fraction as a coefficient function of the mesh.

        Zero outside the grid box, which is the fluid branch: a mesh reaching
        beyond the supplied field is electrolyte there, and continuing by the
        box's edge value would paint a 250 nm reservoir with whatever the grid
        happened to end on (§5.3.1 NOTE).
        """
        return coefficient(self.grid)

    def check_range(self) -> None:
        """Abort unless ``0 <= chi <= 1`` everywhere on the deployed mesh (VER-30).

        Taken on the grid samples, and that is stronger than sampling the mesh:
        bilinear interpolation is a convex combination of the four surrounding
        samples and the padding ring is zero, so an interpolant whose samples all
        lie in ``[0, 1]`` lies in ``[0, 1]`` at every point of every element
        [verified]. A gate evaluated at quadrature points could only ever miss.

        Raises
        ------
        ChargeFieldError
            Naming the offending value and its ``(r, z)`` (QR-12).
        """
        import numpy as np

        values = self.grid.values
        outside = (values < 0.0) | (values > 1.0)
        if not bool(outside.any()):
            return
        flat = np.where(outside, np.abs(values - 0.5), -1.0)
        i_z, i_r = np.unravel_index(int(np.argmax(flat)), values.shape)
        raise ChargeFieldError(
            "the supplied solid fraction leaves [0, 1]",
            f"chi = {float(values[i_z, i_r]):.6g} at the worst of "
            f"{int(outside.sum())} samples. A solid fraction is a blend weight, so a value "
            "outside [0, 1] extrapolates the permittivity beyond both branches (§4.4 NOTE)",
            f"(r, z) = ({float(self.grid.r_nm[i_r]):.4g}, {float(self.grid.z_nm[i_z]):.4g}) nm",
        )

    def material_means(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        """Return the mean of ``chi`` over every material of ``mesh``.

        Parameters
        ----------
        mesh
            The deployed mesh.
        measures
            The quadrature policy; the mean carries the same ``r`` weight the
            forms do, so it is a volume average and not an area one.
        solids
            The materials the blend sends to ``eps_p`` — the keys of
            ``physics.solid_permittivities``. Everything else takes the fluid
            branch, ``exclusion`` included: it is a solid for Nernst-Planck and
            the flow and takes the *fluid's* ``eps_r`` for Poisson (§5.3.1
            NOTE), so a water-filled shell with ``chi`` near zero is exactly
            right there.
        """
        import ngsolve as ngs

        solid_set = set(solids)
        chi = self.chi()
        means: list[MaterialMean] = []
        for material in sorted(set(mesh.GetMaterials())):
            region = mesh.Materials(material)
            volume = measures.integrate(
                ngs.CF(1.0), mesh, definedon=region, what=f"the volume of {material!r}"
            )
            if volume <= 0.0:  # pragma: no cover - an empty material cannot be selected
                continue
            total = measures.integrate(
                chi, mesh, definedon=region, what=f"the solid fraction over {material!r}"
            )
            means.append(
                MaterialMean(
                    material=material,
                    mean=total / volume,
                    branch="solid" if material in solid_set else "fluid",
                )
            )
        return tuple(means)

    def check_materials(
        self, mesh: Mesh, measures: Measures, *, solids: Iterable[str]
    ) -> tuple[MaterialMean, ...]:
        """Abort unless every material's mean ``chi`` matches its branch (VER-30).

        Returns
        -------
        tuple of MaterialMean
            Every mean, so a caller can record them whether or not they passed.

        Raises
        ------
        ChargeFieldError
            Reporting both numbers — the mean found and the threshold its branch
            requires — for every material that failed. An inverted field fails
            this on every material at once, which is what the message should say.
        """
        means = self.material_means(mesh, measures, solids=solids)
        failed = [mean for mean in means if not mean.within]
        if not failed:
            return means
        needs = {
            "solid": f">= {SOLID_MEAN_FLOOR:g}",
            "fluid": f"<= {FLUID_MEAN_CEILING:g}",
        }
        rendered = ", ".join(
            f"{mean.material!r} averages chi = {mean.mean:.4g} and takes the {mean.branch} "
            f"branch, which needs {needs[mean.branch]}"
            for mean in failed
        )
        raise ChargeFieldError(
            "the supplied solid fraction does not register with the mesh's materials",
            f"{rendered}. A field written with r and z transposed, or with its sense inverted, "
            "fails this by construction; a 1-2 Angstrom transition moves no mean by a per cent",
        )


def load_solid_fraction(path: str | Path) -> SolidFractionField:
    """Read a field document and its grid, and return the dielectric field.

    Raises
    ------
    FieldDocumentError
        If the document is invalid, disagrees with its data, or names a quantity
        that is not a solid fraction — an absolute ``eps_r`` field among them,
        refused by the header document with §4.4's reasoning.
    """
    source = Path(path)
    document = load_document(source)
    return SolidFractionField(
        document=document, grid=load_grid(document, base=source.parent), source=source
    )


def blend(
    chi: Expression, solid_permittivity: Expression, fluid_permittivity: Expression
) -> Expression:
    """Return §4.4's dielectric blend, ``chi * eps_p + (1 - chi) * eps_r,f(<c>)``.

    Parameters
    ----------
    chi
        The solid fraction, in ``[0, 1]``.
    solid_permittivity
        The piecewise solid branch — the whole ``MaterialCF`` of
        :meth:`nanopnp.physics.models.CoupledModel.permittivity`, not one
        material's constant, so that a mesh with a protein *and* a membrane
        blends each towards its own ``eps_p``. Where ``chi`` is zero its value
        is irrelevant, which is why its fluid default costs nothing.
    fluid_permittivity
        The corrected ``eps_r,f(<c>)/eps_r,f0`` of PHY-11 and PHY-12.

    Returns
    -------
    Expression
        The blended relative permittivity, nondimensionalised exactly as its two
        arguments are. With the sharp material indicator for ``chi`` this is
        identically the piecewise assignment of PHY-20.
    """
    return chi * solid_permittivity + (1.0 - chi) * fluid_permittivity


def summary(field: SolidFractionField, means: Sequence[MaterialMean]) -> dict[str, object]:
    """Return the FR-25 record of a supplied dielectric field.

    The one place this record is written. :meth:`nanopnp.charge.stage.ResolvedFields.summary`
    adds the header document's own name and digest around it and changes nothing
    inside, so the manifest and the VER-30 assertion read the same dict.
    """
    return {
        **field.document.summary(),
        "grid": field.grid.descriptor(),
        "grid_digest": field.grid.digest(),
        "material_means": [mean.summary() for mean in means],
        "interpolation": "bilinear",
    }
