"""The stage-2 radius set: CHARMM van der Waals radii by residue and atom (WP19 D3).

The ``gaussian_vdw`` kernel gives each atom the width ``sigma R_i``, and R_i is its
CHARMM Rmin/2 as PDB2PQR's ``CHARMM.DAT`` lists it. That is an **author ruling of
25 September 2026**: the reference ensemble's per-frame PQR files carry exactly
this set (``.knowledge/04-clya-geometry-and-charge.md`` §1.1). The table is data,
``data/radii/pdb2pqr_charmm.yaml``, transcribed verbatim, and so are the rules
that map a structure file's names onto it.

**There is no fallback by element.** The isolevel contour of an isolated atom sits
at ``1.095 R``, so the pore wall moves one-for-one with a radius, and a guessed one
is a plausible wrong geometry (section 5.3.1 NOTE on ``geometry.density``). An atom
the rules cannot resolve is refused, naming its chain, residue number, residue and
atom.

The lookup order is D3's:

1. the residue, with PDB2PQR's histidine names ``HID``, ``HIE`` and ``HIP`` read
   as CHARMM's ``HSD``, ``HSE`` and ``HSP``;
2. ``HIS``, which names three CHARMM residues, resolves only where every one of
   them that names the atom gives the same radius: the heavy atoms agree, and
   ``HD2`` (1.468 against 0.9 Å) and ``HE1`` (0.9 against 0.7 Å) do not;
3. the atom aliases, ``ILE CD1`` for CHARMM's ``CD`` and ``OXT`` for ``OT2``;
4. the terminal patches — ``NTER``, or ``GLYP`` and ``PROP`` for glycine and
   proline, and ``CTER`` — for an atom the residue itself lacks.
"""

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

RADII_SCHEMA = "nanopnp/radii/v1"
"""Schema of a shipped radius-set file."""

KERNEL_RADII: Mapping[str, str] = {"gaussian_vdw": "pdb2pqr_charmm"}
"""The radius set each ``geometry.density.kernel`` binds to (WP19 D3).

A kernel names its radii rather than taking them as a case key: the author's
ruling fixes the set, and a second source of truth for a fitted-geometry parameter
is what the specification refuses everywhere else (FR-16).
"""

ANGSTROM_TO_NM = 0.1
"""The table is in ångströms as printed; everything downstream is in nm."""

WILDCARD = "*"
"""The rules' key for every residue not listed by name."""


class DensityInputError(ValueError):
    """An atom the stage-2 radius set does not resolve, or an ensemble stage 2 cannot deposit.

    Raised naming the chain, residue number, residue and atom (QR-12). Classified
    with the gates rather than the case refusals: the case is well formed, and
    the structure it names holds an atom the ruled radius set cannot place.
    """


class _Strict(BaseModel):
    """Unknown keys are refused, as every shipped schema refuses them."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RadiusSource(_Strict):
    """Where a radius table came from, byte for byte."""

    file: str
    package: str
    version: str
    sha256: str
    licence: str
    notice: str


class RadiusRules(_Strict):
    """How a structure file's names map onto the table (D3)."""

    residue_aliases: dict[str, str] = Field(default_factory=dict)
    ambiguous: dict[str, list[str]] = Field(default_factory=dict)
    atom_aliases: dict[str, dict[str, str]] = Field(default_factory=dict)
    patches: dict[str, list[str]] = Field(default_factory=dict)


class RadiusSet(_Strict):
    """A shipped radius table: its source, its lookup rules and the radii in Å."""

    schema_: Literal["nanopnp/radii/v1"] = Field(alias="schema")
    name: str
    source: RadiusSource
    units: Literal["angstrom"]
    quantity: str
    rules: RadiusRules
    residues: dict[str, dict[str, float]]

    @classmethod
    def load(cls, name: str) -> RadiusSet:
        """Read and validate the named set from ``data/radii``.

        Raises
        ------
        FileNotFoundError
            If no set of that name is installed.
        pydantic.ValidationError
            If the file is not a radius set this release reads.
        """
        text = radii_file(name).read_text(encoding="utf-8")
        return cls.model_validate(yaml.safe_load(text))

    def radius_A(self, resname: str, atom: str) -> float:
        """Return one atom's radius in Å by the D3 rules.

        Raises
        ------
        KeyError
            With the reason, when the rules resolve no radius or an ambiguous
            residue name gives several. :func:`resolve_radii` turns it into a
            :class:`DensityInputError` naming the atom.
        """
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
            # Before the patches: a patch names backbone atoms every residue has,
            # and would otherwise place an unknown residue's CA without a word.
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
    """Every atom's radius, and which set it came from."""

    radii_nm: np.ndarray
    """One radius per atom, in nm."""
    name: str
    """The radius set's name."""
    sha256: str
    """The digest of the shipped file, which keys the stage-2 artefact (WP19 D11)."""


def radius_set_digest(name: str) -> str:
    """Return the sha256 of the named radius-set file, as the stage-2 key records it."""
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
    """Resolve every atom of an atom table against the named radius set.

    Each distinct (residue, atom) pair is looked up once.

    Parameters
    ----------
    name
        The radius set, as :data:`KERNEL_RADII` names it.
    resname, atom, chain, resid, icode
        The stage-1 atom table's columns.

    Raises
    ------
    DensityInputError
        For the first atom, in file order, the set does not resolve, naming its
        chain, residue number (with insertion code), residue and atom.
    """
    import numpy as np

    radius_set = RadiusSet.load(name)
    pairs = np.char.add(np.char.add(resname.astype(str), "\t"), atom.astype(str))
    unique, inverse = np.unique(pairs, return_inverse=True)
    radii_A = np.empty(len(unique), dtype=np.float64)
    for index, pair in enumerate(unique.tolist()):
        residue, _, name_ = pair.partition("\t")
        try:
            radii_A[index] = radius_set.radius_A(residue, name_)
        except KeyError as error:
            first = int(np.flatnonzero(inverse == index)[0])
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
