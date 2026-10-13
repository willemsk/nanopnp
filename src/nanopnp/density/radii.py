"""The stage-2 radius set: CHARMM van der Waals radii by residue and atom."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from nanopnp.core.hashing import file_hash
from nanopnp.core.paths import radii_file

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

RADII_SCHEMA = "nanopnp/radii/v0.5"

KERNEL_RADII: Mapping[str, str] = {"gaussian_vdw": "pdb2pqr_charmm"}

ANGSTROM_TO_NM = 0.1

WILDCARD = "*"


class DensityInputError(ValueError): ...


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RadiusSource(_Strict):
    file: str
    package: str
    version: str
    sha256: str
    licence: str
    notice: str


class RadiusRules(_Strict):
    residue_aliases: dict[str, str] = Field(default_factory=dict)
    ambiguous: dict[str, list[str]] = Field(default_factory=dict)
    atom_aliases: dict[str, dict[str, str]] = Field(default_factory=dict)
    patches: dict[str, list[str]] = Field(default_factory=dict)


class RadiusSet(_Strict):
    schema_: Literal["nanopnp/radii/v0.5"] = Field(alias="schema")
    name: str
    source: RadiusSource
    units: Literal["angstrom"]
    quantity: str
    rules: RadiusRules
    residues: dict[str, dict[str, float]]

    @classmethod
    def load(cls, name: str) -> RadiusSet:
        text = radii_file(name).read_text(encoding="utf-8")
        return cls.model_validate(yaml.safe_load(text))

    def radius_A(self, resname: str, atom: str) -> float:
        rules = self.rules
        residue = rules.residue_aliases.get(resname, resname)
        names = [atom]
        alias = rules.atom_aliases.get(residue, {}).get(atom) or rules.atom_aliases.get(
            WILDCARD, {}
        ).get(atom)
        if alias is not None:
            names.append(alias)
        members = rules.ambiguous.get(residue, [residue])
        if not any(member in self.residues for member in members):
            # Before the patches, which name backbone atoms every residue has.
            raise KeyError(f"the {self.name} set has no residue {resname}")
        groups = [
            members,
            rules.patches.get(residue, rules.patches.get(WILDCARD, [])),
        ]
        for group in groups:
            for name in names:
                found = {
                    member: self.residues[member][name]
                    for member in group
                    if name in self.residues.get(member, {})
                }
                if not found:
                    continue
                if len(set(found.values())) > 1:
                    listed = ", ".join(f"{member} {value} Å" for member, value in found.items())
                    raise KeyError(
                        f"{resname} {atom} is ambiguous in the {self.name} set: {listed}. A "
                        "radius the residue names disagree on is not chosen for them; name the "
                        "protonation state (HSD, HSE, HSP or HID, HIE, HIP) in the structure file"
                    )
                radius = next(iter(found.values()))
                if not radius > 0.0:
                    raise KeyError(
                        f"{resname} {atom} has radius {radius} Å in the {self.name} set, and a "
                        "zero-width kernel deposits nothing"
                    )
                return radius
        raise KeyError(
            f"the {self.name} set names no radius for {resname} {atom}, by residue, histidine "
            "name, atom alias or terminal patch, and there is no fallback by element"
        )


@dataclass(frozen=True)
class ResolvedRadii:
    radii_nm: np.ndarray
    name: str
    sha256: str


def radius_set_digest(name: str) -> str:
    return file_hash(radii_file(name))


def resolve_radii(
    name: str,
    *,
    resname: np.ndarray,
    atom: np.ndarray,
    chain: np.ndarray,
    resid: np.ndarray,
    icode: np.ndarray,
) -> ResolvedRadii:
    import numpy as np

    radius_set = RadiusSet.load(name)
    pairs = np.char.add(np.char.add(resname.astype(str), "\t"), atom.astype(str))
    unique, first_seen, inverse = np.unique(pairs, return_index=True, return_inverse=True)
    radii_A = np.empty(len(unique), dtype=np.float64)
    # In order of first appearance, so the atom refused is the first in the file.
    for index in np.argsort(first_seen, kind="stable").tolist():
        residue, _, name_ = str(unique[index]).partition("\t")
        try:
            radii_A[index] = radius_set.radius_A(residue, name_)
        except KeyError as error:
            first = int(first_seen[index])
            number = f"{int(resid[first])}{str(icode[first]).strip()}"
            raise DensityInputError(
                f"stage 2 cannot place atom {name_!r} of residue {residue} {number} in chain "
                f"{str(chain[first])!r}: {error.args[0]} (section 5.3.1 NOTE on geometry.density)"
            ) from None
    return ResolvedRadii(
        radii_nm=radii_A[inverse.reshape(-1)] * ANGSTROM_TO_NM,
        name=radius_set.name,
        sha256=radius_set_digest(name),
    )
