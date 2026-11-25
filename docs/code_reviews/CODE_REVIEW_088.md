# Code review 088: WP6.06, the channel's axis at a ragged rim

2026-11-25 · PR #218, branch `claude/np-carry-wp-6-06-g7y44p`, head `a1a5428` on base `7ebfd4f` (`main`) · scope: the
PR's 24 files, +685 and −68, read from `gh pr diff 218`; the checkout was at the PR's head. Read in place:
`src/nanopnp/structure/cavity.py`, `structure/stage.py` and `structure/orient.py` whole, `io/artefact.py`
(`Artefact.hash`, `StructureArtefact`), `io/resolved.py` (`ResolvedStructure`, the solve's revision),
`pipeline/case.py` (`_resolve_structure`), `density/stage.py` (the key's inputs), `validation/comsol.py`
(`_stage7_recipe`), `core/stages.py` (the registry's description), the channel tests of
`tests/tier1/test_structure_axis.py` and `test_structure_stage.py`, §5.2's NOTE on stage 1, §5.3.2's NOTE on the
solution payload, VER-48 and VER-72, §8.2.55, the WP6.06 plan, the Phase 6 plan, the knowledge note on 2WCD's channel
axis, REV-279's row and section, `.claude/rules/python.md`, `.claude/workflow/core.md`, `np-implement/finish.md` and
`ci.yml`'s modes · level: xhigh, with `--fix` · status: completed.

Static review: no `gate.sh`, no `pytest --nightly`, no benchmark. Seven probes were run with `uv run --frozen python`,
each under a minute, on the test file's own walls: twelve degenerate atom sets through `channel_axis`; the rim wall at
noise above the tested sizes; a count of the rays whose direction rounding signs; the channel tests of both files
with the candidate check of `_sections` switched off; the candidates that are no points of the diagram with it off;
the new test with the check on and off; and the worst angle of the 36 draws. Read-only checks: `decisions.py --check`,
`links.py`, the word counts of the capped sections, the PR's check runs and the branch's workflow runs. After the
fixes: `ruff check` and `ruff format --check` on the three edited Python files, the 23 channel and orientation tests
of the two test files (passed in 35 s), and `index_records.py`.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `structure/cavity.py:271`, `_sections`; `tests/tier1/test_structure_axis.py` | The candidate check (the plan's D2; §5.2's NOTE: "a candidate whose clearance is not its nearest atom's distance … is left out") has no test that notices it. With the check switched off, all 17 channel tests of the two files pass, the 24 draws and the 2WCD test among them. With it off the C8 wall tilted 12° holds 51 candidates past their edges' true ends, each with a "clearance" of up to 8.93 nm in a lumen 2 nm in radius. All 51 lie on the axis, so no assertion on the record sees them; a false candidate off the axis would be taken as its plane's widest space | Fixed: `test_ver48_a_channel_candidate_has_no_atom_nearer_than_its_clearance` measures each candidate of that wall against a tree of the test's own. It passes, and fails with the check off (a relative gap of 0.775). VER-48's row, the plan's *Verification* and the knowledge note name it |
| 2 | Pre-existing | `structure/cavity.py:198`, `_voids` | A ray from a flat tetrahedron that took a neighbour's centre is signed by `np.sign` of a product that is rounding, since the apex lies in the face's plane. On the test's walls 5 to 12 rays a wall start from such an owner, each with a product below 1e-9. Where the product is exactly 0 the ray gets no length and is lost whole: 6 rays of the upright C8 wall, 1 of the C7 wall tilted 12°. The line is unchanged; before this change it signed hull rays alone, and it now signs the rays past a tetrahedron that fixes no centre too, 5 to 8 a draw. A ray signed the wrong way loses its true half. No draw locks with them (the plan's 261; review 087's finding 4 recorded the first half of this) | Not fixed: the exact sign is away from the apex of the neighbour whose centre was taken, and it changes the method the plan left as it is (D1). For the author, with a `REV` row if it stays |
| 3 | Nit | `tests/tier1/test_structure_stage.py:712` | `test_ver48_the_channel_revision_keys_only_the_channel` set the patched revision to the literal 2. At the first real bump, which §5.3.2's NOTE makes a SHALL, the constant is 2, the patch changes nothing and the test fails on "the channel's three moved" | Fixed: the patch sets `cavity.CHANNEL_AXIS_REVISION + 1` |
| 4 | Nit | `tests/tier1/test_structure_axis.py`, `test_ver48_the_channel_axis_gates_fire`; `ci.yml` | The gate test tilts the wall with its rim again. That wall read 11.38° on Windows before the fix, which is why WP6.01 (D9) took the rim out. The PR's CI is Linux alone, and the branch has no dispatched run; the three platforms run on `main` after the merge. If Windows or macOS still locks, `main` is red after the merge and not before | Not fixed, nothing in the tree to change: a `workflow_dispatch` of `ci.yml` on the branch runs the three platforms (mode `main`) before the merge. For `/np-ship` |
| 5 | Nit | `specification/07-verification/02-tier-1.md`, VER-48 | The row said the C7 and C8 walls tilted 12° recover their axis "again through the joggled triangulation when the first is refused". The test forces the joggle on one other wall: C8, tilted 35°, offset, with no draw | Fixed: the row names that wall |
| 6 | Nit | §5.2's NOTE on stage 1; the knowledge note | "To a relative 10⁻⁶" where the code takes `EMPTY_TOL * max(1.0, clearance)`: 10⁻⁶ of the larger of the distance and 1 nm. Below 1 nm of clearance, down to the 0.2 nm a candidate needs, the tolerance is absolute | Fixed in the clause and the note. The comment on `EMPTY_TOL` is left; the line it heads shows the floor |
| 7 | Nit | The knowledge note, the bullet on the fix | "None of the 24 draws locks, the worst 5.4e-11 rad." The plan's *Grounding* (D1), which the footnote cites, gives 5.4e-11 rad for the 36 draws. Measured here: 3.7e-11 and 3.9e-11 rad on the C7 and C8 walls, 5.4e-11 rad on the C12 wall | Fixed: "none of those 36 draws" |
| 8 | Nit | `tests/tier1/test_structure_axis.py`, `_wall` | The diff removed the last `rim=False`, so the keyword was dead. Its comment still gave the cause this package refuted: "no atom there lines the axis's side, so the plane's widest spaces are n equal ones off the axis", where the plan measures the widest candidate of that plane on the axis | Fixed: the keyword is gone and the comment gives the cause found |
| 9 | Nit | `docs/plans/index.md` | The index was not written again at delivery: the WP6.06 plan read "planned, not started" and the Phase 6 plan's line lacked WP6.06 | Fixed: `index_records.py` re-run, which also lists this report |
| 10 | Nit | `CHANGELOG.md`, 0.7.0-alpha.6 | The entry gave the retry and not its other consequence, which §8.2.55 BE4 records: atoms in one plane, on one line or at one point are now refused in the coverage gate's words, "0 of the n planes", and no longer as "span no volume". Probed here: a sheet across z reads "0 of the 0 planes", a sheet along z "0 of the 8 planes", three atoms keep today's message | Fixed: a line under **Changed** |
| 11 | Nit | The Phase 6 plan, *In brief* | "The fix for the pore's axis, which rounding can lock 0.6 degrees off", beside a *Context* and a WP6.06 entry that this PR moved to about 1° | Fixed: "could lock about one degree off" |
| 12 | Nit | `structure/stage.py:81`, `structure_parameters` | The docstring gave the returned key as "the block, each file replaced by its digest"; the function now adds `channel_axis_revision` | Fixed: one sentence added |
| 13 | Nit | `structure/cavity.py:139`, `_voids` | The joggled retry leaves no trace: no log line, and nothing in `ChannelRecord` or the stage's header says the axis came from a joggled triangulation. The run is reproducible, since the joggle is the same on every run, but a reader of the artefact cannot tell which path gave the axis | Not fixed: a mark in the record changes the header of stage 1. For the author |

The pass fixed ten findings and left three: findings 2 and 13 are the author's, and finding 4 is a run for `/np-ship`
to start. No finding goes against a ruling of the author. Finding 1 adds a test to VER-48, which is numerics and in
the test scope (§8.2.13 N1); it changes no behaviour. After the fixes the WP6.06 plan holds 3,507 words (cap 3,850),
1,552 outside *Grounding* and *Implementation details* (1,650), and the Phase 6 plan's In brief 263 (275).

## Checked and found true

- **The diff and the head.** The checkout is the PR's head, `a1a5428`, on `7ebfd4f`; the tree was clean. On that
  head `lint`, the strict documentation build and both test shards are green. The seven commits are conventional,
  and each of the two code commits names its identifiers and carries its clause.
- **D1, the code.** `open_face` is a superset of the hull's faces: a face of a `valid` owner whose neighbour is
  missing or not `valid`. `keep` is unchanged, so no edge is made twice. A face between two tetrahedra that are both
  not `valid` still gets no edge, as before.
- **D2 is sound.** A point as far from its face's three atoms as from its nearest atom is a point of the diagram,
  whichever triangulation gave the face. So the check admits only true points on the standard and on the joggled
  path, and on a true edge it holds to rounding: the worst gap on the test's walls is 2.5e-13 nm. On the upright
  walls and on a 1e-14 draw it removes nothing; a wall's sections take 0.02 s with it.
- **D3.** Twelve degenerate sets went through `channel_axis`: sheets across and along z, lines, coincident atoms, two
  parallel sheets, a spherical shell, a cloud of doubled atoms, and three, four and five atoms. Each is refused with
  `SymmetryGateError` or returns a record; no other exception and no NumPy warning escapes.
- **The fix holds above the tested noise.** The C7 and C8 walls tilted 12°, three draws at each relative size from
  1e-9 to 1e-4: the angle to the wall's axis grows with the noise, from 6.8e-9° to 1.4e-3°, and no draw locks.
  Coordinates rounded to 1e-4 nm, a PDB file's precision, read 1.3e-4° or less at 0° and at 4°.
- **D5.** `_takes_channel` is the one test that `align` and the key share. Only `validation/comsol.py:_stage7_recipe`
  reads stage 1's parameters whole. `density/stage.py` keys on the structure artefact's hash, so the later stages of
  a channel case re-key. No test and no example pins the key of a C1 or `cavity` case. `prepared_pore` digests
  `cavity.py`.
- **The registers.** `decisions.py --check` passes and `links.py` finds no broken path, before and after the fixes.

## Not assessed

- Windows and macOS (finding 4).
- The joggled path on a structure of 2WCD's size, and that Qhull's joggle gives the same simplices in two
  processes: the plan measured both, and neither was repeated.
- The plan's counts that need more draws than the 36 repeated here: the 225 draws, Qhull's 2 refusals of 360, the two
  lesser rules and the 54 runs of the plugged lumen.
- `mypy`, the strict documentation build and the push gate on the fixes, which `/np-ship` runs. One docstring in
  `src/` changed.
- `docs/plans/sessions/phases-6-to-11.md` still describes WP6.06 by the tie. It is the phase's input note, was not
  in the diff and was left.

## For the author

- Finding 2: whether a flat tetrahedron's ray takes its exact sign from the neighbour whose centre it took. It is
  the first place to look if a platform locks (review 087, finding 4), and it needs the plan's draws run again.
- Finding 13: whether a joggled triangulation is marked in the record and the header.

## At the ship

Added by `/np-ship wp 6.06` after the pass above, which stands as the review wrote it.

- **The ten fixes** were read as diffs and kept. The test of finding 1 failed with the candidate check off, as the
  review says, until finding 2 was repaired; it then passed with the check off, since the 51 false candidates of that
  wall came from the rays finding 2 names. It is rebuilt on a diagram made by hand: three atoms on a circle, a fourth
  on its axis, and a ray past the edge's true end. It fails with the check off.
- **Finding 2** is fixed by the author's ruling (§8.2.55 BE5): a flat tetrahedron that took a neighbour's centre
  signs its rays by that neighbour's fourth atom. Of 45 trial walls 23 held a ray without a length or off the diagram
  within 0.001 nm of its start, up to 10 a wall; none does now.
  `test_ver48_a_ray_of_the_diagram_starts_along_a_true_edge` fails on each of its two walls without the repair. The
  plan's 36 and 225 draws recover as before, the worst 5.4e-11 rad and 5.6e-14 rad.
- **Finding 4** is not acted on: a package's `/np-ship` dispatches no three-platform run (§8.2.50 AZ8).
- **Finding 13** is fixed by the author's ruling (§8.2.55 BE6): the record says that the retry was taken, and stage 1
  and a prepared pore report it as a warning.
- **The physics read.** Before the pass a `physics-reviewer` read the numerics. Its three confirmed points: the ray's
  sign, which is finding 2; §5.2's NOTE narrower than the code in three places, now reworded (the tolerance's floor
  of 1 nm, which tetrahedra an edge runs past, and that every refusal of Qhull is retried); and two `[tested]` marks
  of the knowledge note wider than their tests, left, since each bullet carries `[verified]` for its counts. Its
  doubts, none shown to be wrong:
  - A plane can hold one candidate twice, and a centre is a mean over them. Measured: the trial walls hold 143 to
    1,773 repeated pairs a run, and dropping the repeats turns the axis by at most 9.1e-11 rad and moves it by at most
    2.3e-10 nm, the size of the draws' own noise.
  - The candidate check measures to one atom of the face where the diagram's own check measures to the first atom of
    the tetrahedron; a centre solved near the soundness threshold could pass one and fail the other. 2WCD moves by no
    bit, and no trial wall shows it.
  - The check bounds a candidate's distance, not its position past an edge's end; it holds the NOTE's tolerance.
  - The joggle's size is Qhull's own and is not recorded; whether the first triangulation is refused can differ
    between platforms. The record now names the retry (BE6).
  - A ray's candidate is carried between frames with its tetrahedron's atoms, up to the ray's length away; the
    per-frame drift is recorded and not gated.
