"""The outputs registry: what a run can report, and what each quantity needs of a model (MOD-09)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeAlias

from nanopnp.core.hashing import Canonicalisable
from nanopnp.geometry.analyte import ANALYTE_BOUNDARY, ANALYTE_DOMAIN
from nanopnp.mesh.adapter import MeshData
from nanopnp.post import forces as force_post

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.numerics.measures import Measures
    from nanopnp.physics.models import ModelDeclaration, ModelSolution
    from nanopnp.post.qoi import QuantitiesOfInterest

__all__ = [
    "EXTENSION_INNER",
    "EXTENSION_OUTER",
    "Extraction",
    "Need",
    "Output",
    "SelectionError",
    "extension_shell",
    "output",
    "provided",
    "registered_outputs",
]

EXTENSION_INNER = 1.2

EXTENSION_OUTER = 3.0

Need: TypeAlias = Literal["transport", "flow"]

Extractor: TypeAlias = Callable[["Extraction"], Mapping[str, Canonicalisable]]

KeyParameters: TypeAlias = Callable[
    [MeshData, Mapping[str, Canonicalisable]], Mapping[str, Canonicalisable]
]


class SelectionError(ValueError):
    """A word in ``outputs:`` that this run cannot produce; a ValueError."""


@dataclass(frozen=True)
class Extraction:
    """What stage 11 hands each output: the solution and the one shared extraction result."""

    solution: ModelSolution
    measures: Measures
    data: MeshData
    bias_V: float
    band_nm: tuple[float, float]
    quantities: QuantitiesOfInterest
    parameters: Mapping[str, Canonicalisable]


@dataclass(frozen=True)
class Output:
    """One selectable quantity and what it needs of a model."""

    name: str
    needs: frozenset[Need]
    extract: Extractor | None = None
    parameters: KeyParameters | None = None
    export: bool = False
    refusal: str | None = None


_REGISTRY: dict[str, Output] = {}


def register_output(
    name: str,
    *,
    needs: frozenset[Need] | set[Need] = frozenset(),
    extract: Extractor | None = None,
    parameters: KeyParameters | None = None,
    export: bool = False,
    refusal: str | None = None,
) -> None:
    """Register an output under ``name``; ValueError if the name is taken.

    Parameters
    ----------
    needs
        What a model must declare to offer it: ``transport``, ``flow``, or neither.
    extract
        Stage 11's reading of the quantity from an :class:`Extraction`.
    parameters
        The stage-11 key parameters it adds, from the mesh and the stage's options.
    export
        Whether stage 12 writes it to a file.
    refusal
        Set to refuse the output at one operating point, with this reason.
    """
    if name in _REGISTRY:
        raise ValueError(f"the output {name!r} is already registered")
    _REGISTRY[name] = Output(
        name=name,
        needs=frozenset(needs),
        extract=extract,
        parameters=parameters,
        export=export,
        refusal=refusal,
    )


def registered_outputs() -> tuple[str, ...]:
    """Return the registered output names, sorted."""
    return tuple(sorted(_REGISTRY))


def output(name: str) -> Output:
    """Return the output registered as ``name``; KeyError naming the registered ones."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"no output is registered as {name!r}; the outputs are "
            f"{', '.join(registered_outputs())}"
        ) from None


def provided(declaration: ModelDeclaration) -> tuple[str, ...]:
    """Return the outputs a model declaration offers: those whose needs it meets."""
    offered: set[str] = set()
    if declaration.transport:
        offered.add("transport")
    if True in declaration.switches["flow"]:
        offered.add("flow")
    return tuple(sorted(name for name, found in _REGISTRY.items() if found.needs <= offered))


def extension_shell(data: MeshData, *, material: str = ANALYTE_DOMAIN) -> tuple[float, float]:
    """Return the extension shell in nm, scaled to the body; SelectionError if absent."""
    import numpy as np

    if material not in data.materials:
        known = ", ".join(data.materials) or "none"
        raise SelectionError(
            f"outputs asks for analyte_force, which requires the mesh to carry an {material!r} "
            f"material; this mesh has {known}. The NUM-28 force is a force *on a body*, and "
            "there is none in this domain to take it on"
        )
    index = data.materials.index(material)
    selected = data.triangles[data.triangle_material == index]
    points = data.vertices[np.unique(selected)]
    radial = float(points[:, 0].max())
    axial = 0.5 * float(points[:, 1].max() - points[:, 1].min())
    semi_axis = max(radial, axial)
    return (EXTENSION_INNER * semi_axis, EXTENSION_OUTER * semi_axis)


def _shell(data: MeshData, options: Mapping[str, Canonicalisable]) -> tuple[float, float]:
    supplied = options.get("extension_shell_nm")
    if supplied is None:
        return extension_shell(data)
    inner, outer = supplied
    return (float(inner), float(outer))


def _picking(*keys: str) -> Extractor:
    wanted = frozenset(keys)

    def pick(extraction: Extraction) -> Mapping[str, Canonicalisable]:
        record = extraction.quantities.summary()
        return {key: value for key, value in record.items() if key in wanted}

    return pick


def _force_parameters(
    data: MeshData, options: Mapping[str, Canonicalisable]
) -> Mapping[str, Canonicalisable]:
    return {"extension_shell_nm": list(_shell(data, options))}


def _force(extraction: Extraction) -> Mapping[str, Canonicalisable]:
    shell = extraction.parameters["extension_shell_nm"]
    inner, outer = shell
    extension = force_post.axial_extension(
        extraction.solution.space.mesh,
        inner_nm=inner,
        outer_nm=outer,
        order=extraction.measures.element_order,
    )
    record: dict[str, Canonicalisable] = force_post.extract(
        extraction.solution,
        extraction.measures,
        extension,
        boundary=ANALYTE_BOUNDARY,
        data=extraction.data,
    ).summary()
    return {"analyte_force": record, "extension_shell_nm": shell}


register_output(
    "current",
    needs={"transport"},
    extract=_picking("current_A", "currents_A", "conductance_S"),
)
register_output(
    "transport_numbers",
    needs={"transport"},
    extract=_picking("transport_number", "currents_A"),
)
register_output("eof_rate", needs={"transport", "flow"}, extract=_picking("eof_m3_s"))
register_output(
    "rectification",
    needs={"transport"},
    refusal=(
        "outputs asks for rectification, which is the two-point ratio I(+V)/I(-V); this run "
        "has one operating point. The second bias can only come from a sweep (FR-24), and "
        "inventing one would report a ratio the run did not measure"
    ),
)
register_output(
    "analyte_force",
    needs={"transport", "flow"},
    extract=_force,
    parameters=_force_parameters,
)
register_output("fields", export=True)
