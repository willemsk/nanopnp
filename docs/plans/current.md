# Current work

Updated 23 November 2026. Navigation;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Phase 6's first three packages are merged and tagged, and the rescoping round you asked for is held.

You kept the direction. All three tools stay before validation, the workbench is rebuilt in full, and the program is
first compared with the paper in the last phase. The forces on an analyte become a phase of their own, so validation
is now the twelfth phase and the thirteenth release. Version 1 is defined when validation closes. A session may
restructure the code it works with while every test passes. Fractional protonation joins the mutator's phase.

Two things change Phase 6. Its next package reviews the program from the ground up: how would it be built if we
started over? Everything is open to it but the paper's physics. It changes no code and hands you a report, and you
rule on each proposal. The rest of Phase 6, about ten packages, waits for those rulings, except a small fix for the
pore's axis at a ragged rim.

Phase 6 ahead: about 65 sessions, 53 to 106 hours of agent work and 101 times you act, if the review changes nothing.

**Your call.** Start the review of this round's record, in a new session or after a compaction. Then comes the
amendment that plans the ground-up review and the axis fix. Yours later: the rulings on the review's proposals, your
customised protonation tool, the analyte's model files, and what version 1 is. *Next:* the review of the round's
record.

## Position

- Phases 1 to 5 **closed**, `v0.2.0` to `v0.6.0` ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 in flight** ([the plan](phase-6/phase-6-library-foundations.md); §8.2.50), `v0.7`: **WP6.01 to WP6.03
  merged**, `v0.7.0-alpha.3` published, the tag `copilot-host` pushed.
- **The project is rescoped** ([§8.2.51](../../specification/history/51-the-project-rescoped.md), BA1 to BA13).
  Phases 7 to 12: [the input note](sessions/phases-6-to-11.md).
- **Next:** `/np-plan project review` on Fable 5.2; then `/np-plan amend 6`, which plans WP6.04, the ground-up review,
  and the axis package, and lists the rest as provisional; then `/np-plan wp 6.04`.

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
  restructure the code it works with while the push gate passes** (BA7).
- **WP6.04 is the ground-up review: all open but §4's physics, a report and no code, then the author's rulings at
  `/np-plan project`. Only the axis fix is planned before them** (BA8, BA10 to BA13). Until then BA1 to BA9 and AZ1
  to AZ6 hold (BA4).

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
- **Amendments:** `phase-5/phase-5-record.md`.
- **Workflow:** `.claude/workflow/core.md`, `.claude/skills/np-*/`; §8.4.4, §8.4.5.
- **Workbench:** `docs/design/workbench.md`; `docs/design/reviews/`; §8.2.17 onwards.
- **Code:** `docs/project/architecture-survey.md`.

## Handoff Rules

Planning or finishing a package replaces the position and live dependencies. At most 700 words;
an In brief of at most 250 (no backticks or identifiers) ending in **Your call**. Measurements
stay in their records.
