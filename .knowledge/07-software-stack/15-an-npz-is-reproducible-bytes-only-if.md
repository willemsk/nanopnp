---
type: Library Behaviour
title: 15. An `.npz` is reproducible bytes only if nothing in it moves with the clock
description: An .npz is reproducible bytes only if nothing in it moves with the clock.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
---

## 15. An `.npz` is reproducible bytes only if nothing in it moves with the clock **[tested: pending]** {#15-an-npz-is-reproducible-bytes-only-if-nothing-in-it-moves-with-the-clock}

`numpy.savez` writes a zip whose entries carry a fixed modification date, so the same arrays saved
twice give the same bytes, seconds apart. A payload's recorded digest is therefore reproducible as
long as the arrays are. One scalar that is not, such as a wall-clock duration saved beside the
data, changes the bytes and so the digest: stage 7 once wrote `seconds` into `deposit.npz`,
and the same deposit computed twice read as two different payloads, and a reloaded one would have
read as hand-substituted (VER-23). The same holds for a summary the manifest copies: a time in it
gives every run its own manifest hash.

The rule (WP32 D15): no payload, and no stage-7 summary, records wall-clock time. Timings go
to the log and to the run record's per-stage `seconds`, which no key or manifest reads.
`tests/tier1/test_artefact_hashing.py::test_ver23_a_charged_walk_writes_the_same_bytes_into_two_stores`
walks a charged tube into two empty stores, finds every payload byte-identical, and shows that
restoring one `seconds` entry breaks it. Source: WP32 plan D15 and its Outcomes.

**Removing the time is a schema change, not just a code change [verified].** A store hit serves the
stored payload and summary unchanged, and the content hash covers the schema, the parameters and the
input hashes, not the payload. An entry written before the change keeps its key, so it keeps being
served with its old timings. Stage 7 therefore moved to `nanopnp/fields/v2` and
`nanopnp/charge-grid/v2`, which makes every old entry a miss (§5.3.2 stage-7 row, amended for WP32).
Source: the WP32 `/wp-ship` review.

