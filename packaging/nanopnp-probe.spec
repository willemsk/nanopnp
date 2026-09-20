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
# Run as a Python script by PyInstaller, so ruff and mypy do not see it: it has
# no imports of its own, and `Analysis`, `PYZ`, `EXE`, `COLLECT` and `SPECPATH`
# are injected into its namespace.
# ruff: noqa

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

_root = Path(SPECPATH).parent

# The compiled extensions, their data files and their transitive shared
# libraries. `collect_all` rather than a hidden-import list because both
# packages load submodules dynamically and carry data trees PyInstaller's
# static analysis does not see -- and because a payload missing from the bundle
# is exactly what RSK-13 is about, so the collection is deliberately wide.
_datas, _binaries, _hiddenimports = [], [], []
for _package in ("ngsolve", "netgen"):
    _package_datas, _package_binaries, _package_hidden = collect_all(_package)
    _datas += _package_datas
    _binaries += _package_binaries
    _hiddenimports += _package_hidden

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
