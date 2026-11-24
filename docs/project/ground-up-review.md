# The ground-up review

**Status: ruled by the author on 24 November 2026** (`§8.2.53` BC1 to BC24, in
[the decisions register](decisions.md)). WP6.04 of Phase 6 (`§8.2.51` BA10 to BA13; `§8.2.52` BB2 to BB7), written
24 November 2026. The review changes no code, and each verdict below is the proposal as it was put: the rulings
differ from it in eight places. Above all, the kernel is built in Phase 6, the phase is split in two, and the
phases named below are renumbered: the library's foundations are Phase 7 and the workbench's rebuild Phase 8.

## In brief

**What a start-over would keep.** Three designers who had seen neither the code nor the requirements each designed
the program from the paper's physics, its users and the author's interview. All three chose, unprompted, today's
engine, mesher, elements and coupled Newton solve. Of the 259 rows walked, 209 are kept. A designer spoke for 91 of
those with none against; no designer spoke to 64; 54 are kept against at least one designer.

**What it would change** is the shape around the method, and the order of the work:

1. The physics would be composed of registered terms. The plan builds this in Phase 8; the review proposes to state
   the target now and to prepare it in Phase 6.
2. The program would show its proof: a page that maps each term to the analytic case that tests it, an estimate of
   the mesh error, and one early comparison with the paper.
3. The process would keep its form and ask the author for fewer starts a package.
4. The rule that each release ships a graphical surface would go, and parametric shapes would come before the
   hand-drawn sketcher.

**What the challenge changed.** Two challengers and the physics reviewer read the draft, which built the kernel in
Phase 6. They showed that the composition is a design problem and that the stored numbers guard the default
switches alone. The kernel stays in Phase 8, as the author ruled (AZ1). Two proposals moved later, two tests were
replaced, and NUM-33 stays.

**Cost.** The proposals for now add about three packages to Phase 6's ten: 13 to 18 sessions, 8 to 21 agent hours
and 20 to 28 of the author's touches at today's rates. The draft asked for seven packages.

**What could go wrong.** The early comparison asks again what the author ruled on 23 November. The second
challenger finds that the keeps lean towards the program as it is; each objection not met is shown on its row.

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

**Not done here.** No code is changed, no design is tried and nothing is ruled. *Change now* means in Phase 6;
*change later* names its phase.

## What the program should become

The author's picture, from five rounds of interview, is the measure: a modelling and design tool between the
molecular and the continuum worlds. First it is a complete and trusted nanopore tool. Then come full 3D, an exchange
with molecular simulation, and inverse design.

**For whom, in rank order:** the author's own research; method developers in other groups; experimental laboratories;
pore designers. Extensible wins over exact, and the developer's power over the laboratory's ease. The graphical
interface is a goal of its own.

**Its capabilities, in rank order:**

1. A base in which every term is proven against an analytic limit, and the proof can be opened.
2. Physics that a developer composes and extends from an own package.
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
- Second-order elements with a Taylor–Hood pair, primitive unknowns, and no stabilisation by default, with the cell
  Péclet number checked on each run (NUM-11, NUM-12).
- A coupled damped Newton solve with the exact Jacobian, reached by continuation.
- The current by two routes, never as a cross-section integral of the flux.

**Different from today.**

- **The kernel.** A term is one object: what it adds to a flux or a stress, its equation as text, its switches and
  its analytic case. A correction is a coefficient that several terms share, and a rule binds the terms that the
  physics requires together (PHY-08). A model is a named list of terms, each flux integrated once; a variant is a
  difference from its parent. Terms, corrections, shapes and solvers are found in any installed package. The engine
  is confined to the mesh, the terms and the solve, where today eleven of twenty subpackages import it.
- **Trust.** A ledger, generated from the tests, shows each term against its analytic case. A quantity carries an
  estimate of its mesh error. The paper's curves are compared within bands before anything is built on the model.
- **The order.** Idealised pores and the classical model first, with the ledger green; then the corrections, the
  structure pipeline and the comparison with the paper; then the studies, the workbench and the tools. Today's
  program built its workbench twice before its kernel had this shape.
- **Geometry and process.** Parametric shapes before any drawing by hand; one command a package.

**The one choice left open** is the workbench's kit. No designer chose NiceGUI, and a start-over would build its
hardest view in each candidate before it chose.

## The differences

The table groups the walk's rows that are not plain keeps, ranked by gain over cost, and then the keeps that go
against a designer. The numbers are the draft's, kept so that [the challenge](ground-up-review/challenge.md) reads
against them. A *small package* is `§8.3`'s rate for a text or clean-up package: 5 sessions, 3 to 6 agent hours and
8 touches. A *large package* is its rate for a shell package: 6 sessions, 6 to 12 hours and 10 touches.

| GU | Difference | Verdict | Gain | Cost | Moves |
|---|---|---|---|---|---|
| GU-02 | No rule that each release ships a graphical surface | drop | Rule and plan agree | One line | QR-11 |
| GU-07 | Four clauses that misstate; four spent sections | change now: text | A reader can trust them | One commit | FR-03, CON-08, ADR-001, QR-07, §2.7 |
| GU-03 | Fewer starts a package | change now | One start, not four | None, then 1 small package | §8.4.4, §8.4.5 |
| GU-04 | A target for the author's touches | add now | The change is seen to work | With GU-03 | §8.3 |
| GU-06 | A published verification ledger | add now | The proof can be opened | 1 small package | QR-01, FR-25 |
| GU-08 | A mesh-error estimate | change now | Comparisons with a known error | 1 small package | FR-29, NUM-32 |
| GU-09 | One early comparison with the paper | change now | A gap found five phases sooner | Runs at the phase's close | BA3 |
| GU-01 | The composed kernel, stated and prepared | change now: text and guard | Phase 6 builds towards one shape | Half a small package | FR-40, FR-20, ADR-005, §5.4 |
| GU-11 | Parametric shapes in the sketcher's place | change later: Phase 10's round | Most of a tool phase saved | About 2 packages | FR-42, BA1, §2.7 |
| GU-05 | Terms from another group's installed package | change later: Phase 8 | Others extend it without the author | Half a small package | QR-14, §5.5, REV-67 |
| GU-14 | N1 allows terms; 3D checked by a benchmark | change later: Phase 8 | Two clauses that can fail | Priced at Phase 8's round | N1, CON-01, §7.3 |
| GU-15 | A quantity's sensitivity to each atomic charge | add later: Phase 9 | The mutator gets ranked charge changes | 1 large package | FR-41 |
| GU-12 | The workbench's layout left to its design document | change later: Phase 7's round | A design round changes one record | Text | IF-09, FR-31 |
| GU-13 | The gate runs the browser tests by path | change later: Phase 7 | Not measured | A few lines | §7.6 |
| GU-10 | Python from 3.12 | change later: when a dependency forces it | One lock line a dependency | Half a small package | QR-09, §8.4.2 (4) |
| GU-16 | The residual current with the forces | change later: Phase 11 | What an experiment records | Within its package | FR-22 |
| GU-17 | A validated range stated; a second pore | add later: Phase 12 | One-pore tuning is tested | Not known | §7.5 |
| GU-18 | Case files that migrate | change later: version 1's gate | A published case opens later | 1 small package, then upkeep | IF-03, IF-01 |
| GU-19 | The molecular link; the laboratory's quantities | add later: after version 1 | The author's second horizon | Not estimated | §2.7 |
| GU-20 | Engine, mesher, elements, Newton | keep | A start-over chooses the same | None | ADR-001, ADR-002, NUM-01, NUM-16 |
| GU-21 | NiceGUI as the workbench's kit | keep, tried before the rebuild | A start-over would not choose it blind | A trial | ADR-004 |
| GU-22 | The fixed continuation ladder | keep until a trial in Phase 6 | A start-over steps adaptively | A trial | NUM-18 |
| GU-23 | Primitive concentrations as unknowns | keep | Two of three choose the same; C is unsure | None | NUM-02 |
| GU-24 | Built parts that a start-over would not build | keep | Little to gain by deleting | None | FR-39, NUM-14, §2.6 |
| GU-25 | The releases' order; CI's platforms; the process | keep, objected | See group 11 | None | §2.7, §7.6, §8.4 |

GU-24 holds the studies' expression language and build forecast, the mode that reproduces the reference's
stabilisation, and the second structure reader. Two lacks that a designer named are not added: a container image
with MPI, and model comparison as a product of its own.

## The proposals, grouped for the rulings

Each card gives today, the start-over, the gain, the risk, the cost and what it depends on. What it moves is its
row of the table, unless the card adds to it. *Changed* says what the challenge changed, and *Objected* shows an
objection that is not met.

### Group 1: the kernel's shape

**GU-01 The composed kernel: stated and prepared now, built in Phase 8.**

- *Today.* The weak forms sit in five modules beside `physics/models.py`, whose `CoupledModel`, about 760 lines,
  assembles them. `physics/terms.py` holds a `Term` for each, with its clause, its equation as text and its
  switches, for display alone. FR-40 plans the composition for Phase 8, and AZ1 (`§8.2.50`, 22 November) leaves the
  file whole until then.
- *Changed.* Each designer built the kernel first, and the draft built it in Phase 6. Three findings met that:
    - the workbench reads the model through nine names, so Phase 7 can build on those once they are fixed;
    - a correction is a coefficient that several terms share, PHY-08 binds two terms together, and a flux that is
      integrated term by term moves its quadrature: design work, which is Phase 8's round;
    - VER-62's stored numbers cover the default switches alone.
- *Proposed now.* ADR-005 and FR-40 state the target, and FR-20 merges into FR-40. Phase 6's planned step "switches
  as data" fixes the nine names as the kernel's interface. Numbers are stored for the switches off their default
  (PHY-23's terms, the log branch, NUM-14's mode) before any redraw.
- *Gain.* Phases 6 and 7 build towards one stated shape, and Phase 8's redraw is guarded on every path.
- *Risk.* A target stated before its design round may be wrong in detail.
- *Cost.* Text, and half a small package for the stored numbers.
- *At Phase 8.* The redraw must reproduce VER-62 to 10⁻⁸ and pass VER-12 to VER-22, VER-31, VER-42 and VER-77
  unchanged. §7.3 gains a manufactured solution for each term over a verified base operator; it does not reach the
  clamps.

**GU-14 N1 allows terms, and 3D is checked by a benchmark.** Phase 8.

- *Today.* N1: users do not write weak forms. CON-01: the architecture must not preclude 3D, which no test can fail.
- *Start over.* A developer writes terms within electrolyte transport. One benchmark, VER-13 or VER-17, solved on a
  coarse 3D mesh agrees with its axisymmetric solve.
- *Changed.* The draft assembled each term under a 3D measure. Such an assembly takes the Cartesian branch, never
  touches the axisymmetric terms, and lets the charge's quadrature fall back unseen (the physics reviewer).
- *Gain.* N1 no longer contradicts FR-40 and the author's "change equations", and CON-01 can fail.
- *Cost.* Not known: a 3D solve needs a 3D mesh and forms that take it. Phase 8's round prices it.

### Group 2: extension from outside

**GU-05 A term from another group's installed package.** Phase 8.

- *Today.* Nine registries. A package can register by import; nothing finds a registration when the command line or
  the workbench starts without a script. REV-67 waits for Phase 8.
- *Start over.* An installed package declares its terms, corrections, shapes or solvers, and the manifest names
  each with its package and version.
- *Changed.* The draft did this in Phase 6. That would fix nine registries' names before the kernel exists, and no
  second group has asked.
- *Gain.* "Others extend it without you", with no fork. *Risk.* A foreign term changes a result; the manifest names it.
- *Cost.* Half a small package, with the composer.

### Group 3: the proof, shown

**GU-06 A verification ledger.**

- *Today.* §7.3 is published and gives each benchmark its closed form and its criterion. No page starts from a term
  and shows the case that proves it, and a test asserts a threshold without recording the error it measured.
- *Start over.* A page generated from the tests lists each term and correction with its analytic case. A term with
  no case still runs, marked unverified in the manifest: a badge, not a gate. One command runs the cheap cases on
  the user's machine.
- *Gain.* The author's first measure of success can be opened by a reader.
- *Risk.* A page that claims more than the tests prove; so it is generated. Each new term and test must be tagged.
- *Cost.* One small package, with the page keyed on the clause that each `Term` already names. Recording each
  measured error needs the tests to write their numbers; its plan prices that.
- *Depends on* nothing: the draft made it wait for the kernel.

**GU-08 A mesh-error estimate, first where the answer is exact.**

- *Today.* No quantity carries an estimate of its mesh error. `numerics.mesh.size_scale` already makes a mesh study
  a sweep. FR-29 and NUM-32 allow goal-oriented adaptivity after version 1.
- *Start over.* On request, a quantity is solved on a ladder of meshes and reported with its observed order and an
  error bar.
- *Proposed now.* The estimate on the benchmarks whose quantity is exact, and on the idealised pore. On a protein
  pore it is Phase 12's study.
- *Gain.* Two models, or the program and the paper, are compared with a known error.
- *Limits, from the physics reviewer.* The ladder goes finer than the case's mesh, because the gates refuse coarser
  ones, so it costs seven to twenty times the run. Netgen's meshes are not nested: the ratio comes from the element
  counts. Three meshes cannot show the asymptotic range: four, or a safety factor. The differences must stand above
  Newton's stopping floor, about 4 × 10⁻⁶. The bar is the mesh error on the given contour alone.
- *Cost.* One small package. It adds a method and changes none. VER-16 (an exact current), VER-14 (a flow), VER-17
  (corners) and VER-18 argue it. The reported value stays the case mesh's, so VER-62 is not re-pinned.
- *Depends on* Phase 6's quantity catalogue.

**GU-09 One early comparison with the paper.**

- *Today.* No published current has been compared with the program. BA3 (23 November, against the session's
  recommendation) keeps the first comparison in Phase 12; the ruling records no reason.
- *Start over.* Each design validates on ClyA before it builds a workbench. This proposal is the least of that.
- *Gain.* A gap in the equations found in Phase 12 reaches the rebuilt workbench, the tools and the forces (RSK-15).
- *Risk.* It could read as the exact copy that the author ranks second: so it is recorded and not gated, in bands
  and not digits. A gap may be hard to read: the published values were solved with stabilisation and carry no error
  bar.
- *What is new since BA3.* Three blind designs chose it. If the author's ruling stands, this row is a keep.
- *Cost.* No package, where the draft asked one: the frozen ClyA case of example 05 and its sweep run at Phase 6's
  close, and the phase's report sets their numbers beside the paper's.
- *Depends on* Phase 6's open terms.

### Group 4: the process

**GU-03 Fewer starts a package, and GU-04 a target for the author's touches.**

- *Today.* A package takes at least four windows: its plan, the plan's review, its implementation and its shipping,
  each ended by a compaction that the author runs. It takes about eight touches, and no number says how many are
  wanted. Two switches already remove the pause at a checkpoint and before the ship; both are off.
- *Start over.* One command carries a package, and the author acts where there is a judgement.
- *Proposed now, in two steps.* First the author sets both switches for two packages, at no cost, and the usage
  reports show what is left. Then, if it pays, one small package chains the plan's review and runs a level on
  another model as a sub-agent; each plan still proposes both models to the author (AZ20, AZ21). The target is set
  from the measured usage.
- *Changed.* The draft priced a package before the switches were tried, and named three touches, which the brief,
  the plan's approval and the merge already use up.
- *Gain.* The author's one complaint about the process.
- *Risk.* An error runs further before the author sees it. The gates, the ship's review in a fresh context and the
  pull request stay.

### Group 5: the release rule

**GU-02 QR-11 is dropped.**

- *Today.* Each release from v0.2 ships a graphical surface over what exists then. v0.5 added none, v0.7 adds none,
  and v0.9 to v0.12 are library first (BA1, BA5).
- *Start over.* The library first, then the workbench. No designer kept the rule.
- *Risk.* The workbench falls behind. FR-31 and Phase 7 still require it, and QR-11's four verification rows are
  traced under IF-09 already.
- *Cost.* One line, in the round's commit.

### Group 6: text, now

**GU-07 Four clauses that misstate, and four spent sections.**

- *FR-03* names three pores, and all three designers read it as a built-in table. The program takes any `C<n>` from
  the case's `symmetry.point_group`.
- *CON-08 and ADR-001* call PARDISO unavailable. The engine's code takes it from pip's `mkl` on Windows and Linux
  (read, not run). The constraint becomes: the default path needs no closed part, and MKL is an option that a user
  registers.
- *QR-07* asks for a factorisation in "acceptable" time, which cannot fail. The factorisation is 24 % of the
  measured solve and the Jacobian's assembly 62 % (REV-156). Phase 6's speed-up package gives the clause seconds
  and gigabytes for the whole solve.
- *§2.7's backlog* lists nine items in no order. The interview ranks three: 3D, the molecular link, inverse design.
- *The workbench design* keeps four spent sections of about 3,000 words, most on the retired Qt shell. They go now.
- *Cost.* One commit; QR-07 with the speed-up package. *Risk.* None found.

### Group 7: shapes before the sketcher

**GU-11 Parametric shapes in the sketcher's place.** Phase 10's round.

- *Today.* FR-42 and Phase 10 build a sketcher that draws the domain by hand, before validation (BA1). A supplied
  profile is accepted already, so a cone is a file today; `geometry.pore.shape` accepts `cylinder` alone.
- *Start over.* Registered shapes: a cone, an hourglass, a given surface charge. Drawing by hand comes after
  version 1 (A) or never (B, C).
- *Gain.* Solid-state pores and the ledger's public cases.
- *Cost.* About two packages, where BA1 guessed a tool phase, without a measurement, at 50 sessions and 80 touches.
- *Risk.* The sketcher is planned scope, which the author will not lose. It moves after version 1.
- *Objected.* BA1 was ruled on 23 November, and the three designs are the one new reason.
- *Moves* also the workbench design's *Later tools*. *Depends on* GU-05.

### Group 8: the workbench, at Phase 7's round

**GU-12 The layout belongs to the design document.**

- *Today.* IF-09 and FR-31 name six suites, a rail, a count and a queue.
- *Start over.* The requirement holds the server, the browser, the thin shell and the tasks. Three designers drew
  three layouts over that one boundary.
- *Gain.* A design round changes one record. *Risk.* The layout drifts; the document's `WB-` rows still bind it.
- *Objected.* The author ruled the layout on concept boards, and the gain beyond GU-07's deletion is small.
- *Cost.* Text, in Phase 7's planning.

**GU-13 The gate runs the browser tests by path.**

- *Today.* The 149 browser tests take 468 s of the push gate's 539 s on every change of code. A pull request's CI
  runs them too, on Linux; the platform legs skip 142.
- *Start over.* The gate runs them when a push touches the workbench.
- *Gain.* Not measured. `gui` and the packages that feed it changed in 13 to 18 of 20 packages, so a safe rule may
  skip few pushes.
- *Why later.* Phase 7 rebuilds those tests.
- *Objected.* CI runs them already, so the gate could choose by path in Phase 6 (the second challenger).
- *Cost.* A few lines of the gate.

GU-21 belongs to this round. The kit is kept and tried before the rebuild: Phase 7's design study builds its
hardest view in the kit and audits it against QR-16. The draft measured after the first rebuilt suite, the order
of a sunk cost (the second challenger). The trial that chose NiceGUI measured one screen, and neither the ceiling
of a design nor accessibility.

### Group 9: sensitivities, in Phase 9

**GU-15 The sensitivity of a quantity to each atomic charge.**

- *Today.* No quantity has a sensitivity to a charge.
- *Start over.* One adjoint solve at the converged state gives a quantity's sensitivity to every atomic charge: at
  fixed atoms the deposited charge is linear in each.
- *Changed.* The draft also replaced NUM-33's surrogate by this adjoint. NUM-33 governs an error estimator, which an
  adjoint in the same finite-element space gives as zero, so NUM-33 stays. Newton keeps no factors: the adjoint
  costs a new assembly and factorisation, about one Newton step. The transposed solve was checked on a scalar
  matrix alone.
- *Gain.* The mutator gets charge changes ranked by their effect. It does not rank mutations: a mutation moves
  atoms, radii and the contour, and protonation is discrete.
- *Risk.* The Jacobian is exact in the default mode alone, and one-sided at an active clamp.
- *Cost.* One large package. It is argued by Grahame's relation (VER-12, VER-77), which is exact and nonlinear, by
  an identity between adjoint and tangent, and by finite differences above Newton's floor. It moves no stored number.

### Group 10: later capabilities

- **GU-16 The residual current, Phase 11.** FR-22 reports the forces over an analyte's positions. Each position is
  solved already, so the current that an experiment records costs no new physics.
- **GU-17 A validated range, and a second pore, Phase 12.** A result does not say whether its conditions lie inside
  the validated range, and validation is planned on ClyA alone. FR-37 claims that no rule is specific to one pore,
  yet the protein permittivity, the exclusion offset and the isolevel were set on ClyA (B). *Objected:* only ClyA
  has a structure, an ensemble and published data of this model, and no second set is named.
- **GU-18 Case files that migrate, at version 1's gate.** Earlier schemas are refused (AZ5), and IF-01's promise of
  stability names neither the case file nor the run record. *Objected:* each later change of the schema then needs
  its migration.
- **GU-19 After version 1.** Solved fields on a 3D lattice for molecular or Brownian dynamics (A, C). Asymmetric
  reservoirs with the reversal potential, and measured current–voltage data beside a curve (B).
- **GU-10 Python from 3.12, when a dependency forces it.** The newest SciPy and Pint need 3.12, and the program
  holds Pint below 0.26. *Changed:* the draft moved the floor now. The gain is thin today: each push's CI runs 3.14
  alone, and a cluster may offer 3.11 alone.

### Groups 11 and 12: the keeps against the designers, and the trials

GU-20 to GU-25 keep what one designer or more would not build. The second challenger finds that they lean towards
the program as it is. Three rows changed: GU-20 no longer counts the direct solve, which the pack named; GU-21 is
tried before the rebuild; GU-22's trial has a place. Not met, for the author to confirm or reopen:

- **GU-24.** "Built" is a sunk cost. The parts are small: 798 lines for the expression language and the forecast,
  716 for the stabilised mode.
- **GU-25, the records.** "Read on demand" counts reading alone. Since v0.5.0, 317 of 473 commits touch the plans
  and 176 the source. Net of their Outcome annotations the three newest plans hold 3,623 to 4,099 words against a
  cap of 3,850. The keep rests on the author's "same process form".
- **GU-25, CI's platforms.** A red Windows leg cost one package (WP6.01). The keep rests on AZ8, ruled on
  22 November with that cost known.
- **GU-25, validation last.** Each design validates before its workbench; GU-09 is the least of that.
- **Five more keeps** whose reason argues a change of text: §8.4.4 (15), FR-30, §5.3.1, FR-33 and IF-06.

The trials: *What stays open*.

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
| Workbench kit | NiceGUI | ≠ | ≠ | ≠ | React (A, B); trame (C) |
| Physics | Models as classes | ≠ | ≠ | ≠ | Composed terms |
| Proof | Gated, not shown | ≠ | ≠ | ≠ | A ledger and error bars |
| Named by the pack | Python; 2D-axisymmetric finite elements; YAML case file; sparse direct solve; PDB2PQR with PROPKA; browser workbench | = | = | = | Prompted: it proves nothing |

All three designers chose today's in five of the eleven unprompted rows, and all three chose otherwise in five: the
kernel, the proof, the kit, the reader and the ladder. The designs share one pack and one interview, and two ran on
one model, so their agreement is less than three independent votes.

A first run was set aside, because the pack still named the engine and the workbench's terms. A check of every
call in each designer's transcript found no file or address outside the pack.

After the unblinding all three kept ADR-001 and changed FR-40, ADR-005 and N1; two dropped QR-11.

## What stays open

**Seven questions for a trial**, REV-281 to REV-287 of the review register, owned by the round:

1. What a direct solve of the model costs at 10⁶ unknowns, with UMFPACK and with PARDISO.
2. Whether compiled weak forms and a threaded assembly cut the corrections' cost: they make a Newton step six
   times dearer on 392 elements and thirteen times on 16,444 (REV-156).
3. Whether the corrections can be switched on at the target concentration over FR-17's envelope, so that the salt
   ramp's four rungs run in the classical model (GU-22). It is the largest jump of the coefficients. A classical
   state at high salt may pass the packing limit near a charged wall, where the steric rung is refused. A new path
   moves the stored numbers past 10⁻⁸, so VER-62 is re-pinned. The same runs compare the log branch (GU-23). Its
   place is Phase 6's speed-up package.
4. Whether plotly.js pans a field map of 10⁵ cells smoothly.
5. Whether ParaView shows a second-order field from XDMF or VTKHDF without resampling.
6. Whether Netgen meshes a wall layer at the Debye length without Gmsh's size fields.
7. Whether NiceGUI carries the workbench's hardest view and QR-16, before Phase 7's rebuild (GU-21).

**Open by its nature:** whether the keeps lean towards the program as it is, as the second challenger says.

## How it was made

The order was the guard (`wp6.04`'s D1), and each step was committed before the next read anything.

1. **The author's view.** Five rounds of interview, closed when the author called a summary complete.
2. **Three blind designs.** A ran on Fable 5.2 with no lead user, B on Fable 5.2 for the laboratory, and C on
   Opus 5.5 for the method developer. Each read only a pack of the physics, the users and the interview.
3. **The unblinding.** Each designer then read the requirements and the architecture decisions, and marked each.
4. **The evidence.** The program was measured where it cost, and six Sonnet agents surveyed
   [today's alternatives](ground-up-review/technologies.md). The main session checked at its source each fact that
   a card rests on.
5. **The walk.** The main session gave a row to each of the 259 items.
6. **The challenge.** One Sonnet agent argued that each change costs more than it gains, one that each keep is
   habit, and the physics reviewer read each proposal on a numerical method. Their reports are kept unedited.

**Limits.**

- The main session wrote the report, knows the program and checked the report at its ship (BB7). `CLAUDE.md`
  loads at a session's start and names the subpackages, so only the designers were blind. Until the unblinding the
  main session read no source file.
- Where the designers did not judge a row, their marks are read from each design's text.
- Each cost is an estimate at a measured rate, and no measurement of the work it names.

The record of each step is in [How it was made](ground-up-review/method.md). The designs are [A](ground-up-review/design-a.md),
[B](ground-up-review/design-b.md) and [C](ground-up-review/design-c.md).
