"""Loading of ePNP-NS correction parameter files.

A correction model is data, not code (FR-16, ADR-005): the fit coefficients live
in versioned YAML under ``data/corrections`` and are named from the case file by
string. This module only reads and validates the file; evaluation of the
correction forms belongs to the model classes of section 5.4.2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nanopnp.core.paths import correction_file

SCHEMA: str = "nanopnp/corrections/v1"
"""Schema identifier every correction file must declare."""


def load_corrections(name_or_path: str | Path) -> dict[str, Any]:
    """Load a correction parameter file by registered name or by path.

    Parameters
    ----------
    name_or_path
        Registered model name (e.g. ``"willems2020_nacl"``) or a path to a
        correction YAML file.

    Returns
    -------
    dict
        The parsed document.

    Raises
    ------
    ValueError
        If the document declares a schema this version does not understand; the
        message names both the file and the schema found.
    """
    path = (
        Path(name_or_path)
        if Path(name_or_path).suffix == ".yaml"
        else correction_file(str(name_or_path))
    )
    with path.open(encoding="utf-8") as handle:
        document: dict[str, Any] = yaml.safe_load(handle)
    schema = document.get("schema")
    if schema != SCHEMA:
        raise ValueError(f"{path}: expected schema {SCHEMA!r}, found {schema!r}")
    return document
