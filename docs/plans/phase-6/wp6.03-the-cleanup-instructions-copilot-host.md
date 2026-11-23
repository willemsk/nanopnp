# WP6.03 — The cleanup: the instructions cut, the Copilot host retired

**Status: delivered, 23 November 2026.** Written 23 November 2026, grounded in the code at `939009b`. Inherits §8.2.49 AY5,
AY7 and AY8, §8.2.50 AZ7, AZ9 and AZ13 to AZ17, the rulings of this plan (AZ18 to AZ21), WP6.02's
[audit](../sessions/instructions-audit.md) and [baseline](../sessions/reading-baseline.md), REV-166 to REV-168,
REV-278 and the test scope (§8.2.13 N1, N3). Its last commit on `main` takes `v0.7.0-alpha.3` (§8.4.1).

**Delivered.** What an `/np-implement` session reads first holds 3,238 words, from 5,789: `CLAUDE.md` 1,497, the
core 899, `np-implement/wp.md` 739; the finishing rules are in `.claude/workflow/finish.md` and
`np-implement/finish.md`, read when they apply. A new session on the cut read 7,186 words before its first edit,
under the 8,000 of AZ18, which now stands in §8.4.4 without a start date
([the Outcome](#implementation-details)). The Copilot host and `.claude/scripts/audit/` are removed and the
workflow runs on Claude Code alone (AY5); REV-166 to REV-168 are `declined`. A work-package plan proposes its
implementing and shipping model and the author rules them (AZ20, AZ21). `/np-plan project` holds a rescoping round
(AZ7; REV-278 `fixed`). REV-272's section holds the word counts. Live for later packages: the limit binds every
`/np-implement` session's first window; the measuring session starts on the package's branch; the tag
`copilot-host` waits for the author's push after the merge (AZ19).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.03 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** The instructions every session reads first are cut by almost half, from about 5,800 words to
about 3,200. Nothing a session needs is dropped. A rule stated twice is kept once, and the rules for finishing a
package are read when a session finishes, not when it starts. The setup for the second assistant app, Copilot, is
removed from about twenty files and three scripts, and a tag keeps it findable. Each plan now proposes which
model implements and which one reviews, you decide, and the plan is written for your choice. The planning command
for the whole project learns to hold the rescoping round that comes next.

**Cost.** About five sessions, two to four hours of agent work and eleven times you act, among them today's five
answers, a fresh session for the measurement and the tag's push. A user of the program sees no change.

**What could go wrong.** A rule could be lost in the cut: each removed passage is listed with the place that still
states it, and the review reads that list. A fresh session could still read more than the limit: the package then
cuts again and measures again, and the number stays. A script could still expect the removed setup: the three
scripts are run once after the change.

**Your call.** Settled today: the limit is 8,000 words with the plan read whole; the tag is named copilot-host; each
plan proposes its two models; here Fable 5.2 implements and Opus 5.5 reviews. Still yours: start one fresh session
when asked, and push the tag after the merge. *Recommendation:* run both as the session prints them.

## Execution brief

Scope: the Phase 6 plan's WP6.03 entry; AY5; AY8's done-criterion; the audit's hunks; REV-278; AZ18 to AZ21. It
depends on WP6.02's merge (`939009b`). It claims no new identifier and writes no test: instructions, hooks and
workflow scripts are outside the test scope (N1), and the kept tests of VER-61 and VER-79 stay green. The rulings'
clauses, §8.4.4 and §8.4.5, changed in this plan's commit; each item restates the clause it touches in its own commit.
**Implementing session: Fable 5.2, high effort; ship: Opus 5.5, high effort** (ruled by the author, AZ20, AZ21). The
two differ, so the ship never chains: the pause's prompt names Opus 5.5.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The limit** | The first window of an `/np-implement` session reads at most 8,000 words of project text before its first edit, and reads its plan whole. A plan's caps stay | Ruled by the author, §8.2.50 AZ18 |
| **D2 The start path** | What that window must read holds at most: `CLAUDE.md` 1,500 words, `.claude/workflow/core.md` 900, `np-implement/wp.md` 750 (`wc -w`). A removed passage is either a duplicate, deleted with the place that keeps it named, or a finishing rule, moved to a file read when it applies: `.claude/workflow/finish.md` and `np-implement/finish.md`. `/np-implement` and `/np-ship` open `current.md` when they update it, and `/np-implement` reads a clause when the item that cites it starts. Every heading that another file cites keeps its name. The three numbers are this plan's targets, not rules of §8.4 | AY8 chose a measured limit over budgets per file; decided by the plan |
| **D3 The host removed** | Every file, hook branch and rule that serves the Copilot app goes, and with them `.agents/`, the Antigravity adapter that only `hosts.md` describes. `AGENTS.md`, `.githooks/pre-push`, the gate's refusal object and the payload shapes `gate.sh` and `format.sh` read stay as they are. REV-166 to REV-168 close `declined`; AA1 to AA4, AA7 and AA8 are superseded by AY5 | AY5 ("the workflow runs on Claude Code alone"); the list decided by the plan |
| **D4 The tag** | The git tag `copilot-host` marks the parent, on `main`, of the commit that deletes `.claude/workflow/hosts.md`. That commit's body holds the line `Tag: copilot-host`. The ship's report after the merge prints the author's two commands | Ruled by the author, §8.2.50 AZ19 |
| **D5 The models** | A work-package plan proposes its implementing and its shipping model, `/np-plan wp` puts both to the author, and the plan is written for the models ruled. Opus 5.5 implements and Fable 5.2 ships by default. `NANOPNP_AUTO_SHIP` chains only where the plan names one model for both | Ruled by the author, §8.2.50 AZ20, AZ21 |
| **D6 The audit's rest** | Hunk 3 (F4) is applied; hunks 1 and 2 (F1) are replaced by D5. The glob of F8 goes. `.claude/scripts/audit/` is deleted, found again at D4's tag; §8.4.5 names `.claude/scripts/gui/` as `/np-gui`'s scripts. F3 stays the rescoping round's | The audit; WP6.02's outdated list; decided by the plan |
| **D7 The rescoping round** | `np-plan/project.md` says what a round reads and may open when a ruling opens the project's scope, and names `/np-plan amend <n>` for the phase in flight. REV-278 is `fixed` | AZ7; REV-278's recommendation; decided by the plan |
| **D8 The measurement** | After the cut is pushed, the author starts a new session on the package's branch, so that it loads the cut `CLAUDE.md` and skills, and its first window is measured with `usage.py --reading`. At most 8,000 words passes. A miss is recorded, the largest standing file is cut again, and another new session measures. A session that starts on another tree measures that tree: it is recorded and is no miss. The number is not ruled again | AY8; AZ13 and AZ18 ("re-ruled only before a measurement"); decided by the plan; the branch added at item 8 |

### Grounding

**D1, D2**

- A first window reads today, in words (`wc -w`): `CLAUDE.md` 2,342; `np-implement/SKILL.md` 103; `core.md` 1,364;
  `np-implement/wp.md` 1,276; `current.md` 700; a plan of up to 3,850; `knowledge/index.md` 302; `clause.py`'s
  output, a median of 1,192 in the baseline. The two path-scoped rules arrive as attachments and are not counted.
- At D2's targets the window reads 3,253 words of instructions, the index's 302 and this plan's 3,350: about 1,100
  are left for clauses, under the baseline's median. A plan at its cap leaves 595. `clause.py AZ18` alone prints 487.
  `np-implement/wp.md:Load the brief` step 3 reads every cited clause before the first item.
- Four places have an implementing session read `current.md`: `core.md:Reading order` step 2; the last bullet of
  step 2 of the core's *The package's PR and branch* ("Read `current.md` and the plan from this tree");
  `CLAUDE.md`'s *Implementation workflow* ("To plan or resume, read"); and `session-start.sh`'s summary line.
  `np-implement/wp.md:Load the brief` names the file nowhere itself.
- `CLAUDE.md`'s *Commands* states the push gate's selection, its `NANOPNP_REQUIRE_*` variables and the prose-only
  rule. §7.6 (`specification/07-verification/06-continuous-integration.md`) and `CONTRIBUTING.md`'s *The gate*
  state the selection, and between them `NANOPNP_REQUIRE_GMSH` and `NANOPNP_REQUIRE_BROWSER`. The prose-only rule
  is stated by `gate.sh` (its header and the comment above `docs_only`) and `.github/scripts/prose-only.sh`, and
  `NANOPNP_REQUIRE_APBS` by `gate.sh` alone (corrected at item 5).
- `CLAUDE.md`'s *Implementation workflow* holds the command table, the two switches and the list of eight scripts;
  §8.4.4 and §8.4.5 state all three.
- Headings cited from other files: `CLAUDE.md`'s *Setup*, *Commands*, *Testing*, *Implementation workflow* (also by
  `session-start.sh`'s summary), *Models*, *Open items* and *Durable learnings*; the core's *The package's PR and
  branch*, *Two lanes*, *Models and executors*, *Records*, *Gate and push*, *PR contract* and *Report and stop*;
  `np-implement/wp.md`'s *Finishing* and *How the work lands*.
- The core's *PR contract* is cited by `np-implement/wp.md`, `np-plan/wp.md`, `np-plan/review.md` and
  `np-ship/wp.md`; *Report and stop* by `CLAUDE.md`; `np-implement/wp.md`'s *Finishing* by `np-ship/wp.md`.
- The steward's *What CI runs* cites `CLAUDE.md`'s *Commands* for the per-push selection, which leaves that section.
- No test and no CI step reads `CLAUDE.md` or a file under `.claude/skills/` or `.claude/workflow/`.

**D3, D4**

- Claude Code's hooks are wired in `.claude/settings.json` straight to `.claude/hooks/*.sh`. `.agents/hooks/adapter.sh`
  is reached only from `.agents/hooks.json` (Antigravity) and `.github/hooks/nanopnp.json` (Copilot).
- `session-start.sh` opens with a block under `COPILOT_CLI` that collects the summary into one JSON object.
  `checkpoint.sh:switch_on` returns 1 under `COPILOT_CLI`. `gate.sh:refuse` prints one object with the deny
  top-level and as `hookSpecificOutput`; only its header comment names Copilot.
- Two payload shapes came with the host and no file says so: `gate.sh` reads a `tool_input` that is a string, and
  `format.sh` a `path` key and a raw `apply_patch` string. Claude Code sends neither; both are harmless.
- `.githooks/pre-push` calls `gate.sh check-push` and serves any push no agent hook sees; its comment names the
  Copilot app.
- *Host coordination*'s third bullet also holds a rule that is not the host's: rebase on `origin/<head>` before
  each push. No other section states it.
- The host is named in `core.md` (*Reading order* step 1, *Host coordination*, *Gate and push* step 4), `CLAUDE.md`
  (*Commands*, *Other hosts*), `np-plan/review.md` step 2, `np-implement/wp.md` (the task list), `np-ship/wp.md`
  §7 step 3, `justfile`'s comment on the commit gate and `usage.py`'s module docstring.
- §8.4.2's second bullet says "on both hosts"; §8.4.4 has one bullet on the two hosts; §8.4.5 has one on the tiers
  and the sentence "A host without a Claude Code transcript records".
- `holds-now.yaml`: AA1, AA3 and AA4 are `§8.4.4`; AA2 and AA8 name `hosts.md`; AA7 is `§8.4.5`; AA5 and AB1 are
  §8.4.2 and stay. Record 25 holds the AA rows.
- Links to `docs/plans/sessions/copilot-host.md`: four in `docs/project/review-items.md` (REV-166 to REV-168), one in
  `CHANGELOG.md`, one line of `docs/plans/index.md`, which `index_records.py` writes. `links.py` fails on a broken
  relative link.
- `release.yml` starts on tags `v*` alone. A cloud session cannot push a tag (§8.4.1).

**D5**

- The models are stated in `CLAUDE.md` (**Models**), `core.md:Models and executors`, `np-plan/wp.md` (*Grounding the
  plan*, the template's `## Execution brief` row, *Work items*) and the pause prompts of `np-plan/SKILL.md` and
  `np-implement/wp.md`.
- `checkpoint.sh save ship <plan> <n>` prints `on` when `NANOPNP_AUTO_SHIP=1` and `off` otherwise, and reads no
  plan. The session, which has read the plan, decides whether to call it.
- A skill's `model` field holds for one turn and the session's model returns at the next prompt (Claude Code's
  skills documentation, read 23 November 2026). No hook or skill changes a session's model.

**D6, D7**

- `.claude/scripts/audit/` holds ten files, eight of code review 039's audit and two spent migrations; nothing under
  `.claude/`, `CLAUDE.md` or `justfile` runs them. `knowledge/07-software-stack/25-complexity-and-import-contract-tools.md`
  names `audit/survey.sh` as a resource. `.claude/scripts/gui/` holds six files that `np-gui`'s level files run.
- `.claude/rules/python.md`'s front matter lists `.github/scripts/**/*.py`; that folder holds `prose-only.sh` alone.
- `np-plan/project.md` plans "the phases after the phase in flight", reads §3's Release column alone and "decides
  only what spans phases".

**D8**

- `usage.py --reading` prints one line per window of the session, marked `first window` or `later window`, with the
  words of project text by part and the ten largest files. It reads `$CLAUDE_CODE_SESSION_ID`'s transcript.
- The count ends at the first `Edit`, `Write` or `NotebookEdit` (AZ17). A resumed session's window is a later one.
- A new cloud session checks out a branch made from `main`. Until the package merges, the `CLAUDE.md` it loads
  and the skill files it is sent to are `main`'s, the uncut ones, unless the author starts it on the package's
  branch. `usage.py --reading` counts the `CLAUDE.md` of the tree it runs in, not the one the session loaded
  (found at item 8).

### Implementation details

**Item 1 (D3, D4).** The commit's body holds `Tag: copilot-host`.

1. Delete `.claude/workflow/hosts.md`, `.claude/workflow/hosts/`, `.github/copilot-instructions.md`,
   `.github/hooks/`, `.agents/`, `docs/plans/sessions/copilot-host.md` and, for D6, `.claude/scripts/audit/`, two
   of whose files name the host. The knowledge note's resource line names the tag, with a line in
   `knowledge/log.md`.
2. Hooks: remove `session-start.sh`'s `COPILOT_CLI` block and `switch_on`'s guard, each with its comment; reword
   `gate.sh`'s header and `.githooks/pre-push`'s comment. Change no logic of `gate.sh` or `format.sh`.
3. Remove the host from each file Grounding D3 lists; `np-ship/wp.md` keeps its `gh` command, "where `gh` is
   installed". In `core.md` *Host coordination* goes; its rule to rebase on
   `origin/<head>` before each push moves into *Gate and push*, without "the other host".
4. §8.4.2: drop "on both hosts". §8.4.4: replace the bullet with one sentence, that the workflow runs on Claude Code
   alone and `.claude/` is its single source (AY5). §8.4.5: drop the tiers bullet and the "A host without" sentence.
5. Record 25: the first cell of AA1 to AA4, AA7 and AA8 gains `*Superseded by AY5.*`; `holds-now.yaml` gives each
   `superseded by AY5`, AY5 `§8.4.4; the git tag copilot-host`, and AZ19 the tag with
   `open: the author's push after WP6.03's merge`.
6. The register: REV-166 to REV-168 `declined`, each section gaining `**Declined** (§8.2.49 AY5, <date>)` with the
   tag's name. The five links become plain text that names the tag.
7. Run `index_records.py` and `decisions.py`.

**Item 2 (D6).** Apply the audit's hunk 3. Remove the glob. §8.4.5's sentence on the kept scripts gains the `gui/`
folder.

**Item 3 (D7).** `project.md` gains one section, *A rescoping round*. It applies when a ruling opens the project's
scope, as AZ7 does. The round then also reads §3's requirements in full, each tool and phase of §8.1, OPN-08, the
last cleanup's Outcome, `docs/project/architecture-survey.md` and the last closed phase's measured cost. It may open
any requirement, tool or phase, and the rulings that ruling names. It changes the phase in flight only by naming
`/np-plan amend <n>` as the next step. The file's first paragraph says "unless a ruling opens more".

**Item 5 (D2).** Rewrite in place; add the two files.

- `CLAUDE.md`. Keep, tightened: the project, *Before doing anything*, *Setup*, the *Commands* table, *Project
  structure*, *Testing*, *Provenance*, *Git*, *Durable learnings*, *Do NOT*. *Commands* keeps two sentences on the
  gate: the commit hook runs it; a push needs `gate.sh run` to pass, as the core's *Gate and push* says. Its
  selection, variables and prose-only rule go (Grounding D2). *Implementation workflow* keeps the three commands in
  one sentence each, **Models**, **Open items**, the report path, and pointers to §8.4.4, §8.4.5 and the core. *Prose
  in code* folds into *Rules by path*.
- `core.md` keeps *Reading order*, *The branch*, *The package's PR and branch*, *Two lanes*, *Normativity*, *Models
  and executors*, *Records* and *Gate and push*, which gains the three steps of the push gate from `CLAUDE.md`.
  *Reading order* says that `/np-plan` reads `current.md` and that the other two open it when they update it;
  the other three places of Grounding D2 say the same or drop the file.
- `.claude/workflow/finish.md` takes *The author's page*, *The PR contract* and *Report and stop*, unchanged in
  substance. The core ends with one line that names it.
- *Load the brief* step 3 becomes: read a clause the plan cites when the item that cites it starts.
- `np-implement/wp.md` keeps *Load the brief*, the task list, *Sub-agent items*, *How the work lands* and
  *Measurements are deliverables*. `np-implement/finish.md` takes the compaction checkpoint, *Keeping the record
  straight* and *Finishing*. `wp.md` says to read it at the first checkpoint or when the last item is done.
- Change each citing file of Grounding D2 to the new place; the steward cites §7.6 for the per-push selection.
- The commit's body lists each removed passage with the file that keeps it.

**Item 6 (D5).**

- `np-plan/wp.md`, *Putting the decisions to the author*: every plan puts two proposals, the implementing and the
  shipping model, each with its reason and what another model would change in the plan. After the ruling the plan
  fits the models: its executors, its checkpoints and how much *Implementation details* spells out. The template's
  brief names both models. *Grounding the plan* and *Work items* say "the model the author ruled".
- `np-plan/review.md`: the approval summary names both models.
- `CLAUDE.md` **Models** and the core's *Models and executors*: §8.4.5's rule in two sentences.
- `np-implement/finish.md`, the pause: the prompt names the plan's shipping model. Call `checkpoint.sh save ship`
  only where the plan names one model for both; otherwise run `checkpoint.sh clear`, print the prompt and end the turn.
- `np-ship/wp.md`: it runs on the model the plan names. `np-implement/wp.md`'s opening line and
  `checkpoint.sh`'s header say that the ship chains only where the plan names one model.
- `holds-now.yaml`: AZ20 and AZ21 lose their `open:` parts.

**Items 7 and 8 (D8).**

1. Item 7: tick, gate, push. Run `checkpoint.sh clear`. Print a prompt that asks for a new session on Fable 5.2,
   started on the package's branch, not a `/compact`, with `/np-implement wp 6.03`. End the turn whatever
   `NANOPNP_AUTO_CHECKPOINT` says.
2. Item 8, in the new session: read as the instructions say, with no clause before the first edit. Make the first change with `Edit`: the Outcome's
   heading under this section. Then run `uv run .claude/scripts/usage.py --reading` and take the `first window` line.
3. Record the words by part, the ten largest files and the words left under the limit for a plan at its cap. On a
   pass, §8.4.4's bullet loses "From WP6.03's merge",
   and `holds-now.yaml` gives AZ18 `§8.4.4` and AY8 no `open:`.
4. On a miss, record it, cut the largest standing file, commit, and repeat items 7 and 8.

> **Outcome — the first new session measured `main`'s tree, not the cut.** The session of 23 November started on a
> branch at `main` (`e11ef54`). It loaded the uncut `CLAUDE.md` (2,342 words) and read the uncut core,
> `np-implement/wp.md` and `current.md` before it checked out the package's head and read the cut files. Its
> `first window` line: 10,208 words of project text before the first edit (instructions 4,348; records 4,355;
> `CLAUDE.md` 1,505, counted from the head's tree, not the file loaded); 98,038 tokens at the start, 153,311 at the
> edit; largest: this plan 3,349, `core.md` 2,265 (uncut and cut), `np-implement/wp.md` 2,015 (uncut and cut),
> `current.md` 695, `knowledge/index.md` 311. It measures no cut and is no miss, so no file is cut again. Without
> the three uncut reads the window would hold about 6,870 words, 1,130 under the limit, and 629 under it with a
> plan at its cap: an estimate, not D8's measurement. D8 and item 7's prompt now name the package's branch; item 7
> is repeated and row 5 stays open.

> **Outcome — the second new session measured the cut: 7,186 words, a pass.** The session of 23 November started
> on a branch at the package's head (`31e88f2`) and loaded the cut `CLAUDE.md`. Its `first window` line: 7,186
> words of project text before the first edit (instructions 1,706; records 3,975; `CLAUDE.md` 1,505); code 0;
> commands 854; 91,693 tokens at the start, 123,816 at the edit. It read four files, not ten: this plan 3,664,
> `core.md` 899, `np-implement/wp.md` 739, `knowledge/index.md` 311; the skill's own text is the rest of the
> instructions. That is 814 words under the limit, and 628 under it with a plan of 3,850 words in this plan's
> place. One read was not asked for: a combined `git` command also printed the first 60 lines of `current.md`, 592
> words, which the measure counts as command output (AZ16). With them the window holds 7,778 words, still under
> the limit. Row 5 passes; no file is cut again.

> **Outcome — the package cost about one agent hour, under the estimate.** Implementing: three sessions, 0.7 agent
> hours, four touches (Fable 5.2, 0.07 M tokens out); shipping to the review's fixes: 0.3 agent hours, one touch
> (Opus 5.5, 0.11 M out). Together about 1.0 agent hour and five touches, against the In brief's two to four hours
> and eleven touches; the tag's push after the merge is one more. [Review 078](../../code_reviews/CODE_REVIEW_078.md)
> cut `CLAUDE.md` to 1,497 words (1,490 by plain `wc -w`).

**After the merge.** The ship's report adds, each in its own block, with the commit written out:
`git log --diff-filter=D --format=%H -1 origin/main -- .claude/workflow/hosts.md`, whose parent is the tag's commit;
`git tag -a copilot-host <parent> -m "The last commit that holds the Copilot host (§8.2.49 AY5)"`; and
`git push origin copilot-host`.

### Work items

- [x] f850744 1. The Copilot host removed: the files, `.claude/scripts/audit/`, the hooks, the instructions, §8.4, record
  25, `holds-now.yaml`, the register and the links (D3, D4, D6). Done when Verification's rows 1 to 3 pass.
  **Executor:** main
- [x] 4ff5d62 2. The audit's rest: `np-ship/wp.md`, `.claude/rules/python.md`, §8.4.5 (D6). Done when the code and review
  say so. **Executor:** main
- [x] 00faf8a 3. `.claude/skills/np-plan/project.md`; REV-278 `fixed` (D7). Done when the code and review say so.
  **Executor:** main
- [x] 4. Compaction checkpoint. **Executor:** main
- [x] 866dd0e 5. The start path: `CLAUDE.md`, `.claude/workflow/core.md`, `.claude/workflow/finish.md`,
  `.claude/skills/np-implement/wp.md` and `finish.md`, and each citing file (D2). Done when Verification's row 4
  passes and the commit lists each removed passage. **Executor:** main
- [x] 541526b 6. The models: the `np-plan`, `np-implement` and `np-ship` skills, `CLAUDE.md`, the core, `holds-now.yaml`
  (D5). Done when the code and review say so and row 4 still passes. **Executor:** main
- [x] 7. Checkpoint for a new session (D8). **Executor:** main
- [x] 20bb8b4 8. The measurement: its Outcome, §8.4.4, `holds-now.yaml` (D1, D8). Done when Verification's row 5 passes.
  **Executor:** main
- [x] 42f5e50 9. `CHANGELOG.md`'s `## [0.7.0-alpha.3]`; REV-272's section gains the instructions' word counts, before and
  after. Done when the code and review say so. **Executor:** main

### Verification

| # | Check | Oracle | Command |
|---|---|---|---|
| 1 | No live file names the host | Prints nothing | `git grep -il -e copilot -e antigravity -e 'hosts\.md' -e 'another host' -e 'a host where' -- .claude .github .githooks .agents AGENTS.md CLAUDE.md justfile specification/08-implementation-plan/04-development-process.md` |
| 2 | The three hooks run | `bash -n` passes on each; the gate allows a `git status` payload with exit 0 and no output; `session-start.sh` exits 0 with its summary; with the switch unset `checkpoint.sh` prints `off`. Run before item 4: `off` drops a saved checkpoint | `bash -n .claude/hooks/<hook>.sh`; `echo '{"tool_input":{"command":"git status"}}' \| .claude/hooks/gate.sh`; `.claude/hooks/session-start.sh </dev/null`; `NANOPNP_AUTO_SHIP= .claude/hooks/checkpoint.sh save ship <plan> 6.03 </dev/null` |
| 3 | The records agree (Tier 1; VER-61, VER-79; VER-45) | The kept tests pass unchanged; `links.py --anchors` names no file this package changed; the strict documentation build passes | `.claude/hooks/gate.sh run`; `uv run .claude/scripts/links.py --anchors`; `CLAUDE.md`, *Commands* |
| 4 | D2's targets | 1,500, 900 and 750 words or fewer | `wc -w CLAUDE.md .claude/workflow/core.md .claude/skills/np-implement/wp.md` |
| 5 | The limit (AZ18) | The new session's `first window` line gives at most 8,000 words of project text | `uv run .claude/scripts/usage.py --reading` |
| 6 | The plan's identifiers | `clause.py` resolves AY5, AY7, AY8, AZ7, AZ9, AZ13 to AZ21, AA1 to AA8, AB1, AI4, AN8, N1, N3, OPN-08, VER-45, VER-61 and VER-79 | `uv run .claude/scripts/clause.py <ID>` |

No test is added: every item is outside the test scope.

### Out of scope

- Who owns the code (audit F3), REV-183's owner, REV-279 and v1.0's content: the rescoping round.
- The other skills' length (`np-plan`, `np-ship`, `np-gui`, the steward): no limit binds them.
- Phase 6's fourth closing criterion: the close measures a later package's session again.
- The tokens the app loads before a session's first message: the author's settings.

### Open questions

None blocks. The author's rulings on this plan are AZ18 to AZ21.
