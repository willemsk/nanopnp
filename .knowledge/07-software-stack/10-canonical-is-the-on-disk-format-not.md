---
type: Library Behaviour
title: 10. `canonical()` is the on-disk format, not only the hash input
---

## 10. `canonical()` is the on-disk format, not only the hash input

`nanopnp.core.hashing.canonical` produces the bytes that are hashed **and** the bytes that
`manifest.json` and `run.json` hold — both are written through it, so the file a reader opens and
the bytes that were hashed cannot disagree. The consequence is easy to miss and produces a
confusing failure: every float on disk is a one-key wrapper `{"__f__": <float.hex()>}`, so
`json.loads` of a run record yields `{"current_A": {"__f__": "0x1.3e...p-35"}}` rather than a
number.

Comparing such a record against live values without decoding it does not report a *different*
number — it reports a **missing** one, because a flatten-to-dotted-paths comparison yields
`current_A.__f__` on one side and `current_A` on the other **[tested]**. `decode_floats` is the
inverse and belongs to any reader of these files.

It is deliberately not a full inverse of `canonical`: an array encodes as dtype, shape and a
*digest* of its bytes (`"__a__"`), which nothing can undo, and is left as it stands.

The 12-hex-character display prefix (`core.hashing.SHORT_LENGTH`) is 48 bits; over the 3,675-solve
datum at about six artefacts each (n ≈ 2.2 × 10⁴) the collision probability is n²/2N ≈ 8.6 × 10⁻⁷, adequate
for a label. The store keys on the full digest, never on the prefix **[verified]** (`core/hashing.py`).

