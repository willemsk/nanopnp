"""A case held for repeated runs with edited values."""

from __future__ import annotations

import difflib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Literal, get_args

from nanopnp.core.hashing import content_hash, short
from nanopnp.core.scaling import debye_length_nm
from nanopnp.io.case import CaseDocument, FieldValue, dumps_case
from nanopnp.io.case_paths import UnknownCasePathError, case_fields, substitute, value_at
from nanopnp.io.defaults import VALIDATED_DEFAULT_CASE
from nanopnp.io.store import Store
from nanopnp.materials.corrections import load_corrections
from nanopnp.mesh.cylinder import mesh_cylinder, mesher_identity
from nanopnp.mesh.defaults import (
    DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
    DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
    DEFAULT_CYLINDER_WALL_H_NM,
    DEFAULT_MAXH_NM,
    DEFAULT_PORE_RADIUS_NM,
)
from nanopnp.mesh.sizing import debye_wall_nm, ionic_strength_of_M
from nanopnp.pipeline.case import load_case, loads_case
from nanopnp.pipeline.run import RunResult, run_document

CYLINDER_MESH_SCHEMA = "nanopnp/mesh/cylinder/v0.5"

DEFAULT_OUTPUTS: tuple[str, ...] = ("current", "transport_numbers", "eof_rate")


@cache
def _path_fields() -> tuple[str, ...]:
    # Every case field that names a file, read off the schema so that a new one is not missed.
    # A relative one is read against the working directory, so Case.load makes each absolute
    # beside the case file.
    return tuple(
        reference.path
        for reference in case_fields()
        if reference.annotation is Path or Path in get_args(reference.annotation)
    )


def field_path(name: str) -> str:
    """Return the dotted case path ``name`` stands for: itself, or the one field it ends."""
    if "." in name:
        return name
    matches = sorted(
        reference.path for reference in case_fields() if reference.path.rsplit(".", 1)[-1] == name
    )
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise UnknownCasePathError(
            f"{name!r} names more than one field: {', '.join(matches)}. Write the dotted path"
        )
    leaves = sorted({reference.path.rsplit(".", 1)[-1] for reference in case_fields()})
    close = difflib.get_close_matches(name, leaves, n=3)
    hint = f" Did you mean {', '.join(map(repr, close))}?" if close else ""
    raise UnknownCasePathError(f"{name!r} is not a field of the case schema.{hint}")


@dataclass(frozen=True)
class Case:
    """A validated case, a store, and the edits to run it with.

    A ``Case`` is immutable: ``with_`` returns an edited copy, and ``run`` runs the case with
    edits that apply to that one run. A field is named by its dotted case-file path
    (``boundary_conditions.bias_V``) or, where one field ends in the name, by that name alone
    (``bias_V``).

    Parameters
    ----------
    document
        The validated case document.
    store
        Where artefacts are cached; the default store when ``None``.
    source
        Where the case was read from, if it was.
    write
        Whether a run writes its run directory.
    """

    document: CaseDocument
    store: Store | None = None
    source: Path | None = None
    write: bool = True

    @classmethod
    def load(
        cls, path: str | Path, *, store: Store | str | Path | None = None, write: bool = True
    ) -> Case:
        """Read a case file, its relative input paths made absolute beside it.

        ``store`` may be a directory.
        """
        source = Path(path).resolve()
        return cls(_rebased(load_case(source), source.parent), _store(store), source, write)

    @classmethod
    def loads(
        cls, text: str, *, store: Store | str | Path | None = None, write: bool = True
    ) -> Case:
        """Read a case from its text."""
        return cls(loads_case(text), _store(store), None, write)

    @classmethod
    def cylinder(
        cls,
        *,
        concentration_M: float,
        bias_V: float,
        pore_radius_nm: float = DEFAULT_PORE_RADIUS_NM,
        membrane_thickness_nm: float = DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
        reservoir_radius_nm: float = DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
        charge: str | Path | None = None,
        parameters: str = "willems2020_nacl",
        maxh_nm: float = DEFAULT_MAXH_NM,
        wall_h_nm: float | Literal["debye"] = DEFAULT_CYLINDER_WALL_H_NM,
        outputs: Sequence[str] = DEFAULT_OUTPUTS,
        name: str = "cylinder",
        store: Store | str | Path | None = None,
        write: bool = True,
    ) -> Case:
        """Build a case of a cylindrical pore on the validated ePNP-NS model, its mesh in the store.

        Parameters
        ----------
        charge
            A field document (``field1``) of the fixed charge; an uncharged pore when ``None``.
        wall_h_nm
            The element size on the pore wall; the default is the mesh command's, coarser than
            NUM-30's first layer at most concentrations. ``"debye"`` sizes it as NUM-30 does,
            ``min(0.05 nm, λ_D/5)`` of this salt at ``ε_r,f0``, so a new concentration above
            about 1.5 M meshes again.
        parameters
            The correction parameter file every correction and the membrane permittivity
            are read from.
        """
        held = _store(store) or Store()
        geometry = {
            "pore_radius_nm": pore_radius_nm,
            "membrane_thickness_nm": membrane_thickness_nm,
            "reservoir_radius_nm": reservoir_radius_nm,
            "maxh_nm": maxh_nm,
            "wall_h_nm": (
                _debye_wall_nm(parameters, concentration_M) if wall_h_nm == "debye" else wall_h_nm
            ),
        }
        key = short(content_hash(CYLINDER_MESH_SCHEMA, geometry, {"mesher": mesher_identity()}), 12)
        mesh = held.root / "meshes" / f"cylinder-{key}.msh"
        if not mesh.is_file():
            mesh.parent.mkdir(parents=True, exist_ok=True)
            mesh_cylinder(**geometry, out=mesh)
        inputs: dict[str, Any] = {
            "mesh": {"path": str(mesh), "format": "msh41", "groups": {"default": "interface"}}
        }
        if charge is not None:
            inputs["charge"] = {"path": str(Path(charge).resolve()), "format": "field1"}
        dielectrics = load_corrections(parameters).dielectrics
        document = {
            "schema": VALIDATED_DEFAULT_CASE.schema_id,
            "name": name,
            "inputs": inputs,
            "electrolyte": _electrolyte(parameters, concentration_M),
            "boundary_conditions": {"bias_V": bias_V, "ground": "cis"},
            "physics": {
                "model": VALIDATED_DEFAULT_CASE.physics.model,
                "solid_permittivities": {"membrane": dielectrics.membrane},
            },
            "outputs": list(outputs),
        }
        return cls(_validated(document, name), held, None, write)

    @classmethod
    def from_structure(
        cls,
        path: str | Path,
        *,
        point_group: str,
        concentration_M: float,
        bias_V: float,
        chains: str = "all",
        parameters: str = "willems2020_nacl",
        size_scale: float = 1.0,
        outputs: Sequence[str] = DEFAULT_OUTPUTS,
        name: str | None = None,
        store: Store | str | Path | None = None,
        write: bool = True,
    ) -> Case:
        """Build a case of a structure's pore, charged from it, on the validated ePNP-NS model.

        Parameters
        ----------
        path
            A PDB or mmCIF file whose pore axis is z, as ``orient_pore`` writes it.
        point_group
            The pore's symmetry, ``C<n>``.
        parameters
            The correction parameter file every correction and both solid permittivities
            are read from.
        size_scale
            ``numerics.mesh.size_scale``: below 1 refines every element size.
        """
        source = Path(path).resolve()
        label = name if name is not None else source.name.split(".")[0]
        dielectrics = load_corrections(parameters).dielectrics
        document = {
            "schema": VALIDATED_DEFAULT_CASE.schema_id,
            "name": label,
            "structure": {
                "source": {"path": str(source), "chains": chains},
                "symmetry": {"point_group": point_group},
            },
            # The defaults, held as a block so that an edit can reach them (with_).
            "geometry": {},
            "charge": {},
            "electrolyte": _electrolyte(parameters, concentration_M),
            "boundary_conditions": {"bias_V": bias_V, "ground": "cis"},
            "physics": {
                "model": VALIDATED_DEFAULT_CASE.physics.model,
                "solid_permittivities": {
                    "protein": dielectrics.protein,
                    "membrane": dielectrics.membrane,
                },
            },
            "numerics": {"mesh": {"size_scale": size_scale}},
            "outputs": list(outputs),
        }
        return cls(_validated(document, label), _store(store) or Store(), None, write)

    def __getitem__(self, name: str) -> FieldValue:
        """Return the value of one field of the case."""
        return value_at(self.document, field_path(name))

    def with_(self, **edits: FieldValue) -> Case:
        """Return a copy with these fields set; CaseValidationError if one is refused."""
        assignments = {field_path(name): value for name, value in edits.items()}
        return Case(substitute(self.document, assignments), self.store, self.source, self.write)

    def run(self, *, upto: str | None = None, only: bool = False, **edits: FieldValue) -> RunResult:
        """Run the case with ``edits`` applied; ``upto`` and ``only`` are ``run_document``'s."""
        edited = self.with_(**edits) if edits else self
        return run_document(
            edited.document,
            case_text=dumps_case(edited.document),
            # The document as held, its paths rebased and its edits applied, is not the file's
            # text, so the run records it as a case in memory.
            case_path=None,
            store=self.store,
            upto=upto,
            only=only,
            write=self.write,
        )


def _electrolyte(parameters: str, concentration_M: float) -> dict[str, Any]:
    corrections = load_corrections(parameters)
    validated = VALIDATED_DEFAULT_CASE.electrolyte
    # The validated model: each correction fitted in the validated file is read from this one.
    choices = validated.corrections.model_dump(by_alias=True, mode="json")
    for choice in choices.values():
        if choice["model"] == validated.parameters:
            choice["model"] = parameters
    return {
        "species": [{"name": key, "z": species.z} for key, species in corrections.species.items()],
        "concentration_M": concentration_M,
        "temperature_K": corrections.temperature_K,
        "parameters": parameters,
        "corrections": choices,
    }


def _debye_wall_nm(parameters: str, concentration_M: float) -> float:
    corrections = load_corrections(parameters)
    debye = debye_length_nm(
        ionic_strength_of_M(
            (species.z for species in corrections.species.values()), concentration_M
        ),
        relative_permittivity=corrections.solvent.permittivity.eps_r0,
        temperature_K=corrections.temperature_K,
    )
    return debye_wall_nm(debye)


def _validated(document: dict[str, Any], name: str) -> CaseDocument:
    return loads_case(json.dumps(document), source=f"<case {name!r}>")


def input_paths(document: CaseDocument) -> dict[str, str]:
    """Return every input file a case names, by dotted case path, as written."""
    payload = document.model_dump(by_alias=True, mode="json")
    found: dict[str, str] = {}
    for dotted in _path_fields():
        cursor: Any = payload
        for part in dotted.split("."):
            cursor = cursor.get(part) if isinstance(cursor, dict) else None
        if isinstance(cursor, str):
            found[dotted] = cursor
    return found


def _rebased(document: CaseDocument, base: Path) -> CaseDocument:
    moved: dict[str, FieldValue] = {
        dotted: str((base / value).resolve())
        for dotted, value in input_paths(document).items()
        if not Path(value).is_absolute()
    }
    return substitute(document, moved) if moved else document


def _store(store: Store | str | Path | None) -> Store | None:
    if store is None or isinstance(store, Store):
        return store
    return Store(store)
