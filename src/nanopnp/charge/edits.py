"""Charge edits: PROPKA's titratable groups, an edited table, and its difference from its parent."""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Field

from nanopnp.core.hashing import Canonicalisable
from nanopnp.core.paths import charge_data_file
from nanopnp.io.resolved import ResolvedEdit
from nanopnp.structure.protonated import ProtonationTable, parent_residue

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

CHARGE_TOLERANCE_E = 1e-12
"""Below this a charge counts as unchanged: both tables read the same four-decimal charges."""

RADIUS_TOLERANCE_NM = 1e-12
"""Below this a radius counts as unchanged."""

POSITION_TOLERANCE_NM = 1e-9
"""Below this a coordinate counts as unchanged: the table rounds them to 1e-4 nm (0.001 Å)."""


class EditError(ValueError):
    """A residue edit that names a residue or group atoms the table does not hold."""


class TitratableGroups(BaseModel):
    """The titratable groups PROPKA 3.5.1 defines, by parent residue name."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    schema_id: str = Field(alias="schema")
    source: dict[str, object]
    anchors: dict[str, str]
    groups: dict[str, tuple[str, ...]]

    @classmethod
    def load(cls) -> TitratableGroups:
        """Read the shipped titratable-groups data file."""
        raw = yaml.safe_load(charge_data_file("titratable_groups.yaml").read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    def has_group(self, residue: str) -> bool:
        """Return whether a parent residue name, such as ``ASP``, carries a titratable group."""
        return residue in self.groups


def variant_parent(name: str) -> str | None:
    """Return the parent that a protonation-variant name such as ``HSD`` stands for, or None."""
    parent = parent_residue(name)
    return parent if parent != name else None


def edit_records(edits: Sequence[ResolvedEdit]) -> list[Canonicalisable]:
    """Return the edits as the plain records a table header and a summary carry."""
    return [
        {
            "residue": f"{edit.parent} {edit.resid}{edit.icode}",
            "kind": edit.kind,
            "value": edit.value,
        }
        for edit in edits
    ]


def _owner(table: ProtonationTable) -> np.ndarray:
    import numpy as np

    index = {
        (str(chain), int(resid), str(icode)): number
        for number, (chain, resid, icode) in enumerate(
            zip(
                table.residue_chain.tolist(),
                table.residue_resid.tolist(),
                table.residue_icode.tolist(),
                strict=True,
            )
        )
    }
    return np.array(
        [
            index[(str(chain), int(resid), str(icode))]
            for chain, resid, icode in zip(
                table.chain.tolist(), table.resid.tolist(), table.icode.tolist(), strict=True
            )
        ],
        dtype=np.intp,
    )


def _residues(table: ProtonationTable) -> list[tuple[str, int, str, str]]:
    return list(
        zip(
            table.residue_chain.tolist(),
            table.residue_resid.tolist(),
            table.residue_icode.tolist(),
            table.residue_name.tolist(),
            strict=True,
        )
    )


def _targets(residues: Sequence[tuple[str, int, str, str]], edit: ResolvedEdit) -> dict[str, int]:
    label = f"{edit.parent} {edit.resid}{edit.icode}"
    found = {
        str(chain): number
        for number, (chain, resid, icode, _) in enumerate(residues)
        if (int(resid), str(icode)) == (edit.resid, edit.icode)
    }
    for chain in sorted({str(chain) for chain, _, _, _ in residues}):
        if chain not in found:
            raise EditError(
                f"frame 0: charge edit of {label}: chain {chain!r} holds no such residue (FR-38)"
            )
    for chain, number in found.items():
        name = parent_residue(str(residues[number][3]))
        if name != edit.parent:
            raise EditError(
                f"frame 0: charge edit of {label}: the residue on chain {chain!r} is {name}, not "
                f"{edit.parent} (FR-38)"
            )
    return found


def check_targets(
    residues: Sequence[tuple[str, int, str, str]], edits: Sequence[ResolvedEdit]
) -> None:
    """Refuse an edit whose residue a chain lacks, or holds under another parent name.

    Parameters
    ----------
    residues
        ``(chain, resid, icode, name)`` per residue, as a frame lists them.
    """
    for edit in edits:
        _targets(residues, edit)


def apply_edits(
    table: ProtonationTable, edits: Sequence[ResolvedEdit], groups: TitratableGroups
) -> ProtonationTable:
    """Apply the charge and radius edits to a table; record every edit in its header.

    A state edit is made by the protonation itself and only recorded here.
    """
    import numpy as np

    charge = table.charge_e.copy()
    radius = table.radius_nm.copy()
    expected = table.expected_charge_e.copy()
    owner = _owner(table)
    residues = _residues(table)
    for edit in edits:
        targets = _targets(residues, edit)
        if edit.kind == "state":
            continue
        if edit.kind == "charge":
            # The charge was set by the case, not by PROPKA's pKa, so there is no expectation.
            expected[:, list(targets.values())] = np.nan
        for frame in range(table.frames):
            atoms = table.frame_slice(frame)
            names = table.name[atoms].astype(str)
            for chain, number in targets.items():
                mine = owner[atoms] == number
                if edit.kind == "radius":
                    radius[atoms][mine] *= float(edit.value)
                    continue
                group = mine & np.isin(names, groups.groups[edit.parent])
                if not group.any():
                    raise EditError(
                        f"frame {frame}: charge edit of {edit.parent} {edit.resid}{edit.icode}: "
                        f"chain {chain!r} holds none of the {edit.parent} group's atoms "
                        f"({', '.join(groups.groups[edit.parent])}) (FR-38)"
                    )
                charge[atoms][group] += float(edit.value) / int(group.sum())
    residue_charge = np.stack(
        [
            np.bincount(
                owner[table.frame_slice(frame)],
                weights=charge[table.frame_slice(frame)],
                minlength=len(table.residue_name),
            )
            for frame in range(table.frames)
        ]
    )
    return dataclasses.replace(
        table,
        charge_e=charge,
        radius_nm=radius,
        residue_charge_e=residue_charge,
        expected_charge_e=expected,
        unapplied=~np.isnan(expected) & (np.abs(residue_charge - np.nan_to_num(expected)) > 0.5),
        header={**table.header, "edits": edit_records(edits)},
    )


def _residue_atoms(
    table: ProtonationTable,
) -> list[dict[tuple[str, int, str], dict[str, tuple[float, float, tuple[float, ...]]]]]:
    owner = _owner(table)
    keys = list(
        zip(
            table.residue_chain.tolist(),
            table.residue_resid.tolist(),
            table.residue_icode.tolist(),
            strict=True,
        )
    )
    frames = []
    for frame in range(table.frames):
        atoms = table.frame_slice(frame)
        found: dict[tuple[str, int, str], dict[str, tuple[float, float, tuple[float, ...]]]] = {}
        for number, name, charge, radius, position in zip(
            owner[atoms].tolist(),
            table.name[atoms].tolist(),
            table.charge_e[atoms].tolist(),
            table.radius_nm[atoms].tolist(),
            table.positions_nm[atoms].tolist(),
            strict=True,
        ):
            chain, resid, icode = keys[number]
            found.setdefault((str(chain), int(resid), str(icode)), {})[str(name)] = (
                charge,
                radius,
                tuple(position),
            )
        frames.append(found)
    return frames


def difference(parent: ProtonationTable, variant: ProtonationTable) -> dict[str, Canonicalisable]:
    """Return every residue whose atoms, charges, radii or positions differ, and Q_net per frame."""
    before, after = _residue_atoms(parent), _residue_atoms(variant)
    names = {
        (str(c), int(r), str(i)): str(n)
        for c, r, i, n in zip(
            variant.residue_chain.tolist(),
            variant.residue_resid.tolist(),
            variant.residue_icode.tolist(),
            variant.residue_name.tolist(),
            strict=True,
        )
    }
    residues: list[Canonicalisable] = []
    for key, name in names.items():
        added: set[str] = set()
        removed: set[str] = set()
        worst = 0.0
        displacement = 0.0
        charges: dict[str, list[float]] = {"parent": [], "variant": []}
        differs = False
        for frame in range(parent.frames):
            old, new = before[frame].get(key, {}), after[frame].get(key, {})
            added |= new.keys() - old.keys()
            removed |= old.keys() - new.keys()
            for atom in old.keys() & new.keys():
                if abs(old[atom][0] - new[atom][0]) > CHARGE_TOLERANCE_E:
                    differs = True
                worst = max(worst, abs(old[atom][1] - new[atom][1]))
                moved = max(
                    abs(before_x - after_x)
                    for before_x, after_x in zip(old[atom][2], new[atom][2], strict=True)
                )
                displacement = max(displacement, moved)
            charges["parent"].append(math.fsum(atom[0] for atom in old.values()))
            charges["variant"].append(math.fsum(atom[0] for atom in new.values()))
        if (
            differs
            or added
            or removed
            or worst > RADIUS_TOLERANCE_NM
            or displacement > POSITION_TOLERANCE_NM
        ):
            residues.append(
                {
                    "chain": key[0],
                    "residue": f"{parent_residue(name)} {key[1]}{key[2]}",
                    "charge_e": {kind: list(values) for kind, values in charges.items()},
                    "atoms_added": sorted(added),
                    "atoms_removed": sorted(removed),
                    "max_radius_change_nm": worst,
                    "max_displacement_nm": displacement,
                }
            )
    return {
        "residues": residues,
        "q_net_e": {
            "parent": [round(value) for value in parent.q_net_e().tolist()],
            "variant": [round(value) for value in variant.q_net_e().tolist()],
        },
    }
