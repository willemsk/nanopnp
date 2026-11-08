# Task walks 7 to 12: a cold session start, and the author's five hard-to-reach things

Walker: a Sonnet 5.5 sub-agent at medium effort, holding only each walk's path. Return saved verbatim.

All six walks below. Each starts afresh from its starting file. Words are `wc -w`. Tokens are bytes ÷ 4. No walk reached twelve files. Tool output that the harness appended (an MCP server list, a "while auto mode is active" note) carried no pointer and was not used in any walk.

## Walk 7: cold session start (fix a failing Tier 2 ionic-current test)

| # | File | Words | Pointer | What it gave |
|---|---|---|---|---|
| 1 | CLAUDE.md | 2092 | start | "Before doing anything": read knowledge/index.md, SPECIFICATION.md (the map), and the rules by path. Commands, gate, Testing section. |
| 2 | knowledge/index.md | 192 | CLAUDE.md "Read knowledge/index.md" | Ten KB directories. Nothing was followed from it, because the task is a test fix. |
| 3 | SPECIFICATION.md | 1017 | CLAUDE.md "entry point and the map" | Task table: "Write or judge a test" points to §7.1, the VER row and Appendix A. §7.3 maps to 03-tier-2.md. |
| 4 | specification/07-verification/03-tier-2.md | 2990 | SPEC map §7.3 | The Tier 2 rows VER-12 to VER-62. Current-related rows: VER-16 (1D PNP limiting current, no numeric tolerance), VER-17 (Maxwell–Hall conductance, 2 %), VER-62 (`current_A` within 10⁻⁸ relative of the golden `tests/tier2/data/number_stability.json`). |
| 5 | .claude/rules/physics-numerics.md | 380 | CLAUDE.md "Rules by path … load when you read or edit a file they cover" | Never compute ionic current from a cross-section integral of the CG flux. Use the indicator form or the variational reaction flux and cross-check both (FR-23, QR-04, `knowledge/06-numerics-fem/07-…flux-trap.md`). It also covers Newton convergence and recording the stabilisation mode. |
| 6 | specification/07-verification/01-strategy.md | 511 | SPEC task table "§7.1" | Test scope: no tolerance may be slackened. Tier 1 and 2 never read the Tier 3 archive. |
| 7 | specification/a-traceability-matrix.md | 2675 | SPEC "Appendix A" | FR-23 maps to VER-11, VER-38 and VAL-16. QR-01 maps to VER-12 to VER-22. QR-04 maps to VER-11, VER-40, VER-42. It names no test file for VER-16, VER-17 or VER-62. |
| 8 | `clause.py --no-history FR-23` | 77 (printed, including a uv warning) | rules file names FR-23 | FR-23: extract the ionic current by two independent routes whose agreement is checked automatically. |

Stalls:
- Nothing I read names the test file of any current-related Tier 2 row. The matrix gives test paths only for VAL, FR-30 and later rows. Only VER-62's data file is named. Finding the file would need a search, so I stopped.
- "The ionic current Tier 2 benchmark" is ambiguous between VER-16, VER-17 and VER-62. The task statement gives nothing to choose among them.
- Reading the `knowledge/index.md` entry was required by CLAUDE.md, but nothing in it was relevant to this task. It cost 192 words with no gain.
- The rules file points to a KB file (`07-quantities-of-interest-and-the-flux-trap.md`) for the flux trap. I did not follow it, because the walk's question was about which files to open.

Answer: partly answered. The order of opening, with what each gives, is in the table. The governing clauses are FR-23 and QR-04, plus whichever of VER-16, VER-17 or VER-62 the failing test carries. The test file under `tests/tier2/` is not named by any pointer, so it is not determined.

Totals: 8 files, 9,934 words, about 17,161 tokens (68,645 bytes ÷ 4).

## Walk 8: which ruling set the word cap on a WP plan

| # | File | Words | Pointer | What it gave |
|---|---|---|---|---|
| 1 | SPECIFICATION.md | 1017 | start | "Read specification/history/ on demand … when the reason behind a rule is wanted"; §8.4 and §8.2 map entries. |
| 2 | specification/history/index.md | 4025 | SPEC map and "Read history on demand" | The "Where each ruling holds now" list: Q1 → §8.4.4, R11 → §8.4.4 and §8.4.5, X5 "cap superseded by Y11", Y11 → §8.4.4. The §8.2.33 description mentions "word caps allowing 10% over". |
| 3 | specification/08-implementation-plan/04-development-process.md | 2069 | history index (Q1, R11 → §8.4.4); SPEC map | The current cap in §8.4.4 (below). It cites §8.2.15 Q1; §8.2.16 R11; §8.2.33 AI15. WP57's plan is exempt (Y11). |
| 4 | `clause.py Q1` (with history) | 800 | §8.4.4 cites Q1 | I ran it but did not read its output separately. The Q1 row also printed inside the R11 output. |
| 5 | `clause.py R11` (with history) | 630 | §8.4.4 cites R11 | R11 row, Q1 row, AI15 row, each with its reason column. |

Stalls:
- The history index is 4025 words, mostly a long "holds now" list, to learn which letters to look up. Its text does not say which of Q1, R11, X5 or AI15 answers a "word cap" question. I inferred it from §8.4.4.
- I ran `clause.py Q1` and R11 in one call. Q1's output turned out to be redundant, since R11's output already printed the Q1 row. That is 800 words counted but not used.
- L7's original 1,500-word cap is only named inside Q1's "supersedes" column. Its own record was not opened.

Answer: the ruling that set the cap is Q1 (§8.2.15, 22 Oct 2026, at WP51). It set a work-package plan at 2,500 words outside Outcome annotations, 1,500 outside Grounding, and six decisions, superseding L7's 1,500-word cap. It has been amended twice:
- R11 (§8.2.16, 22 Oct 2026, at WP52) raised the cap to 3,500 words. At most 1,500 of them may lie outside `### Grounding` and `### Implementation details`. The details section is at most 1,000 words, and the plan is written for a smaller model.
- AI15 (§8.2.33, 5 Nov 2026, at WP5.08) made "about six decisions" a guideline and let every cap run 10 % over before the plan is trimmed or split.

The cap today (§8.4.4) is:
- 3,500 words outside Outcome annotations;
- 1,500 of them outside Grounding and Implementation details;
- 1,000 for the details;
- an In brief of 250 words;
- each count may run 10 % over;
- WP57's plan is exempt (Y11).

Why:
- Q1: a plan grounded in the code lets the implementer re-decide nothing, and a plan that guessed is caught before work starts, not by a failing gate. The added budget buys facts only.
- R11: the author wanted "the ability to write the plan for a smaller model (and add up to 1000 more words on implementation details)" and an executor named per item.
- AI15: the author feared a hard limit would force the plan to be less complete and wanted to avoid needless rewording for small excesses.

Totals: 5 files, 8,541 words, about 13,698 tokens (54,794 bytes ÷ 4).

## Walk 9: state of the work

| # | File | Words | Pointer | What it gave |
|---|---|---|---|---|
| 1 | docs/plans/current.md | 699 | start | In brief, Position, standing rulings, "On demand" list. |

Stalls: none that blocked the answer. The file does not say whether the CODE_REVIEW_036 refactors or WP5.15 comes first after WP5.09. Only "after WP5.09, through `/np-plan amend 5`" is stated. I did not open `phase-5-workbench.md`, because the question was answered from this file.

Answer, as of 8 Nov 2026:
- Merged: Phases 1 to 4, closed and released as v0.2.0, v0.3.0, v0.4.0 and v0.5.0. In Phase 5 (v0.6.0, in progress), WP5.01 to WP5.08 are merged (`v0.6.0-alpha.8`): the library steps and the window frame.
- Being built now: WP5.09, the physics model, is delivered on branch `claude/keen-turing-g32u0j`, planned, reviewed (CODE_REVIEW_035) and not yet merged. The next command is `/np-ship wp 5.09`. The file's In brief says it "awaits review".
- Next after it: the six refactors from CODE_REVIEW_036 (REV-217 to REV-221 and REV-170) land after WP5.09 through `/np-plan amend 5`, with corrections C0 to C6.1. Then come the remaining amended packages: WP5.15 the frame, WP5.16 to WP5.20 the suites, WP5.21 the route and Qt's removal, WP5.22 the close. The file says three to four weeks remain.

Totals: 1 file, 699 words, about 1,209 tokens (4,837 bytes ÷ 4).

## Walk 10: a Copilot session wants to push a branch

| # | File | Words | Pointer | What it gave |
|---|---|---|---|---|
| 1 | CLAUDE.md | 2092 | start | "The gate before a push" section. "Other hosts" says the workflow runs on the Copilot app as a WSL host (§8.4.4; §8.2.25) and that another host reads its map through `.claude/workflow/hosts.md`. |
| 2 | .claude/workflow/hosts.md | 91 | CLAUDE.md "Another host reads its map through …" | Index only: the Copilot map is `hosts/copilot.md`. |
| 3 | .claude/workflow/hosts/copilot.md | 1223 | hosts.md link | The Copilot-specific push rules (below). |

Stalls:
- CLAUDE.md cites §8.4.4 and §8.2.25 for the hosts rule. I did not resolve them, because that needs SPECIFICATION.md's map. The statement of the rule in the specification is therefore not verified in this walk.
- "Hooks fire only on a WSL host. On a `\\wsl.localhost\` folder, run both gates of CLAUDE.md's *Commands* by hand." The pointer says where to look but not which situation the session is in.
- "Until REV-166 closes, run the gate by hand before each commit and push." REV-166 is not opened. The state of the open probes is unknown.

Answer: the rule is the push gate, written in CLAUDE.md under "The gate before a push" and applied to Copilot by `.claude/workflow/hosts/copilot.md` (Safety hooks and Session operations).
- Before the push, `.claude/hooks/gate.sh run` must pass on the tree being pushed. Start it asynchronously with output to a log ending in `echo "exit $?"`. Wait for the log's completion notice, or run the `until grep` loop with `initial_wait` up to 600 s. Never use `nohup`, `setsid` or `&`.
- Push only when the log ends in `exit 0`.
- The gate refuses with an exit-0 structured denial. Once the clone sets `git config core.hooksPath .githooks`, git's `pre-push` also refuses a tree with no `push` stamp.
- Never use the app's Commit or Push buttons, and never type a commit or push into a running shell. Push through the shell, with the gate run by hand while REV-166 is open.
- On Copilot the push is followed by a checkpoint in the PR's Verification section and a stop at CI (§8.2.25 AA3). The app's agent merge stays off.

Totals: 3 files, 3,406 words, about 5,456 tokens (21,824 bytes ÷ 4).

## Walk 11: the Tier 2 tolerance on the ionic current

| # | File | Words | Pointer | What it gave |
|---|---|---|---|---|
| 1 | SPECIFICATION.md | 1017 | start | "Touch the numerics" and "Write or judge a test" point to §7.3 (03-tier-2.md). `VER-nn` maps to the tier files. |
| 2 | specification/07-verification/03-tier-2.md | 2990 | SPEC map §7.3 | VER-16: no numeric tolerance on the current. VER-17: conductance "better than 2 %". VER-62: `current_A` within 10⁻⁸ relative on a golden mesh, up to a mesh-moved tolerance of 10 × the spread, ≥ 10⁻⁸ and ≤ 10⁻³. The row cites §8.2.7 G10. |
| 3 | `clause.py --no-history QR-01` | 58 | none in this walk's text (stall) | QR-01: "Maxwell–Hall access conductance to better than 2 %". |
| 4 | `clause.py VER-62` (with history) | 3346 | the VER-62 row names G10 (§8.2.7) | The VER-62 row, four NOTEs from other files, and the rulings G10, I4, X4, AG8, among others. G10 gives the derivation. |

Stalls:
- QR-01 had no pointer from anything read in this walk. I opened it from memory of another walk's matrix. That is a stall.
- The question's "ionic current" has no single Tier 2 tolerance. Three candidates exist: VER-16 (none), VER-17 (2 %, conductance, not current) and VER-62 (10⁻⁸, `current_A`).
- The VER-62 output is 3,346 words, mostly unrelated rulings. I used only the G10 and I4 rows.
- G10 says 10⁻⁸ is "a figure the package argues from a measured rerun on each CI platform". The measurement itself is not in the text I read.

Answer: the only tolerance stated directly on the ionic current (`current_A`) is VER-62's:
- 10⁻⁸ relative on a mesh the golden holds.
- On an unseen mesh, 10 × the largest spread between recorded meshes, at least 10⁻⁸ and never above 10⁻³, except in the reference environment `linux-x86_64/X86_V3`, where an unseen mesh always fails.
- The 10⁻⁸ comes from §8.2.7 G10 (5 Oct 2026). G10 records a golden on `v0.4.0`'s tree. It sets 10⁻⁸ as "two orders inside VER-35's 10⁻⁶ nonlinear tolerance", on the grounds that predicted drift is round-off, and as a figure argued from a measured rerun on each CI platform.
- The mesh-moved ceiling of 10⁻³ is also from G10.
- I4 gives a pre-ruled path to re-pin the golden for WP41's accuracy fixes, within a bound the plan argues.
- The nearest other Tier 2 figure is VER-17's 2 % on access conductance (QR-01). It is for conductance, not current, and its row gives no derivation beyond Hall's closed form in the NOTE.

Totals: 4 files, 7,411 words, about 12,628 tokens (50,512 bytes ÷ 4).

## Walk 12: owner and importers of the wall-distance field

| # | File | Words | Pointer | What it gave |
|---|---|---|---|---|
| 1 | SPECIFICATION.md | 1017 | start | Map: §5.1 → 01-architectural-overview.md; §5.4 → 04-component-design.md. |
| 2 | specification/05-software-design/01-architectural-overview.md | 436 | SPEC map §5.1 | The `physics/` row: "Weak forms: Poisson, Nernst–Planck, Navier–Stokes; the wall-distance field". It lists no importer relation. |
| 3 | specification/05-software-design/04-component-design.md | 749 | SPEC map §5.4; §5.1 names MOD-04 | `physics/` expresses the weak forms and the PHY-02 distance field is read by layers through a model's declaration. The relation of subpackages is `docs/project/modularity-layering.yaml` (VER-61, VER-65). |
| 4 | docs/project/modularity-layering.yaml | 1849 | §5.4.1 NOTE (backtick path) | The measured subpackage import edges (below). |

Stalls:
- The spec files give the owner but no importers. The importers came from a YAML file that §5.4 names in a NOTE about the backend. The pointer did not say it holds the import relation.
- The YAML edges are per subpackage, not per symbol. They show who imports `physics`, not who imports the wall-distance field specifically. The identifier to file entry for PHY-02 (04-physics.md) was not opened.
- §8.2.35 AK1 ("the physics model owns the wall-distance field the corrections read") is in the history index's description. I did not open it, so I cannot say whether it changes the owner from `physics/`.

Answer: `physics/` owns the wall-distance field (§5.1). Subpackages that import `physics/` at module scope (static edges): `io` (MOD-04, annotation-only upward edge), `pipeline`, `post`, `solve`, `validation` and the top-level `nanopnp` package. By string reference only: `cli` and `core`. `gui` and `api` have no direct `physics` edge. These are import edges of the subpackage as a whole. The yaml does not say which of them touch the field itself.

Totals: 4 files, 4,051 words, about 7,953 tokens (31,813 bytes ÷ 4).
