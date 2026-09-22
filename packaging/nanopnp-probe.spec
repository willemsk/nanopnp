# PyInstaller recipe for the RSK-13 packaging probe (SPECIFICATION.md section 8.2
# criterion 4, as amended by section 8.2.1 A4; ADR-004's packaging NOTE).
#
# ONE-DIR, NOT ONE-FILE, for two independent reasons.
#
#   LGPL-3. PySide6 and Qt are used under the LGPL option (CON-09), which
#   requires that a recipient be able to replace the covered libraries. A
#   directory of shared libraries satisfies that plainly; an opaque
#   self-extracting executable invites the argument.
#
#   Qt WebEngine. Its renderer is a separate helper executable, which a one-file
#   extractor must locate at run time inside a temporary directory -- a failure
#   mode with nothing to do with this project.
#
# Built by the gated `bundle` job of .github/workflows/ci.yml on every push:
#
#     uv run pyinstaller --clean --noconfirm packaging/nanopnp-probe.spec
#     dist/nanopnp-probe/nanopnp-probe --selftest
#
# Run as a Python script by PyInstaller, so ruff and mypy do not see it.
# `Analysis`, `PYZ`, `EXE`, `COLLECT`, `SPECPATH` and `workpath` are injected
# into its namespace.
# ruff: noqa

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

_root = Path(SPECPATH).parent

# The compiled extensions, their data files and their transitive shared
# libraries. `collect_all` rather than a hidden-import list because both
# packages load submodules dynamically and carry data trees PyInstaller's
# static analysis does not see -- and because a payload missing from the bundle
# is exactly what RSK-13 is about, so the collection is deliberately wide.
#
# `ngsolve_openblas` is its own distribution: `ngsolve/__init__.py` imports it
# and preloads the BLAS it carries as package data, which static analysis does
# not see, so the bundle had `ngsolve_openblas/__init__.py` and no library. It
# has no macOS wheel, and `ngsolve` does not import it there.
import importlib.util as _importlib_util

_datas, _binaries, _hiddenimports = [], [], []
for _package in ("ngsolve", "netgen", "ngsolve_openblas"):
    if _importlib_util.find_spec(_package) is None:
        continue
    _package_datas, _package_binaries, _package_hidden = collect_all(_package)
    _datas += _package_datas
    _binaries += _package_binaries
    _hiddenimports += _package_hidden

# OPEN CASCADE, AND WHY `collect_all("netgen")` DOES NOT CARRY IT.
#
# `import netgen` runs `netgen.load_occ_libs()`, which preloads the OCCT shared
# libraries in dependency order from the paths the `netgen-occt` distribution's
# RECORD lists. That wheel installs them OUTSIDE site-packages -- `bin/TK*.dll`
# at the environment root on Windows, `lib/libTK*.so.*` on Linux -- so RECORD
# names them `../../bin/TKernel.dll`, relative to the dist-info's parent. Two
# things then break in a bundle, independently:
#
#   1. PyInstaller never finds the libraries: they are on none of the paths it
#      searches, and the build log says `Library not found: could not resolve
#      'TKernel.dll', dependency of ...\netgen\nglib.dll` once per library.
#   2. The dist-info IS collected, so `load_occ_libs` does not take its
#      `PackageNotFoundError` no-op branch; but from `_internal/` every RECORD
#      entry points outside the bundle, `importlib.metadata`'s `files` drops
#      entries that do not exist (`skip_missing_files`, Python 3.12), and the
#      first lookup -- `lib_paths["tkernel"]` -- raises `KeyError: 'tkernel'`.
#
# So both halves are supplied here: the libraries go into the bundle root, and a
# rewritten dist-info whose RECORD names them by bare file name replaces the
# collected one, so that netgen's own loader, unchanged, finds them beside it.
# Nothing is Windows-specific; a Linux bundle failed identically without it.
import importlib.metadata as _metadata

_occt = _metadata.distribution("netgen-occt")
# The filter `load_occ_libs` itself applies. `files` has already dropped any
# entry that does not exist on this machine.
_occt_libraries = [
    Path(_entry.locate()).resolve()
    for _entry in _occt.files or []
    if _entry.match("*libTK*") or _entry.match("*.dll")
]
if not any(_path.name.lower().replace("lib", "").startswith("tkernel.") for _path in _occt_libraries):
    raise SystemExit(
        "netgen-occt lists no TKernel library in this environment; a bundle built now would "
        "fail on `import netgen` with KeyError: 'tkernel' (see the comment above)"
    )
_binaries += [(str(_path), ".") for _path in _occt_libraries]

_occt_metadata = Path(workpath) / "netgen-occt-metadata" / f"netgen_occt-{_occt.version}.dist-info"
_occt_metadata.mkdir(parents=True, exist_ok=True)
(_occt_metadata / "METADATA").write_text(_occt.read_text("METADATA"), encoding="utf-8")
(_occt_metadata / "RECORD").write_text(
    "".join(f"{_path.name},,\n" for _path in _occt_libraries), encoding="utf-8"
)
_occt_datas = [(str(_occt_metadata / "METADATA"), _occt_metadata.name)]
_occt_datas.append((str(_occt_metadata / "RECORD"), _occt_metadata.name))
# OCCT's LGPL-2.1 text travels with the libraries it covers.
for _entry in _occt.files or []:
    if _entry.match("*LICENSE*"):
        _occt_datas.append((str(Path(_entry.locate()).resolve()), _occt_metadata.name))

# The CON-11 licence notice travels beside the executable. `probe.licence_notice`
# looks for it at the bundle root first, and `--selftest` fails if it is absent:
# a bundle that cannot state its own obligations must not be distributed.
_datas.append((str(_root / "packaging" / "LICENSES-BUNDLE.md"), "."))

# The shipped correction parameter files (FR-16, section 11). The probe does not
# read them, but `core/paths.py` resolves them relative to the installed package
# and a bundle without them would import cleanly and then fail to validate any
# case -- which is the class of defect this bundle exists to find early.
_datas.append((str(_root / "data"), "nanopnp/data"))

a = Analysis(
    [str(_root / "src" / "nanopnp" / "gui" / "probe.py")],
    pathex=[str(_root / "src")],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=[*_hiddenimports, "nanopnp", "nanopnp.gui.probe"],
    hookspath=[],
    runtime_hooks=[],
    # PyQt is forbidden by CON-09. Excluded rather than merely unused, so that a
    # transitive dependency pulling one in fails the build rather than shipping
    # a GPL-3 library inside an LGPL bundle.
    excludes=["PyQt5", "PyQt6", "tkinter", "matplotlib"],
    noarchive=False,
)
# Swap the dist-info PyInstaller collected (it follows `load_occ_libs`'s
# `metadata("netgen-occt")` call) for the rewritten one above. A TOC entry is
# `(destination, source, typecode)`.
a.datas = [
    _entry for _entry in a.datas if not _entry[0].replace("\\", "/").startswith("netgen_occt-")
]
a.datas += [
    (f"{_destination}/{Path(_source).name}", _source, "DATA")
    for _source, _destination in _occt_datas
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="nanopnp-probe",
    debug=False,
    strip=False,
    # Compression is off: UPX mangles Qt WebEngine's helper executable, and the
    # bundle's size is not what criterion 4 is about.
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="nanopnp-probe",
)
