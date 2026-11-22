# Current work

Updated 22 November 2026. Navigation;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Version 0.6.0 is released. The project is planned again from there, in six phases. The next phase cleans up the
records and instructions and restructures the library, and changes no number a user sees. The phase after it rebuilds
the workbench on new foundations and adds the tree of results and the guided route. Then come the three tools, each a
phase: the physics composer, the structural mutator and the sketcher. Validation against the published results, with
the paper, is the last phase before version 1.

You ruled that all three tools come before validation, so no published number is reproduced until the last phase,
and a gap found there would reach every tool built before it. The known gaps in the equations are closed in the next
phase for that reason.

The next phase is about 15 packages: 75 sessions, 45 to 90 hours of agent work and 120 times you act. The workbench
phase is about 14 packages: 85 sessions, 85 to 170 hours and 140. The tool phases are estimated when each is planned.

**Your call.** Approve the re-plan after its review, then merge it. *Next:* the review of this plan, then the plan of
the next phase.

## Position

- Phases 1 to 5 **closed**: `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`, `v0.6.0`
  ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **The project is re-planned** (§8.2.49): Phase 6, the cleanup and the library's foundations (`v0.7`); Phase 7, the
  workbench rebuilt (`v0.8`); Phases 8 to 10, the tools (`v0.9` to `v0.11`); Phase 11, validation and release
  (`v0.12`). Their provisional packages: [the input note](sessions/phases-6-to-11.md).
  **Next:** `/np-plan project review`, then `/np-plan phase 6`. host: claude-code.

## Not to be re-decided

- **Process rules** are §8.4. **Cost fixes follow measurement** (M2). **Two lanes at most** (S15). **Qt is removed**
  (S17).
- **A moved edge edits `modularity-layering.yaml` in its commit (VER-61)**; a VER-62 miss is reverted or re-pinned by
  ruling (G10, I4). **An open item is a `REV-nn` row** until resolved (H12).
- **A `Case` is the case document; a `Session` runs it for every caller** (§8.2.23). **The front end is NiceGUI; Mol*
  draws the molecule** (AF4). **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4).
- **The workbench's design rulings stand** (§8.2.31 to §8.2.46; WB-33 to WB-63): a study overrides any model value;
  physics is a third model; layers read a model's declaration, never its name (VER-56); a callback is not an input
  (VER-44); a generated mesh is read only through `deployed_mesh`; text follows the tested program (AM1, AM2); red
  blocks, blue informs, refusals are ASD-STE100 (WB-42); Analysis is COMSOL's tree and Plotly draws every chart and
  map (WB-54 to WB-63); every open item names a package (§8.2.46).
- **QR-10's trial waits for v1.0's release candidate; QR-16's keyboard gaps and five Qt details are carried to
  Phase 7** (§8.2.47; REV-274).
- **The phases are library, workbench, composer, structural mutator, sketcher, validation** (§8.2.49 AY1, AY2). **The
  Windows leg is Phase 6's first package; every later gate asks the three platforms** (AY4). **The speed-up closes
  Phase 6; the equations are brought to §4 there** (AY3, AY6). **The Copilot host is retired at the cleanup** (AY5).
  **Fable 5.2 plans and ships, Opus 5.5 implements** (AY7). **The cleanup ends at a measured reading limit** (AY8).

## Somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents.
- **The 200 ms redraw**'s GPU run (REV-258); **verdicts at each design round** (AJ8).
- **Rulings on a cycle (H6) or drift (I4)**.
- **The reading limit and what leaves the history** (AY8), and **the Copilot host's tag** (AY5), at Phase 6's cleanup;
  **QR-10's observer** (AW2).

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
