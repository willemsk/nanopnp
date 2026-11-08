# Code review 038: audit of the agentic setup (`CLAUDE.md`, skills, workflows, hooks)

2026-11-08 · branch `claude/inspiring-gates-v05nh5` at `1e7fa2e` · scope: `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.agents/`, `.githooks/`, `.github/` · focus: efficiency, clarity and accuracy of the instructions an agent session reads

## 1. Verdict

The setup is unusually well engineered. Every specification identifier cited in the instruction
files resolves, every path and symbol they name exists, the hooks behave as documented when probed,
and the CI description in the steward skill matches `ci.yml` job for job. The configuration keys in
use are all supported by current Claude Code.

The findings below are mostly second-order: one efficiency trap in `CLAUDE.md` that can cost a
session three to four minutes per commit, a handful of statements that drifted from what the code
does, an undocumented third host, an orphaned helper script, and prose that is dense enough to
slow a fresh session down. Nothing found would make a session do the wrong thing on physics,
numerics or the gate.

Severity scale: **High** changes what a session does or costs real time on every use; **Medium**
misleads a reader or a host; **Low** is polish.

## 2. What was audited and how

Files read in full: `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json`, `.claude/workflow/*`,
`.claude/workflow/hosts/copilot.md`, `.claude/rules/*`, every `.claude/skills/*/*.md`, every
`.claude/agents/*.md`, `.claude/hooks/*`, `.claude/scripts/*.py` and the heads of the GUI scripts,
`.agents/*`, `.githooks/pre-push`, `.github/workflows/*`, `.github/actions/tier12/action.yml`,
`.github/hooks/nanopnp.json`, `.github/copilot-instructions.md`, `.github/scripts/prose-only.sh`,
the PR and issue templates, `docs/plans/current.md`, and the specification sections the files cite.

Checks run:

- `clause.py` on all 93 identifiers the agentic files cite: every one resolves.
- `duplicates.py`: passes.
- Existence of 42 referenced paths and 5 referenced symbols: all present.
- `gate.sh` in hook mode on four synthetic payloads (a non-git command, a push without a stamp, a
  commit with `--no-verify`, a commit under a 1 s budget): each gave the documented verdict in
  under 50 ms, or the documented refusal.
- `prose-only.sh` on six paths: matches its header comment.
- `pytest --collect-only` with and without `--nightly`: 1754 of 1867 tests in the per-push
  selection, 1823 with `--nightly`; example 01 and example 02's ePNP-NS leg are in the per-push
  selection, as `CLAUDE.md` and §7.6 say.
- Current Claude Code documentation, fetched through a sub-agent, for every frontmatter and
  settings key in use.

## 3. Findings

### 3.1 Accuracy

**A1 (High). `CLAUDE.md` line 43 tells a session to run the commit gate by hand, and the hook
then runs it again.** "The gate before a commit" lists the four checks plus `pytest -m tier1`.
A session that follows it and then runs `git commit` pays twice: the manual run writes no stamp,
so the PreToolUse hook re-runs lint, format, types, the lock check and all of Tier 1. §7.6 records
that run at 187 to 220 s. The hook's own stamp (`nanopnp-gate.pass`) exists precisely so a tree
state is gated once. Recommendation: replace line 43 with "The commit hook runs the gate; do not
run the checks by hand before a commit. Run `.claude/hooks/gate.sh` with no argument only to
reproduce a refusal." Also note that `-m tier1` is not what the hook runs (`tier1 and not slow`,
plus the GUI file, plus `uv lock --check`); today no Tier 1 test carries `slow`, so the selections
coincide by accident.

**A2 (Medium). The push gate's requirements list is incomplete.** `CLAUDE.md` line 63 says `run`
sets `NANOPNP_REQUIRE_GMSH=1` and `NANOPNP_REQUIRE_APBS=1`. `gate.sh` also sets
`NANOPNP_REQUIRE_BROWSER=1` and locates Chromium under `/opt/pw-browsers/` (`gate.sh` lines
395 to 405; read by `tests/tier1/test_gui_screens.py`). A developer whose machine has no browser
learns this only from the failure. `CONTRIBUTING.md` line 74 says it; `CLAUDE.md` should too.

**A3 (Medium). `hosts.md` documents one host; the adapter implements two.** `hosts.md` says "A
new host adds one map here and, for its hooks, a dialect in `.agents/hooks/adapter.sh`", and
lists Copilot only. `adapter.sh`'s default dialect is `antigravity`, wired through
`.agents/hooks.json` (matchers `run_command`, `replace_file_content|write_to_file`) and
`.agents/skills.json`. Antigravity appears in no current instruction file, only in old plans. Either
add an Antigravity row to `hosts.md` with its map, or state that `.agents/` is a legacy adapter
kept for one tool. As it stands, a reader of `hosts.md` cannot tell whether `.agents/` is live.

**A4 (Medium). `same_tree.py` is an orphan.** `.claude/scripts/same_tree.py` is referenced by no
skill, rule, `CLAUDE.md` line, or test; only historical plans (WP45, WP50) and the changelog
mention it. Its test was deleted by WP50. `CLAUDE.md` line 148 names "the kept helpers" as the
three sub-agents and `clause.py`, which omits `duplicates.py` (live: `core.md`, `np-ship/wp.md`)
and `same_tree.py`. Either delete `same_tree.py` or name it with its use (a prose-only commit
check) and keep the helpers line complete.

**A5 (Medium). The `out=` argument to the built-in `code-review` skill is undocumented.**
`np-ship/wp.md` line 69 and `np-plan/review.md` line 26 pass
`--max-findings all <target> out=docs/code_reviews/ -- <brief>`. The built-in skill documents
`<level>`, a target, `--comment`, `--fix` and `--max-findings`; `out=` is not among them, and it
sits in the position where a second target would be parsed. The reports exist, so either the skill
tolerates it or the fallback in `review.md` step 2 ("if the review wrote no report, write it")
has been doing the work. Move `out=` after the `--` into the brief, where it is prose the review
agent reads, and say in `CLAUDE.md` line 154 that the report path is given in the brief.

**A6 (Medium). `np-ship/wp.md` lines 72 to 79 argue from infrastructure facts that are not
verifiable from the repo and may have moved.** "Inside an `Agent`, the skill returned no findings"
is a historical observation stated as a rule. "The review agent's prompt cache lives five minutes,
against one hour here" is a claim about the serving platform; this session's own runtime reports a
one-hour cache. Keep the instruction (run the review from the main session, keep the review without
gaps, do not run the gate inside it) and move the reasoning into one sentence with a date, or drop
it. An instruction that rests on a stale premise invites a future session to reverse it.

**A7 (Low). `settings.json` line 39 matches `MultiEdit`.** `MultiEdit` is no longer in the
documented tool list. The entry is harmless (`Edit|Write` still match) but reads as live.

**A8 (Low). `gate.sh` emits a top-level `permissionDecision` beside `hookSpecificOutput`.**
The top-level form is for Copilot, as the comment says, and Claude Code documents only the nested
one. Fine as is; worth a line in `settings.json`'s neighbourhood or `hosts/copilot.md` so nobody
"cleans it up". The `{"systemMessage": …}` the gate prints on a pass (line 605) is documented as a
universal field but not listed for PreToolUse; it may be silently dropped. Not a defect.

**A9 (Low). `AGENTS.md` and `copilot-instructions.md` call `CLAUDE.md` "normative".** `CLAUDE.md`
itself says `SPECIFICATION.md` is normative and the physics concepts under `knowledge/` are
normative. Say "the entry point" or "the working instructions", which is what `README.md` line 140
says.

**A10 (Low). The PR template's comment says `/np-ship` fills it in.** `np-implement/wp.md`
opens the PR and fills the body; `np-ship` reuses it. Say "`/np-implement` fills this in and
`/np-ship` keeps it current."

**A11 (Low). `steward/SKILL.md` line 100 says the default selection is "tiers 1 and 2 without
the `nightly` tests".** It is also without `slow` (`pyproject.toml` `addopts`). Line 105 names three
network steps; the apt cache action, `playwright install` and `actions/checkout` reach the network
too. Both are small, but the steward is the file a session reads when deciding whether a failure is
infrastructure.

**A12 (Low). `core.md` line 11 and `CLAUDE.md` line 26 give different sync commands.** `core.md`
says `uv sync --all-extras --frozen`, `CLAUDE.md` says `uv sync --all-extras`, the session hook
uses `--frozen`, and the gate and CI set `UV_LOCKED=1`. `--frozen` installs a stale lock silently;
`UV_LOCKED` fails on one. One sentence in `CLAUDE.md` *Setup* should say which to use when, or the
two should agree.

**A13 (Low). `docs/plans/current.md` is 780 words against its own 700-word rule** (its *Handoff
Rules*, line 71). The rule is the file's; the next package edit should trim it.

### 3.2 Efficiency

**E1 (High). See A1.** The double-run of the commit gate is the one cost that recurs on every
commit of every package.

**E2 (Medium). `permissions.allow` does not cover the commands the instructions ask for.**
`settings.json` line 11 allows `Bash(.claude/hooks/gate.sh run)` exactly, but `CLAUDE.md` line 57
tells the session to run `.claude/hooks/gate.sh run > <log> 2>&1; echo "exit $?" >> <log>`, which
does not match, so the one command every push needs still prompts. `uv run .claude/scripts/clause.py`
and `duplicates.py`, which the skills call often, are not listed either (`uv run pytest:*`,
`uv run ruff:*` and `uv run mypy:*` are). Add `Bash(.claude/hooks/gate.sh run:*)`,
`Bash(uv run .claude/scripts/clause.py:*)`, `Bash(uv run .claude/scripts/duplicates.py:*)`,
`Bash(git fetch:*)` and `Bash(git branch:*)`. The `:*` suffix is current syntax.

**E3 (Medium). `clause.py` prints every superseded ruling and crashes when piped to `head`.**
`clause.py §7.6` emits §7.6 and then seven ruling rows, four of them marked superseded, about 2,000
words; `§8.4.4` is similar. A session that pipes into `head` to limit this gets a
`BrokenPipeError` traceback (line 143, `_emit`). Suggested: handle `BrokenPipeError` (or set
`SIGPIPE` to default), add `--no-history` to print definitions and NOTEs only, and mark or skip rows
whose first cell starts with *Superseded*. The skills tell sessions to run this script for every
cited clause, so its output size is a per-session cost.

**E4 (Low). The commit hook starts pytest on the GUI widget file on every commit** (`gate.sh`
line 574) even where PySide6 cannot import; it collects, exits 5, and is counted as a pass. That is
one `uv run pytest` start-up per commit on Linux for nothing. Gate it on `.venv/bin/python -c
"import PySide6"` or on a change under `src/nanopnp/gui/` or `tests/tier1/test_gui_widgets.py`.

**E5 (Low). Read cost per command is moderate and well bounded.** Word counts: `CLAUDE.md` 1,951;
`core.md` 1,478; `np-plan/wp.md` 1,689; `np-ship/wp.md` 1,686; `steward` 1,708; `copilot.md`
1,182. `/np-plan wp` reads about 4,200 words of skill text plus `CLAUDE.md`; `/np-ship wp` about
5,700. `knowledge/index.md` (192 words) and `SPECIFICATION.md` (1,017) are cheap entry points.
No file is bloated. The one structural cost is `core.md`: `/np-implement` reads its 300-word
*Putting a choice to the author* and *The In brief* sections, which only `/np-plan` uses. Splitting
those two into `np-plan/` would save `/np-implement` and `/np-ship` about 450 words each; low value,
noted for completeness.

**E6 (Low). `AGENTS.md` imports `CLAUDE.md` with `@`, so Copilot loads it twice** (`copilot.md`
admits this). About 2,000 words per Copilot session. If Copilot is to stay a host, make
`AGENTS.md` a one-line pointer without the import, since Copilot reads `copilot-instructions.md`
and `CLAUDE.md` anyway.

**E7 (Low). The session hook is lean.** It fetched `origin/main` with a 30 s cap, synced the
environment, found the Gmsh libraries present and printed three lines. The apt install path (up to
three 120 s attempts) runs only when a library is missing. No change needed.

### 3.3 Clarity

**C1 (Medium). The prose is uniformly dense, and several sentences need two readings.** The style
(short declaratives, "takes", "names", "goes to") keeps the files small, which is right for agent
text, but a few constructions are ambiguous on first read:

- `core.md` *Host coordination*: "It is named `host: claude-code|copilot` in the lane line". The
  pipe reads as "or" in prose and as literal text in code; say "`host: claude-code` or
  `host: copilot`".
- `np-plan/phase.md` "### 4 and 5. Draft the decisions and put them to the author / As `rulings.md`
  says." A two-word section body is a pointer, not a step; fold it into step 3's list.
- `np-plan/wp.md` *The caps*: "about 3,500 words outside its Outcome annotations, about 1,500 of
  them outside `### Grounding` and `### Implementation details`, and the details about 1,000" is
  three nested limits in one sentence; a three-row table would be read correctly first time.
- `core.md` *The package's PR and branch* step 1: four conditions and an "otherwise ask" in one
  paragraph. A numbered decision list would remove the guesswork.
- `np-ship/wp.md` §0.3: "Suppose the PR's Verification records a completed review, and the only
  commits after its reviewed head are …" is the resume path, but the heading does not say so.
  Name it "Resuming after a review".

**C2 (Medium). Identifiers are used as the primary cross-reference.** Phrases like "(§8.2.33 AI4)"
or "(§8.2.16 R6, R11)" appear about 90 times across the skills. Every one resolves, but each costs
a `clause.py` call to understand, and E3 makes that call noisy. Where the ruling's content is one
clause, say the clause in five words and keep the identifier in brackets, as `core.md`'s
*Normativity* does. This is a convention the files already state (`core.md`, *Putting a choice to
the author*: "An identifier only follows its words"); it is just not applied to the skills
themselves.

**C3 (Low). The same procedure is stated in four places with small differences.** *Gate and push*
is in `CLAUDE.md` (lines 45 to 61, the fullest), `core.md`, `steward/SKILL.md` and
`hosts/copilot.md`. The two-lane rule is in `core.md`, `np-implement/wp.md`, `np-ship/wp.md`,
`CONTRIBUTING.md` and §8.4.4. The renumbering rule is in `core.md` and `np-ship/wp.md` §1 with
slightly different wording. None contradicts another today; the risk is drift. Keep the full
statement in one place (`CLAUDE.md` for the gate, `core.md` for the lanes) and make the others
one-line pointers.

**C4 (Low). `copilot.md` is the longest file nobody on Claude Code needs**, and REV-166 to
REV-168 record that the host has never been verified live. The file is internally consistent and
carefully hedged. Consider a one-line banner at its top saying that status, so a Claude Code
session that lands on it does not treat the Copilot substitutes as tested.

**C5 (Low). `render.md`'s `qt` target says "today's shell (removed with it)"** while
`current.md` places Qt's removal in WP5.16. Accurate, but "removed with it" needs the reader to
know what "it" is; say "removed in WP5.16".

## 4. What checked out

- All 93 cited clause, ruling and requirement identifiers resolve through `clause.py`.
- All referenced paths, scripts, fixtures, YAML files and module symbols exist, including
  `STATES`, `SCREENS`, `server.READY`, the `--state` and `--no-browser` flags, the knowledge
  anchor `#815-…`, and `docs/project/modularity-layering.yaml`.
- `gate.sh` hook mode: ignores a non-git command in 19 ms; refuses a push with no stamp in 41 ms
  with the documented message; honours `--no-verify`; reports a budget exhaustion as a refusal with
  the documented remedy. The 1500 s budget sits under the 1800 s hook timeout, and a timed-out hook
  lets the call through, so the budget is the right design.
- `prose-only.sh` agrees with its own header on every probed path.
- The per-push selection is what `CLAUDE.md`, §7.6 and the steward describe; example 01 carries no
  `nightly` marker, example 02's classical leg does, example 03 does.
- `steward/SKILL.md`'s description of CI matches `ci.yml`: one ubuntu 3.14 leg on a PR with two
  marker shards; `CI result` as the single required check; `docs` on every push regardless of prose;
  `platforms` after a merge; `bundle` gated; `tier3` recorded; the nightly issue.
- Agent frontmatter (`model`, `tools`, `effort`, `omitClaudeMd`), skill frontmatter
  (`argument-hint`), `${CLAUDE_SKILL_DIR}` and `$ARGUMENTS`, `.claude/rules` with `paths:`, hook
  `timeout` and `statusMessage`, `SessionStart` stdout as context, and the `hookSpecificOutput`
  deny shape are all documented and current.
- The Chromium glob in `gate.sh run` matches this container (`/opt/pw-browsers/chromium-1243/…`).
- `duplicates.py` passes; the plan caps are honoured by the current package plan (WP5.09, 2,184
  words with every required section).

## 5. Recommended changes, in order

1. `CLAUDE.md` line 43: stop asking for the manual commit gate (A1, E1). Add
   `NANOPNP_REQUIRE_BROWSER` to line 63 (A2). Fix the helpers line (A4) and the `out=` note (A5).
2. `settings.json`: widen the allow list to the commands the instructions use (E2); drop
   `MultiEdit` (A7).
3. `clause.py`: handle a closed pipe, add `--no-history`, mark superseded rows (E3).
4. `hosts.md`: document or retire the Antigravity dialect (A3). Decide the fate of `same_tree.py`
   (A4).
5. `np-ship/wp.md` lines 72 to 79: keep the rule, date or drop the rationale (A6).
6. Wording: A9, A10, A11, A12, C1, C5. Then trim `current.md` to its own cap (A13).

None of these changes specified behaviour, so none needs a specification edit. Items 1, 2 and 3
touch `CLAUDE.md`, `settings.json` and a script under `.claude/scripts/`, which the python rule
covers; the commit hook will run the Tier 1 selection on item 3.

## 6. Outcome

Items 1 to 6 of section 5 landed in the commit that adds this file, plus E4 (the commit hook starts
pytest on the GUI widget file only where `PySide6.QtWidgets` imports) and C4 (the banner on
`hosts/copilot.md`). The line numbers above are those of the files before that commit. Decisions
taken: `same_tree.py` stays and is named with its use; `.agents/` stays and `hosts.md` names it as
the Antigravity adapter, unverified. Left open, as REV-222: C2 (identifiers as the primary
cross-reference in the skills), C3 (the gate and lane procedures stated in several places), E5 (the
`core.md` sections only `/np-plan` reads) and E6 (`AGENTS.md`'s `@` import on Copilot).
