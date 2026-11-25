# Code review 089: WP6.06, the ship's two repairs

2026-11-25 · PR #218, branch `claude/np-carry-wp-6-06-g7y44p`, head `3f5d467` on base `7ebfd4f` (`main`) · scope: a
second, short pass over what `3f5d467` changed over `a1a5428`, 20 files, +315 and −58, read from `gh pr diff 218` and
narrowed with `git diff a1a5428 3f5d4675`; the checkout was at the PR's head and clean. Above all the two repairs the
author ruled in after review 088 (§8.2.55 BE5 and BE6). Read in place: `src/nanopnp/structure/cavity.py` and
`structure/orient.py` whole, `structure/stage.py` (`structure_parameters`, `align`, `_gates`), `cli/running.py` and
`cli/building.py` (where a warning is printed), `gui/web/tools.py` (`warnings`), the two new tests and
`test_ver48_a_refused_triangulation_is_joggled` in `tests/tier1/test_structure_axis.py`, §5.2's NOTE on stage 1,
IF-02's NOTE on preparation, VER-48's row, §8.2.55, the WP6.06 plan, the knowledge note on 2WCD's channel axis,
review 088 and `.claude/rules/python.md` · level: high, with `--fix` · status: completed.

Static review: no `gate.sh`, no `pytest`, no benchmark. Four probes were run with `uv run --frozen python`, each under
a minute: the rays of a cubic lattice, of exact C4 to C12 rings, of a hexagonal lattice and of the nine test walls,
each measured as the new test measures them, plain and with the joggled retry forced; the two new tests' assertions
with the repair taken out and with the candidate check's input built by hand; the adoption loop of `_voids`, counting
what each pass takes; and the flat tetrahedra of 2WCD. Read-only checks: `decisions.py --check`, `links.py`, the word
counts of the plan's capped sections. After the fixes: `ruff check` and `ruff format --check` on `cavity.py`, and
`index_records.py`. Review 088 covered `a1a5428` and is not repeated.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Nit | §5.2's NOTE on stage 1 (`specification/05-software-design/02-pipeline-stages.md`); `structure/cavity.py:156`, `_voids` | The clause this commit wrote says a flat tetrahedron's edges "run on away from that neighbour's fourth atom". Where the neighbour is itself a flat one that took the centre in an earlier pass, its fourth atom lies in the same plane, and the code hands on that neighbour's own `ender` (`np.where(ender[source] >= 0, …)`). The clause read alone signs such an edge by rounding again. Measured: 1 to 3 tetrahedra of a test wall take their centre this way (the C8 wall tilted 12° and 35°, the C12 wall at each angle, the C7 wall tilted 12°); each `ender` lies 0.009 or more of the tetrahedron's size off its plane | Fixed: the clause names the case, and the comment in `_voids` says why a flat neighbour hands on its own |
| 2 | Nit | §5.2's NOTE on stage 1 | "One whose sphere … is wider than twice the atoms' greatest distance from their centroid." The code leaves a tetrahedron out where its sphere's radius is over that length (`radius <= reach`, `reach` twice the greatest distance). A sphere's width is its diameter, so the clause read alone drops spheres half as large as the code does. This commit wrote the wording (review 088, *The physics read*) | Fixed: "has a radius over twice" |
| 3 | Nit | IF-02's NOTE on preparation, `specification/03-requirements.md:103` | The NOTE states what `nanopnp prepare` warns of: the straightness, "in the record's `warnings` and in its text output". Since BE6 it warns the same way of an axis found from joggled input (`orient.py:_channel_line`, `cli/building.py:149`). §8.2.55 BE6 and the changelog say so; the clause does not, and §5.2's NOTE gives the reporting of stage 1 alone. CLAUDE.md: "A change to specified behaviour changes the specification in the same commit" | Not fixed: the file is outside the diff, and BE6's row lists its clauses as §5.2's NOTE and VER-48. A wording: after "(§8.2.39 AO4)", "; an axis found from joggled input is warned of the same way (§8.2.55 BE6)", with `holds-now.yaml` and BE6's last column naming the NOTE. For `/np-ship` |
| 4 | Nit | `structure/stage.py:259`, `align` | The frame check finds the channel's axis a second time, among the aligned atoms (`again = channel_axis(aligned_mean[heavy])`), and writes its tilt and offset into the header. Those atoms are other numbers than the file's, so Qhull can refuse one set and not the other; `again.joggled` is not read. A header can then warn of a retry its frame check did not take, or give a frame check from joggled input with no warning | Not fixed: a mark on the frame check changes stage 1's header beyond BE6's ruling. The check is recorded and not gated. For the author |

The pass fixed two findings and left two. None is a fault of the method: no finding goes against BE5 or BE6, and the
two fixes change a clause's words and a comment, no behaviour. No test is added (§8.2.13 N1).

## Checked and found true

- **BE5, the geometry.** A flat tetrahedron that took the centre `c` of a neighbour has four atoms on one circle, and
  the neighbour's fourth atom `y` on the same sphere, off the circle's plane. A point `c + t·n` on the circle's axis
  is nearer to `y` than to the circle by `2·t·h` in squared distance, `h` being the height of `y` on the side `n`
  points to. So the one direction from `c` in which the circle's atoms stay nearest is away from `y`, whichever of the
  tetrahedron's four faces the edge leaves by. The code signs each ray so.
- **BE5, the code.** `facing` is the place of the flat tetrahedron among its source's neighbours, so
  `simplices[source, facing]` is the source's atom opposite the shared face. In the probe each source names the flat
  tetrahedron once, and no `ender` is an atom of its own tetrahedron. A tetrahedron that is `valid` and was flat always
  has an `ender`, so `apex` falls back to the tetrahedron's own fourth atom only where that atom is off the face. A
  chain of flat tetrahedra shares faces of three atoms not on one line, so it stays in one plane and the handed-on
  `ender` is off it.
- **The ray test fails without the repair.** With `apex` taken from the tetrahedron's own fourth atom again, the
  upright C8 wall holds 6 rays with no length and the wall tilted 35° holds 6 that leave the diagram within 0.001 nm;
  with the repair both hold none, of 2,460 rays each. The plan's row and review 088 say the same.
- **The repair holds on exact symmetry and on the joggled path.** A cubic lattice of 216 atoms upright and tilted,
  exact rings of C4, C6, C8 and C12 upright and twisted, a hexagonal lattice in an annulus, and the nine walls (C7, C8,
  C12; upright, 12°, 35°): 124 to 3,596 rays each, 5 to 240 of them from flat tetrahedra, none with no length and none
  off the diagram. With the retry forced on the lattice, two of the rings and the nine walls, the same: none, and the
  nine walls recover their axis to 5e-16 rad in 1 to 4 iterations, converged, straight to 3e-15 nm.
- **The candidate test.** Its seven planes cut the ray at z = 0 to 3.0 nm; the fourth atom is nearer from z = 4/3 nm
  on, so three candidates stay. The numbers are exact in floating point (0.75, 0.5), and the test's `approx` holds to
  1e-12. With the check off the same call keeps seven.
- **`joggled` and its warning.** `_voids` sets the flag only where the first triangulation raised; `channel_axis`
  copies it; nothing else builds a `ChannelRecord`, and the one hand-built `_Voids` is the test's. `orient.py` finds
  the three starts among the same atoms, so the three records agree on it. The warning reaches `nanopnp run`, a cached
  stage 1 and the workbench's structure tools through the header's `warnings`, and `nanopnp prepare` through the
  record's; each reader takes the list whole. A structure that took no retry gets no new key in its header.
- **The joggled test's new assertion.** `assert not cavity.channel_axis(wall).joggled` reads the plain triangulation
  of the C8 wall tilted 35° and offset. `test_ver48_the_channel_axis_recovers_a_known_axis` triangulates the same
  atoms and has run on `main`'s three platforms since before this package, where a refusal failed it as "span no
  volume". Its runs were not read here.
- **The clauses and the records.** VER-48's row, the plan's D9, D10 and two verification rows, §8.2.55 BE5 and BE6,
  `holds-now.yaml`, the changelog and the knowledge note agree with the code and with each other on the counts (45
  walls, 23 with such a ray, 6 failing rays a wall, 2,460 rays, 1e-6). The deposited 2WCD has no flat tetrahedron
  among the 26,844 heavy atoms of chains A to L. The plan holds 3,588 words outside its Outcome annotations (cap
  3,850), 1,615 outside *Grounding* and *Implementation details* (1,650). `decisions.py --check` passes and `links.py`
  finds no broken path.

## Not assessed

- `mypy`, the strict documentation build, Tier 1 and the push gate on the two fixes, which `/np-ship` runs. One
  comment in `src/` changed, so a prepared pore's file name moves once (`prepared_pore` digests `cavity.py`).
- Windows and macOS: whether Qhull's triangulation of the two walls of the ray test holds a flat tetrahedron with an
  open face there too. The test asserts nothing on their number.
- The plan's 36 and 225 draws and the 45 and 63 trial walls of the ship's Outcome, which were not repeated.
- The knowledge note's two `[tested]` marks on the bullet for BE5, wider than their tests as review 088 found of two
  others; the bullet carries `[verified]` for its counts.

## For the author

- Finding 3: whether IF-02's NOTE on preparation names the second warning.
- Finding 4: whether the frame check says which triangulation gave its line.

## At the ship

Added by `/np-ship wp 6.06` after the pass above, which stands as the review wrote it.

- **The two fixes** were read as diffs and kept: each states what `_voids` does.
- **Finding 3** is fixed: IF-02's NOTE on preparation says that an axis found from joggled input is warned of as the
  straightness is, and `holds-now.yaml` and BE6's row name the NOTE.
- **Finding 4** is fixed inside BE6, whose ruling is that a result says where the retry was used: the frame check's
  record is read too, and a retry there adds its own line to the header's `warnings`, naming the aligned atoms.
  §5.2's NOTE names both axes. A header that warns of nothing keeps its bytes.
