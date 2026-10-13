"""Filesystem locations of packaged data and of the result store."""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_PACKAGED_DATA = _PACKAGE_ROOT / "data"
_REPO_DATA = _PACKAGE_ROOT.parents[1] / "data"

PACKAGE_ROOT: Path = _PACKAGE_ROOT

DATA_DIR: Path = _PACKAGED_DATA if _PACKAGED_DATA.is_dir() else _REPO_DATA

CORRECTIONS_DIR: Path = DATA_DIR / "corrections"


GEOMETRY_DIR: Path = DATA_DIR / "geometry"


RADII_DIR: Path = DATA_DIR / "radii"


STRUCTURES_DIR: Path = DATA_DIR / "structures"


def available_corrections() -> tuple[str, ...]:
    if not CORRECTIONS_DIR.is_dir():
        return ()
    return tuple(sorted(path.stem for path in CORRECTIONS_DIR.glob("*.yaml")))


def correction_file(name: str) -> Path:
    path = CORRECTIONS_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no correction file {name!r} in {CORRECTIONS_DIR}")
    return path


def profile_file(name: str) -> Path:
    path = GEOMETRY_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no geometry profile {name!r} in {GEOMETRY_DIR}")
    return path


def radii_file(name: str) -> Path:
    path = RADII_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no radius set {name!r} in {RADII_DIR}")
    return path


def structure_file(name: str) -> Path:
    path = STRUCTURES_DIR / f"{name}.pdb"
    if not path.is_file():
        raise FileNotFoundError(f"no structure fixture {name!r} in {STRUCTURES_DIR}")
    return path


STORE_ROOT_VARIABLE = "NANOPNP_STORE"

DEFAULT_STORE_DIRNAME = "nanopnp-store"


def store_root() -> Path:
    configured = os.environ.get(STORE_ROOT_VARIABLE)
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / DEFAULT_STORE_DIRNAME).resolve()


REFERENCE_DATA_VARIABLE = "NANOPNP_REFERENCE_DATA"


def reference_data_root() -> Path | None:
    configured = os.environ.get(REFERENCE_DATA_VARIABLE)
    if not configured:
        return None
    root = Path(configured).expanduser().resolve()
    return root if root.is_dir() else None


def reference_file(name: str) -> Path | None:
    root = reference_data_root()
    if root is None:
        return None
    path = root / name
    return path if path.is_file() else None
