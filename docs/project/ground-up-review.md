# The ground-up review

**Status: draft, before its challenge.** WP6.04 of Phase 6 (`§8.2.51` BA10 to BA13; `§8.2.52` BB2 to BB6), started
24 November 2026. The review changes no code. Each verdict is a proposal: nothing changes until the author has ruled.

## In brief

**What a start-over would keep.** Three designers who had seen neither the code nor the requirements each designed
the program from the paper's physics, its users and the author's interview. All three chose, unprompted, today's
engine, mesher, elements and coupled Newton solve. Of the 259 rows walked, 207 are kept.

**What it would change** is the shape around the method, and the order of the work:

1. The physics would be composed of registered terms from the start. Today the coupled model is one class in a file
   of 2,076 lines, and Phases 6 and 7 build on it before Phase 8 redraws it.
2. Another group could add a term from its own package. Today nine registries exist, and none looks in an installed
   package.
3. The program would show its proof: a published page that maps each term to the analytic case that tests it, an
   error estimate with each number, and one early comparison with the paper.
4. The process would keep its form and ask the author to start one session a package, where a package now takes four.
5. The rule that each release ships a graphical surface would go, and parametric shapes would come before the
   hand-drawn sketcher.

**Cost.** The proposals for now add about seven packages to Phase 6's ten: about 38 sessions, 30 to 60 agent hours
and 62 of the author's touches at today's rates. Twelve of those sessions are the kernel's, moved from Phase 8.

**What could go wrong.** The review may propose more than one phase can carry, so the differences are ranked by gain
over cost and the author can cut from the bottom. Two proposals, the kernel's place and the early comparison, ask
again what the author ruled on 22 and 23 November; each says what is new.

**Your call.** Twelve groups of proposals, in the order to rule them. *Recommendation:* rule groups 1 to 6 at the
round, and leave groups 7 to 10 to the rounds of their phases.

## The question, and what is given

**The question** is the author's (BA10 to BA13): if the program were designed today from nothing, what would it be,
and where does today's program differ? Every requirement, constraint, exclusion, dependency, method, phase and process
rule is open, and the reason behind an earlier ruling counts as evidence and not as authority.

**Given, and not reviewed:**

- the physics of §4 and the paper it restates (BA12);
- what the author calls fixed: free and open throughout, simple cases on any ordinary computer, and one maintainer
  whose time is the limit;
- what the author will not lose: openness, extensibility and today's feature scope.

**Not done here.** No code is changed and no design is tried: a question that only a trial settles is listed under
*What stays open*. The review rules nothing. A verdict of *change now* means in Phase 6, and *change later* names its
phase.

## What the program should become

The author's picture, from five rounds of interview, is the measure.

**What it is.** A modelling and design tool between the molecular and the continuum worlds. First it is a complete and
trusted nanopore tool. Then come full 3D, an exchange with molecular simulation, and inverse design, where the user
states features and the program proposes mutations.

**For whom, in rank order:** the author's own research; method developers in other groups; experimental laboratories;
pore designers. Where two pull apart, extensible wins over exact, and the developer's power over the laboratory's
ease. The graphical interface is a goal of its own.

**Its capabilities, in rank order:**

1. A base in which every term is proven against an analytic limit, and the proof can be opened.
2. Physics that a developer composes and extends: corrections swapped, equations changed, models run side by side,
   from the developer's own package.
3. From a structure to current, selectivity and flow, each with an error estimate, on an ordinary computer.
4. Studies of many runs; mutation; the forces on an analyte.
5. A workbench over the same interface, designed as a product.

**Never:** a closed black box, a code for one paper, or a code for experts only. **Success:** every part holds
against its analytic limits; papers are built on the program; others extend it without the author.

## The design a start-over would choose

This design is the main session's, argued from the three designs, [the walk](ground-up-review/walk.md) and
[the evidence](ground-up-review/evidence.md).

**The same as today.**

- A YAML case file, a pipeline of pure stages with content hashes, and a manifest with every result.
- NGSolve and Netgen: no other engine with symbolic forms and an automatic Jacobian installs without a compiler on
  three systems.
- Second-order elements with a Taylor–Hood pair, primitive unknowns and no stabilisation: the largest cell Péclet
  number of the two timed cases is 0.33.
- A coupled damped Newton solve with the exact Jacobian, reached by continuation, and a sparse direct solve.
- The current by two routes, never as a cross-section integral of the flux.
- One Python interface under a command line and a browser workbench.

**Different from today.**

- **The kernel.** A term is one object: its weak form, its equation as text, its switches and its analytic case. A
  model is a named list of terms, and a variant is a difference from its parent. Terms, corrections, shapes and
  solvers are found in any installed package. The engine is confined to the mesh, the terms and the solve, where
  today eleven of twenty subpackages import it.
- **Trust.** A ledger, generated from the tests, shows each term against its analytic case. Each quantity carries an
  error estimate from three meshes; the adjoint later replaces the ladder and gives sensitivities. The paper's
  curves are compared within bands before anything is built on the model.
- **The order.** Idealised pores and the classical model first, with the ledger green; then the corrections, the
  structure pipeline and the comparison with the paper; then the studies, the workbench and the tools. Today's
  program built its workbench twice before its kernel had this shape.
- **Geometry and process.** Parametric shapes before any drawing by hand; one command a package.

**The one choice left open** is the workbench's kit. Two designers chose a TypeScript application and one chose
trame; none chose NiceGUI, which the author picked on a measured trial of one screen. A start-over would measure a
whole suite before it chose.

## The differences

The walk holds one row for each of the 259 items. The table groups its rows that are not plain keeps, ranked by gain
over cost, and then the keeps that go against a designer. A *small package* is `§8.3`'s measured rate for a text or
clean-up package: 5 sessions, 3 to 6 agent hours and 8 touches. A *large package* is its rate for a shell package: 6
sessions, 6 to 12 hours and 10 touches.

| GU | Difference | Verdict | Gain | Cost | Moves |
|---|---|---|---|---|---|
| GU-01 | Physics composed of registered terms, in Phase 6 | change now; surfaces later, Phase 8 | Phases 6 and 7 build on the final shape | 2 large packages, moved from Phase 8 | FR-40, FR-20, ADR-005, §5.4, §7.3, AZ1 |
| GU-02 | No rule that each release ships a graphical surface | drop | Rule and plan agree | One line | QR-11 |
| GU-03 | One command carries a package | change now | One start a package, not four | 1 small package | §8.4.4 (1), (8), (14), (16); §8.4.5 (1) |
| GU-04 | A target for the author's touches | add now | The change is seen to work | With GU-03 | §8.3 |
| GU-05 | Terms from another group's installed package | change now | Others extend it without the author | Half a small package | QR-14, §5.5, REV-67 |
| GU-06 | A published verification ledger | add now | The proof can be opened | 1 small package | QR-01, FR-25 |
| GU-07 | Four clauses that misstate | change now: text | A reader can trust them | One commit | FR-03, CON-08, ADR-001, QR-07, §2.7 |
| GU-08 | An error estimate with each quantity | change now | Comparisons with a known error | 1 large package | FR-29, NUM-32 |
| GU-09 | One early comparison with the paper | change now | A gap found five phases sooner | 1 small package | BA3 |
| GU-10 | Python from 3.12 | change now | One lock line a dependency | Half a small package | QR-09, §8.4.2 (4) |
| GU-11 | Parametric shapes in the sketcher's place | change later: Phase 10's round | Most of a tool phase saved | 2 packages, not about 50 sessions | FR-42, BA1, §2.7 |
| GU-12 | The workbench's layout left to its design document | change later: Phase 7's round | A design round changes one record | Text | IF-09, FR-31 |
| GU-13 | Browser tests in CI; in the gate by path | change later: Phase 7 | 468 s off most pushes | Within the rebuild | §7.6 |
| GU-14 | N1 allows terms; 3D becomes a test | change later: Phase 8 | Two clauses that can fail | With the composer | N1, CON-01 |
| GU-15 | The full adjoint; sensitivities to each residue | change later: Phase 9 | The mutator gets a ranked list | 1 large package | NUM-33, FR-29 |
| GU-16 | The residual current with the forces | change later: Phase 11 | What an experiment records | Within its package | FR-22 |
| GU-17 | A validated range stated; a second pore | add later: Phase 12 | One-pore tuning is tested | 1 small package | §7.5 |
| GU-18 | Case files that migrate | change later: version 1's gate | A published case opens later | 1 small package | IF-03, IF-01 |
| GU-19 | Fields for molecular simulation; the laboratory's quantities | add later: after version 1 | The author's second horizon | Not estimated | §2.7 |
| GU-20 | Engine, mesher, elements, Newton, direct solve | keep | A start-over chooses the same | None | ADR-001, ADR-002, NUM-01, NUM-16 |
| GU-21 | NiceGUI as the workbench's kit | keep, measured again | A start-over would not choose it blind | One measurement | ADR-004 |
| GU-22 | The fixed continuation ladder | keep until a trial | A start-over steps adaptively | A trial | NUM-18 |
| GU-23 | Primitive concentrations as unknowns | keep | Two of three choose the same | None | NUM-02 |
| GU-24 | Built parts that a start-over would not build | keep | Nothing to gain by deleting | None | FR-39, NUM-14, §2.6 |
| GU-25 | The order of the releases; the process's form and records | keep | A start-over validates sooner (GU-09) | None | §2.7, §8.4 |

GU-24 holds the studies' expression language and build forecast, the mode that reproduces the reference's
stabilisation, and the second structure reader. Two lacks that a designer named are not added: a container image
with MPI, which earns its upkeep only when 3D needs a distributed solve, and model comparison as a product of its
own, which a sweep over models already gives.

## The proposals, grouped for the rulings

Each card gives today, the start-over, the gain, the risk, the cost and what it depends on. What it moves is its
row of the table, unless the card adds to it.

### Group 1: the kernel's shape

Rule this first: groups 2, 3, 7 and 9 build on it.

**GU-01 The physics is composed of registered terms, from Phase 6.**

- *Today.* `physics/models.py` holds 2,076 lines and one class for the coupled model. Its four switches are a closed
  tuple, and `physics/terms.py` states each model's terms a second time, for display. FR-40 plans the composition for
  Phase 8. AZ1 (`§8.2.50`, 22 November) leaves the file whole until then, "so the same lines are redrawn once".
- *Start over.* The kernel described above, which each designer built first.
- *Gain.* Phase 6 turns the switches into data and adds the model's open terms, and Phase 7 rebuilds the Physics
  suite over the model. With the kernel first, those three are built on the final shape. The display and the solve
  can no longer disagree.
- *Risk.* A redraw of the equations could move a number unseen. The guard exists: the composition must reproduce
  VER-62's stored numbers to 10⁻⁸ with no re-pin, and pass VER-12 to VER-21, VER-31 and VER-77 unchanged.
- *What is new since AZ1.* Three blind designs put the composition before all that Phases 6 and 7 build.
- *Cost.* Two large packages: 12 sessions, 12 to 24 agent hours and 20 touches, moved from Phase 8.
- *Moves.* FR-40 (split), FR-20 (merged into it), ADR-005, §5.4, §7.3 (a manufactured solution for each term), AZ1,
  BA4, and §2.7's rows for v0.7 and v0.9. The composer's surfaces stay in Phase 8.
- *Depends on* nothing. It precedes Phase 6's open terms.

**GU-14 N1 allows terms, and 3D becomes a test.** Phase 8.

- *Today.* N1 says that users do not write weak forms. CON-01 says that the architecture must not preclude 3D, which
  no test can fail.
- *Start over.* A developer writes terms within electrolyte transport. Each registered term assembles under a 3D
  measure on a coarse mesh.
- *Gain.* N1 no longer contradicts FR-40 and the author's "change equations".
- *Risk.* N1 could be read as a general framework; its text keeps unrelated problems out.
- *Cost.* Within the composer's package: a third measure beside the two of `numerics/measures.py`, and one test.
- *Depends on* GU-01.

### Group 2: extension from outside

**GU-05 A term from another group's installed package.**

- *Today.* Nine registries, each filled by a call inside the program. Nothing looks for a registration in an
  installed package: `src/` and `pyproject.toml` name no entry point. REV-67 asks whether the registering functions
  are public, and waits for Phase 8.
- *Start over.* An installed package declares its terms, corrections, shapes or solvers. The manifest names each
  with its package and version.
- *Gain.* "Others extend it without you", with no fork.
- *Risk.* A foreign term changes a result. The manifest names it, and the stored numbers are computed with none
  installed. The registries' names become a promise to keep.
- *Cost.* Half a small package, with Phase 6's step that gives the registries one shape.
- *Depends on* GU-01, for terms alone.

### Group 3: the proof, shown

**GU-06 A verification ledger.**

- *Today.* QR-01 gates the analytic limits in Tier 2. No page shows which term each case proves.
- *Start over.* A page generated from the tests lists each term and correction with its analytic case and its
  measured error, and is published with each release. A term with no case still runs, marked unverified in the
  manifest: a badge, not a gate. One command runs the cheap cases on the user's machine.
- *Gain.* The author's first measure of success can be opened by a reader, and a foreign term's standing is visible.
- *Risk.* A page that claims more than the tests prove; so it is generated and never written by hand.
- *Cost.* One small package.
- *Moves* a new requirement beside QR-01. *Depends on* GU-01, which gives its rows their keys.

**GU-08 An error estimate with each quantity.**

- *Today.* No quantity carries an estimate of its discretisation error. FR-29 and NUM-32 allow goal-oriented
  adaptivity after version 1.
- *Start over.* On request, a quantity is solved on three meshes and reported with its observed order, its
  extrapolated value and an error bar.
- *Gain.* Two models, or the program and the paper, are compared with a known error. NUM-33's note says that the
  published numbers carry no error bar, so Phase 12 needs this study in any case.
- *Risk.* On a contour with many corners the three meshes may show no clean order; the estimate then says so and
  gives no bar. The ladder costs a third more than one run if it goes coarser than the case's mesh, and twenty
  times the run if finer; its package decides.
- *Cost.* One large package. It adds a method and changes none. VER-12, VER-13 and VER-18 argue it: their exact
  solutions give the true error to hold the estimate against. VER-62 never holds an error estimate, so no stored
  number is re-pinned.
- *Depends on* Phase 6's quantity catalogue.

**GU-09 One early comparison with the paper.**

- *Today.* No published current has been compared with the program. BA3 (23 November, against the session's
  recommendation) keeps the first comparison in Phase 12.
- *Start over.* Each design compares with the published ClyA curves, within bands, before it builds a workbench.
- *Gain.* A gap in the equations found in Phase 6 costs one package. Found in Phase 12, it reaches the rebuilt
  workbench, the tools and the forces (RSK-15).
- *Risk.* It could read as the exact copy that the author ranks second. So it is recorded and not gated, in bands
  and not digits, on the paper's tables alone.
- *What is new since BA3.* Three blind designs chose it. If the author's reason stands, this row is a keep.
- *Cost.* One small package. A ClyA run takes 394 s a point, so the curves cost hours of computing.
- *Depends on* Phase 6's open terms.

### Group 4: the process

**GU-03 One command carries a package, and GU-04 a target for the author's touches.**

- *Today.* A package takes at least four windows: its plan, the plan's review, its implementation and its shipping,
  each ended by a compaction that the author runs. It takes about eight touches, and no number says how many are
  wanted. This package paused at four checkpoints with nothing for the author to judge.
- *Start over.* One command carries a package from its brief to its pull request. The plan's review is chained,
  checkpoints do not stop by default, and a level on another model runs as a sub-agent, as this package's designers
  did. The author acts where there is a judgement: the brief, a finding, the result. A target, for example three
  touches a package, is read from the usage that each report already ends with.
- *Gain.* The author's one complaint about the process. `§8.3` estimates 317 touches to v0.13 without Phases 8 to
  10; at three a package that falls to about 120.
- *Risk.* An error runs further before the author sees it. The gates, the ship's review in a fresh context and the
  pull request stay, and so do the switches that turn each pause back on.
- *Cost.* One small package, on the workflow's files alone.
- *Depends on* nothing.

### Group 5: the release rule

**GU-02 QR-11 is dropped.**

- *Today.* Each release from v0.2 ships a graphical surface over what exists then. v0.5 added none, v0.7 adds none,
  and v0.9 to v0.12 are library first (BA1, BA5).
- *Start over.* A capability is built and tested in the library, and the workbench follows. No designer kept the rule.
- *Gain.* The rule and the plan agree, and no release waits for a surface.
- *Risk.* The workbench falls behind. FR-31 and Phase 7 still require it, and QR-11's four verification rows are
  traced under IF-09 already.
- *Cost.* One line, in the round's commit. *Depends on* nothing.

### Group 6: text, now

**GU-07 Four clauses that misstate.**

- *FR-03* names three pores, and all three designers read it as a built-in table. The program takes any `C<n>` from
  the case's `symmetry.point_group`. The clause should say so.
- *CON-08 and ADR-001* call PARDISO unavailable. The installed engine takes it from pip's `mkl` on Windows and
  Linux (checked). The constraint becomes: the default path needs no closed part, and MKL is an option that a user
  registers.
- *QR-07* asks for a factorisation in "acceptable" time, which cannot fail. The factorisation is 24 % of the
  measured solve and the Jacobian's assembly on one thread 62 % (REV-156). Phase 6's speed-up package gives the
  clause seconds and gigabytes for the whole solve on a named machine.
- *§2.7's backlog* lists nine items in no order. The interview ranks three: 3D, the molecular link, inverse design.
- *Cost.* One commit of the round's amendment; QR-07 with the speed-up package. *Risk.* None found.

**GU-10 Python from 3.12.**

- *Today.* Python 3.11 to 3.14. The newest SciPy, Pint, Zarr and Panel need 3.12; the program holds Pint below 0.26
  and locks an older SciPy for 3.11.
- *Start over.* Each designer kept 3.11; the survey of releases argues the change.
- *Gain.* One locked line for each dependency, and one CI leg fewer.
- *Risk.* A cluster that offers 3.11 alone. On a user's own machine uv fetches a newer Python.
- *Cost.* Half a small package: the lock, CI's matrix and the texts.

### Group 7: shapes before the sketcher

**GU-11 Parametric shapes in the sketcher's place.** Phase 10's round.

- *Today.* FR-42 and Phase 10 build a sketcher that draws the domain by hand, before validation (BA1).
  `geometry.pore.shape` accepts `cylinder` alone.
- *Start over.* Registered shapes: a cone, an hourglass, a supplied profile, a given surface charge. Drawing by
  hand comes after version 1 (A) or never (B, C).
- *Gain.* Solid-state pores and the ledger's public cases.
- *Cost.* About two packages, where BA1 guessed a tool phase at 50 sessions and 80 touches.
- *Risk.* The author will not lose today's feature scope, and the sketcher is planned scope. It moves after
  version 1; it is not dropped.
- *Moves* also the workbench design's *Later tools*. *Depends on* GU-05.

### Group 8: the workbench, at Phase 7's round

**GU-12 The layout belongs to the design document.**

- *Today.* IF-09 and FR-31 name six suites, a rail, a count and a queue. The design document, 16,450 words, keeps
  four spent sections of about 3,000 words, most of them on the retired Qt shell.
- *Start over.* The requirement holds the server, the browser, the thin shell and the tasks. Three designers drew
  three layouts over that one boundary.
- *Gain.* A design round changes one record, and each workbench session reads 3,000 words fewer.
- *Risk.* A looser requirement lets the layout drift; the document's `WB-` rows still bind it.
- *Cost.* Text, in Phase 7's planning.

**GU-13 The browser tests run in CI, and in the gate by path.**

- *Today.* The 149 browser tests take 468 s of the push gate's 539 s on every change of code. CI's legs install no
  browser and skip 142 of them.
- *Start over.* CI runs them, and the gate runs them when a push touches the workbench.
- *Gain.* Most pushes are gated in about a minute, and the tests run where a merge is decided.
- *Risk.* A break of the workbench by a library change is found in CI and not before the push.
- *Cost.* Within Phase 7's rebuild of those tests.

GU-21 belongs to this round: the kit is kept, and measured again on the first rebuilt suite. The trial that chose
NiceGUI measured one screen, 169 lines against 246 and a redraw of 22 ms against 14 ms. At 18,183 lines a like
redraw takes 315 ms against a line of 200 ms (REV-258).

### Group 9: sensitivities, in Phase 9

**GU-15 The full adjoint, and the sensitivity of a quantity to each residue.**

- *Today.* NUM-33 prefers a linear Poisson–Boltzmann surrogate to the full adjoint, for its cost. No quantity has a
  sensitivity to a residue's charge.
- *Start over.* One transposed solve, with the factors that Newton already holds, gives a quantity's sensitivity to
  every atomic charge, since the fixed charge is linear in each. The engine solves the transposed system with the
  same factors (checked).
- *Gain.* The mutator gets a ranked list of residues for about the cost of one more solve step. It is the first
  step of inverse design.
- *Risk.* The Jacobian must be exact where a clamp is active, and the derivative is one-sided there.
- *Cost.* One large package. The method is argued by finite differences of the full model and by VER-13, whose
  solution is linear in its wall value, so that its derivative is known exactly. It adds quantities and moves no
  stored number, so VER-62 is not re-pinned.
- *Depends on* GU-01 and GU-08.

### Group 10: later capabilities

- **GU-16 The residual current, Phase 11.** FR-22 reports the forces over an analyte's positions. Each position is
  solved already and FR-23 reads the current from any solve, so the current that an experiment records costs no new
  physics. *Cost:* within Phase 11's package. *Risk:* none found.
- **GU-17 A validated range, and a second pore, Phase 12.** A result does not say whether its conditions lie inside
  the validated range, and validation is planned on ClyA alone. FR-37 claims that no rule is specific to one pore,
  yet the protein permittivity, the exclusion offset and the isolevel were set on ClyA (B). *Risk:* the second pore
  disagrees and version 1 waits. *Cost:* one small package and its published data.
- **GU-18 Case files that migrate, at version 1's gate.** Earlier schemas are refused, and IF-01's promise of
  stability names neither the case file nor the run record. Until version 1 the author is the one user, so a
  migration for each change buys little. *Cost:* one small package.
- **GU-19 After version 1.** Solved fields on a 3D lattice for molecular or Brownian dynamics, the author's second
  horizon (A, C). Asymmetric reservoirs with the reversal potential, and measured current–voltage data beside a
  curve (B). Both join the backlog with no estimate.

### Groups 11 and 12: the keeps against the designers, and the trials

GU-21 to GU-25 keep what one designer or more would not build; each reason is in the walk. Most are kept because
they are built and no cost of them was measured, not because a start-over would choose them. The author may confirm
or reopen each. The six trials are listed under *What stays open*.

## What the guard showed

`=` is today's choice, `≠` another. A choice that the designers' pack names is marked *prompted*.

| Choice | Today | A | B | C | Note |
|---|---|---|---|---|---|
| Engine | NGSolve | = | = | = | Each runner-up is FEniCSx |
| Mesher | Netgen; Gmsh optional | = | = | = | B would not keep Gmsh |
| Elements | Second order, Taylor–Hood, no stabilisation | = | = | = | The pack held the reference's first-order pair |
| Unknowns | Primitive | = | ≠ | = | B: log-concentrations |
| Nonlinear solve | Coupled Newton, exact Jacobian | = | = | = | |
| Continuation | A fixed ladder | ≠ | ≠ | ≠ | Each steps adaptively |
| Current | Two routes, no cross-section flux | = | = | = | |
| Structure reading | MDAnalysis and gemmi | ≠ | ≠ | ≠ | gemmi for both formats |
| Record | A manifest with each result | = | = | = | |
| Workbench kit | NiceGUI | ≠ | ≠ | ≠ | React (A, B); trame (C) |
| Physics | Models as classes | ≠ | ≠ | ≠ | Composed terms |
| Proof | Gated, not shown | ≠ | ≠ | ≠ | A ledger and error bars |
| Named by the pack | Python; 2D-axisymmetric finite elements; YAML case file; sparse direct solve; PDB2PQR with PROPKA; browser workbench | = | = | = | Prompted: it proves nothing |

All three designers chose today's in six of the twelve unprompted rows, and all three chose otherwise in five: the
kernel, the proof, the kit, the reader and the ladder. The first two are this review's first proposals.

A first run of the three designers was set aside, because one line of the pack still named the engine. A check of
every call in each designer's transcript found no file or address outside the pack.

After the unblinding each designer judged the requirement lists. All three kept ADR-001 and changed FR-40, ADR-005
and N1; two dropped QR-11 and one changed it.

## What stays open

**Six questions for a trial**, each to become a row of the review register, owned by the round:

1. What a direct solve of the model costs at 10⁶ unknowns, with UMFPACK and with PARDISO. Two surveys timed
   stand-in matrices and disagree.
2. Whether compiled weak forms and a threaded assembly cut the corrections' cost. The corrections make a Newton step
   up to thirteen times dearer, the forms run uncompiled, and no file enters the engine's task manager.
3. Whether the corrections can be switched on at the target concentration over FR-17's whole envelope. The salt
   ramp could then run in the classical model, and four of the six costly rungs would go (GU-22).
4. Whether plotly.js pans a field map of 10⁵ cells smoothly.
5. Whether ParaView shows a second-order field from XDMF or VTKHDF without resampling.
6. Whether Netgen meshes a wall layer at the Debye length without Gmsh's size fields.

**Open by their nature:**

- The workbench's kit, until Phase 7 measures a rebuilt suite (GU-21).
- The records' weight. Plans, reviews and history hold 1.18 million words, 2.5 for each word of code and tests. They
  are kept: they are read on demand, and the caps on a plan are two packages old. Their effect should be measured at
  Phase 6's close.

## How it was made

The order was the guard (`wp6.04`'s D1), and each step was committed before the next read anything.

1. **The author's view.** Five rounds of interview, closed when the author called a summary complete.
2. **Three blind designs.** A ran on Fable 5.2 with no lead user, B on Fable 5.2 for the laboratory, and C on
   Opus 5.5 for the method developer. Each read only a pack of the physics, the users and the interview.
3. **The unblinding.** Each designer then read the requirements, the releases and the architecture decisions, and
   marked each keep, change or drop.
4. **The evidence.** The program was measured where it cost, and six Sonnet agents surveyed
   [today's alternatives](ground-up-review/technologies.md). The main session checked at its source each fact that
   a card rests on.
5. **The walk.** The main session gave a row to each of the 259 items.

**Limits.**

- The main session wrote the report and knows the program. `CLAUDE.md` loads at a session's start and names the
  subpackages, so only the designers were blind. Until the unblinding the main session read no source file, no
  design section and no survey.
- For the rows that the designers did not judge one by one, their marks are read from each design's text.
- Each cost is an estimate at a measured rate, and none is a measurement of the work it names.
- [The challenge](ground-up-review/challenge.md) by two agents and the physics reviewer follows this draft.

The record of each step, with every brief and every list of calls, is in
[How it was made](ground-up-review/method.md). The designs are [A](ground-up-review/design-a.md),
[B](ground-up-review/design-b.md) and [C](ground-up-review/design-c.md).
