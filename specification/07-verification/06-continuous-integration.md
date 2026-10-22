---
type: Specification
title: "7.6 Continuous integration"
description: "Maps each CI trigger, a pull request, a push to main, or the nightly run, to the tiers and platforms it runs."
---

### 7.6 Continuous integration

| Trigger | Tiers run |
|---|---|
| A pull request | The per-push selection (Tier 1; Tier 2 without `nightly` or `slow`), on ubuntu, Python 3.14 |
| A push to `main` | The per-push selection on ubuntu, macOS and Windows, Python 3.14 |
| Nightly | 1 and 2 in full (`--nightly`, and the `slow` tests) on ubuntu, macOS and Windows, Python 3.14; 3, and 1 on Python 3.11 to 3.13 on the three platforms, recorded and not gated; a failed run opens an issue and blocks nothing |
| Before a tagged release | 1, 2, 3 and 4, Python 3.11 to 3.14, on the three platforms |
| Every push, prose-only pushes included | The strict documentation build of VER-45 |

The per-push selection is Tier 1, the Tier 2 tests that neither walk the pipeline nor carry `slow`,
example 01 while its solve takes under 60 s, and one charged walk, example 02's ePNP-NS pore with
its VER-62 golden (§8.2.13 N4).

Every run SHALL emit a provenance manifest recording input hashes, library versions, mesh hash,
solver settings, stabilisation mode and correction parameter file versions (FR-25).

NOTE (a gated test's runtime; WP33): every push pays for the tests of
Tiers 1 and 2, so their runtime is a cost. It is reduced by sharing identical
work, by dropping work whose result no assertion reads, by coarsening a discretisation where every
gate the test carries is measured to pass at the coarser setting with at least three times its
headroom, by splitting a file so that its parts run in parallel, or by moving a walk to `nightly` (§8.2.13 N4). No tolerance is loosened and no
oracle weakened to save time. A test that asserts a cold computation is never given a warm store.
A test moves to `slow` only if another test on every push gates the same claim on the same kind of
input.

NOTE (the development loop's timings): the commit hook, the push gate and a pull request's CI run are
reported, not enforced (§8.2.11 L2, L3, L8; §8.2.13 N4). Predicted: the commit hook about 90 s on four cores, the
push gate under 4 minutes after the test scope, a pull request under 6 minutes from its first job's start to its last job's
completion. Measured in the plan of WP44: the commit hook 187 to 220 s, the push gate 509 s, a pull
request 194 s. The floor of the push gate is example
07's walk (421 to 477 s), which the runtime NOTE above does not let the suite shorten. A slow loop is
met by the four ways of the runtime NOTE, never by loosening a tolerance or weakening an oracle.

NOTE (the per-push selection; §8.2.13 N4): a Tier-1 or Tier-2 test that walks the pipeline end to end
carries the marker `nightly`: an executed worked example of VER-46 other than example 01, or the
vendored 2WCD entry taken through the stages. Example 01 carries it only if its solve takes 60 s
or more on four cores; example 02's ePNP-NS leg with its VER-62 golden carries none, so a moved
physics number is caught before the merge. The nightly run, the release and a `--nightly` run
include them. A failed nightly run opens an issue titled `Nightly failed: <date> <sha7>` and blocks
nothing; a golden on another walk is caught the night after its merge. The selection leaves the
`nightly` tests out unless `--nightly` is passed or the test's file is named. That selection is
what `uv run pytest` runs; the commit hook runs every Tier 1 test without the `nightly` marker and
no Tier 2 test (§8.2.11 L2); the push gate (`gate.sh run`) runs the per-push selection. The marker
never goes on an analytic benchmark, which is the test that localises a failure (§7.1).

NOTE (Gmsh): `gate.sh run` and CI set `NANOPNP_REQUIRE_GMSH=1`, so a Gmsh that cannot import
fails instead of skipping, and the commit hook sets it only for a change to Gmsh's own code or
tests. No coverage is measured and no changed line is required to be executed (§8.2.13 N2).

NOTE (a golden asserted on more than one platform; WP35): a test that holds a computed number
against a recorded one, on every leg, asks one of two questions, and its tolerance follows the
question. Whether a change moved a number is asked on the mesh the number was recorded on, at
round-off, because one mesh and one build repeat bit for bit. Whether a platform's answer is still
right is asked on whatever mesh that platform deploys, and netgen's mesh moves with the platform and
with NumPy's runtime SIMD dispatch upstream of it, so it is held at a tolerance derived from the
spread measured between recorded meshes, with a stated safety factor and a ceiling well inside the
quantity's physical significance. The mesh's content hash decides which question a run answers; it
is never the assertion itself, except in one pinned reference environment, where a moved mesh is a
moved code path and fails. CI and the gate cap NumPy's dispatch at `X86_V3` with
`NPY_DISABLE_CPU_FEATURES`, so that every x86-64 Linux leg is that environment. VER-62 is the
instance, and `nanopnp.validation.stability` the mechanism a later golden reuses.

---

