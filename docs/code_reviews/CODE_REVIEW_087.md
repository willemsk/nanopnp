# Code review 087: WP6.06's plan, the channel's axis at a ragged rim

2026-11-25 · branch `claude/np-carry-wp-6-06-g7y44p` at `4277fa8` on `main` (`7ebfd4f`) · scope: the plan commit's
9 files, +353 and −30, read from `git show HEAD`. Read in place: `.claude/skills/np-plan/` (`wp.md`, `review.md`,
`rulings.md`), `.claude/workflow/author.md`, `src/nanopnp/structure/cavity.py` whole, `structure/stage.py`
(`structure_parameters`, `_digest`, `align`, `StructureStage`), `structure/orient.py` (`_channel_line`,
`prepared_pore`), `io/artefact.py` (`Artefact.hash`, `StructureArtefact`), `io/resolved.py`, `validation/comsol.py`
(`_stage7_recipe`), `tests/tier1/test_structure_axis.py` (`_wall` and the channel's tests),
`tests/tier1/test_structure_stage.py` (`_case`, `_block`, the 2WCD channel test), `tests/conftest.py` (the 2WCD
fixtures), §5.2's NOTE on stage 1, §5.3.2's NOTE on the solution payload, VER-48, §8.1's Phase 6 row, §8.2.39 AO1
and AO4, §8.2.51 BA8, §8.2.55, the Phase 6 plan, REV-279's row and section, and the knowledge note on 2WCD's channel
axis · level: high, with `--fix` · status: completed.

No test and no `gate.sh` was run. The plan's three edits of `cavity.py` were applied to a copy of the file outside
the repository, and the plan's measurements were repeated on it with `uv run --frozen python`: the 24 draws of the
new test and the two walls without a draw, the forced joggled path, the gate test's walls, six degenerate inputs,
and the vendored 2WCD in its deposited frame. Nothing under `src/` or `tests/` was changed. Read-only checks:
the word counts of the plan and of `current.md`; `git merge-base` for the base commit. After the fixes
`decisions.py` and `index_records.py` were re-run.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | The plan, *Implementation details*, item 2; *Verification*, the last row | D5 says the revision is in the key "where the channel gives the axis, and nowhere else", and its grounding names the variant the obvious path misses: `axis: z` under C1. The test built three cases, the ring under `auto`, `cavity`, and C1 under `auto`. Neither C1 with `z` nor a ring with `z` was checked, so a `_takes_channel` written as `axis != "z"` and the rest, or as `axis == "cavity"` alone with C1 handled elsewhere, passes. `wp.md` asks one assertion for each point of failure of a decision that says *every* or *nowhere* | Fixed: the test builds five cases, the ring's two (`auto`, `z`) and the channel's three (`cavity`, C1, C1 with `z`), and the row names them |
| 2 | Important | The plan, *Implementation details*, item 2, `structure/stage.py` | The test patches `nanopnp.structure.stage.CHANNEL_AXIS_REVISION`, and the item put the constant in `cavity.py` without saying how `stage.py` reads it. Read as `cavity.CHANNEL_AXIS_REVISION` through the module, the patch has no such name to set, or sets one the key does not read, and the hashes do not move. The test's own assertion also named `cavity.CHANNEL_AXIS_REVISION`, and the test file imports no `cavity` and uses the name for a local in the 2WCD test | Fixed: the item says `stage.py` imports the constant by name with its other names of `cavity`, and the assertion names `nanopnp.structure.cavity.CHANNEL_AXIS_REVISION` |
| 3 | Important | The Phase 6 plan, completion criterion 10 | The commit settled open decision 11 (BE1: a moved number is re-pinned and reported, and the package stops only if 2WCD would pass a limit) and left criterion 10 saying that a move "goes to the author (open decision 11)". The implementing session reads both: by the criterion any move of 2WCD's numbers stops the package, by D4 it does not | Fixed: the criterion says the move is reported, the limits stay, and the package stops only if 2WCD would pass one (BE1) |
| 4 | Nit | The plan, *Grounding*, D1, second bullet | "The ray's direction, away from the apex, is exact" does not hold for every ray the change adds. A flat tetrahedron that took a neighbour's centre is `valid`, and its apex lies in the face's plane, so `(apex - base) @ normal` is rounding and `np.sign` of it signs the ray. On the copy, 0 to 12 of about 2,100 to 2,300 added rays in a draw start from such an owner, each with a product below 1e-9. No draw locks with them: D2 keeps a point of such a ray only where it is a true point of the diagram. A ray signed the wrong way still leaves its true half out, which rounding decides | Fixed in the plan's text: the bullet says where the direction is exact and gives the count. Not changed: the method. If a draw on macOS or Windows locks at the close (criterion 10), these rays are the first place to look |
| 5 | Nit | The plan, *Grounding*, D3, last bullet | "Atoms Qhull refuses twice, fewer than five, keep today's message." Four atoms triangulate at the first call and are refused by coverage; three or fewer are refused twice. The bullet also did not say that the refusal's words change for the inputs today's message was written for: coplanar, collinear and coincident atoms now joggle and read "channel coverage gate: 0 of the n planes", n being 0 for a sheet across z | Fixed: "fewer than four", and the bullet names the changed words. `channel_axis`'s docstring ("When the atoms span no volume") stays true |
| 6 | Nit | D3; §8.2.55's opening paragraph | D3 is "decided by the plan". It changes what a user sees: a structure that Qhull refuses for precision is refused today and gets an axis from joggled input after it, and degenerate atoms get another refusal. The record of the round says one point was told to the author and not asked, the cause; it does not mention the joggled retry. It is a repair of a wrong refusal and the phase entry's criterion 10 needs it ("every perturbed draw"), so one answer is defensible | Put to the author at the review turn, with three options: the retry, the retry with today's words kept for flat input, and the refusal kept with its true reason. The author chose "Try once more (Recommended)". Fixed: D3 is ruled (§8.2.55 BE4), and the plan's In brief and the Phase 6 entry say what a user sees |
| 7 | Nit | The Phase 6 plan, *Context*, "True of the codebase today"; criterion 10, "Today 3 of 8 draws lock 0.22° to 0.62° off" | The commit rewrote the WP6.06 entry to the plan's 1.05° and left the two older statements of the same fault beside it | Fixed: the context line gives about 1° with the plan's measurement, and the criterion adds the plan's 17 of 24, up to 0.84° |
| 8 | Nit | The plan, *Grounding*, D5, second bullet | "Only `_digest` reads the parameters by key" is true, and one more reader takes the whole mapping: `validation/comsol.py:_stage7_recipe` copies stage 1's parameters into the deposited charge's recipe, so a C1 case's recipe gains `channel_axis_revision`. Every Tier 3 case is C12, so no stored recipe moves | Fixed at the review turn, in the plan's text: the D5 bullet names the second reader and says why no stored recipe moves. No behaviour changes |

## Checked and found true

- **D1, the code.** `_voids` makes edges from `keep` and from `open_face = (other < 0) & valid[owner]` alone;
  `valid` is `sound & (radius <= reach)` less the spheres not empty to 1e-6; a flat tetrahedron becomes `sound` only
  by taking a neighbour's centre. The plan's one-line change is well formed against the arrays there.
- **D1, the numbers, repeated.** `_wall(8)` tilted 12° about x: 50 unsound of 27,644 tetrahedra; its `seed` 0 draw
  at 1e-14: 2,146 of 29,741. Today's method locks 17 of the 24 draws of the new test (C7: 3, 4, 1; C8: 2, 4, 3),
  the worst 0.84°. With the three edits none locks: the worst angle is 3.9e-11 rad, the worst offset 1.0e-10 nm and
  the worst straightness 3.1e-10 nm, each draw converged in 2 or 3 iterations with full coverage. Each of the new
  test's four assertions holds on each draw.
- **D2, the code.** `_sections` takes the clearance from `edge_atom` and keeps `MIN_CLEARANCE_NM <= clearance <=
  reach_nm`; `_Voids.tree` is the atoms' `cKDTree`; the snippet runs as written between `wide` and `order`.
- **D3.** `_voids` turns any `QhullError` into "span no volume". With `Qz` beside `QJ` a simplex indexes
  `len(atoms)`. The forced test as specified works: `_voids` imports `Delaunay` when called, a wrapper on
  `scipy.spatial.Delaunay` records `[None, "QJ Qbb Qc Q12"]`, and `_wall(8) @ TILT.T + OFFSET_NM` recovers to
  2.9e-16 rad, 5.0e-15 nm and 9.5e-15 nm straightness in 4 iterations.
- **D4.** The 2WCD test pins 0.00732 nm, 0.0418°, 0.00946 nm and 0.01477 nm, `(28, 28, 3)` and no warning. On the
  vendored file's chains A to L, 26,844 heavy atoms, in the deposited frame, the copy gives the same axis, centroid
  and centres to the last bit as today's code from each of three starts, and adds 182 rays to 114 on the hull, the
  plan's numbers. No tetrahedron is flat.
- **D5.** `Artefact.hash` is `content_hash(schema, parameters, inputs)`. `StructureStage.key` and `run` both call
  `structure_parameters`; `align` computes `channel = axis_mode == "cavity" or n == 1`; `check_z_channel` is what
  `axis: z` runs under C1. `prepared_pore` digests `cavity.py`'s bytes. `ResolvedStructure` has `spec` and `n`.
  `tests/tier1/test_protonation.py` builds its C1 case by hand. No test pins a stage-1 hash.
- **D6.** `_wall`, `_rotation`, `TILT` and `OFFSET_NM` are in `test_structure_axis.py`; the gate test tilts
  `_wall(8, rim=False)` under a comment naming REV-279. With the edits `_wall(8)` tilted 12° is refused at "12.00
  degrees", and the test's other walls keep their results: the bent wall 1.05 nm, the straight one no warning, the
  0.0200 nm displacement refused and the 0.005 nm one measured.
- **The clauses.** §5.2's NOTE defines the candidates and calls the clearance "its distance to the nearest atom";
  §5.3.2's NOTE holds "The other stages' payloads have no such counter" and leaves a store invalidation to the
  author (REV-77); VER-48's row holds "the axis being its fixed line" and "is relabelled". No clause outside the
  history gives 0.6° or names the tie as the cause, so D7's records are the ones that need the new number.
- **The rulings.** BE1, BE2 and BE3 are in D4, D5 and D8 as the author chose them; `holds-now.yaml` has the three.
- **The caps and sections.** After the fixes and the review turn's ruling the plan holds 3,259 words (cap 3,850),
  1,309 outside *Grounding* and *Implementation details* (1,650), and 818 in *Implementation details* (1,100). Its
  In brief has 270 words and no
  backtick. Each section of `wp.md` is present; each work item names its executor; `current.md` holds 700 words.
- **The base.** `7ebfd4f` is `origin/main`'s head; the local `main` is behind it.

## Not assessed

- The counts that need more draws than the 26 repeated here: none of 225 at 1e-14 over three tilts, Qhull's 2
  refusals of 360, the two lesser rules, and the 54 runs of the plugged lumen.
- The prepared 2WCD of the test fixture: the deposited frame was measured in its place, and the stage was not run.
- macOS and Windows: the phase's close (criterion 10).
- The timings, and the whole file's 26 tests under the edits.
