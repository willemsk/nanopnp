"""Canonical serialisation and the content hashes every artefact is keyed on."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypeAlias

Canonicalisable: TypeAlias = Any

JSONValue: TypeAlias = "bool | int | float | str | list[JSONValue] | dict[str, JSONValue] | None"

HASH_PREFIX = b"nanopnp/hash/v1"

SHORT_LENGTH = 12

_CHUNK = 1 << 20


class CanonicalisationError(ValueError):
    """A value has no canonical serialisation, so it cannot enter a hash."""


def canonical(obj: Canonicalisable) -> bytes:
    """Return the canonical UTF-8 JSON of ``obj``; CanonicalisationError on an unsupported leaf."""
    return json.dumps(
        _encode(obj, "$"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _encode(obj: Canonicalisable, path: str) -> JSONValue:
    if obj is None:
        return None
    if isinstance(obj, bool):  # before int: bool is an int in Python
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):  # also catches numpy.float64, a float subclass
        return {"__f__": (0.0 if obj == 0.0 else obj).hex()}
    if isinstance(obj, str):
        return obj
    if isinstance(obj, Path):
        raise CanonicalisationError(
            f"{path}: a filesystem path cannot enter a content hash, because the same case would "
            "then hash differently on another machine and a moved file would read as a changed "
            "input; hash the file's contents with file_hash() and record the path in the manifest"
        )
    if isinstance(obj, (set, frozenset)):
        raise CanonicalisationError(
            f"{path}: a set has no canonical order, so its hash would depend on insertion order; "
            "pass a sorted list instead"
        )
    if _is_array(obj):
        return _encode_array(obj, path)
    if isinstance(obj, Mapping):
        encoded: dict[str, JSONValue] = {}
        for key, value in obj.items():
            if not isinstance(key, str):
                raise CanonicalisationError(
                    f"{path}: mapping keys must be strings to sort canonically, got "
                    f"{type(key).__name__} {key!r}"
                )
            encoded[key] = _encode(value, f"{path}.{key}")
        return encoded
    if isinstance(obj, (list, tuple)):
        return [_encode(item, f"{path}[{index}]") for index, item in enumerate(obj)]
    raise CanonicalisationError(
        f"{path}: no canonical serialisation for {type(obj).__name__}; convert it to a mapping, "
        "a sequence or a scalar before hashing it"
    )


def _is_array(obj: Canonicalisable) -> bool:
    return hasattr(obj, "dtype") and hasattr(obj, "shape") and hasattr(obj, "tobytes")


def _encode_array(array: Canonicalisable, path: str) -> JSONValue:
    import numpy as np

    if array.shape == ():
        # keeps ``np.float64(1.5)`` and ``1.5``, which resolve to the same run, hashing alike
        return _encode(array.item(), path)
    contiguous = np.ascontiguousarray(array)
    return {
        "__a__": {
            "dtype": str(contiguous.dtype),
            "shape": list(contiguous.shape),
            "bytes": hashlib.sha256(contiguous.tobytes()).hexdigest(),
        }
    }


def decode_floats(value: JSONValue) -> JSONValue:
    """Return a canonical document with floats restored; arrays stay as digests."""
    if isinstance(value, dict):
        if len(value) == 1:
            encoded = value.get("__f__")
            if isinstance(encoded, str):
                return float.fromhex(encoded)
        return {key: decode_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decode_floats(item) for item in value]
    return value


def content_hash(
    schema: str,
    parameters: Mapping[str, Canonicalisable],
    inputs: Mapping[str, str] | None = None,
) -> str:
    """Return the sha256 content hash of one artefact, as 64 lower-case hex characters.

    Parameters
    ----------
    inputs
        Upstream artefact and input-file hashes, keyed by name.
    """
    digest = hashlib.sha256()
    digest.update(HASH_PREFIX)
    digest.update(b"\0")
    digest.update(schema.encode("utf-8"))
    digest.update(b"\0")
    digest.update(canonical(parameters))
    digest.update(b"\0")
    digest.update(canonical(dict(sorted((inputs or {}).items()))))
    return digest.hexdigest()


def file_hash(path: str | Path) -> str:
    """Return the sha256 of a file's bytes, as 64 hex characters."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def short(digest: str, length: int = SHORT_LENGTH) -> str:
    """Return the display prefix of a hash; see :data:`SHORT_LENGTH`."""
    return digest[:length]
