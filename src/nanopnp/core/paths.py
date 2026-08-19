"""Filesystem locations of packaged data.

The correction parameter files live at the repository root (``data/corrections``)
as specified in ``SPECIFICATION.md`` section 11, and are force-included into the
wheel under ``nanopnp/data``. Both layouts resolve here so that code and tests
never have to know which one they are running against.
"""

from __future__ import annotations

from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_PACKAGED_DATA = _PACKAGE_ROOT / "data"
_REPO_DATA = _PACKAGE_ROOT.parents[1] / "data"

PACKAGE_ROOT: Path = _PACKAGE_ROOT
"""Directory containing the installed ``nanopnp`` package."""

DATA_DIR: Path = _PACKAGED_DATA if _PACKAGED_DATA.is_dir() else _REPO_DATA
"""Root of the shipped data files, wherever they were installed."""

CORRECTIONS_DIR: Path = DATA_DIR / "corrections"
"""Versioned ePNP-NS correction parameter files (FR-16)."""


def correction_file(name: str) -> Path:
    """Return the path of a named correction parameter file.

    Parameters
    ----------
    name
        Registered model name, e.g. ``"willems2020_nacl"``.

    Returns
    -------
    Path
        Path to ``<name>.yaml``.

    Raises
    ------
    FileNotFoundError
        If no such file is installed; the message names the directory searched.
    """
    path = CORRECTIONS_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no correction file {name!r} in {CORRECTIONS_DIR}")
    return path
