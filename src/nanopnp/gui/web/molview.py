"""The 3D view's documents: a model's structure, its colours and its MolViewSpec scene."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from nanopnp.charge.protonation import PAYLOAD_NAME as TABLE_PAYLOAD
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.gui.geometry import lookup_table
from nanopnp.gui.web.link import _chain_id
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.gui.web.molecular import MolecularModel

__all__ = [
    "COLOURINGS",
    "REPRESENTATIONS",
    "Colouring",
    "Representation",
    "annotation",
    "scene",
    "structure_text",
]

Representation = Literal["cartoon", "ball_and_stick", "spacefill", "surface"]
REPRESENTATIONS: dict[Representation, str] = {
    "cartoon": "Cartoon",
    "ball_and_stick": "Ball and stick",
    "spacefill": "Spheres",
    "surface": "Surface",
}
"""The representations the view offers, by MolViewSpec name, with the title each shows."""

Colouring = Literal["chain", "charge", "changed"]
COLOURINGS: dict[Colouring, str] = {
    "chain": "Chain",
    "charge": "Residue charge",
    "changed": "Changed residues",
}
"""The colourings the view offers, with the title each shows."""

MVS_VERSION = "1.4"

# The residue charge at which the diverging scale saturates, in e: a charged side chain.
CHARGE_SCALE_E = 1.0

# Eight hues of one lightness band, told apart on the dark and the light 3D background alike.
CHAIN_COLOURS = (
    "#4e9ad6",
    "#e0913a",
    "#56b377",
    "#d66a6a",
    "#9d86d9",
    "#b39a45",
    "#d77fb4",
    "#6fb6b6",
)
NEUTRAL = "#b9bcc2"
CHANGED = "#f2c744"
AXIS_COLOUR = "#f2c744"
AXIS_RADIUS_A = 0.6
AXIS_MARGIN_A = 15.0


def _pdb(
    positions_nm: Any,  # noqa: ANN401 - a numpy array, imported nowhere at module scope
    name: Sequence[str],
    resname: Sequence[str],
    chain: Sequence[str],
    resid: Sequence[int],
    icode: Sequence[str],
) -> str:
    lines = []
    for row in range(len(name)):
        x, y, z = (float(v) * 10.0 for v in positions_nm[row])
        atom = str(name[row]).strip()
        number = int(resid[row])
        # The four columns hold -999 to 9999; a number past them wraps, as the charge link's does.
        if not -999 <= number <= 9999:
            number %= 10000
        lines.append(
            f"ATOM  {(row + 1) % 100000:5d} {atom:<4s} {str(resname[row]).strip():>3s} "
            f"{_chain_id(str(chain[row]))}{number:4d}"
            f"{str(icode[row]).strip()[:1] or ' '}   {x:8.3f}{y:8.3f}{z:8.3f}"
            f"  1.00  0.00          {atom[:1]:>2s}"
        )
    return "\n".join([*lines, "END"]) + "\n"


def _table(model: MolecularModel) -> ProtonationTable | None:
    stored = model.artefacts().get("protonation")
    return None if stored is None else ProtonationTable.read(Path(stored.payload[TABLE_PAYLOAD]))


def _ensemble(model: MolecularModel) -> AlignedEnsemble | None:
    stored = model.artefacts().get("structure")
    return None if stored is None else AlignedEnsemble.read(Path(stored.payload[ENSEMBLE_PAYLOAD]))


def structure_text(model: MolecularModel) -> tuple[str, str]:
    """Return what the view draws of a model and its format: ``pdb`` or ``mmcif``.

    The protonated first frame where the model is built, else stage 1's aligned first frame,
    else the source file as it lies, else nothing.
    """
    table = _table(model)
    if table is not None:
        stop = int(table.frame_offsets[1])
        return (
            _pdb(
                table.positions_nm[:stop],
                table.name[:stop].tolist(),
                table.resname[:stop].tolist(),
                table.chain[:stop].tolist(),
                table.resid[:stop].tolist(),
                table.icode[:stop].tolist(),
            ),
            "pdb",
        )
    ensemble = _ensemble(model)
    if ensemble is not None:
        return (
            _pdb(
                ensemble.positions_nm[0],
                ensemble.name.tolist(),
                ensemble.resname.tolist(),
                ensemble.chain.tolist(),
                ensemble.resid.tolist(),
                ensemble.icode.tolist(),
            ),
            "pdb",
        )
    case = model.case()
    if case is None or case.structure is None:
        return "", "pdb"
    source = Path(case.structure.source.path)
    suffixes = [suffix.lower() for suffix in source.suffixes]
    if not source.is_file() or ".gz" in suffixes:
        return "", "pdb"
    form = "mmcif" if {".cif", ".mmcif"} & set(suffixes) else "pdb"
    return source.read_text(encoding="utf-8", errors="replace"), form


def _hex(rgb: Sequence[int]) -> str:
    return f"#{int(rgb[0]):02x}{int(rgb[1]):02x}{int(rgb[2]):02x}"


def _row(chain: str, resid: int, icode: str, colour: str) -> dict[str, object]:
    row: dict[str, object] = {
        "auth_asym_id": _chain_id(chain),
        "auth_seq_id": int(resid),
        "color": colour,
    }
    if icode.strip():
        row["pdbx_PDB_ins_code"] = icode.strip()[:1]
    return row


def annotation(model: MolecularModel, by: Colouring) -> list[dict[str, object]]:
    """Return one colour per residue, as the rows of a MolViewSpec annotation.

    ``charge`` is the residue's net charge on a diverging scale about zero, saturating at one
    elementary charge; ``chain`` a hue per chain; ``changed`` marks the residues the model's
    edits name. A colouring that needs a stage not built gives no rows.
    """
    table = _table(model)
    if by == "charge":
        if table is None:
            return []
        stop = int(table.frame_offsets[1])
        totals: dict[tuple[str, int, str], float] = {}
        keys = zip(
            table.chain[:stop].tolist(),
            table.resid[:stop].tolist(),
            table.icode[:stop].tolist(),
            table.charge_e[:stop].tolist(),
            strict=True,
        )
        for chain, resid, icode, charge in keys:
            key = (str(chain), int(resid), str(icode))
            totals[key] = totals.get(key, 0.0) + float(charge)
        colours = lookup_table("diverging")
        middle = (len(colours) - 1) // 2
        rows = []
        for (chain, resid, icode), total in totals.items():
            step = round(max(-1.0, min(1.0, total / CHARGE_SCALE_E)) * middle)
            rows.append(_row(chain, resid, icode, _hex(colours[middle + step])))
        return rows
    ensemble = None if table is not None else _ensemble(model)
    held = table if table is not None else ensemble
    if held is None:
        return []
    stop = int(table.frame_offsets[1]) if table is not None else len(held.chain)
    residues = dict.fromkeys(
        zip(
            (str(c) for c in held.chain[:stop].tolist()),
            (int(r) for r in held.resid[:stop].tolist()),
            (str(i) for i in held.icode[:stop].tolist()),
            (str(n).strip() for n in held.resname[:stop].tolist()),
            strict=True,
        )
    )
    if by == "chain":
        order = list(dict.fromkeys(chain for chain, _, _, _ in residues))
        hue = {c: CHAIN_COLOURS[i % len(CHAIN_COLOURS)] for i, c in enumerate(order)}
        return [_row(chain, resid, icode, hue[chain]) for chain, resid, icode, _ in residues]
    case = model.case()
    edited = set()
    for edit in case.charge.edits if case is not None and case.charge is not None else ():
        parent, _, number = edit.residue.partition(" ")
        edited.add((parent.strip(), number.strip().lstrip("0") or "0"))
    return [
        _row(chain, resid, icode, CHANGED)
        for chain, resid, icode, resname in residues
        if (resname, f"{resid}{icode.strip()}") in edited
    ]


def _extent_a(model: MolecularModel) -> tuple[float, float] | None:
    ensemble = _ensemble(model)
    if ensemble is None:
        return None
    z = ensemble.positions_nm[0][:, 2]
    return float(z.min()) * 10.0, float(z.max()) * 10.0


def scene(
    model: MolecularModel | None,
    *,
    structure_url: str,
    annotation_url: str | None,
    representation: Representation = "cartoon",
    form: str = "pdb",
    axis: bool = True,
) -> dict[str, object]:
    """Return the MolViewSpec document of one view: the structure, its look and the pore's axis.

    Parameters
    ----------
    structure_url, annotation_url
        Where the page reads the structure and the per-residue colours, on the server's own
        origin; without an annotation the viewer's own colours stand.
    axis
        Draw the pore's axis as a tube along z, once stage 1 has aligned the structure to it.
    """
    colours: list[dict[str, object]] = []
    if annotation_url is not None:
        colours.append({"kind": "color", "params": {"color": NEUTRAL}})
        colours.append(
            {
                "kind": "color_from_uri",
                "params": {"uri": annotation_url, "format": "json", "schema": "auth_residue"},
            }
        )
    children: list[dict[str, object]] = [
        {
            "kind": "download",
            "params": {"url": structure_url},
            "children": [
                {
                    "kind": "parse",
                    "params": {"format": form},
                    "children": [
                        {
                            "kind": "structure",
                            "params": {"type": "model"},
                            "children": [
                                {
                                    "kind": "component",
                                    "params": {"selector": "all"},
                                    "children": [
                                        {
                                            "kind": "representation",
                                            "params": {"type": representation},
                                            "children": colours,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    extent = _extent_a(model) if axis and model is not None else None
    if extent is not None:
        low, high = extent
        children.append(
            {
                "kind": "primitives",
                "params": {"tooltip": "The pore's axis"},
                "children": [
                    {
                        "kind": "primitive",
                        "params": {
                            "kind": "tube",
                            "start": [0.0, 0.0, low - AXIS_MARGIN_A],
                            "end": [0.0, 0.0, high + AXIS_MARGIN_A],
                            "radius": AXIS_RADIUS_A,
                            "color": AXIS_COLOUR,
                        },
                    }
                ],
            }
        )
    return {
        "metadata": {"version": MVS_VERSION},
        "root": {"kind": "root", "children": children},
    }
