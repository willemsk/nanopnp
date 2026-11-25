# WP6.06 — The channel's axis at a ragged rim

**Status: delivered, 25 November 2026.** Written 25 November 2026, grounded in the code at `7ebfd4f`. Inherits §8.2.51 BA8,
§8.2.52 BB1, §8.2.54 BD1, §8.2.39 AO1 and AO4, the rulings of this plan (§8.2.55 BE1 to BE4), REV-279 and the test
scope (§8.2.13 N1). Its last commit on `main` takes `v0.7.0-alpha.6` (§8.4.1).

**Delivered.** `structure/cavity.py:_voids` runs a Voronoi edge on past a tetrahedron that fixes no centre, as past the
hull; `_sections` keeps a candidate only where its clearance is its nearest atom's distance to 1e-6; a triangulation
Qhull refuses for precision is joggled once (`JOGGLE_OPTIONS`, BE4). The 24 draws of VER-48's new test, 17 of which
locked before, recover the axis to 1e-6 rad; the gate test tilts the wall with its rim again. 2WCD's test passes
unchanged, so no number and no limit moved (BE1). Stage 1's key carries `channel_axis_revision` where the channel
gives the axis (BE2). §5.2's and §5.3.2's NOTEs and VER-48 say so; REV-279 is fixed, its cause and bound corrected
([the note](../../../knowledge/04-clya-geometry-and-charge/15-the-channel-axis-of-2wcd.md)). Live: a change that moves
a channel's axis bumps `CHANNEL_AXIS_REVISION` (BE2); a lumen with atoms on its axis reads 7° to 8° off, warned of
(AO4).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.06 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** A pore's axis found from its channel no longer depends on rounding. The cause is not the one on
record: where the atoms of a rim lie exactly in one plane, the program lost the open space on the axis in the end
slice, and its first, tilted cut picked one of the equal spaces beside it. On 36 trial walls today's method ends off
the axis in 17, by up to 0.84 degrees; one further wall read 1.05. The fix restores the lost space: none of 261 trial
walls ends off it. The real pore keeps its axis to the last digit; its two limits stay. A structure wrongly refused
when rounding defeats the first step is tried once more.

**Cost.** About 4 sessions, 2 to 4 agent hours and 7 times you act, two of them done. A symmetric or idealised
structure may get an axis up to about one degree different from the last release, and a case that takes its axis from
the channel runs again once.

**What could go wrong.** A structure the trials did not cover could still end off its axis; the new test sees only its
own walls. A channel with atoms on its axis still reads several degrees off, with the warning you ruled. The real pore
was measured on a trial copy; the build repeats it, and a move comes back to you.

**Your call.** Settled today: the limits stay; channel cases run again once; a wrongly refused structure is tried once
more; Opus 5.5 builds and Fable 5.2 ships. Still yours: approve this reviewed plan. *Recommendation:* approve.

## Execution brief

Scope: the Phase 6 plan's WP6.06 entry (REV-279; BA8). The fix is in `structure/cavity.py`, the diagram the channel's
axis is read from, and not in the tie rule the entry names: D1 says why. It depends on nothing unmerged. It amends
VER-48 and the NOTEs of §5.2 (stage 1) and §5.3.2 (the solution payload), and touches FR-02, FR-37, QR-12 and IF-04
through them; it claims no new identifier and has no Tier 3 leg.

**Opus 5.5 implements, at high effort; Fable 5.2 ships, at high effort** (BE3). The two differ, so the ship starts in
a fresh helper and never chains from the implementing one (`NANOPNP_AUTO_SHIP`).

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The cause is fixed, not the tie** | `_voids` continues an edge of the diagram as a ray past a face whose far tetrahedron is not `valid`, as it does past the hull. The tie rule and `TIE_NM` stay | The dropped edges are what empties the axis at a flat rim; the fix cures 261 of 261 draws, and neither a narrower ray rule nor a tie-robust centre does (*Grounding*). The NOTE already defines the candidates by the whole diagram. Decided by the plan |
| **D2 A candidate is a point of the diagram** | `_sections` keeps a candidate only where its clearance is its nearest atom's distance, to the 1e-6 of `_voids`' own check | A ray can pass its edge's true end, and a point past it is no space; the NOTE calls the clearance "its distance to the nearest atom". Decided by the plan |
| **D3 A refused triangulation is joggled** | On `QhullError`, `_voids` triangulates again with `QJ Qbb Qc Q12`; today's refusal stands only if that fails too | Qhull refuses 2 of 360 draws for precision, which the code reports as "no volume"; every draw must recover (criterion 10). Ruled by the author, BE4 ("Try once more") |
| **D4 The limits stay** | 0.015 nm and 0.03 nm are not edited. 2WCD is measured again by its test. A moved number re-pins the test's measured constants and the NOTE's numbers, and is reported; 2WCD over a limit stops the package for the author | Ruled by the author, BE1 ("The limits stay") |
| **D5 Stored channel results run again once** | Stage 1's key carries `channel_axis_revision`, 1, where the channel gives the axis, and nowhere else | Ruled by the author, BE2 ("Recompute those cases once") |
| **D6 Every draw recovers the axis** | 24 draws of the C7 and C8 walls with the rim, tilted 12°, each checked for direction, offset, convergence and straightness; the gate test tilts the wall with the rim again; the joggled path is forced once | VER-48's 1e-6 rad and 1e-6 nm, unchanged; the oracle is the axis the wall is built about. Decided by the plan |
| **D7 The records say what was measured** | The changelog and the knowledge note give "about 1°" and the cause found; a lumen with atoms on its axis is recorded under AO4 and gets no row | Measured here: 1.05°, not 0.6°; AO4 rules a channel that is not straight. Decided by the plan |
| **D8 The models** | Opus 5.5 implements; Fable 5.2 ships | Ruled by the author, BE3 |

### Grounding

Measured at `7ebfd4f` on SciPy 1.18.0 and NumPy 2.5.2, Linux. A *draw* multiplies a wall's coordinates by
`1 + relative * rng.standard_normal(shape)`, `rng = np.random.default_rng(seed)`; a draw *locks* when its axis is more
than 1e-6 rad from the wall's.

**D1**

- `structure/cavity.py:_voids` makes an edge from `keep` (both tetrahedra `valid`) or from `open_face` (`other < 0`,
  the hull). A face between a `valid` tetrahedron and one that is not gets neither, so its edge is dropped. `valid`
  is `sound & (radius <= reach)`, less a tetrahedron whose solved sphere is not empty to 1e-6; a flat tetrahedron
  becomes `sound` only by taking the centre of a neighbour whose sphere holds its four atoms.
- The change adds to `open_face` each face of a `valid` owner whose neighbour exists and is not `valid`. The ray's
  direction, away from the apex, is exact where the owner is `sound` by itself: the far tetrahedron's centre lies
  further that way. A flat owner that took a neighbour's centre has its apex in the face's plane, so rounding signs
  its ray: at most 12 of about 2,300 rays in a draw (the review's count), and D2 keeps only true points of them.
- `_wall(8)` tilted 12° about x has 50 unsound tetrahedra of 27,644; a draw at 1e-14 has 2,146 of 29,741, of which
  1,161 lie wholly in the top rim plane. Its last plane then holds no candidate within 0.36 nm of the axis: without
  the draw it holds one on the axis at 2.018 nm clearance, eight 0.106 nm aside at 1.921 nm and eight 0.364 nm aside
  at 1.678 nm. The first cut, 12° off, takes one of the last eight.
- Today, on 12° walls about x, four draws (`seed` 0 to 3) at each of 1e-14, 1e-12 and 1e-10: C7 locks 3, 4 and 1;
  C8 locks 2, 4 and 3; C12 none. The worst is 0.84° (C7); a further C8 draw read 1.05°. The recovery test's own walls
  lock in 12 of 13 draws (C7 and C8 at 8°) and 11 of 12 (C8 at 35°).
- With D1 to D3: none of those 36 locks, the worst 5.4e-11 rad at 1e-10; none of 225 at 1e-14 over C7, C8 and C12 at
  8°, 12° and 35°, the worst 5.7e-14 rad, in 2 to 4 iterations.
- Two lesser rules fail. Rays past flat tetrahedra alone still lock 14 of 18 draws at 1e-12 and 11 of 18 at 1e-10. A
  tie weighted over 0.02 nm, without the rays, locks 11 of 21 C7 draws.
- It runs on the default path: `structure/stage.py:align` calls `detect_channel` and `channel_axis` under C1 or
  `axis: cavity`, and `structure/orient.py:_channel_line` calls `channel_axis` where no covariance axis stands apart.
  No option reaches `_voids`.

**D2**

- `_sections` takes a candidate's clearance as its distance to `edge_atom`, one atom of the edge's face, and keeps
  `MIN_CLEARANCE_NM <= clearance <= reach_nm`. A ray is `reach` long. Past a neighbour whose sphere is wider than
  `reach`, the clearance passes `reach` before the edge's true end; past a flat or mis-solved neighbour the true end
  is not known.
- The walls without a draw hold such points today, between centres that flat tetrahedra took over: on the axis at
  8.34 nm and 8.83 nm "clearance" in a lumen 2.0 nm in radius, and the search starts from them. 2WCD holds none among
  its 34,786 candidates.
- `_Voids.tree` is the atoms' `cKDTree`; `_voids` tests each centre with
  `np.abs(nearest - radius) <= 1e-6 * np.maximum(1.0, radius)`.

**D3**

- `_voids` turns any `QhullError` of `Delaunay(local)` into "span no volume to triangulate". Qhull refuses 2 of 360
  draws with `QH6417 qhull precision error (qh_merge_twisted)`: C7 at 8° with `seed` 17 and C8 at 35° with `seed` 1,
  both about (1, 2, 0), with `OFFSET_NM`, at 1e-14.
- `Delaunay(local, qhull_options="QJ Qbb Qc Q12")` triangulates both, with the same simplices in two processes, and
  both then recover to 1.7e-14 rad. With `Qz` beside `QJ` a simplex indexes the point at infinity, `len(atoms)`, and
  `circumcentres` raises `IndexError`. SciPy's tutorial names `QJ` for degenerate input.
- Forced on the 35° walls with `OFFSET_NM` (C7, C8, C12; no draw, and `seed` 0 and 1), the joggled path recovers to
  4.1e-14 rad.
- Atoms Qhull refuses twice, fewer than four, keep today's message. Coplanar, collinear and coincident atoms joggle
  into a triangulation that encloses nothing, and `channel_axis`'s coverage refusal takes them, as "0 of the n planes"
  in place of today's "span no volume".

**D4**

- `tests/tier1/test_structure_stage.py:test_ver48_2wcd_channel_axis_agrees_with_its_ring_axis` pins 0.00732 nm,
  0.0418°, 0.00946 nm and 0.01477 nm, each to 1e-4 or 1e-3, `(planes, centres, iterations) == (28, 28, 3)`, and no
  warning.
- The prepared 2WCD has 26,844 heavy atoms and 181,048 tetrahedra, none flat. Today 286 of its 362,002 interior
  faces and 74 of its 188 hull faces carry no edge; the prototype adds 182 rays. Under the prototype its axis, its
  centroid and its 28 centres are the same to the last bit, in 1.63 s against 1.45 s. Prediction: the test passes
  unchanged.

**D5**

- `io/artefact.py:Artefact.hash` is `content_hash(schema, parameters, inputs)`. It holds no package version, so an
  entry stored by v0.6 is a hit on v0.7.
- `structure/stage.py:structure_parameters` returns the block's dump with each file as its digest;
  `StructureStage.key` and `StructureStage.run` both call it. `align` computes `channel = axis_mode == "cavity" or
  n == 1` for itself. Only `_digest` reads the parameters by key (`source.path`, `ensemble.trajectory`).
  `validation/comsol.py:_stage7_recipe` copies the whole mapping into a deposited charge's recipe; every Tier 3 case
  is C12, so no stored recipe moves.
- The change: a private `_takes_channel(structure)` holds that test for both, and where it is true
  `structure_parameters` sets `parameters["channel_axis_revision"]`. `axis: z` under C1 carries it too: its refusal
  is measured against the channel's axis.
- `structure/orient.py:prepared_pore` digests `cavity.py`'s bytes, so each prepared pore is written again once under
  a new name. A file with the same bytes keeps its stage-1 key.
- No test pins a stage-1 hash. `tests/tier1/test_protonation.py` builds its C1 `StructureArtefact` by hand. VER-62's
  walks take the ring's axis, so no key of theirs moves.
- The package adds no registry entry, no row of `modularity-layering.yaml` and no public name: `stage.py` imports
  `cavity.py` already.

**D6**

- `tests/tier1/test_structure_axis.py` holds `_wall`, `_rotation`, `TILT` and `OFFSET_NM`.
  `test_ver48_the_channel_axis_gates_fire` tilts `_wall(8, rim=False)` since WP6.01, under a comment naming REV-279.
- The file's 26 tests pass with the prototype swapped in. A draw takes 0.4 s to 0.9 s, the 24 draws about 12 s.

**D7**

- A wall with atoms 0.1 nm to 0.3 nm from its axis over its top 1 nm reads 7° to 8° off in 54 of 54 runs, under both
  methods, with a straightness of 0.46 nm to 0.54 nm: AO4's warning fires.
- `knowledge/04-clya-geometry-and-charge/15-the-channel-axis-of-2wcd.md`'s last two bullets and REV-279's section
  give the tie as the cause and 0.6° as the bound.

### Implementation details

**Item 1, `structure/cavity.py`.** Three edits; no other function changes.

1. A constant `JOGGLE_OPTIONS = "QJ Qbb Qc Q12"`, with a comment that `Qz` is left out (D3). In `_voids`:

   ```python
   try:
       mesh = Delaunay(local)
   except QhullError:
       try:
           mesh = Delaunay(local, qhull_options=JOGGLE_OPTIONS)
       except QhullError:
           raise SymmetryGateError(...) from None  # today's message, unchanged
   ```

2. In `_voids`, `keep` unchanged:

   ```python
   open_face = ((other < 0) | ~valid[np.maximum(other, 0)]) & valid[owner]
   ```

   Reword the comment above `owner` to say that the edge runs on past the hull and past a tetrahedron that fixes no
   centre.

3. In `_sections`, after `wide` is set and before `order`:

   ```python
   if wide.any():
       nearest, _ = voids.tree.query(points[wide])
       wide[np.flatnonzero(wide)] = np.abs(nearest - clearance[wide]) <= EMPTY_TOL * np.maximum(
           1.0, clearance[wide]
       )
   ```

   `EMPTY_TOL = 1e-6` is a new module constant that `_voids`' own check takes too.

**Item 1, `tests/tier1/test_structure_axis.py`.**

- `test_ver48_the_channel_axis_gates_fire`: `_wall(8)` in place of `_wall(8, rim=False)`; its comment goes.
- A new test, its first line saying that rounding of the atoms must not hold the axis at a second line:

  ```python
  @pytest.mark.parametrize("relative", [1e-14, 1e-12, 1e-10])
  @pytest.mark.parametrize("n", [7, 8])
  def test_ver48_the_channel_axis_is_not_locked_by_rounding(n: int, relative: float) -> None:
      tilt = _rotation(np.array([1.0, 0.0, 0.0]), math.radians(12.0))
      wall = _wall(n) @ tilt.T
      true_axis = tilt @ np.array([0.0, 0.0, 1.0])
      for seed in range(4):
          rng = np.random.default_rng(seed)
          atoms = wall * (1.0 + relative * rng.standard_normal(wall.shape))
          record = cavity.channel_axis(atoms)
          ...
  ```

  Per draw, four assertions, each with the seed in its message: the angle to `true_axis`, computed as in
  `test_ver48_the_channel_axis_recovers_a_known_axis`, is at most 1e-6 and `record.axis @ true_axis > 0`; the origin
  lies within 1e-6 nm of the line through `record.centroid_nm`; `record.converged`; `record.straightness_nm <= 1e-6`.
- `test_ver48_a_refused_triangulation_is_joggled(monkeypatch)`: replace `scipy.spatial.Delaunay` by a wrapper that
  records `qhull_options` and raises `scipy.spatial.QhullError` when it is `None`, else calls the real class. On
  `_wall(8) @ TILT.T + OFFSET_NM` assert the same four, the offset measured from `OFFSET_NM`, and that the recorded
  options are `[None, cavity.JOGGLE_OPTIONS]`. `_voids` imports `Delaunay` when called, so the patch is seen.

**Item 1, the clauses.** In `specification/05-software-design/02-pipeline-stages.md`, the NOTE on stage 1, after the
sentence that defines the candidates, say in the NOTE's own voice: that an edge runs on past the hull and past a
tetrahedron that fixes no centre; that a candidate whose clearance is not its nearest atom's distance to 10⁻⁶ is left
out; that atoms Qhull refuses for precision are triangulated again from joggled input (§8.2.55 BE4); and, beside the two limits,
that they do not follow a later measurement of 2WCD (§8.2.55 BE1). In `specification/07-verification/02-tier-1.md`,
VER-48's row gains, after "the axis being its fixed line", the 24 draws with their three sizes, and the forced retry.
Run `uv run pytest tests/tier1/test_structure_axis.py tests/tier1/test_structure_stage.py -q`. If 2WCD's test fails,
apply D4: re-pin its measured constants and the NOTE's four numbers, leave the limits, and report the move; stop if a
number passes its limit.

**Item 2.**

- `structure/cavity.py`: `CHANNEL_AXIS_REVISION = 1`, its comment citing §5.3.2's NOTE.
- `structure/stage.py`: import `CHANNEL_AXIS_REVISION` by name with its other names of `cavity`, so that the
  test's patch of the module's name is read; `_takes_channel(structure: ResolvedStructure) -> bool`, true where
  `structure.spec.symmetry.axis == "cavity" or structure.n == 1`; `align` uses it for `channel`;
  `structure_parameters` sets the key last, where it is true.
- `tests/tier1/test_structure_stage.py`: `test_ver48_the_channel_revision_keys_only_the_channel(prepared, tmp_path,
  monkeypatch)`. Build five cases with `_case`, each under its own `name`: the ring's two, `_block(prepared)` and
  `_block(prepared, axis="z")`, and the channel's three, `_block(prepared, axis="cavity")`,
  `_block(prepared, point_group="C1")` and `_block(prepared, point_group="C1", axis="z")`. Take
  `structure_parameters(resolve(load_case(case)).structure)` and `StructureArtefact(parameters=...).hash` for each.
  Assert that the ring's two hold no `channel_axis_revision` and the channel's three hold
  `nanopnp.structure.cavity.CHANNEL_AXIS_REVISION`. Then set `nanopnp.structure.stage.CHANNEL_AXIS_REVISION` to 2
  with `monkeypatch`, take the five again and assert that the ring's two hashes are the same and the channel's
  three moved. No stage runs.
- `specification/05-software-design/03-2-artefacts.md`, the NOTE on the solution payload: before "The other stages'
  payloads have no such counter", say that stage 1's key carries `channel_axis_revision` where the channel gives the
  axis, which a change that moves a channel's axis SHALL bump (§8.2.55 BE2). In
  `specification/07-verification/02-tier-1.md`, VER-48's row gains, after "is relabelled", that the key carries the
  revision under the channel alone.

**Item 4, the records.**

- The knowledge note: replace its last two bullets by the cause, the counts of D1's grounding, the joggled retry and
  the plugged lumen, each `[tested: ...]` by a test above or `[verified]` with a footnote to this plan; add this plan
  to its `sources`; add a line to `knowledge/log.md`.
- `CHANGELOG.md`, a section `## [0.7.0-alpha.6]` under `## [Unreleased]`, shaped as WP6.05's: **Fixed**, the axis, up
  to about 1° different for a structure with coplanar or exactly symmetric atoms, and the refused triangulation;
  **Changed**, the key of a channel case, so its stored first stage runs again once.
- `docs/project/review-findings.md`: REV-279 `fixed`, with a **Fixed** paragraph in `review-items.md` that corrects
  the cause and the bound. `specification/history/holds-now.yaml`: BA8, BE1, BE2 and BE4 name their clauses. Run
  `uv run .claude/scripts/decisions.py` and `uv run just docs`, and commit what they write.

### Work items

- [x] 3a53f58 1. `src/nanopnp/structure/cavity.py`, `tests/tier1/test_structure_axis.py`,
  `specification/05-software-design/02-pipeline-stages.md`, `specification/07-verification/02-tier-1.md`: the diagram's
  edges, the candidate check and the joggled retry, with their tests and clauses (D1 to D4, D6); done when
  `tests/tier1/test_structure_axis.py` and `tests/tier1/test_structure_stage.py` pass. **Executor:** main
  > **Outcome — the prediction held.** The six new cases fail on the code at `7ebfd4f` and pass with D1 to D3;
  > 2WCD's test passes unchanged, so no measured number and no limit moved (D4).
- [x] d9c5427 2. `src/nanopnp/structure/cavity.py`, `src/nanopnp/structure/stage.py`,
  `tests/tier1/test_structure_stage.py`, `specification/05-software-design/03-2-artefacts.md`,
  `specification/07-verification/02-tier-1.md`: the revision in a channel case's key (D5); done when `test_ver48_the_channel_revision_keys_only_the_channel` passes.
  **Executor:** main
- [x] 3. Compaction checkpoint. **Executor:** main
- [x] 1b2ef63 4. `knowledge/04-clya-geometry-and-charge/15-the-channel-axis-of-2wcd.md`, `knowledge/log.md`, `CHANGELOG.md`,
  `docs/project/review-findings.md`, `docs/project/review-items.md`, `specification/history/holds-now.yaml`: the
  records (D7); done when the code and review say so. **Executor:** main

### Verification

| Test | Tier | Identifier | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| `test_structure_axis.py::test_ver48_the_channel_axis_is_not_locked_by_rounding`, 6 cases of 4 draws | 1 | VER-48 | The axis each wall is built about: per draw its direction, its offset, `converged`, and the straightness. Today 17 of the 24 draws fail | VER-48: 1e-6 rad, 1e-6 nm | `uv run pytest tests/tier1/test_structure_axis.py -q` |
| `test_structure_axis.py::test_ver48_a_refused_triangulation_is_joggled` | 1 | VER-48 | The same axis and limits, through the joggled path; the options asked | VER-48 | the same |
| `test_structure_axis.py::test_ver48_the_channel_axis_gates_fire`, the wall with its rim | 1 | VER-48, QR-12 | The 12° the wall is tilted by, read from the refusal | 12 ± 0.005°, the refusal's two printed decimals (WP6.01) | the same |
| `test_structure_axis.py::test_ver48_the_channel_axis_recovers_a_known_axis`, unchanged | 1 | VER-48 | The known axis | VER-48 | the same |
| `test_structure_stage.py::test_ver48_2wcd_channel_axis_agrees_with_its_ring_axis`, unchanged | 1 | VER-48 | 2WCD's stored numbers; prediction: unmoved | VER-48: 1e-4 nm | `uv run pytest tests/tier1/test_structure_stage.py -q` |
| `test_structure_stage.py::test_ver48_the_channel_revision_keys_only_the_channel` | 1 | VER-48 | Neither ring case's hash, `auto` or `z`, moves with the revision; each channel case's does: `cavity`, C1, and C1 with `z` | exact | the same |

### Out of scope

- The tie rule, `TIE_NM` and the two limits: unchanged (D1; BE1).
- A lumen with atoms on its axis: AO4's warning stands, and the knowledge note records the measurement (D7). A ruling
  on it waits for a pore that has one; the author owns it.
- The run on macOS and Windows: the phase's close (criterion 10).
- A second real pore's measurement: none is in the repository (BC19).

### Open questions

None. The four choices that were the author's are ruled (BE1 to BE4).
