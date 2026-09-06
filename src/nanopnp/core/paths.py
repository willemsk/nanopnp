"""Filesystem locations of packaged data and of the result store.

The correction parameter files live at the repository root (``data/corrections``)
as specified in ``SPECIFICATION.md`` section 11, and are force-included into the
wheel under ``nanopnp/data``; ``data/geometry`` ships the same way and by the same
rule. Both layouts resolve here so that code and tests never have to know which
one they are running against.
"""

from __future__ import annotations

import os
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


GEOMETRY_DIR: Path = DATA_DIR / "geometry"
"""Shipped geometry fixtures: pore profile tables and the polygons derived from them."""


def available_corrections() -> tuple[str, ...]:
    """Return the names of every installed correction parameter file, sorted.

    Adding an electrolyte is a data file, never a code change (FR-16, ADR-005),
    so the set of selectable correction models is whatever is on disk here.
    """
    if not CORRECTIONS_DIR.is_dir():
        return ()
    return tuple(sorted(path.stem for path in CORRECTIONS_DIR.glob("*.yaml")))


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


def profile_file(name: str) -> Path:
    """Return the path of a named pore-profile fixture in :data:`GEOMETRY_DIR`.

    Parameters
    ----------
    name
        Fixture name without its suffix, e.g. ``"clya_reference_profile"``.

    Returns
    -------
    Path
        Path to ``<name>.yaml``.

    Raises
    ------
    FileNotFoundError
        If no such fixture is installed; the message names the directory
        searched, as :func:`correction_file` does.
    """
    path = GEOMETRY_DIR / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no geometry profile {name!r} in {GEOMETRY_DIR}")
    return path


STORE_ROOT_VARIABLE = "NANOPNP_STORE"
"""Environment variable naming the artefact and result store."""

DEFAULT_STORE_DIRNAME = "nanopnp-store"
"""Store directory created in the working directory when nothing else is set."""


def store_root() -> Path:
    """Return the root of the content-addressed artefact and result store.

    ``$NANOPNP_STORE`` if it is set, else ``./nanopnp-store`` in the working
    directory. A platform cache directory would be tidier for the desktop shell
    but would need another dependency and would put a run's outputs somewhere a
    user has to be told about; a visible default is the one a reader can find.

    Returns
    -------
    Path
        The store root, expanded and made absolute. It is not created here:
        :class:`nanopnp.io.store.Store` creates it on first write, so that
        merely reporting the environment (``nanopnp --env``) leaves no
        directories behind.
    """
    configured = os.environ.get(STORE_ROOT_VARIABLE)
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / DEFAULT_STORE_DIRNAME).resolve()


REFERENCE_DATA_VARIABLE = "NANOPNP_REFERENCE_DATA"
"""Environment variable naming the directory of archived Tier-3 reference files."""


def reference_data_root() -> Path | None:
    """Return the directory of archived reference files, or ``None`` if unset.

    Tier 3 compares against the reference implementation's own inputs and
    outputs, and some of those are far too large to ship: the delivered ClyA
    ``rho_q`` table alone is 77 MB of text. They are named by
    ``$NANOPNP_REFERENCE_DATA`` rather than vendored, so that a Tier-3 test
    *skips* where the archive is absent instead of failing, and so that no test
    ever reaches the network for one (section 7.1).

    Returns
    -------
    Path or None
        The configured directory, expanded and made absolute, or ``None`` when
        the variable is unset or names something that is not a directory. A
        misconfigured path and an unset one are deliberately the same answer
        here: both mean the archive is unavailable, and :func:`reference_file`
        is where the distinction would matter if it ever did.
    """
    configured = os.environ.get(REFERENCE_DATA_VARIABLE)
    if not configured:
        return None
    root = Path(configured).expanduser().resolve()
    return root if root.is_dir() else None


def reference_file(name: str) -> Path | None:
    """Return an archived reference file by name, or ``None`` if unavailable.

    Parameters
    ----------
    name
        The file's name within the archive, e.g. ``"prod5_clya_charge"``.

    Returns
    -------
    Path or None
        The file, or ``None`` when the archive is not configured or does not
        carry it. ``None`` rather than an exception because the caller is a
        Tier-3 skip condition, and a test that raised on an absent archive
        would make the whole tier unrunnable off the machine that holds it.
    """
    root = reference_data_root()
    if root is None:
        return None
    path = root / name
    return path if path.is_file() else None
