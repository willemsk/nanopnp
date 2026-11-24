# Current work

Updated 24 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

The ground-up review is written. It waits for its check, and then for your rulings. It changed nothing in the
program.

It finds that a start-over would keep the numerical method: three designers who had never seen the program chose the
same engine, mesh tool, elements and solver. What they would change is the shape around it. For this phase the review
proposes a published page that shows which test proves each term of the model, an estimate of the mesh error beside
a number, one comparison with the paper at the phase's close, fewer sessions that you must start, and a few
corrections of text. Building the physics from registered terms stays where you ruled it, with the composer: two
challengers and the physics reviewer showed that moving it forward would cost more than the draft said.

The proposals for this phase add about three packages to its ten: 13 to 18 sessions, 8 to 21 agent hours and 20 to
28 times you act.

The review may lean towards the program as it is. One challenger says so; each objection not met is shown beside its
row.

**Your call.** Nothing yet: the review is checked first. At the round after it you rule on twelve groups of
proposals. *Recommendation:* read the report's first section before that round; it is one page.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md); §8.2.50), `v0.7`: **WP6.01 to WP6.03
  merged**, `v0.7.0-alpha.3` published, the tag `copilot-host` pushed.
- **The project is rescoped** ([§8.2.51](../../specification/history/51-the-project-rescoped.md)). Phases 7 to 12:
  [the input note](sessions/phases-6-to-11.md).
- **WP6.04, the ground-up review, is implemented and its pull request open**
  ([its plan](phase-6/wp6.04-the-ground-up-review.md)). Its
  proposals are REV-280 and its seven trials REV-281 to REV-287. WP6.05 follows the rulings; the rest is provisional.
- **Next:** `/np-ship wp 6.04` on Opus 5.5 in a new session. After its merge: `/np-plan project`, then
  `/np-plan amend 6` and `/np-plan wp 6.05`.

## Not to be re-decided

- **Process rules** are §8.4: two lanes at most (S15); a moved edge edits
  `modularity-layering.yaml` (VER-61); a VER-62 miss is reverted or re-pinned by ruling (G10); an open item is a
  `REV-nn` row (H12); the reading limit is 8,000 words (AZ18).
- **A `Case` is the case document; a `Session` runs it** (§8.2.23). **The front end is NiceGUI** (AF4). **The schema
  and `nanopnp.PUBLIC` may change until v1.0** (F4). **The workbench's design rulings stand** (§8.2.31 to §8.2.46).
- **Every gate asks the three platforms at a phase's close; a pull request tests Linux** (AY4; AZ8). **Fable 5.2
  plans; each plan proposes its two models** (AZ20, AZ21).
- **The phases are library, workbench, composer, mutator, sketcher, analyte forces, validation** (BA1, BA2, BA5);
  **validation is Phase 12 and `v0.13`, with no earlier comparison against the paper** (BA3). **A session may
  restructure the code it works with while the push gate passes, its nightly walks not asked** (BA7, BA14).
- **The ground-up review's verdicts are proposals; the author rules them at `/np-plan project`** (BA11, BA13).
  **WP6.05, the axis fix, is firm and follows those rulings** (BA8; BB1). Until then BA1 to BA9 and AZ1 to AZ6 hold
  (BA4).

## Somebody else's

- **The paper's figure data** (D6); E1's ensemble legs; **Read the Docs**; **`$NANOPNP_REFERENCE_DATA` on the nightly
  runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents, at Phase 12's close (BA6).
- **The 200 ms redraw**'s GPU run (REV-258); **verdicts at each design round** (AJ8); rulings on a cycle (H6) or
  drift (I4).
- **The rulings on the ground-up review** (BA13; REV-280); **the customised PDB2PQR**, by Phase 9's round (BA9);
  **the PlyAB model files**, by Phase 11's (OPN-03); **QR-10's observer** (AW2).

## On demand

- **Specification:** `SPECIFICATION.md` and the file it maps; `docs/project/decisions.md`.
- **Amendments:** `phase-6/phase-6-record.md`.
- **Workflow:** `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5.
- **Workbench:** `docs/design/workbench.md`; `docs/design/reviews/`; §8.2.17 onwards.
- **Code:** `docs/project/architecture-survey.md`.

## Handoff Rules

Planning or finishing a package replaces the position and live dependencies. At most 700 words;
an In brief of at most 250 (no backticks or identifiers) ending in **Your call**. Measurements
stay in their records.
