"""The axial force on an embedded analyte by three routes (NUM-28, NUM-29)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nanopnp.core.typing import (
    AssembledForm,
    Expression,
    GridFunction,
    Mesh,
    Numeric,
    Option,
)
from nanopnp.geometry.analyte import ANALYTE_BOUNDARY
from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
)
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.numerics.measures import Measures, require_boundary
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.coupled import BODY_FORCE, DIELECTRIC_FORCE, term
from nanopnp.physics.distance import wall_distance
from nanopnp.physics.kernel import Context, force_density
from nanopnp.physics.models import (
    ModelSolution,
    TransportModel,
    transport_model,
)
from nanopnp.post.indicator import smoothstep
from nanopnp.post.qoi import TWO_PI
from nanopnp.post.reaction_flux import boundary_reaction_flux

if TYPE_CHECKING:
    from nanopnp.mesh.adapter import MeshData

__all__ = [
    "FORCE_ROUTE_TOLERANCE_N",
    "AnalyteForces",
    "ExtensionError",
    "ForceAgreement",
    "ForceComponents",
    "ForceDisagreementError",
    "ForceSurfaceError",
    "axial_extension",
    "check_extension",
    "check_force_surface",
    "domain_force",
    "electrostatic_domain_force",
    "electrostatic_surface_force",
    "extract",
    "hydrodynamic_stress",
    "maxwell_stress",
    "reaction_force",
    "surface_force",
]

logger = logging.getLogger(__name__)

# NUM-29's 0.1 pN, absolute: the total is a small difference of two large forces
# (knowledge/06-numerics-fem/16-tier-2-test-evidence-ladder-walks-block.md).
FORCE_ROUTE_TOLERANCE_N = 1.0e-13


class ExtensionError(ValueError):
    """``w`` is not the smooth extension of ``e_z`` the force needs."""


class ForceDisagreementError(RuntimeError):
    """Two force routes disagree beyond tolerance, so no force is reported."""


class ForceSurfaceError(ValueError):
    """The force surface does not lie between one pair of materials all along it."""


def axial_extension(  # noqa: PLR0913
    mesh: Mesh,
    *,
    inner_nm: float,
    outer_nm: float,
    order: int = 2,
    fluid: str = ELECTROLYTE_DOMAINS,
    body: str = ANALYTE_BOUNDARY,
    axis: str = "axis",
    distance_nm: GridFunction | None = None,
    check: bool = True,
) -> GridFunction:
    """Return ``w``: ``e_z`` within ``inner_nm`` of the body, 0 beyond ``outer_nm``.

    Parameters
    ----------
    inner_nm, outer_nm
        Transition shell ends, in nm from the body; ``inner_nm`` exceeds the element size.
    body
        Boundary-name regular expression of the analyte surface.
    axis
        Boundary name of the symmetry axis, excluded from the zero check.
    check
        Whether to verify the result with ``check_extension``.
    """
    import ngsolve as ngs

    if not outer_nm > inner_nm:
        raise ExtensionError(
            f"the transition shell must have positive width, got inner={inner_nm} nm and "
            f"outer={outer_nm} nm"
        )
    if not inner_nm >= 0.0:
        raise ExtensionError(f"inner_nm must not be negative, got {inner_nm} nm")

    if distance_nm is None:
        distance_nm = wall_distance(
            mesh,
            body,
            order=order,
            diffusion_length_nm=(outer_nm - inner_nm) / 4.0,
            max_distance_nm=2.0 * outer_nm,
        )
    space = ngs.VectorH1(mesh, order=order, definedon=mesh.Materials(fluid))
    extension = ngs.GridFunction(space, name="w")
    profile = 1.0 - smoothstep(distance_nm, lower_nm=inner_nm, upper_nm=outer_nm)
    extension.Set(ngs.CF((0.0, profile)))
    if check:
        check_extension(extension, mesh, body=body, axis=axis, fluid=fluid)
    return extension


def _outer_boundaries(mesh: Mesh, body: str, axis: str, fluid: str) -> str:
    on_body = mesh.Boundaries(body).Mask()
    on_axis = mesh.Boundaries(axis).Mask()
    fluid_mask = mesh.Materials(fluid).Mask()
    # ``domin``/``domout`` are 1-based material numbers, 0 meaning the outside;
    # the descriptors are in the order of ``GetBoundaries``.
    descriptors = list(mesh.ngmesh.EdgeDescriptors())

    def _interior_to_the_fluid(index: int) -> bool:
        descriptor = descriptors[index]
        return all(
            side > 0 and fluid_mask[side - 1] for side in (descriptor.domin, descriptor.domout)
        )

    names = sorted(
        {
            name
            for index, name in enumerate(mesh.GetBoundaries())
            if not on_body[index] and not on_axis[index] and not _interior_to_the_fluid(index)
        }
    )
    return "|".join(names)


def check_extension(
    extension: GridFunction,
    mesh: Mesh,
    *,
    body: str = ANALYTE_BOUNDARY,
    axis: str = "axis",
    fluid: str = ELECTROLYTE_DOMAINS,
    tolerance: float = 1e-12,
) -> None:
    """Assert that ``w`` is ``e_z`` on the body and zero on other boundaries.

    Raises
    ------
    ExtensionError
        If either condition fails.
    """
    import ngsolve as ngs

    def _mean_square(target: Expression, boundary: str) -> float:
        require_boundary(mesh, boundary, error=ExtensionError)
        region = mesh.Boundaries(boundary)
        length = float(ngs.Integrate(ngs.CF(1.0), mesh, definedon=region))
        if not length > 0.0:
            # A named boundary that carries no segment passes the mask but has nothing to average.
            raise ExtensionError(f"the boundary {boundary!r} has no length in this mesh")
        difference = extension - ngs.CF(target)
        deviation = float(
            ngs.Integrate(ngs.InnerProduct(difference, difference), mesh, definedon=region)
        )
        return deviation / length

    outer = _outer_boundaries(mesh, body, axis, fluid)
    on_body = _mean_square((0.0, 1.0), body)
    on_outer = _mean_square((0.0, 0.0), outer) if outer else 0.0
    if not on_body <= tolerance or not on_outer <= tolerance:
        raise ExtensionError(
            f"w must be e_z on {body!r} and zero on {outer!r}; the mean-square departures are "
            f"{on_body:.3e} and {on_outer:.3e} against a tolerance of {tolerance:.3e}. An "
            "inverted shell returns the force on the reservoir and a shell wider than the "
            "domain returns zero, neither with any other symptom. If only the body fails, "
            "inner_nm is smaller than the element size there"
        )
    logger.debug("w is e_z on %r and 0 on %r: %.2e, %.2e", body, outer, on_body, on_outer)


def maxwell_stress(potential_gradient: Expression, permittivity: Numeric) -> Expression:
    """Return the in-plane Maxwell stress ``eps (E x E - 1/2 |E|^2 I)``.

    Parameters
    ----------
    permittivity
        ``eps~_r`` in the fluid; the solid's own permittivity never enters.
    """
    import ngsolve as ngs

    field = potential_gradient
    return permittivity * (
        ngs.OuterProduct(field, field) - 0.5 * ngs.InnerProduct(field, field) * ngs.Id(2)
    )


def hydrodynamic_stress(
    velocity_gradient: Expression, pressure: Expression, viscosity: Numeric
) -> Expression:
    """Return the in-plane hydrodynamic stress ``-p I + 2 eta sym grad(u)``."""
    import ngsolve as ngs

    strain = 0.5 * (velocity_gradient + velocity_gradient.trans)
    return -pressure * ngs.Id(2) + 2.0 * viscosity * strain


def electrostatic_domain_force(
    mesh: Mesh,
    potential_gradient: Expression,
    permittivity: Numeric,
    extension: GridFunction,
    measures: Measures,
    *,
    force_N: float,
    fluid: str = ELECTROLYTE_DOMAINS,
) -> float:
    """Return the electrostatic force on the body from the domain integral, in newtons."""
    import ngsolve as ngs

    stress = maxwell_stress(potential_gradient, permittivity)
    work = measures.integrate(
        ngs.InnerProduct(stress, ngs.grad(extension)),
        mesh,
        definedon=mesh.Materials(fluid),
        what="the Maxwell stress work",
    )
    return -TWO_PI * force_N * work


def electrostatic_surface_force(
    mesh: Mesh,
    potential_gradient: Expression,
    permittivity: Numeric,
    measures: Measures,
    *,
    force_N: float,
    boundary: str = ANALYTE_BOUNDARY,
    piecewise_permittivity: Numeric | None = None,
) -> float:
    """Return the electrostatic force on the body from its surface traction, in newtons.

    Parameters
    ----------
    piecewise_permittivity
        Permittivity over Omega, if it jumps across the surface; enables a fluid-side check.

    Raises
    ------
    ValueError
        If the boundary matches nothing or the normal's orientation is undetermined.
    """
    import ngsolve as ngs

    region, arc = _boundary_region(mesh, boundary)
    lift = ngs.BoundaryFromVolumeCF
    fluid_permittivity = lift(permittivity)
    if piecewise_permittivity is not None:
        _check_fluid_side(mesh, lift(piecewise_permittivity), fluid_permittivity, region, arc)
    normal = _oriented_normal(mesh, region, arc)
    stress = maxwell_stress(lift(potential_gradient), fluid_permittivity)
    traction = measures.integrate(
        (stress * normal)[1], mesh, definedon=region, what="the Maxwell surface traction"
    )
    return TWO_PI * force_N * traction


@dataclass(frozen=True)
class ForceComponents:
    """The axial force on the body, split into its two origins, in newtons."""

    em_N: float
    hd_N: float

    @property
    def total_N(self) -> float:
        """The net axial force, the electrostatic and hydrodynamic parts summed."""
        return self.em_N + self.hd_N

    def summary(self) -> dict[str, float]:
        """Return the three numbers, for logs and the manifest."""
        return {
            "electromagnetic_N": self.em_N,
            "hydrodynamic_N": self.hd_N,
            "total_N": self.total_N,
        }


@dataclass(frozen=True)
class ForceAgreement:
    """How far apart the force routes are on one solution."""

    domain: ForceComponents
    surface: ForceComponents
    reaction_hd_N: float | None = None

    @property
    def total_difference_N(self) -> float:
        """``|F_tot(A) - F_tot(B)|``, the domain route against the surface route."""
        return abs(self.domain.total_N - self.surface.total_N)

    @property
    def hydrodynamic_difference_N(self) -> float:
        """``|F^hd(A) - F^hd(C)|``, the split against its oracle; 0 without the third route."""
        if self.reaction_hd_N is None:
            return 0.0
        return abs(self.domain.hd_N - self.reaction_hd_N)

    def check(self, tolerance_N: float = FORCE_ROUTE_TOLERANCE_N) -> None:
        """Assert the routes agree within tolerance; ForceDisagreementError otherwise."""
        total = self.total_difference_N
        hydrodynamic = self.hydrodynamic_difference_N
        if total <= tolerance_N and hydrodynamic <= tolerance_N:
            logger.debug(
                "force routes agree: total %.3e N, hydrodynamic %.3e N", total, hydrodynamic
            )
            return
        if self.reaction_hd_N is None:
            reaction = "not taken"
        else:
            reaction = f"{self.reaction_hd_N * 1e12:+.4f}"
        raise ForceDisagreementError(
            "the NUM-28 force routes disagree beyond the NUM-29 tolerance of "
            f"{tolerance_N * 1e12:.4f} pN. Domain (A): F^em = "
            f"{self.domain.em_N * 1e12:+.4f} pN, F^hd = {self.domain.hd_N * 1e12:+.4f} pN, "
            f"total {self.domain.total_N * 1e12:+.4f} pN. Surface (B): F^em = "
            f"{self.surface.em_N * 1e12:+.4f} pN, F^hd = {self.surface.hd_N * 1e12:+.4f} pN, "
            f"total {self.surface.total_N * 1e12:+.4f} pN. Reaction (C): F^hd = "
            f"{reaction} pN. The differences are {total * 1e12:.4f} pN on the total and "
            f"{hydrodynamic * 1e12:.4f} pN on the hydrodynamic split. A disagreement on the "
            "split alone points at a missing or mis-signed body-force consistency term; the "
            "net force is a small difference of two large ones and an error in either flips "
            "the trapping landscape (RSK-04)"
        )

    def summary(self) -> dict[str, Option]:
        """Return every route and both differences, for the manifest."""
        return {
            "domain": self.domain.summary(),
            "surface": self.surface.summary(),
            "reaction_hydrodynamic_N": self.reaction_hd_N,
            "total_difference_N": self.total_difference_N,
            "hydrodynamic_difference_N": self.hydrodynamic_difference_N,
        }


@dataclass(frozen=True)
class AnalyteForces:
    """The force on one body, in SI units, with its route record."""

    forces: ForceComponents
    dielectric_gradient_N: float
    agreement: ForceAgreement | None

    @property
    def total_N(self) -> float:
        """The net axial force, in newtons."""
        return self.forces.total_N

    def summary(self) -> dict[str, Option]:
        """Return every quantity, for logs and the provenance manifest."""
        record: dict[str, Option] = {
            **self.forces.summary(),
            # The PHY-23 term the validated model omits, already inside ``electromagnetic_N``.
            "dielectric_gradient_N": self.dielectric_gradient_N,
            "two_pi_included": True,
            "routes_checked": self.agreement is not None,
        }
        if self.agreement is not None:
            record["route_agreement"] = self.agreement.summary()
        return record


# -- the three routes --------------------------------------------------------


def _coupled(solution: ModelSolution) -> TransportModel:
    model = transport_model(solution)
    if not model.flow:
        raise TypeError(
            f"{model.name!r} solves no flow block, so it has no hydrodynamic force to report; "
            "NUM-28 splits the force into an electromagnetic and a hydrodynamic half and "
            "reporting the second as zero would claim a computed result"
        )
    return model


@dataclass(frozen=True)
class _Integrands:
    model: TransportModel
    mesh: Mesh
    context: Context
    potential_gradient: Expression
    velocity_gradient: Expression
    pressure: Expression
    viscosity: Expression
    permittivity: Expression
    medium_permittivity: Expression

    @property
    def coefficients(self) -> NondimensionalCoefficients:
        return self.context.trial.coefficients

    def work(self, density: Expression | None, extension: GridFunction, what: str) -> float:
        import ngsolve as ngs

        if density is None:
            return 0.0
        return self.context.measures.integrate(
            ngs.InnerProduct(density, extension),
            self.mesh,
            definedon=self.context.fluid,
            what=what,
        )

    def omits_the_dielectric_force(self) -> bool:
        return all(each.name != DIELECTRIC_FORCE for each in self.context.terms)


def _integrands(
    solution: ModelSolution, measures: Measures, wall_distance_nm: Expression | None
) -> _Integrands:
    import ngsolve as ngs

    model = _coupled(solution)
    mesh = solution.space.mesh
    functions = {field.name: solution.component(field.name) for field in model.fields}
    distance = solution.wall_distance_nm if wall_distance_nm is None else wall_distance_nm
    context = model.context(
        mesh,
        measures,
        trial=functions,
        wall_distance_nm=distance,
        solid_fraction=solution.solid_fraction,
        solid_fraction_gradient=solution.solid_fraction_gradient,
    )
    # The force blends wherever a solid fraction is given, the dielectric switch on or off.
    solid = model.solid_blend(mesh, solution.solid_fraction, solution.solid_fraction_gradient)
    context = replace(context, inputs=replace(context.inputs, solid=solid))
    coefficients = context.trial.coefficients
    permittivity = coefficients.relative_permittivity()
    # The Maxwell stress takes the permittivity Poisson was solved with: the blend where a
    # solid fraction reaches into the electrolyte. Any other leaves a force the split omits.
    medium = (
        permittivity
        if solid is None
        else model.permittivity(mesh, coefficients, solid_fraction=solution.solid_fraction)
    )
    velocity = functions[VELOCITY]
    return _Integrands(
        model=model,
        mesh=mesh,
        context=context,
        potential_gradient=ngs.grad(functions[POTENTIAL]),
        velocity_gradient=ngs.grad(velocity),
        pressure=functions[PRESSURE],
        viscosity=coefficients.viscosity(),
        permittivity=permittivity,
        medium_permittivity=medium,
    )


def _density(name: str, context: Context) -> Expression | None:
    force = term(name).force
    if force is None:
        raise RuntimeError(f"the term {name!r} states no force density")
    return force(context, context.trial)


def domain_force(
    solution: ModelSolution,
    measures: Measures,
    extension: GridFunction,
    *,
    wall_distance_nm: Expression | None = None,
) -> ForceComponents:
    """Return the force on the body from the domain route, in newtons."""
    return _domain_force(_integrands(solution, measures, wall_distance_nm), extension)[0]


def _dielectric_work(terms: _Integrands, extension: GridFunction) -> float:
    return terms.work(
        _density(DIELECTRIC_FORCE, terms.context),
        extension,
        "the dielectric-gradient consistency term",
    )


def _domain_force(terms: _Integrands, extension: GridFunction) -> tuple[ForceComponents, float]:
    import ngsolve as ngs

    mesh, model, context = terms.mesh, terms.model, terms.context
    scale = TWO_PI * model.scales.force_N

    ionic_work = terms.work(
        _density(BODY_FORCE, context), extension, "the ionic body-force consistency term"
    )
    dielectric_work = _dielectric_work(terms, extension)
    em_N = electrostatic_domain_force(
        mesh,
        terms.potential_gradient,
        terms.medium_permittivity,
        extension,
        context.measures,
        force_N=model.scales.force_N,
        fluid=model.fluid,
    )
    em_N -= scale * (ionic_work + dielectric_work)

    hydro = hydrodynamic_stress(terms.velocity_gradient, terms.pressure, terms.viscosity)
    hd = -context.measures.integrate(
        ngs.InnerProduct(hydro, ngs.grad(extension)),
        mesh,
        definedon=context.fluid,
        what="the hydrodynamic stress work",
    )
    hd += terms.work(
        force_density(context, context.trial), extension, "the body-force consistency term"
    )

    forces = ForceComponents(em_N=em_N, hd_N=scale * hd)
    logger.debug("domain force (pN): %s", {k: v * 1e12 for k, v in forces.summary().items()})
    return forces, dielectric_work


def dielectric_gradient_residual(
    solution: ModelSolution,
    measures: Measures,
    extension: GridFunction,
    *,
    wall_distance_nm: Expression | None = None,
) -> float:
    """Return the dielectric-gradient term the model omits, in newtons; zero if enabled."""
    return _dielectric_gradient_residual(
        _integrands(solution, measures, wall_distance_nm), extension
    )


def _dielectric_gradient_residual(
    terms: _Integrands, extension: GridFunction, *, work: float | None = None
) -> float:
    if not terms.omits_the_dielectric_force():
        return 0.0
    if work is None:
        work = _dielectric_work(terms, extension)
    return -TWO_PI * terms.model.scales.force_N * work


def surface_force(
    solution: ModelSolution,
    measures: Measures,
    *,
    boundary: str = ANALYTE_BOUNDARY,
    wall_distance_nm: Expression | None = None,
) -> ForceComponents:
    """Return the traction integral over the body's surface, in newtons."""
    return _surface_force(_integrands(solution, measures, wall_distance_nm), boundary)


def _surface_force(terms: _Integrands, boundary: str) -> ForceComponents:
    import ngsolve as ngs

    mesh, model, measures = terms.mesh, terms.model, terms.context.measures
    region, arc = _boundary_region(mesh, boundary)

    lift = ngs.BoundaryFromVolumeCF
    normal = _oriented_normal(mesh, region, arc)
    hydro = hydrodynamic_stress(
        lift(terms.velocity_gradient), lift(terms.pressure), lift(terms.viscosity)
    )
    scale = TWO_PI * model.scales.force_N
    forces = ForceComponents(
        em_N=electrostatic_surface_force(
            mesh,
            terms.potential_gradient,
            terms.permittivity,
            measures,
            force_N=model.scales.force_N,
            boundary=boundary,
            piecewise_permittivity=model.permittivity(mesh, terms.coefficients),
        ),
        hd_N=scale
        * measures.integrate(
            (hydro * normal)[1],
            mesh,
            definedon=region,
            what="the hydrodynamic surface traction",
        ),
    )
    logger.debug("surface force (pN): %s", {k: v * 1e12 for k, v in forces.summary().items()})
    return forces


def _boundary_region(mesh: Mesh, boundary: str) -> tuple[Option, float]:
    import ngsolve as ngs

    require_boundary(mesh, boundary)
    region = mesh.Boundaries(boundary)
    arc = float(ngs.Integrate(ngs.CF(1.0), mesh, definedon=region))
    if not arc > 0.0:
        raise ValueError(f"the boundary {boundary!r} has no length in this mesh")
    return region, arc


def _check_fluid_side(
    mesh: Mesh, piecewise: Expression, fluid: Expression, region: Option, arc: float
) -> None:
    import ngsolve as ngs

    departure = float(ngs.Integrate((piecewise - fluid) ** 2, mesh, definedon=region)) / arc
    reference = float(ngs.Integrate(fluid**2, mesh, definedon=region)) / arc
    if not departure <= 1e-4 * max(reference, 1.0):
        raise ValueError(
            "the boundary lift is evaluating the analyte surface on the solid side: the "
            f"piecewise permittivity there departs from the fluid's by {departure:.3e} in mean "
            f"square against {reference:.3e}. The traction would then be the body's own stress "
            "rather than the medium's, wrong by the whole dielectric contrast"
        )


def _oriented_normal(mesh: Mesh, region: Option, arc: float) -> Expression:
    import ngsolve as ngs

    normal = ngs.specialcf.normal(2)
    position = ngs.CF((ngs.x, ngs.y))
    centroid = ngs.CF(
        tuple(
            float(ngs.Integrate(component, mesh, definedon=region)) / arc
            for component in (ngs.x, ngs.y)
        )
    )
    radial = position - centroid
    sense = float(ngs.Integrate(ngs.InnerProduct(normal, radial), mesh, definedon=region)) / arc
    span = float(ngs.Integrate(ngs.sqrt(ngs.InnerProduct(radial, radial)), mesh, definedon=region))
    if not abs(sense) >= 0.1 * span / arc:
        raise ValueError(
            f"cannot orient the normal on this surface: the mean of n.(x - c) is {sense:.3e} "
            f"against a mean radius of {span / arc:.3e}. The surface is not star-shaped about "
            "its own centroid, and an unoriented normal negates the force with no other symptom"
        )
    return normal if sense > 0.0 else -normal


_FLUID = re.compile(ELECTROLYTE_DOMAINS)


def _one_fluid(sides: set[str]) -> tuple[str, ...]:
    # electrolyte, cis and trans are three names for one fluid, so a surface meeting two of them
    # meets one material and is orientable; the names are compared after the side beyond the
    # domain has been settled, or a fluid on both sides would read as an outer boundary.
    canonical = {"electrolyte" if _FLUID.fullmatch(name) else name for name in sides}
    return tuple(sorted(canonical))


def check_force_surface(data: MeshData, boundary: str = ANALYTE_BOUNDARY) -> tuple[str, str]:
    """Return the material pair on the two sides of the force surface; refuse a surface of several.

    Parameters
    ----------
    data
        The mesh the surface belongs to.
    boundary
        Boundary-name regular expression of the surface.

    Raises
    ------
    ForceSurfaceError
        If no boundary matches, or the edges meet more than one pair of materials; the side
        beyond the domain counts as ``outside``, and the fluid's several domain names count as
        one material.
    """
    import numpy as np

    wanted = [i for i, name in enumerate(data.boundaries) if re.fullmatch(boundary, name)]
    if not wanted:
        known = ", ".join(sorted(data.boundaries))
        raise ForceSurfaceError(f"no boundary matching {boundary!r} in this mesh; it has {known}")
    count = data.vertices.shape[0]

    def keyed(ends: np.ndarray) -> np.ndarray:
        # One integer per undirected edge, so a boundary edge and an element's edge compare.
        low = np.minimum(ends[:, 0], ends[:, 1])
        keys: np.ndarray = low * count + np.maximum(ends[:, 0], ends[:, 1])
        return keys

    surface = np.unique(keyed(data.edges[np.isin(data.edge_group, wanted)]))
    if surface.size == 0:
        raise ForceSurfaceError(
            f"the force surface {boundary!r} names a boundary of this mesh that carries no edge, "
            "so there is no surface to take the traction on"
        )
    triangles = data.triangles
    element_keys = keyed(
        np.concatenate((triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]))
    )
    owners = np.tile(data.triangle_material, 3)
    # Matched in one pass over the elements rather than one Python loop per element edge.
    place = np.searchsorted(surface, element_keys)
    on_surface = (place < surface.size) & (
        surface[np.minimum(place, surface.size - 1)] == element_keys
    )
    # Sorted by (edge, material), so one edge's materials are contiguous and repeats collapse.
    touching = np.unique(np.stack((place[on_surface], owners[on_surface]), axis=1), axis=0)
    edges_met, met = np.unique(touching[:, 0], return_counts=True)

    pairs: dict[tuple[str, ...], int] = {}
    at = 0
    for number in met.tolist():
        names = {data.materials[int(index)] for index in touching[at : at + number, 1]}
        at += number
        # One material means the other side is outside the domain, as an outer boundary is.
        pair = _one_fluid(names if len(names) == 2 else names | {"outside"})
        pairs[pair] = pairs.get(pair, 0) + 1
    unowned = int(surface.size) - int(edges_met.size)
    if unowned:
        pairs[("no element",)] = unowned
    if len(pairs) != 1 or ("no element",) in pairs:
        meets = "; ".join(f"{' | '.join(pair)} on {n} edges" for pair, n in sorted(pairs.items()))
        raise ForceSurfaceError(
            f"the force surface {boundary!r} does not lie between one pair of materials: it "
            f"meets {meets or 'nothing'}. The traction normal is oriented by one pair, so part "
            "of the force would be negated with no other symptom; give the body a surface that "
            "touches one fluid domain"
        )
    met_pair = next(iter(pairs))
    # A surface with fluid on both sides meets one material under two names.
    first, second = met_pair if len(met_pair) == 2 else (met_pair[0], met_pair[0])
    return first, second


def reaction_force(
    solution: ModelSolution,
    *,
    boundary: str = ANALYTE_BOUNDARY,
    load_form: AssembledForm | None = None,
) -> float:
    """Return the hydrodynamic force from the assembled residual, the reference route.

    Parameters
    ----------
    boundary
        The body's surface; its velocity degrees of freedom must be constrained.

    Raises
    ------
    ValueError
        If the solution carries no residual form.
    """
    model = _coupled(solution)
    if solution.residual is None:
        raise ValueError(
            "this solution carries no residual form, so the NUM-28 reaction force cannot be "
            "taken from it; solve through the model's own solve, which records it"
        )
    block = [field.name for field in model.fields].index(VELOCITY)
    traction = boundary_reaction_flux(
        solution.residual,
        solution.state,
        boundary,
        component=block,
        value=(0.0, 1.0),
        load_form=load_form,
    )
    force = -TWO_PI * model.scales.force_N * traction
    logger.debug("reaction force (pN): %+.6f", force * 1e12)
    return force


def extract(  # noqa: PLR0913
    solution: ModelSolution,
    measures: Measures,
    extension: GridFunction,
    *,
    boundary: str = ANALYTE_BOUNDARY,
    wall_distance_nm: Expression | None = None,
    load_form: AssembledForm | None = None,
    tolerance_N: float = FORCE_ROUTE_TOLERANCE_N,
    check_routes: bool = True,
    data: MeshData | None = None,
) -> AnalyteForces:
    """Return the force on the body, with every route checked.

    Parameters
    ----------
    boundary
        The body's surface.
    data
        The mesh as ingested; given, the surface is refused unless one pair of materials lies
        on its two sides all along it.
    check_routes
        Whether to check the other two routes; False skips them, a recorded deviation.

    Raises
    ------
    ForceDisagreementError
        If the routes disagree beyond tolerance.
    ForceSurfaceError
        If ``data`` is given and the surface meets more than one pair of materials.
    """
    if data is not None:
        check_force_surface(data, boundary)
    # One rebuild of the coefficients for all three routes.
    terms = _integrands(solution, measures, wall_distance_nm)
    forces, dielectric_work = _domain_force(terms, extension)
    residual = _dielectric_gradient_residual(terms, extension, work=dielectric_work)

    agreement: ForceAgreement | None = None
    if check_routes:
        # Compared uncorrected: each route carries its own tensor's divergence.
        surface = _surface_force(terms, boundary)
        agreement = ForceAgreement(
            domain=forces,
            surface=surface,
            reaction_hd_N=reaction_force(solution, boundary=boundary, load_form=load_form),
        )
        agreement.check(tolerance_N)
    return AnalyteForces(forces=forces, dielectric_gradient_N=residual, agreement=agreement)
