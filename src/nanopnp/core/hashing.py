"""Canonical serialisation and the content hashes every artefact is keyed on.

``SPECIFICATION.md`` section 5.3.2 requires every artefact to carry a content
hash "over a canonical serialisation of its payload and the parameters that
produced it", and makes that hash the cache key: a stage whose input hashes and
parameters are unchanged is not recomputed, and a hand-substituted artefact
registers as a changed input.

The hash is taken over the *validated* payload, never over file text. YAML gives
``1`` an ``int`` and ``1.0`` a ``float``, orders keys freely, carries comments
and admits several spellings of the same scalar; validation collapses all of
that onto one shape. Hashing afterwards is what makes FR-26's round trip true by
construction rather than something the serialiser must be defended against.

Three properties follow from the encoding below, and each is a Tier-1 test.
The hash is stable across processes and platforms, because nothing in it depends
on dict insertion order, ``repr`` formatting, memory layout or the filesystem.
It changes under any change to a payload or a parameter, because every leaf
reaches the digest. And a changed input hash changes the output hash, because
the input hashes are inside the digest.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypeAlias

Canonicalisable: TypeAlias = Any
"""Any value the canonical encoder accepts.

A mapping, a list or tuple, a string, a bool, an int, a float, ``None`` or a
NumPy array, nested arbitrarily. Named rather than written as a bare ``Any`` so
that the signature says what a caller may pass, which ``Any`` does not.
"""

JSONValue: TypeAlias = "bool | int | float | str | list[JSONValue] | dict[str, JSONValue] | None"
"""The JSON tree the encoder produces, before it is serialised to bytes."""

HASH_PREFIX = b"nanopnp/hash/v1"
"""Domain separator, so a digest cannot be confused with a bare payload hash."""

SHORT_LENGTH = 12
"""Hex characters of the display and directory-fan-out prefix.

48 bits over the section 8.3 datum of 3,675 solves at about six artefacts each
(n ~ 2.2e4) gives a collision probability n^2 / 2N ~ 8.6e-7. Adequate for a
label; the store keys on the full digest and never on this.
"""

_CHUNK = 1 << 20
"""Bytes read per iteration by :func:`file_hash`."""


class CanonicalisationError(ValueError):
    """A value has no canonical serialisation, so it cannot enter a hash.

    A ``ValueError``, because the offending value is data rather than a type
    error in the caller: a ``set`` has no canonical order and a ``Path`` names a
    file instead of describing it, and in both cases the fix is to pass
    something else.
    """


def canonical(obj: Canonicalisable) -> bytes:
    """Return the canonical UTF-8 serialisation of ``obj``.

    Parameters
    ----------
    obj
        A tree of mappings, lists, tuples, strings, bools, integers, floats,
        ``None`` and NumPy arrays.

    Returns
    -------
    bytes
        Compact JSON with sorted keys and no non-ASCII escapes.

    Raises
    ------
    CanonicalisationError
        If any leaf has no canonical form, naming the dotted path to it.

    Notes
    -----
    The encoding, leaf by leaf:

    - mappings serialise with **sorted keys**, and every key must be a string;
    - lists and tuples preserve order, because order is meaning;
    - ``bool`` is checked before ``int``, ``bool`` being an ``int`` in Python;
    - floats encode as ``{"__f__": x.hex()}``: ``float.hex`` is the IEEE-754 bit
      pattern by definition, so it is exact and independent of the repr
      algorithm, and ``-0.0`` is normalised to ``0.0`` first — two spellings of
      a bias that resolve to the same run;
    - arrays encode as dtype, shape and a digest of their C-contiguous bytes,
      never as a nested list;
    - ``set`` is rejected: a set of mixed types has no canonical order, so
      accepting one would make the hash depend on insertion;
    - ``Path`` is rejected: a path in a hash makes a case unreproducible on
      another machine and a moved file a changed input. Hash the *contents*
      with :func:`file_hash` and record the path in the manifest.
    """
    return json.dumps(
        _encode(obj, "$"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def _encode(obj: Canonicalisable, path: str) -> JSONValue:
    """Return ``obj`` as a JSON-encodable tree; ``path`` names it in diagnostics."""
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
    """Return whether ``obj`` looks like a NumPy array or scalar.

    Duck-typed rather than ``isinstance(obj, np.ndarray)`` so that importing this
    module never imports NumPy: it costs about 67 ms, and the CLI, the GUI and
    the sweep runner all import stage modules purely to introspect them (FR-27).
    """
    return hasattr(obj, "dtype") and hasattr(obj, "shape") and hasattr(obj, "tobytes")


def _encode_array(array: Canonicalisable, path: str) -> JSONValue:
    """Return an array as dtype, shape and a digest of its contiguous bytes."""
    import numpy as np

    if array.shape == ():
        # A 0-d array or a NumPy scalar is a number, and hashing it as one keeps
        # ``np.float64(1.5)`` and ``1.5`` — which resolve to the same run —
        # hashing identically.
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
    """Return a document read back from a canonical file with its floats restored.

    :func:`canonical` writes every float as ``{"__f__": x.hex()}``, and that is
    the encoding of the files it produces as well as of the bytes that are
    hashed — ``manifest.json`` and ``run.json`` are both written through it. A
    reader that wants the numbers back rather than the digest has to undo the
    one leaf that is not itself: ``json.loads`` restores mappings, lists,
    strings, integers and ``None`` unchanged, and turns a float into the
    one-key mapping this function unwraps.

    Parameters
    ----------
    value
        A tree as ``json.loads`` returned it.

    Returns
    -------
    JSONValue
        The same tree with every ``{"__f__": <hex>}`` mapping replaced by the
        float it encodes.

    Notes
    -----
    Not an inverse of :func:`canonical` in general, and deliberately not named
    as one: an array encodes as a *digest* of its bytes (``"__a__"``), which no
    reader can undo, and is left as it stands. A mapping that carries ``__f__``
    beside other keys is left alone too — the wrapper the encoder writes has
    exactly one key, so anything else is a document that happens to use the
    name.
    """
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
    """Return the sha256 content hash of one artefact, as 64 hex characters.

    Parameters
    ----------
    schema
        The artefact's schema identifier, e.g. ``"nanopnp/case/v1"``. It is
        inside the digest so that two artefacts with coincidentally identical
        parameters cannot share a key.
    parameters
        The validated parameters that produced the artefact.
    inputs
        Name to content hash of every upstream artefact and input file. Because
        these are inside the digest, a hand-substituted input changes the output
        hash by construction rather than by a check somebody must remember to
        run (section 5.3.2).

    Returns
    -------
    str
        Lower-case hex sha256.
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
    """Return the sha256 of a file's contents, as 64 hex characters.

    Parameters
    ----------
    path
        File to read. Only its bytes reach the digest; its name and location do
        not, so moving a mesh does not invalidate the cache.
    """
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def short(digest: str, length: int = SHORT_LENGTH) -> str:
    """Return the display prefix of a hash; see :data:`SHORT_LENGTH`."""
    return digest[:length]
