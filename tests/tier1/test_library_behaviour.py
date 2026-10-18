"""Tier-1 library and software behaviour checks for knowledge/07-software-stack (WP48 item 6)."""

from __future__ import annotations

import ast
import inspect
import io
import json
import math
import subprocess
import sys
import tarfile
import tomllib
import warnings
from pathlib import Path
from typing import Any

import gemmi
import gridData
import MDAnalysis
import meshio
import netgen.occ as occ
import netgen.read_gmsh as read_gmsh
import ngsolve
import ngsolve.webgui
import numpy as np
import pytest
import shapely
from MDAnalysis.analysis import align, density
from pdb2pqr import main as pdb2pqr_main
from propka import parameters as propka_parameters
from shapely.geometry import LineString, box
from skimage import measure

from nanopnp.charge.protonation import restore_propka_annotations
from nanopnp.core import errors, hashing, stages
from nanopnp.core import typing as core_typing
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.validation import okf


def test_ngsolve_wheel_table_and_config_flags() -> None:
    lock = tomllib.loads((okf.REPOSITORY / "uv.lock").read_text(encoding="utf-8"))
    packages = {p["name"]: p for p in lock["package"]}
    assert "mpi4py" not in packages
    ngs_wheels = packages["ngsolve"]["wheels"]
    assert len(ngs_wheels) == 12
    for tag in ("cp311", "cp312", "cp313", "cp314"):
        assert sum(tag in w["url"] for w in ngs_wheels) == 3
    win_sizes = [w["size"] for w in ngs_wheels if "win_amd64" in w["url"]]
    mac_sizes = [w["size"] for w in ngs_wheels if "macosx_10_15_universal2" in w["url"]]
    assert all(14_000_000 <= s <= 15_500_000 for s in win_sizes)
    assert all(43_000_000 <= s <= 45_000_000 for s in mac_sizes)
    for flag in ("USE_MUMPS", "USE_PARDISO", "USE_HYPRE", "USE_MKL"):
        assert getattr(ngsolve.config, flag) is False
    assert ngsolve.config.USE_UMFPACK is True
    non_local = [p for p in lock["package"] if p["name"] != "nanopnp"]
    assert all("wheels" in p for p in non_local)


def test_ngsolve_newton_and_webgui_api() -> None:
    sig = inspect.signature(ngsolve.solvers.Newton)
    assert "a" in sig.parameters and "u" in sig.parameters and "dampfactor" in sig.parameters
    shape = occ.Rectangle(1.0, 1.0).Face()
    mesh = ngsolve.Mesh(occ.OCCGeometry(shape, dim=2).GenerateMesh(maxh=0.3))
    fes = ngsolve.H1(mesh, order=2)
    u, v = fes.TnT()
    form = ngsolve.BilinearForm(fes)
    form += (ngsolve.grad(u) * ngsolve.grad(v) + u * v) * ngsolve.dx
    gfu = ngsolve.GridFunction(fes)
    gfu.Set(ngsolve.x + ngsolve.y)
    form.AssembleLinearization(gfu.vec)
    assert np.linalg.norm(form.mat.AsVector().FV().NumPy()) > 0.0
    scene = ngsolve.webgui.Draw(gfu, mesh, order=2, show=False)
    data = scene.GetData()
    dumped = json.dumps(data)
    per_el = len(dumped.encode("utf-8")) / mesh.ne
    assert 150.0 <= per_el <= 600.0
    html = scene.GenerateHTML()
    assert "webgui" in html


def test_webgui_region_draw_and_tarball_contents() -> None:
    mesh = CylindricalPoreGeometry(2.0, 13.0, 25.0).generate(maxh_nm=5.0)
    fes = ngsolve.H1(mesh, order=2)
    gfu = ngsolve.GridFunction(fes)
    gfu.Set(ngsolve.x)
    whole = json.dumps(ngsolve.webgui.Draw(gfu, mesh, show=False, order=2).GetData())
    fluid = json.dumps(
        ngsolve.webgui.Draw(
            gfu, mesh.Materials("electrolyte|cis|trans"), show=False, order=2
        ).GetData()
    )
    assert len(fluid) < len(whole)
    vec_cf = ngsolve.CoefficientFunction((ngsolve.x, ngsolve.y))
    vec_scene = json.dumps(
        ngsolve.webgui.Draw(
            vec_cf, mesh.Materials("electrolyte|cis|trans"), show=False, order=2
        ).GetData()
    )
    assert len(vec_scene) > len(fluid)
    tarball = okf.REPOSITORY / "third_party/webgui-0.2.39.tgz"
    assert tarball.stat().st_size == 503_052
    with tarfile.open(tarball, "r:gz") as archive:
        names = set(archive.getnames())
        assert "package/src/scene.ts" in names
        js_bytes = archive.extractfile("package/dist/webgui.js")
        assert js_bytes is not None
        js_text = js_bytes.read()
    assert len(js_text) == 779_484
    assert b"@license" in js_text and b"dat.gui" in js_text


def test_mdanalysis_and_gemmi_wheel_and_format_facts() -> None:
    assert callable(align.AlignTraj) and callable(align.rotation_matrix)
    for key in ("CIF", "MMCIF", "PDBX"):
        assert key not in MDAnalysis._PARSERS and key not in MDAnalysis._READERS
    with pytest.raises(ImportError):
        __import__("MDAnalysis.topology.PDBxParser")
    lock = tomllib.loads((okf.REPOSITORY / "uv.lock").read_text(encoding="utf-8"))
    gemmi_pkg = next(p for p in lock["package"] if p["name"] == "gemmi")
    urls = [w["url"] for w in gemmi_pkg["wheels"]]
    for py in ("cp311", "cp312", "cp313", "cp314"):
        assert any(py in u and "manylinux" in u for u in urls)
        assert any(py in u and "musllinux" in u for u in urls)
        assert any(py in u and "macosx" in u for u in urls)
        assert any(py in u and "win_amd64" in u for u in urls)


def test_mdanalysis_density_analysis_is_histogram_only() -> None:
    sig = inspect.signature(density.DensityAnalysis.__init__)
    assert "kernel" not in sig.parameters
    src = inspect.getsource(density.DensityAnalysis)
    assert "histogramdd" in src


def test_griddata_exporters_mrc_float32_and_2d_refusal(tmp_path: Path) -> None:
    empty = gridData.core.Grid()
    assert "CCP4" not in empty._exporters
    assert "DX" in empty._exporters and "MRC" in empty._exporters
    assert "CCP4" in empty._loaders and "MRC" in empty._loaders and "DX" in empty._loaders
    assert "MAP" not in empty._loaders
    arr3 = np.arange(12, dtype=np.float64).reshape((4, 3, 1)) + 0.123456789123
    grid3 = gridData.core.Grid(arr3, origin=(0.0, 0.0, 0.0), delta=(0.05, 0.05, 0.05))
    with pytest.raises(ValueError, match="CCP4"):
        grid3.export(str(tmp_path / "x.ccp4"), file_format="ccp4")
    mrc_path = tmp_path / "x.map"
    grid3.export(str(mrc_path), file_format="MRC")
    with pytest.raises(ValueError, match="MAP"):
        gridData.core.Grid(str(mrc_path))
    reloaded = gridData.core.Grid(str(mrc_path), file_format="MRC")
    assert reloaded.grid.dtype == np.float32
    assert np.allclose(reloaded.grid, arr3.astype(np.float32))
    assert reloaded.delta[0] == pytest.approx(float(np.float32(0.05)), rel=0, abs=1e-9)
    grid2 = gridData.core.Grid(np.ones((4, 3)), origin=(0.0, 0.0), delta=(0.1, 0.1))
    with pytest.raises(TypeError):
        grid2.export(str(tmp_path / "bad.dx"), file_format="DX")


def test_pyproject_requires_python_311_and_griddata_12() -> None:
    pyproject = tomllib.loads((okf.REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["requires-python"] == ">=3.11,<3.15"
    structure = pyproject["project"]["optional-dependencies"]["structure"]
    assert any(dep.startswith("MDAnalysis>=2.10") for dep in structure)
    assert any(dep.startswith("GridDataFormats>=1.2") for dep in structure)
    assert any(dep.startswith("pdb2pqr>=3.7") for dep in structure)
    lock = tomllib.loads((okf.REPOSITORY / "uv.lock").read_text(encoding="utf-8"))
    versions = {p["name"]: p["version"] for p in lock["package"] if "version" in p}
    assert versions["mdanalysis"] == "2.10.0"
    assert versions["griddataformats"] == "1.2.0"
    assert versions["pdb2pqr"] == "3.7.1"


def test_mdanalysis_and_gemmi_blank_and_odd_fields(tmp_path: Path) -> None:
    pdb_blank = (
        "ATOM      1  CA  ALA A   1       1.000   2.000   3.000  1.00  0.00            \nEND\n"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe = MDAnalysis.Universe(io.StringIO(pdb_blank), format="PDB")
        assert not hasattr(universe.atoms, "elements")
        assert list(universe.atoms.segids) == ["A"]
        assert universe.trajectory.dt == 1.0
    pdb_mixed = (
        "ATOM      1  CA  ALA A   1       1.000   2.000   3.000  1.00  0.00           C\n"
        "ATOM      2  CB  ALA A   1       2.000   2.000   3.000  1.00  0.00            \n"
        "END\n"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe_mixed = MDAnalysis.Universe(io.StringIO(pdb_mixed), format="PDB")
        assert list(universe_mixed.atoms.elements) == ["C", ""]
    base = gemmi.read_structure(str(okf.REPOSITORY / "tests/data/structures/2wcd.cif.gz"))
    sub = gemmi.Structure()
    model = gemmi.Model(1)
    chain_src = base[0][0]
    chain_new = gemmi.Chain(chain_src.name)
    res_new = chain_src[0].clone()
    while len(res_new) > 1:
        del res_new[1]
    chain_new.add_residue(res_new)
    model.add_chain(chain_new)
    sub.add_model(model)
    doc = sub.make_mmcif_document()
    block = doc[0]
    block.find_loop("_atom_site.type_symbol")[0] = "?"
    block.find_loop("_atom_site.auth_asym_id")[0] = "B"
    block.find_loop("_atom_site.auth_seq_id")[0] = "42"
    structure = gemmi.make_structure_from_block(block)
    chain = structure[0][0]
    residue = chain[0]
    atom = residue[0]
    assert chain.name == "B"
    assert residue.seqid.num == 42
    assert atom.element.name == "X"


def test_mdanalysis_trajectory_formats_and_dt(tmp_path: Path) -> None:
    coords = np.array(
        [
            [[10.0, 20.0, 130.0], [30.0, 40.0, 50.0]],
            [[11.0, 21.0, 130.5], [31.0, 41.0, 50.5]],
            [[12.0, 22.0, 131.0], [32.0, 42.0, 51.0]],
        ],
        dtype=np.float32,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe = MDAnalysis.Universe.empty(2, trajectory=True)
        universe.load_new(coords.copy())
        for suffix, expected_dt, tol_angstrom in (
            ("dcd", 1.0, 0.0),
            ("ncdf", 0.0, 0.0),
            ("trr", 0.0, 2e-5),
            ("xtc", 0.0, 6e-3),
        ):
            path = tmp_path / f"traj.{suffix}"
            with MDAnalysis.Writer(str(path), n_atoms=2) as writer:
                for _ts in universe.trajectory:
                    writer.write(universe.atoms)
            loaded = MDAnalysis.Universe(str(path))
            if suffix in ("xtc", "trr", "ncdf"):
                assert loaded.trajectory[0].time == pytest.approx(0.0)
            else:
                assert loaded.trajectory.dt == pytest.approx(expected_dt)
            read_coords = np.stack([loaded.atoms.positions.copy() for _ in loaded.trajectory])
            assert np.max(np.abs(read_coords - coords)) <= tol_angstrom


def test_numpy_unicode_array_strips_trailing_nul() -> None:
    arr = np.array(["ALA"], dtype="<U3")
    assert np.char.add(arr, "\x00")[0] == "ALA"
    assert np.char.add(arr, "\t")[0] == "ALA\t"


def test_pdb2pqr_cli_parser_and_propka_annotations() -> None:
    parser = pdb2pqr_main.build_main_parser()
    option_strings = set(parser._option_string_actions)
    for flag in (
        "--ff",
        "--ffout",
        "--with-ph",
        "--titration-state-method",
        "--drop-water",
        "--keep-chain",
    ):
        assert flag in option_strings
    ff_choices = {c.upper() for c in parser._option_string_actions["--ff"].choices}
    assert {"CHARMM", "AMBER", "PARSE"} <= ff_choices
    method_choices = tuple(parser._option_string_actions["--titration-state-method"].choices)
    assert method_choices == ("propka",)
    restore_propka_annotations()
    instance = propka_parameters.Parameters()
    assert isinstance(instance.__annotations__, dict)


def test_shapely_and_skimage_contour_and_offset_facts() -> None:
    line = LineString([(0.0, 0.0), (1.0, 0.0)])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        offset = line.parallel_offset(0.1, "left")
    assert not caught and not offset.is_empty
    grid = np.zeros((11, 11), dtype=float)
    grid[3:8, 3:8] = 1.0
    loops = measure.find_contours(grid, 0.5, positive_orientation="high")
    assert len(loops) == 1
    rz = loops[0][:, ::-1]
    signed_area = 0.5 * np.sum(rz[:-1, 0] * rz[1:, 1] - rz[1:, 0] * rz[:-1, 1])
    assert signed_area < 0.0
    edge_grid = np.zeros((5, 5), dtype=float)
    edge_grid[:, :2] = 1.0
    open_contour = measure.find_contours(edge_grid, 0.5, positive_orientation="high")[0]
    assert not np.allclose(open_contour[0], open_contour[-1])
    delta = 0.2
    l_shape = box(0.0, 0.0, 2.0, 2.0).difference(box(1.0, 1.0, 2.0, 2.0))
    closed = l_shape.buffer(delta, quad_segs=8, join_style="round").buffer(
        -delta, quad_segs=8, join_style="round"
    )
    expected_gain = delta**2 * (1.0 - math.pi / 4.0)
    assert closed.area - l_shape.area == pytest.approx(expected_gain, rel=2e-2)
    assert shapely.__version__ == "2.1.2"


def test_netgen_vol_round_trip_and_read_gmsh_msh41_failure(tmp_path: Path) -> None:
    mesh = CylindricalPoreGeometry(2.0, 13.0, 25.0).generate(maxh_nm=5.0)
    vol_path = tmp_path / "pore.vol"
    mesh.ngmesh.Save(str(vol_path))
    reloaded = ngsolve.Mesh(str(vol_path))
    assert reloaded.GetMaterials() == mesh.GetMaterials()
    assert reloaded.GetBoundaries() == mesh.GetBoundaries()
    msh41 = tmp_path / "four_one.msh"
    msh41.write_text(
        "$MeshFormat\n4.1 0 8\n$EndMeshFormat\n$Entities\n0 0 0 0\n$EndEntities\n",
        encoding="utf-8",
    )
    with pytest.raises((ValueError, IndexError)):
        read_gmsh.ReadGmsh(str(msh41))


def test_meshio_msh_stdout_and_xdmf_information_quirks(tmp_path: Path) -> None:
    assert meshio._helpers.extension_to_filetypes[".msh"] == ["ansys", "gmsh"]
    xdmf_path = tmp_path / "bad_info.xdmf"
    xdmf_path.write_text(
        '<?xml version="1.0" ?>\n'
        '<Xdmf Version="3.0">\n'
        "  <Domain>\n"
        '    <Information Name="scales"><Scale unit="nm"/></Information>\n'
        '    <Grid Name="mesh" GridType="Uniform">\n'
        '      <Topology TopologyType="Triangle" NumberOfElements="0"/>\n'
        '      <Geometry GeometryType="XY"/>\n'
        "    </Grid>\n"
        "  </Domain>\n"
        "</Xdmf>\n",
        encoding="utf-8",
    )
    with pytest.raises(meshio.ReadError, match="Only supports one grid"):
        meshio.xdmf.read(str(xdmf_path))


def test_netgen_occ_orientation_glue_compound_and_edge_facts() -> None:
    ccw = occ.WorkPlane().MoveTo(0, 0).LineTo(1, 0).LineTo(1, 1).LineTo(0, 1).Close().Face()
    cw = occ.WorkPlane().MoveTo(0, 0).LineTo(0, 1).LineTo(1, 1).LineTo(1, 0).Close().Face()
    assert ccw.mass > 0.0 and cw.mass < 0.0
    left = occ.MoveTo(0, 0).Rectangle(1, 1).Face()
    right = occ.MoveTo(1, 0).Rectangle(1, 1).Face()
    left.bc("left")
    right.bc("right")
    glued = occ.Glue([left, right])
    comp = occ.Compound([left, right])
    mesh_glued = ngsolve.Mesh(occ.OCCGeometry(glued, dim=2).GenerateMesh(maxh=0.5))
    mesh_comp = ngsolve.Mesh(occ.OCCGeometry(comp, dim=2).GenerateMesh(maxh=0.5))
    assert mesh_glued.nv < mesh_comp.nv
    with pytest.raises(Exception, match="compound"):
        _ = (left - right).name
    arc_edge = occ.Circle(occ.Pnt(0, 0, 0), occ.Vec(0, 0, 1), 2.0)
    assert list(arc_edge.faces) == []
    t0, t1 = arc_edge.parameter_interval
    mid = arc_edge.Value(0.5 * (t0 + t1))
    assert math.hypot(mid.x, mid.y) == pytest.approx(2.0)
    assert math.hypot(arc_edge.center.x, arc_edge.center.y) < 1e-12
    face_edges = [set(f.edges) for f in glued.faces]
    assert len(face_edges[0] & face_edges[1]) == 1
    assert len(set(glued.edges)) == 7


def test_cli_deferred_imports_and_hashing_duck_typing() -> None:
    hashing_tree = ast.parse(
        (okf.REPOSITORY / "src/nanopnp/core/hashing.py").read_text(encoding="utf-8")
    )
    imported = [
        alias.name
        for node in hashing_tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    ] + [node.module or "" for node in hashing_tree.body if isinstance(node, ast.ImportFrom)]
    assert not any(name.startswith("numpy") for name in imported)
    for entry in stages._REGISTRY.values():
        assert ":" in entry.target
    table_keys = set(errors.EXIT_CODES)
    assert all(":" in k for k in table_keys)

    class SubMissingError(FileNotFoundError):
        pass

    assert errors.classify(SubMissingError("x")) == errors.EXIT_CASE
    code = (
        "import sys, nanopnp.io.case; "
        "subs = sorted(m for m in sys.modules if m.startswith('nanopnp.') and m.count('.') == 1); "
        "assert subs == ['nanopnp.core', 'nanopnp.io'], subs; "
        "assert 'ngsolve' not in sys.modules and 'numpy' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_gitattributes_marks_data_binary_and_crlf_moves_file_hash(tmp_path: Path) -> None:
    attrs = (okf.REPOSITORY / ".gitattributes").read_text(encoding="utf-8")
    assert "data/** -text" in attrs
    src = okf.REPOSITORY / "data/corrections/willems2020_nacl.yaml"
    raw = src.read_bytes()
    assert b"\r\n" not in raw
    crlf = tmp_path / "willems2020_nacl.yaml"
    crlf.write_bytes(raw.replace(b"\n", b"\r\n"))
    assert hashing.file_hash(src) != hashing.file_hash(crlf)


def test_ngsolve_stubs_have_no_py_typed_and_invalid_init_pyi() -> None:
    ngs_dir = Path(ngsolve.__file__).resolve().parent
    assert not (ngs_dir / "py.typed").exists()
    init_pyi = ngs_dir / "__init__.pyi"
    assert init_pyi.is_file()
    with pytest.raises(SyntaxError):
        ast.parse(init_pyi.read_text(encoding="utf-8"))
    assert core_typing.Mesh is Any
