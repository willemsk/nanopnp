# Current work

Updated 22 November 2026. Navigation;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Version 0.6.0 is released, and the next phase is planned. Three packages are fixed: the Windows test run is repaired,
then the records and instructions are cut down to a measured reading limit, and the second host is retired with them.

After those three comes the open-minded rescoping you asked for: one round with every requirement, tool and phase on
the table. Fifteen more packages are drafted and wait for it. As drafted they restructure the library without moving
a stored number, close the known gaps in the equations, add field exports and make the solve faster.

The three packages are about 15 sessions, 9 to 18 hours of agent work and 24 times you act; the fifteen drafted ones,
if confirmed, 75 sessions, 45 to 90 hours and 120.

**Your call.** The plan is reviewed and waits for your approval and merge. *Next:* the plan of the Windows package.

## Position

- Phases 1 to 5 **closed**: `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`, `v0.6.0`
  ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 is planned** ([the plan](phase-6/phase-6-library-foundations.md); §8.2.50), `v0.7`: WP6.01 to WP6.03,
  then the rescoping round at `/np-plan project`; WP6.04 to WP6.18 provisional until it rules. Phases 7 to 11:
  [the input note](sessions/phases-6-to-11.md).
  **Next:** the author approves and merges the plan; then `/np-plan wp 6.01`. host: claude-code.

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
- **The Windows leg is first; every later gate asks the three platforms** (§8.2.49 AY4). **The Copilot host is
  retired at the cleanup** (AY5), **which ends at a measured reading limit** (AY8). **Fable 5.2 plans and ships,
  Opus 5.5 implements** (AY7).
- **An open-minded rescoping follows WP6.03; no package from WP6.04 is planned before it** (§8.2.50 AZ7). Until it
  rules: the phases are library, workbench, composer, mutator, sketcher, validation (AY1, AY2); the speed-up closes
  Phase 6, with no fixed target (AY3; AZ6); the equations are brought to §4 there (AY6); §5.4.1's interface is Phase 8's
  round's (AZ1); a field is read by its cell's own basis (AZ2); a v0.6 run is refused, never converted (AZ5).

## Somebody else's

- **The paper's figure data** for VAL-16 and VAL-17 (D6); E1's ensemble legs; **Read the Docs**;
  **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, v1.0's contents.
- **The 200 ms redraw**'s GPU run (REV-258); **verdicts at each design round** (AJ8).
- **Rulings on a cycle (H6) or drift (I4)**.
- **The reading limit and what leaves the history** (AY8), at WP6.02's plan; **the Copilot host's tag** (AY5), at
  WP6.03; **what to keep, cut and add**, at the rescoping round (AZ7); **QR-10's observer** (AW2).

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
