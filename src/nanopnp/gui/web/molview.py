"""The 3D view's documents: a model's structure, its colours and its MolViewSpec scene."""

from __future__ import annotations

import math
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from nanopnp.charge.pqr import PQRFrame, read_pqr
from nanopnp.charge.protonation import PAYLOAD_NAME as TABLE_PAYLOAD
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.gui.geometry import lookup_table
from nanopnp.plot.data import chain_letters, residue_key, table_letters
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.structure.protonated import parent_residue

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.gui.web.molecular import MolecularModel
    from nanopnp.io.case import Membrane

__all__ = [
    "COLOURINGS",
    "MOVED_COLOURS",
    "REPRESENTATIONS",
    "ChargeColours",
    "Colouring",
    "Isosurfaces",
    "Representation",
    "SideView",
    "annotation",
    "chain_rows",
    "charge_rows",
    "first_frame_pdb",
    "has_backbone",
    "moved_rows",
    "overlaid",
    "pqr_frame",
    "pqr_pdb",
    "scene",
    "side_view",
    "structure_text",
    "study_side_view",
]


def _chain_id(chain: str, letters: dict[str, str] | None = None) -> str:
    # The one column of a PDB chain, as a residue's key names it.
    letter = (letters or {}).get(chain, chain)
    return residue_key(letter, 0, "").partition(":")[0]


# Atoms as PDB text, which Mol* reads; the positions are in Å.
def _pdb_text(
    positions_nm: np.ndarray,
    name: Sequence[str],
    resname: Sequence[str],
    chain: Sequence[str],
    resid: Sequence[int],
    icode: Sequence[str],
) -> str:
    lines = []
    letters = chain_letters(str(c) for c in chain)
    for row in range(len(name)):
        x, y, z = (float(v) * 10.0 for v in positions_nm[row])
        atom = str(name[row]).strip()
        number = int(resid[row])
        # The four columns hold -999 to 9999, which the protonation stage keeps to; only a number
        # past them wraps (a negative one wrapped here would be named otherwise by Mol*).
        if not -999 <= number <= 9999:
            number %= 10000
        lines.append(
            f"ATOM  {(row + 1) % 100000:5d} {atom:<4s} {str(resname[row]).strip():>3s} "
            f"{_chain_id(str(chain[row]), letters)}{number:4d}"
            f"{str(icode[row]).strip()[:1] or ' '}   {x:8.3f}{y:8.3f}{z:8.3f}"
            f"  1.00  0.00          {atom[:1]:>2s}"
        )
    return "\n".join([*lines, "END"]) + "\n"


def pqr_pdb(frame: PQRFrame) -> str:
    """Return a PQR file's atoms as PDB text, which Mol* reads."""
    return _pdb_text(
        frame.positions_A / 10.0,
        frame.name.tolist(),
        frame.resname.tolist(),
        frame.chain.tolist(),
        frame.resid.tolist(),
        frame.icode.tolist(),
    )


def has_backbone(table: ProtonationTable | None, pqr: PQRFrame | None = None) -> bool:
    """Say whether the atoms hold a protein backbone, an alpha carbon, which a cartoon draws."""
    if table is not None:
        names = table.name[: int(table.frame_offsets[1])].tolist()
    elif pqr is not None:
        names = pqr.name.tolist()
    else:
        return False
    return any(str(name).strip() == "CA" for name in names)


def first_frame_pdb(table: ProtonationTable) -> str:
    """Return the first frame of a protonation table as PDB text, which Mol* reads."""
    stop = int(table.frame_offsets[1])
    return _pdb_text(
        table.positions_nm[:stop],
        table.name[:stop].tolist(),
        table.resname[:stop].tolist(),
        table.chain[:stop].tolist(),
        table.resid[:stop].tolist(),
        table.icode[:stop].tolist(),
    )


Representation = Literal["cartoon", "ball_and_stick", "spacefill", "surface"]
REPRESENTATIONS: dict[Representation, str] = {
    "cartoon": "Cartoon",
    "ball_and_stick": "Ball and stick",
    "spacefill": "Spheres",
    "surface": "Surface",
}
"""The representations the view offers, by MolViewSpec name, with the title each shows."""

ChargeColours = Literal["blue", "red"]
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
MOVED_COLOURS = {"out": "#2fa4c9", "in": "#e0913a"}
"""The residues an edit of the outline moves: into the water, and into the protein."""
AXIS_COLOUR = "#f2c744"
AXIS_RADIUS_A = 0.6
AXIS_MARGIN_A = 15.0
PLANE_RADIUS_A = 90.0
PLANE_OPACITY = 0.35
# The side view's distance from the axis, in pore lengths; one subunit's, from its centre.
SIDE_DISTANCE = 2.5
ALONE_DISTANCE = 1.4


def _table(model: MolecularModel) -> ProtonationTable | None:
    stored = model.artefacts().get("protonation")
    return None if stored is None else ProtonationTable.read(Path(stored.payload[TABLE_PAYLOAD]))


def _ensemble(model: MolecularModel) -> AlignedEnsemble | None:
    stored = model.artefacts().get("structure")
    return None if stored is None else AlignedEnsemble.read(Path(stored.payload[ENSEMBLE_PAYLOAD]))


# A PQR file's first frame, by its path and modification time.
_PQR: dict[tuple[Path, int], PQRFrame] = {}


def _pqr(model: MolecularModel) -> PQRFrame | None:
    return pqr_frame(model.pqr())


def pqr_frame(path: Path | None) -> PQRFrame | None:
    """Return a PQR file's first frame, read once per change of it; None where it reads none."""
    if path is None or not path.is_file():
        return None
    key = (path, path.stat().st_mtime_ns)
    if key not in _PQR:
        try:
            frames = read_pqr(path)
        except (ValueError, OSError):
            return None
        if not frames:
            return None
        _PQR[key] = frames[0]
    return _PQR[key]


def frame_count(model: MolecularModel) -> int:
    """Return how many frames the view can draw of a model: the built ones, else one."""
    table = _table(model)
    if table is not None:
        return len(table.frame_offsets) - 1
    ensemble = _ensemble(model)
    return 1 if ensemble is None else len(ensemble.positions_nm)


def residues(model: MolecularModel) -> list[tuple[str, str]]:
    """Return each residue the view draws, as its pick key and the name a list shows."""
    table = _table(model)
    held = table if table is not None else _ensemble(model)
    if held is None:
        return []
    stop = int(table.frame_offsets[1]) if table is not None else len(held.chain)
    found = dict.fromkeys(
        zip(
            (str(c) for c in held.chain[:stop].tolist()),
            (int(r) for r in held.resid[:stop].tolist()),
            (str(i).strip() for i in held.icode[:stop].tolist()),
            (str(n).strip() for n in held.resname[:stop].tolist()),
            strict=True,
        )
    )
    letters = chain_letters(chain for chain, _, _, _ in found)
    return [
        (f"{_chain_id(chain, letters)}:{resid}{icode}", f"{resname} {resid}{icode}, chain {chain}")
        for chain, resid, icode, resname in found
    ]


def titration_states(model: MolecularModel) -> list[dict[str, object]]:
    """Return each titratable group of a built model's first frame, as a table's rows.

    A row holds the group's label, its kind, its pKa, the charge the force field applied to its
    residue, the charge PROPKA's state expects, and whether that state was left unapplied.
    """
    table = _table(model)
    if table is None:
        return []
    rows: list[dict[str, object]] = []
    letters = table_letters(table)
    for index, residue in enumerate(table.group_residue.tolist()):
        expected = float(table.expected_charge_e[0][residue])
        rows.append(
            {
                "id": index,
                "group": " ".join(str(table.group_label[index]).split()),
                "kind": str(table.group_type[index]),
                "pka": round(float(table.group_pka[0][index]), 2),
                "applied_e": round(float(table.residue_charge_e[0][residue]), 3),
                "expected_e": None if expected != expected else round(expected, 3),
                "unapplied": bool(table.unapplied[0][residue]),
                "key": (
                    f"{_chain_id(str(table.residue_chain[residue]), letters)}:"
                    f"{int(table.residue_resid[residue])}"
                    f"{str(table.residue_icode[residue]).strip()}"
                ),
            }
        )
    return rows


def structure_text(model: MolecularModel, frame: int = 0) -> tuple[str, str]:
    """Return what the view draws of a model and its format: ``pdb`` or ``mmcif``.

    One protonated frame where the model is built, else one of stage 1's aligned frames, else
    the source file as it lies, else nothing. A frame past the last gives the last.
    """
    table = _table(model)
    if table is not None:
        frame = max(0, min(frame, len(table.frame_offsets) - 2))
        start, stop = int(table.frame_offsets[frame]), int(table.frame_offsets[frame + 1])
        return (
            _pdb_text(
                table.positions_nm[start:stop],
                table.name[start:stop].tolist(),
                table.resname[start:stop].tolist(),
                table.chain[start:stop].tolist(),
                table.resid[start:stop].tolist(),
                table.icode[start:stop].tolist(),
            ),
            "pdb",
        )
    ensemble = _ensemble(model)
    if ensemble is not None:
        frame = max(0, min(frame, len(ensemble.positions_nm) - 1))
        return (
            _pdb_text(
                ensemble.positions_nm[frame],
                ensemble.name.tolist(),
                ensemble.resname.tolist(),
                ensemble.chain.tolist(),
                ensemble.resid.tolist(),
                ensemble.icode.tolist(),
            ),
            "pdb",
        )
    pqr = _pqr(model)
    if pqr is not None:
        return pqr_pdb(pqr), "pdb"
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


def _row(
    chain: str, resid: int, icode: str, colour: str, letters: dict[str, str] | None = None
) -> dict[str, object]:
    row: dict[str, object] = {
        "auth_asym_id": _chain_id(chain, letters),
        "auth_seq_id": int(resid),
        "color": colour,
    }
    if icode.strip():
        row["pdbx_PDB_ins_code"] = icode.strip()[:1]
    return row


def annotation(
    model: MolecularModel, by: Colouring, *, positive: ChargeColours = "blue"
) -> list[dict[str, object]]:
    """Return one colour per residue, as the rows of a MolViewSpec annotation.

    ``charge`` is the residue's net charge on a diverging scale about zero, saturating at one
    elementary charge; ``chain`` a hue per chain; ``changed`` marks the residues the model's
    edits name. A colouring that needs a stage not built gives no rows.

    Parameters
    ----------
    positive
        The colour of a positive residue; a negative one takes the scale's other end.
    """
    table = _table(model)
    pqr = None if table is not None else _pqr(model)
    if by == "charge":
        return _charge_rows(_residue_charges(table, pqr), positive, _letters(table, pqr))
    ensemble = None if table is not None else _ensemble(model)
    held = table if table is not None else ensemble if ensemble is not None else pqr
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
    letters = chain_letters(chain for chain, _, _, _ in residues)
    if by == "chain":
        order = list(dict.fromkeys(chain for chain, _, _, _ in residues))
        hue = {c: CHAIN_COLOURS[i % len(CHAIN_COLOURS)] for i, c in enumerate(order)}
        return [
            _row(chain, resid, icode, hue[chain], letters) for chain, resid, icode, _ in residues
        ]
    case = model.case()
    edited = set()
    for edit in case.charge.edits if case is not None and case.charge is not None else ():
        parent, _, number = edit.residue.partition(" ")
        edited.add((parent.strip(), number.strip().lstrip("0") or "0"))
    # An edit names the parent residue, and a protonated table the state it holds, as HSD.
    return [
        _row(chain, resid, icode, CHANGED, letters)
        for chain, resid, icode, resname in residues
        if (parent_residue(resname), f"{resid}{icode.strip()}") in edited
    ]


def charge_rows(
    table: ProtonationTable | None,
    pqr: PQRFrame | None = None,
    *,
    positive: ChargeColours = "blue",
) -> list[dict[str, object]]:
    """Return one colour per residue by its net charge: the table's, else the PQR's.

    The scale is diverging about zero and saturates at one elementary charge, a positive residue
    in the named colour, as the charge map's.
    """
    return _charge_rows(_residue_charges(table, pqr), positive, _letters(table, pqr))


def moved_rows(
    table: ProtonationTable | None,
    pqr: PQRFrame | None,
    out: Collection[str],
    into: Collection[str],
) -> list[dict[str, object]]:
    """Return a colour for each residue an edit moves, by its key, each way; none for the rest."""
    found = []
    for row in chain_rows(table, pqr):
        code = row.get("pdbx_PDB_ins_code", "")
        key = f"{row['auth_asym_id']}:{row['auth_seq_id']}{code}"
        if key in out or key in into:
            found.append({**row, "color": MOVED_COLOURS["out" if key in out else "in"]})
    return found


def chain_rows(
    table: ProtonationTable | None, pqr: PQRFrame | None = None
) -> list[dict[str, object]]:
    """Return one colour per residue by its chain, a hue per chain: the table's, else the PQR's."""
    if table is not None:
        keys = zip(
            (str(c) for c in table.residue_chain.tolist()),
            (int(r) for r in table.residue_resid.tolist()),
            (str(i) for i in table.residue_icode.tolist()),
            strict=True,
        )
        residues = list(dict.fromkeys(keys))
    elif pqr is not None:
        residues = list(
            dict.fromkeys(
                zip(
                    (str(c) for c in pqr.chain.tolist()),
                    (int(r) for r in pqr.resid.tolist()),
                    (str(i) for i in pqr.icode.tolist()),
                    strict=True,
                )
            )
        )
    else:
        return []
    letters = _letters(table, pqr)
    order = list(dict.fromkeys(chain for chain, _, _ in residues))
    hue = {c: CHAIN_COLOURS[i % len(CHAIN_COLOURS)] for i, c in enumerate(order)}
    return [_row(chain, resid, icode, hue[chain], letters) for chain, resid, icode in residues]


def _letters(table: ProtonationTable | None, pqr: PQRFrame | None) -> dict[str, str]:
    if table is not None:
        return table_letters(table)
    return {} if pqr is None else chain_letters(pqr.chain.tolist())


def _charge_rows(
    totals: dict[tuple[str, int, str], float],
    positive: ChargeColours,
    letters: dict[str, str],
) -> list[dict[str, object]]:
    colours = lookup_table("diverging")
    if positive == "blue":
        colours = colours[::-1]
    middle = (len(colours) - 1) // 2
    rows = []
    for (chain, resid, icode), total in totals.items():
        step = round(max(-1.0, min(1.0, total / CHARGE_SCALE_E)) * middle)
        rows.append(_row(chain, resid, icode, _hex(colours[middle + step]), letters))
    return rows


def _residue_charges(
    table: ProtonationTable | None, pqr: PQRFrame | None
) -> dict[tuple[str, int, str], float]:
    """Return each residue's net charge: the table's own, the mean over its frames, or the PQR's."""
    import numpy as np

    if table is not None:
        charge = np.asarray(table.residue_charge_e, dtype=np.float64)
        if charge.ndim == 2:
            charge = charge.mean(axis=0)
        keys = zip(
            (str(c) for c in table.residue_chain.tolist()),
            (int(r) for r in table.residue_resid.tolist()),
            (str(i) for i in table.residue_icode.tolist()),
            strict=True,
        )
        return dict(zip(keys, charge.tolist(), strict=True))
    if pqr is None:
        return {}
    # A PQR file carries its atoms' charges: the residue's is their sum.
    totals: dict[tuple[str, int, str], float] = {}
    for chain, resid, icode, charge_e in zip(
        pqr.chain.tolist(),
        pqr.resid.tolist(),
        pqr.icode.tolist(),
        pqr.charge_e.tolist(),
        strict=True,
    ):
        key = (str(chain), int(resid), str(icode))
        totals[key] = totals.get(key, 0.0) + float(charge_e)
    return totals


def _extent_a(model: MolecularModel) -> tuple[float, float] | None:
    ensemble = _ensemble(model)
    if ensemble is None:
        return None
    z = ensemble.positions_nm[0][:, 2]
    return float(z.min()) * 10.0, float(z.max()) * 10.0


@dataclass(frozen=True)
class SideView:
    """How a pore is seen from the side beside its (r, z) map.

    Parameters
    ----------
    extent_a
        The structure's lowest and highest z, in Å.
    cut_deg
        The azimuth of the cut through the axis, chosen so the first chain stands whole behind it;
        for fewer than two chains, the atoms' mean azimuth, which the view looks across uncut.
    chain
        The first chain, which the view draws alone as one subunit; None for fewer than two chains,
        which are not cut.
    chain_deg
        The azimuth of the first chain's centre.
    reach_a
        The first chain's farthest atom from the axis, in Å; for fewer than two chains, the
        farthest atom's.
    centre_a
        The first chain's centre's distance from the axis, in Å, where one subunit is aimed.
    alone
        Draw the first chain alone, seen across its centre, in place of the cut.
    """

    extent_a: tuple[float, float]
    cut_deg: float
    chain: str | None
    chain_deg: float
    reach_a: float = 0.0
    centre_a: float = 0.0
    alone: bool = False


def side_view(positions_nm: np.ndarray, chains: Sequence[str]) -> SideView:
    """Return the side view of a structure aligned to the z axis, its atoms in nm."""
    import numpy as np

    xyz = np.asarray(positions_nm, dtype=float)
    extent = (float(xyz[:, 2].min()) * 10.0, float(xyz[:, 2].max()) * 10.0)
    letters = chain_letters(str(chain) for chain in chains)
    ids = [_chain_id(str(chain), letters).strip() for chain in chains]
    order = [chain for chain in dict.fromkeys(ids) if chain]
    if len(order) < 2:
        # Seen across the atoms' mean azimuth, no atom stands behind the axis's tube.
        mean = math.degrees(math.atan2(xyz[:, 1].mean(), xyz[:, 0].mean()))
        return SideView(extent, mean, None, 0.0, float(np.hypot(xyz[:, 0], xyz[:, 1]).max()) * 10.0)
    first = np.array([chain == order[0] for chain in ids])
    x_mean, y_mean = float(xyz[first, 0].mean()), float(xyz[first, 1].mean())
    centre = math.degrees(math.atan2(y_mean, x_mean))
    reach = float(np.hypot(xyz[first, 0], xyz[first, 1]).max()) * 10.0
    # Half a subunit's angle back, so the first chain stands whole behind the cut, at the right.
    return SideView(
        extent,
        centre - 180.0 / len(order),
        order[0],
        centre,
        reach,
        centre_a=math.hypot(x_mean, y_mean) * 10.0,
    )


def study_side_view(table: ProtonationTable | None, pqr: PQRFrame | None) -> SideView | None:
    """Return the side view of a study's atoms: its protonated first frame, else its PQR file."""
    if table is not None:
        stop = int(table.frame_offsets[1])
        return side_view(table.positions_nm[:stop], table.chain[:stop].tolist())
    if pqr is not None and len(pqr.chain):
        return side_view(pqr.positions_A / 10.0, pqr.chain.tolist())
    return None


@dataclass(frozen=True)
class Isosurfaces:
    """One volume drawn over the structure as two isosurfaces, at plus and minus its level.

    Parameters
    ----------
    url
        Where the page reads the volume, as OpenDX in angstroms on the server's own origin.
    level
        The magnitude of the two isovalues, in the volume's own units.
    positive, negative
        The colour of the surface at the positive and at the negative isovalue.
    """

    url: str
    level: float
    positive: str
    negative: str


OVERLAY_OPACITY = 0.5
"""The opacity of an overlay's isosurfaces, so the structure shows through them."""


def scene(
    model: MolecularModel | None,
    *,
    structure_url: str,
    annotation_url: str | None,
    representation: Representation = "cartoon",
    form: str = "pdb",
    clip: bool = False,
    frames: Sequence[int] = (0,),
    side_on: Membrane | SideView | None = None,
) -> dict[str, object]:
    """Return the MolViewSpec document of one view: the structure, its look and the pore's axis.

    The axis is a tube along z, drawn once stage 1 has aligned the model's structure to it.

    Parameters
    ----------
    structure_url, annotation_url
        Where the page reads the structure and the per-residue colours, on the server's own
        origin; without an annotation the viewer's own colours stand.
    clip
        Cut the half in front of the plane through the axis away, so the lumen shows from the side.
    frames
        The frames drawn, each over the others.
    side_on
        Open the view from the side, z up, as a pore is drawn in its membrane, with this
        membrane's two leaflets, at its centre less and plus half its thickness. A side view
        opens along its cut, or across its first chain drawn alone, with no leaflet.
    """
    side = side_on if isinstance(side_on, SideView) else None
    chain = side.chain if side is not None and side.alone else None
    colours: list[dict[str, object]] = []
    if annotation_url is not None:
        colours.append({"kind": "color", "params": {"color": NEUTRAL}})
        colours.append(
            {
                "kind": "color_from_uri",
                "params": {"uri": annotation_url, "format": "json", "schema": "auth_residue"},
            }
        )
    # The view looks along the plane's normal, the plane's own direction at its right.
    azimuth = 0.0 if side is None else math.radians(side.chain_deg if chain else side.cut_deg)
    normal = [-math.sin(azimuth), math.cos(azimuth), 0.0]
    if clip:
        colours.append(
            {
                "kind": "clip",
                "params": {"type": "plane", "point": [0.0, 0.0, 0.0], "normal": normal},
            }
        )
    joiner = "&" if "?" in structure_url else "?"
    children: list[dict[str, object]] = [
        {
            "kind": "download",
            "params": {"url": f"{structure_url}{joiner}frame={frame}"},
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
                                    "params": {
                                        "selector": "all"
                                        if chain is None
                                        else {"auth_asym_id": chain}
                                    },
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
        for frame in frames
    ]
    extent = _extent_a(model) if model is not None else None if side is None else side.extent_a
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
    if (
        side_on is not None
        and not isinstance(side_on, SideView)
        and not clip
        and extent is not None
    ):
        centre_a, half_a = side_on.centre_z_nm * 10.0, side_on.thickness_nm * 5.0
        for leaflet, z_a in (("cis", centre_a + half_a), ("trans", centre_a - half_a)):
            children.append(
                {
                    "kind": "primitives",
                    "params": {
                        "tooltip": f"The membrane's {leaflet} leaflet",
                        "opacity": PLANE_OPACITY,
                    },
                    "children": [
                        {
                            "kind": "primitive",
                            "params": {
                                "kind": "ellipse",
                                "center": [0.0, 0.0, z_a],
                                "major_axis": [1.0, 0.0, 0.0],
                                "minor_axis": [0.0, 1.0, 0.0],
                                "radius_major": PLANE_RADIUS_A,
                                "radius_minor": PLANE_RADIUS_A,
                                "color": AXIS_COLOUR,
                            },
                        }
                    ],
                }
            )
    if side_on is not None and extent is not None:
        middle = (extent[0] + extent[1]) / 2.0
        # Fewer than two chains need not stand about the axis: framed to their reach as well.
        few = side is not None and side.chain is None
        across = 2.0 * side.reach_a if side is not None and few else 0.0
        away = SIDE_DISTANCE * max(extent[1] - extent[0], across)
        # Fewer than two chains are aimed midway out to their reach, the axis at their left;
        # one subunit at its own centre, from nearer, so it fills the view.
        out = side.reach_a / 2.0 if side is not None and few else 0.0
        if side is not None and chain is not None:
            out = side.centre_a or side.reach_a / 2.0
            away = ALONE_DISTANCE * (extent[1] - extent[0])
        target = [out * math.cos(azimuth), out * math.sin(azimuth), middle]
        children.append(
            {
                "kind": "camera",
                "params": {
                    "target": target,
                    "position": [
                        target[0] - away * normal[0],
                        target[1] - away * normal[1],
                        middle,
                    ],
                    "up": [0.0, 0.0, 1.0],
                },
            }
        )
    return {
        "metadata": {"version": MVS_VERSION},
        "root": {"kind": "root", "children": children},
    }


def overlaid(document: dict[str, Any], volumes: Sequence[Isosurfaces]) -> dict[str, Any]:
    """Return a scene with volumes drawn over its structure, each cut as the structure is."""
    cut: list[Any] = []

    def find(node: dict[str, Any]) -> None:
        for child in node.get("children", ()):
            if child.get("kind") == "clip" and not cut:
                cut.append(child)
            find(child)

    find(document["root"])
    children: list[Any] = list(document["root"]["children"])
    for volume in volumes:
        surfaces: list[dict[str, Any]] = [
            {
                "kind": "volume_representation",
                "params": {"type": "isosurface", "absolute_isovalue": sign * volume.level},
                "children": [
                    {"kind": "color", "params": {"color": colour}},
                    {"kind": "opacity", "params": {"opacity": OVERLAY_OPACITY}},
                    *cut,
                ],
            }
            for sign, colour in ((1.0, volume.positive), (-1.0, volume.negative))
        ]
        children.append(
            {
                "kind": "download",
                "params": {"url": volume.url},
                "children": [
                    {
                        "kind": "parse",
                        "params": {"format": "dx"},
                        "children": [{"kind": "volume", "params": {}, "children": surfaces}],
                    }
                ],
            }
        )
    return {**document, "root": {**document["root"], "children": children}}
