"""The geometry, mesh and prepare commands."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.cli.common import _common, _destination, _emit, _positive_nm, _refuse
from nanopnp.core.errors import EXIT_OK
from nanopnp.mesh.defaults import (
    DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
    DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
    DEFAULT_CYLINDER_WALL_H_NM,
    DEFAULT_MAXH_NM,
    DEFAULT_PORE_RADIUS_NM,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.cli.common import Subparsers
    from nanopnp.core.hashing import Canonicalisable


def _geometry(args: argparse.Namespace) -> int:
    from nanopnp.geometry.region import derive_idealised_region, write_region
    from nanopnp.io.case import Membrane, Pore, Reservoir

    out = _destination(args, ".yaml")
    if args.pore_radius_nm >= args.reservoir_radius_nm:
        args.parser.error(
            f"--pore-radius-nm {args.pore_radius_nm:g} must be smaller than "
            f"--reservoir-radius-nm {args.reservoir_radius_nm:g}"
        )
    record = derive_idealised_region(
        Pore(shape="cylinder", radius_nm=args.pore_radius_nm),
        Membrane(thickness_nm=args.membrane_thickness_nm),
        Reservoir(radius_nm=args.reservoir_radius_nm),
    )
    write_region(record, out)
    faces = ", ".join(
        f"{name} {area:.4g} nm^2" for name, area in sorted(record.face_areas_nm2.items())
    )
    payload: dict[str, Canonicalisable] = {"path": str(out), **record.summary()}
    lines = [
        f"region    {out}",
        f"faces     {faces}",
        "",
        "geometry:",
        f"  pore: {{shape: cylinder, radius_nm: {args.pore_radius_nm:g}}}",
        f"  membrane: {{thickness_nm: {args.membrane_thickness_nm:g}}}",
        f"  reservoir: {{radius_nm: {args.reservoir_radius_nm:g}}}",
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _mesh(args: argparse.Namespace) -> int:
    from nanopnp.mesh.idealised import write_gated_msh

    out = _destination(args, ".msh")
    if args.source == "reference":
        for flag, value in (("--maxh-nm", args.maxh_nm), ("--wall-h-nm", args.wall_h_nm)):
            if value is not None:
                args.parser.error(
                    f"{flag} sizes an idealised pore's mesh; the reference geometry is meshed "
                    "at the section 5.2.2 preset, which these flags do not move"
                )
        from nanopnp.mesh.reference import ReferenceGeometry

        generated = ReferenceGeometry.from_fixture().generate(check_quality=False)
    else:
        from nanopnp.geometry.pore import IdealisedRegionRecord
        from nanopnp.geometry.region import read_region
        from nanopnp.mesh.idealised import generate_idealised

        try:
            record = read_region(Path(args.source))
        except (OSError, ValueError, KeyError) as error:
            _refuse(args, f"{args.source} is not a geometry file `nanopnp geometry` wrote: {error}")
        if not isinstance(record, IdealisedRegionRecord):
            _refuse(
                args,
                f"{args.source} is the region of a structure; only an idealised pore's geometry "
                "file is meshed here, and a structure's region is meshed by running its case",
            )
        generated = generate_idealised(
            record,
            maxh_nm=args.maxh_nm if args.maxh_nm is not None else DEFAULT_MAXH_NM,
            wall_h_nm=args.wall_h_nm if args.wall_h_nm is not None else DEFAULT_CYLINDER_WALL_H_NM,
        )
    mapped, quality, groups = write_gated_msh(generated, out)
    flow = "{" + ", ".join(f"{key}: {value}" for key, value in sorted(groups.items())) + "}"
    payload: dict[str, Canonicalisable] = {
        "path": str(out),
        "format": "msh41",
        "content_hash": mapped.content_hash,
        "groups": dict(sorted(groups.items())),
        "elements": mapped.element_count,
        "vertices": mapped.vertex_count,
        "materials": list(mapped.materials),
        "boundaries": list(mapped.boundaries),
        "min_sicn": quality.min_sicn,
        "min_gamma": quality.min_gamma,
    }
    lines = [
        f"mesh      {out}",
        f"hash      {mapped.content_hash}",
        f"elements  {mapped.element_count} ({mapped.vertex_count} vertices)",
        f"quality   min SICN {quality.min_sicn:.3f}, min gamma {quality.min_gamma:.3f}",
        f"domains   {', '.join(mapped.materials)}",
        f"groups    {flow}",
        "",
        "inputs:",
        "  mesh:",
        f"    path: {out}",
        "    format: msh41",
        f"    groups: {flow}",
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _prepare(args: argparse.Namespace) -> int:
    from nanopnp.structure.orient import orient_pore

    out = _destination(args, ".pdb")
    try:
        written = orient_pore(
            Path(args.source),
            chains=args.chains,
            cis_end=args.cis_end,
            registration_residues=args.registration,
            centroid_z_nm=args.centroid_z_nm,
            axis=args.axis,
            out=out,
        )
    except ValueError as error:
        _refuse(args, str(error))
    record = written.with_suffix(".prepare.json")
    payload: dict[str, Canonicalisable] = json.loads(record.read_text(encoding="utf-8"))
    axis = ", ".join(f"{value:.4f}" for value in payload["axis"])
    lines = [
        f"structure {written}",
        f"record    {record}",
        f"axis      ({axis}) by {payload['method']}, {payload['tilt_deg']:.2f} degrees from z",
        f"cis end   the {payload['cis_end']} one, now +z",
        f"centroid  {payload['off_axis_nm']:.3f} nm from the axis, at z = "
        f"{payload['centroid_z_nm']:g} nm",
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _registration(text: str) -> tuple[int, int]:
    first, colon, last = text.partition(":")
    try:
        span = (int(first), int(last))
    except ValueError:
        span = (1, 0)
    if not colon or span[0] > span[1]:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not FIRST:LAST residue numbers, FIRST <= LAST"
        )
    return span


def _axis(text: str) -> tuple[float, float, float]:
    try:
        parts = [float(part) for part in text.split(",")]
    except ValueError:
        parts = []
    if len(parts) != 3 or not all(math.isfinite(part) for part in parts) or not any(parts):
        raise argparse.ArgumentTypeError(
            f"{text!r} is not X,Y,Z, three finite numbers, not all zero"
        )
    return (parts[0], parts[1], parts[2])


def _register_geometry(subparsers: Subparsers) -> None:
    geometry_command = subparsers.add_parser(
        "geometry", help="write an idealised pore's geometry as a file a case or a mesh reads"
    )
    shapes = geometry_command.add_subparsers(dest="shape", required=True)
    cylinder = _common(shapes.add_parser("cylinder", help="a cylindrical pore through a membrane"))
    cylinder.add_argument(
        "--pore-radius-nm",
        type=_positive_nm,
        default=DEFAULT_PORE_RADIUS_NM,
        help=f"lumen radius (default {DEFAULT_PORE_RADIUS_NM:g})",
    )
    cylinder.add_argument(
        "--membrane-thickness-nm",
        type=_positive_nm,
        default=DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
        help=(
            "membrane thickness, the lumen's length "
            f"(default {DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM:g})"
        ),
    )
    cylinder.add_argument(
        "--reservoir-radius-nm",
        type=_positive_nm,
        default=DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
        help=(
            "radius of each quarter-disc reservoir "
            f"(default {DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM:g})"
        ),
    )
    cylinder.add_argument("--out", type=Path, required=True, help="the .yaml file to write")
    cylinder.set_defaults(handler=_geometry, parser=cylinder)


def _register_mesh(subparsers: Subparsers) -> None:
    # Defaults: the coarsest mesh the NUM-34 gate admits with wall corrections on (392 elements).
    mesh = _common(
        subparsers.add_parser(
            "mesh", help="write a gated MSH 4.1 mesh of a geometry file, or of the reference"
        )
    )
    mesh.add_argument(
        "source",
        metavar="SOURCE",
        help="a geometry file `nanopnp geometry` wrote, or `reference` for the ClyA preset",
    )
    mesh.add_argument(
        "--maxh-nm",
        type=_positive_nm,
        default=None,
        help=f"global maximum element size (default {DEFAULT_MAXH_NM:g}); not for `reference`",
    )
    mesh.add_argument(
        "--wall-h-nm",
        type=_positive_nm,
        default=None,
        help=(
            f"element size on the pore wall (default {DEFAULT_CYLINDER_WALL_H_NM:g}); "
            "not for `reference`"
        ),
    )
    mesh.add_argument("--out", type=Path, required=True, help="the .msh file to write")
    mesh.set_defaults(handler=_mesh, parser=mesh)


def _register_prepare(subparsers: Subparsers) -> None:
    prepare = _common(
        subparsers.add_parser(
            "prepare",
            help="write a structure's chains with the pore axis on z and the named end cis",
        )
    )
    prepare.add_argument("source", metavar="SOURCE", help="a PDB or mmCIF file, may be gzipped")
    prepare.add_argument(
        "--cis-end",
        choices=("wider", "narrower"),
        required=True,
        help="which end of the pore faces cis (+z), by the mean C-alpha radius of its last fifth",
    )
    prepare.add_argument("--out", type=Path, required=True, help="the .pdb file to write")
    prepare.add_argument(
        "--chains", default="all", help="the chains kept, comma-separated (default all)"
    )
    prepare.add_argument(
        "--registration",
        type=_registration,
        default=None,
        metavar="FIRST:LAST",
        help="the residues whose C-alpha centroid is placed on the axis (default every C-alpha)",
    )
    prepare.add_argument(
        "--centroid-z-nm",
        type=float,
        default=0.0,
        help="where that centroid goes on z, in nm (default 0)",
    )
    prepare.add_argument(
        "--axis",
        type=_axis,
        default=None,
        metavar="X,Y,Z",
        help="the pore axis in the file's frame, instead of an estimate",
    )
    prepare.set_defaults(handler=_prepare, parser=prepare)


def register(subparsers: Subparsers) -> None:
    """Add the geometry, mesh and prepare subcommands."""
    _register_geometry(subparsers)
    _register_mesh(subparsers)
    _register_prepare(subparsers)
