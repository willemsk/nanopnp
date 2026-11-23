# Current work

Updated 23 November 2026. Navigation; `SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Phase 6's next package, the ground-up review, is planned.

The review asks how the program would be built if we started over, and takes only the paper's physics as given. It
changes no code and hands you a report on the project's pages: what the program should become, the design it would
choose, and each difference from today's program marked keep, change now, change later, drop or add, with its gain,
risk and cost.

As you ruled at its plan, three designers who have never seen the code or the requirement list design the
program from its purpose and your view, before a reviewer who knows the program goes rule by rule. Fable writes the
report and Opus checks it.

The review: about 10 sessions, 7 to 13 agent hours and 13 times you act. Phase 6 ahead: about 66 sessions, 54 to 107
agent hours and 102 times you act, if the review changes nothing.

**Your call.** Do you approve the review's plan, once its own review has read it? *Recommendation:* approve, so the
review can start. Yours later: three answers at its start, then the rulings on its proposals.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md); §8.2.50), `v0.7`: **WP6.01 to WP6.03
  merged**, `v0.7.0-alpha.3` published, the tag `copilot-host` pushed.
- **The project is rescoped** ([§8.2.51](../../specification/history/51-the-project-rescoped.md)). Phases 7 to 12:
  [the input note](sessions/phases-6-to-11.md).
- **WP6.04, the ground-up review, is planned**
  ([its plan](phase-6/wp6.04-the-ground-up-review.md);
  [§8.2.52](../../specification/history/52-phase-6-amended-the-ground-up-review-planned.md)); WP6.05 follows the
  rulings on it; the rest is provisional.
- **Next:** `/np-plan wp 6.04 review` on Fable 5.2; then `/np-implement wp 6.04` on Fable 5.2 and `/np-ship wp 6.04`
  on Opus 5.5, in a new session. After WP6.04: `/np-plan project`, `/np-plan amend 6`, `/np-plan wp 6.05`.

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
- **WP6.04 is the ground-up review: all open but §4's physics, designed for the whole of §3, a report and no code,
  then the author's rulings at `/np-plan project`** (BA10 to BA13; BB2). **Its guard, its report's place and its two
  models are ruled** (BB3 to BB5). **WP6.05, the axis fix, is firm and follows those rulings** (BA8; BB1). Until then
  BA1 to BA9 and AZ1 to AZ6 hold (BA4).

## Somebody else's

- **The paper's figure data** (D6); E1's ensemble legs; **Read the Docs**; **`$NANOPNP_REFERENCE_DATA` on the nightly
  runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents, at Phase 12's close (BA6).
- **The 200 ms redraw**'s GPU run (REV-258); **verdicts at each design round** (AJ8); rulings on a cycle (H6) or
  drift (I4).
- **The rulings on the ground-up review** (BA13); **the customised PDB2PQR**, by Phase 9's round (BA9); **the PlyAB
  model files**, by Phase 11's (OPN-03); **QR-10's observer** (AW2).

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
