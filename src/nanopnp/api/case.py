"""The case document as a Python object: read, edited by copy, and built from presets."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import PrivateAttr

from nanopnp.core.paths import names_a_path, store_root, structure_file
from nanopnp.io.case import (
    SCHEMA,
    CaseDocument,
    FieldValue,
    _model_of,
    dumps_case,
    read_case_text,
)
from nanopnp.io.case_paths import (
    UnknownCasePathError,
    _entry_annotation,
    correction_paths,
    field_at,
    field_path,
    input_paths,
    substitute,
    value_at,
)
from nanopnp.io.defaults import VALIDATED_DEFAULT_CASE
from nanopnp.materials.corrections import load_corrections
from nanopnp.mesh.defaults import (
    DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
    DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
    DEFAULT_CYLINDER_WALL_H_NM,
    DEFAULT_MAXH_NM,
    DEFAULT_PORE_RADIUS_NM,
)
from nanopnp.pipeline.checks import check_document
from nanopnp.structure.orient import prepared_pore

__all__ = ["DEFAULT_OUTPUTS", "Case"]

DEFAULT_OUTPUTS: tuple[str, ...] = ("current", "transport_numbers", "eof_rate")

_ORIENT_KEYS = ("chains", "cis_end", "registration_residues", "centroid_z_nm")


class Case(CaseDocument):
    """A validated case file, edited by copy and run by a :class:`Session`.

    A ``Case`` holds the same blocks as the case file and refuses assignment: ``with_`` returns
    an edited copy. A field is named by its dotted case-file path (``boundary_conditions.bias_V``)
    or, where one field or block ends in the name, by that name alone (``bias_V``).
    """

    _path: Path | None = PrivateAttr(default=None)
    _text: str | None = PrivateAttr(default=None)
    _base: Path | None = PrivateAttr(default=None)

    @classmethod
    def load(cls, path: str | Path, *, base: str | Path | None = None) -> Case:
        """Read a case file; a relative path it names is read beside it.

        Parameters
        ----------
        base
            The directory to read relative paths against instead of the file's own.
        """
        source = Path(path)
        text = source.read_bytes().decode("utf-8")
        case = cls.loads(
            text, base=source.resolve().parent if base is None else base, source=str(source)
        )
        case._path = source
        return case

    @classmethod
    def loads(cls, text: str, *, base: str | Path | None = None, source: str = "<string>") -> Case:
        """Read a case from its text.

        Parameters
        ----------
        base
            The directory a relative path of the case is read against; the working directory
            when ``None``.
        """
        case = check_document(read_case_text(text, source=source, model=cls), source=source)
        assert isinstance(case, cls)
        case._text = text
        case._base = Path(base).resolve() if base is not None else None
        return case

    def __eq__(self, other: object) -> bool:
        """Compare the documents; the text and file a case was read from do not count."""
        if not isinstance(other, CaseDocument):
            return NotImplemented
        return self.model_dump() == other.model_dump()

    def __hash__(self) -> int:
        """Hash the document as it is dumped."""
        return hash(self.dumps())

    def dump(self, path: str | Path) -> Path:
        """Write the case to ``path`` as YAML and return it."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.dumps(), encoding="utf-8")
        return target

    def dumps(self) -> str:
        """Return the case as YAML text, under the keys a case file writes."""
        return dumps_case(self)

    def __getitem__(self, name: str) -> FieldValue:
        """Return the value of one field or block of the case."""
        return value_at(self, field_path(name))

    def with_(self, edits: Mapping[str, FieldValue] | None = None, /, **named: FieldValue) -> Case:
        """Return a copy with these fields set; CaseValidationError if one is refused.

        A value that is a block replaces the block whole. A mapping given for a block sets the
        leaves it names and creates the block if the case has none. The copy keeps no file of
        its own: a run of it records the case as text in memory.

        Parameters
        ----------
        edits
            Fields by dotted path or name, for a name that is not a Python identifier.
        """
        given = {**(edits or {}), **named}
        if len(given) != len(edits or {}) + len(named):
            repeated = ", ".join(sorted(set(edits or {}) & set(named)))
            raise ValueError(f"{repeated} is given both in the mapping and by keyword")
        assignments: dict[str, FieldValue] = {}
        for name, value in given.items():
            self._assign(field_path(name), value, assignments)
        source = f"<{self.name} edited>"
        edited = check_document(substitute(self, assignments), source=source)
        assert isinstance(edited, Case)
        edited._base = self._base
        # After the caller's edits, not before: a path an edit names is read beside the case
        # the edit came from, as every path the case already named is.
        rebased = _rebased_paths(edited, self._base)
        if rebased:
            edited = check_document(substitute(edited, rebased), source=source)
            assert isinstance(edited, Case)
            edited._base = self._base
        return edited

    def _absent(self, path: str) -> bool:
        try:
            return value_at(self, path) is None
        except UnknownCasePathError:
            return True

    def _assign(self, path: str, value: FieldValue, found: dict[str, FieldValue]) -> None:
        parts = path.split(".")
        for depth in range(1, len(parts)):
            prefix = ".".join(parts[:depth])
            if self._absent(prefix):
                nested = value
                for part in reversed(parts[depth:]):
                    nested = {part: nested}
                found[prefix] = _merged(found.get(prefix), nested)
                return
        reference = field_at(path)
        is_block = _entry_annotation(reference.annotation) is None and (
            _model_of(reference.annotation) is not None
        )
        if not (is_block and isinstance(value, Mapping)):
            found[path] = value
        elif self._absent(path):
            found[path] = _merged(found.get(path), dict(value))
        else:
            for key, item in value.items():
                self._assign(f"{path}.{key}", item, found)

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
        wall_charge_C_m2: float = 0.0,
        maxh_nm: float = DEFAULT_MAXH_NM,
        wall_h_nm: float | Literal["auto"] = DEFAULT_CYLINDER_WALL_H_NM,
        outputs: Sequence[str] = DEFAULT_OUTPUTS,
        name: str = "cylinder",
    ) -> Case:
        """Build a case of a cylindrical pore on the validated ePNP-NS model.

        Parameters
        ----------
        charge
            A field document (``field1``) of the fixed charge; an uncharged pore when ``None``.
        parameters
            The correction parameter file every correction and the membrane permittivity are
            read from.
        wall_charge_C_m2
            The surface charge of the pore wall.
        maxh_nm, wall_h_nm
            The element sizes of the mesh stage 6 makes; ``"auto"`` sizes the wall layer by the
            Debye length.
        """
        boundary: dict[str, Any] = {"bias_V": bias_V, "ground": "cis"}
        if wall_charge_C_m2:
            boundary["wall_charge_C_m2"] = wall_charge_C_m2
        inputs: dict[str, Any] = {}
        if charge is not None:
            inputs["charge"] = {"path": str(Path(charge).resolve()), "format": "field1"}
        document = {
            "schema": SCHEMA,
            "name": name,
            "inputs": inputs,
            "geometry": {
                "pore": {"shape": "cylinder", "radius_nm": pore_radius_nm},
                "membrane": {"thickness_nm": membrane_thickness_nm},
                "reservoir": {"radius_nm": reservoir_radius_nm},
            },
            "electrolyte": _electrolyte(parameters, concentration_M),
            "boundary_conditions": boundary,
            "physics": {
                "model": VALIDATED_DEFAULT_CASE.physics.model,
                "solid_permittivities": {
                    "membrane": load_corrections(parameters).dielectrics.membrane
                },
            },
            "numerics": {"mesh": {"maxh_nm": maxh_nm, "wall_h_nm": wall_h_nm}},
            "outputs": list(outputs),
        }
        return _built(cls, document, name)

    @classmethod
    def from_structure(
        cls,
        source: str | Path,
        *,
        point_group: str,
        concentration_M: float,
        bias_V: float,
        orient: Mapping[str, Any] | None = None,
        structures: str | Path | None = None,
        chains: str = "all",
        parameters: str = "willems2020_nacl",
        size_scale: float = 1.0,
        outputs: Sequence[str] = DEFAULT_OUTPUTS,
        name: str | None = None,
    ) -> Case:
        """Build a case of a structure's pore, charged from it, on the validated ePNP-NS model.

        Parameters
        ----------
        source
            A PDB or mmCIF file whose pore axis is z, or the name of a shipped structure.
        point_group
            The pore's symmetry, ``C<n>``.
        orient
            Keywords of ``orient_pore`` (``chains``, ``cis_end``, ``registration_residues``,
            ``centroid_z_nm``): the structure is oriented first, into ``structures``, and the
            case reads the oriented file.
        structures
            Where an oriented file is written; the store's ``structures`` directory when ``None``.
        parameters
            The correction parameter file every correction and both solid permittivities are
            read from.
        size_scale
            ``numerics.mesh.size_scale``: below 1 refines every element size.
        """
        unknown = sorted(set(orient or {}) - set(_ORIENT_KEYS))
        if unknown:
            raise TypeError(
                f"orient names {', '.join(unknown)}, which orient_pore does not take; "
                f"it takes {', '.join(_ORIENT_KEYS)}"
            )
        origin = Path(source)
        path = (origin if origin.is_file() else structure_file(str(source))).resolve()
        if orient is not None:
            path = prepared_pore(
                path,
                directory=Path(structures) if structures else store_root() / "structures",
                **orient,
            )
        label = name if name is not None else path.name.split(".")[0]
        dielectrics = load_corrections(parameters).dielectrics
        document = {
            "schema": SCHEMA,
            "name": label,
            "structure": {
                "source": {"path": str(path.resolve()), "chains": chains},
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
        return _built(cls, document, label)


def _rebased_paths(case: CaseDocument, base: Path | None) -> dict[str, FieldValue]:
    if base is None:
        return {}
    return {
        dotted: str((base / value).resolve())
        for dotted, value in {**input_paths(case), **correction_paths(case)}.items()
        if not Path(value).is_absolute()
    }


def _merged(first: FieldValue, second: FieldValue) -> FieldValue:
    if isinstance(first, dict) and isinstance(second, dict):
        merged = dict(first)
        for key, value in second.items():
            merged[key] = _merged(merged.get(key), value) if key in merged else value
        return merged
    return second


def _electrolyte(parameters: str, concentration_M: float) -> dict[str, Any]:
    corrections = load_corrections(parameters)
    # As the factory treats charge and source: resolved here, where the caller's working
    # directory is the one the name was written against, so the case runs from any folder.
    parameters = str(Path(parameters).resolve()) if names_a_path(parameters) else parameters
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


def _built(cls: type[Case], document: dict[str, Any], name: str) -> Case:
    return cls.loads(json.dumps(document), source=f"<case {name!r}>")
