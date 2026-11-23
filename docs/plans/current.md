# Current work

Updated 23 November 2026. Navigation;
`SPECIFICATION.md` governs; an unmerged branch is not shipped.

## In brief

Phase 6's first two packages are merged and tagged.

The third package, the cleanup's second half, is implemented and waits for its review. The instructions a session
reads first are cut by almost half, from about 5,800 words to about 3,200. The setup for the Copilot app is removed,
and a tag will keep it findable. Each plan now proposes which model implements and which reviews, and you decide. The
project-planning command can hold the rescoping round that follows. A new session that started on the cut
instructions read 7,186 words before its first change, under the limit of 8,000 you set, so the limit now binds every
implementing session.

**Your call.** Start the review on Opus 5.5, in a new session or after a compaction. After the merge, push the tag
named copilot-host as the review's report prints it. Who owns the code waits for the rescoping round. *Next:* the
review of the third package.

## Position

- Phases 1 to 5 **closed**: `v0.2.0`, `v0.3.0`, `v0.4.0`, `v0.5.0`, `v0.6.0`
  ([Phase 5's report](phase-5/phase-5-workbench.md#end-of-phase-report)).
- **Phase 6 is planned** ([the plan](phase-6/phase-6-library-foundations.md); §8.2.50), `v0.7`: WP6.01 to WP6.03,
  then the rescoping round at `/np-plan project`; WP6.04 to WP6.18 provisional until it rules. Phases 7 to 11:
  [the input note](sessions/phases-6-to-11.md).
  **WP6.01 and WP6.02 merged**, `v0.7.0-alpha.2` published.
  **WP6.03 implemented**, PR #209 ([the plan](phase-6/wp6.03-the-cleanup-instructions-copilot-host.md); AZ18 to AZ21).
  **Next:** `/np-ship wp 6.03` on Opus 5.5.

## Not to be re-decided

- **Process rules** are §8.4. **Cost fixes follow measurement** (M2). **Two lanes at most** (S15). **Qt is removed**
  (S17).
- **A moved edge edits `modularity-layering.yaml` in its commit (VER-61)**; a VER-62 miss is reverted or re-pinned by
  ruling (G10, I4). **An open item is a `REV-nn` row** until resolved (H12).
- **A `Case` is the case document; a `Session` runs it for every caller** (§8.2.23). **The front end is NiceGUI; Mol*
  draws the molecule** (AF4). **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4).
- **The workbench's design rulings stand** (§8.2.31 to §8.2.46; WB-33 to WB-63; VER-44, VER-56); every open item
  names a package (§8.2.46).
- **QR-10's trial waits for v1.0's release candidate; QR-16's keyboard gaps and five Qt details go to Phase 7** (§8.2.47; REV-274).
- **The Windows leg is first; every later gate asks the three platforms** (§8.2.49 AY4); **a pull request and a
  package's ship test Linux alone, the close the three** (§8.2.50 AZ8). **The Copilot host is
  retired, findable by the tag `copilot-host`** (AY5; AZ19). **Fable 5.2 plans; each plan proposes its implementing
  and shipping model, and the author rules them** (AY7; AZ20, AZ21).
- **The reading limit counts project text in words; 8,000 for an `/np-implement` session's
  first window; a phase plan 2,500** (§8.2.50 AZ9 to AZ18); **nothing leaves the rulings' history; a closed item is archived**.
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
- **Who owns the code** (audit F3) and **what to keep, cut and add**, at the rescoping round (AZ7); **the tag
  `copilot-host`**, pushed after WP6.03's merge; **QR-10's observer** (AW2).

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
