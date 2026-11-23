# Code review 081: WP6.04's plan, the ground-up review

2026-11-23 · branch `ccr-e0fd1539-vkifjy` at `52967fc` on `main` (`efda55e`) · scope: the plan commit's 14 files,
read from `git diff HEAD~1 HEAD`. Read in place: `.claude/skills/np-plan/` (`wp.md`, `review.md`, `rulings.md`,
`SKILL.md`, `phase.md`'s caps), `.claude/skills/np-implement/` (`SKILL.md`, `wp.md`, `finish.md`'s checkpoint),
`.claude/workflow/` (the core, `author.md`), `.claude/settings.json`, `.claude/agents/physics-reviewer.md`,
`.claude/scripts/usage.py`, `mkdocs.yml`, `justfile`, §1.1 to §1.3, §2.1 to §2.7, §8.3, §8.4.4, §8.4.5, records 07,
51 and 52, `holds-now.yaml`, the Phase 6 plan and its record, `docs/project/` and this session's own sub-agent
transcripts · level: medium asked, high as the reviewer reports it, with `--fix` · status: completed.

Static review of a plan commit: no test and no `gate.sh` run. Read-only checks were run: `wc -w` on the plan and its
parts, on its In brief, on `current.md` and on the Phase 6 plan without its report; `grep -ciE` with the plan's
pattern on the pack's sources; `find` and `wc -l` for the code and test sizes; `grep` for each identifier range of
the walk; `git ls-remote --tags origin`; a listing of the transcript folder the plan names. After the fixes
`decisions.py` and `index_records.py` were re-run, and `decisions.py --check`, `links.py` and `duplicates.py` pass. The
plan holds 3,602 words, 1,622 of them outside its Grounding (894) and its Implementation details (1,087); its In
brief holds 275. Each is within its cap. The Phase 6 plan holds 2,749 words against 2,750.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | D2; item 3's check | The check discards a design for "a `Read`, `Grep`, `Glob` or `Bash` input that names a path outside the pack, or an address holding `nanopnp`". A sub-agent's working directory is the repository (each transcript event's `cwd` is `/home/user/nanopnp`), so a `Grep` or `Glob` with no `path` searches the tree and names no path. A relative path in `Bash` names none outside the pack either. A `WebSearch` has a query and no address, and a tool beyond the four (an MCP tool that reads the public repository, say) is not looked at. A designer could read the code and pass. The pack's own path holds `-home-user-nanopnp`, so the address rule read literally over every input would discard every design | Fixed: the grounding states the four calls a check of named paths misses and the pack path's name; item 3's rule discards on each, and on a query that holds `nanopnp`; the brief asks each search to carry the pack's path |
| 2 | Important | Item 6 | The two cases are timed with `/usr/bin/time -v`. The container has no `/usr/bin/time` (`ls /usr/bin/time` fails, `which time` prints nothing), so the command fails as written and the implementer chooses another | Fixed: the grounding states it, and item 6 times with bash's `time`, which gives the wall time D5 asks for |
| 3 | Important | D2; Grounding D2; item 3; item 12 | The grounding counts implementation words in four knowledge folders and two specification files, and not in the sources of `purpose.md`. §1.1 and §2.5 name Python, §1.2 a 2D-axisymmetric finite-element mesh and the pipeline's steps, §1.3 a YAML case file, P3 and §2.5 the browser workbench, §2.5 a sparse direct solve. §1.3's closing paragraph lists the workbench's terms and links `docs/design/workbench.md`, a path D1 forbids and item 3's check discards. "How many blind designers chose the same unprompted" (the In brief) would then count choices the pack named | Fixed: the grounding lists what the sources name; item 3 leaves §1.3's closing paragraph out of the pack; item 12 marks as prompted each choice the pack names. BB3's sources are kept |
| 4 | Important | D1; Verification | D1 says the main session "reads no `src/`, no §5 or §6, no survey and no modularity report" until item 4's commit. The verification row checks only that the commits of items 2 to 4 precede item 6's, which says nothing of what was read. `wp.md` asks one assertion for each point of failure of a decision that says never | Fixed: the grounding names the session's own transcript; item 4 lists the session's calls from it as it lists an agent's and records the result in `method.md`; the verification row reads that list |
| 5 | Important | D2 | A design that peeked is "discarded and redone once by a new agent". What happens when the second one peeks too is not said, and item 3's done-criterion (no path outside the pack) then cannot be met. The `Plan` type's own prompt may ask it to explore the codebase, which would make this likely; that prompt was not read here | Fixed, decided by the plan as the check is: a second peek is kept, marked not blind and left out of the guard's counts |
| 6 | Nit | D3; item 4 | The unblinding continues each agent in the repository and names three files to read, with no check. A designer that then opens `src/` judges §3 knowing the code, and the In brief says the three "have never seen the code" | Fixed: item 4 lists each agent's calls again, and they name the three files alone; its done-criterion and the verification row say so |
| 7 | Nit | D6; Verification | D6 caps the report at 5,500 words and its proposals at twelve groups. No verification row checks either | Fixed: one row, with `wc -w` |
| 8 | Nit | D3, D4; Grounding D4; items 9 and 10 | The designers read §2.6, the dependencies, and BA12 opens every technology, but no walk group holds §2.6's twelve rows. "About 260 rows" does not follow from the ranges listed, which sum to 235 | Fixed: item 9 walks §2.6, and the grounding says about 245 |
| 9 | Nit | Grounding D2 | `specification/04-physics.md` has 8 lines with an implementation word, not 18: the pattern that gives the two knowledge folders their 22 and 30 gives 8 | Fixed |
| 10 | Nit | Grounding D6 | "G1 to G11 are rulings of §8.2.7": the record holds G1 to G12. The conclusion stands, `GU-` is free | Fixed |
| 11 | Nit | The Phase 6 plan, WP6.04's entry; the input note | D6 and `current.md` mark a difference keep, change now, change later, drop or add. The phase plan's entry and the input note still listed four verdicts, beside a guard line that allows a new requirement | Fixed: both say "drop or add"; the phase's record quotes the list as it was |
| 12 | Nit | Grounding D1 | The list of what the main session must not read names `docs/project/modularity*.md` and not `docs/_generated/`, where `uv run just docs` in item 1 writes the modularity report and the architecture page again | Fixed |
| 13 | Nit | Item 3's brief; item 1 | The three designs are written unedited into pages of the strict site. A relative link in one, to a pack file say, fails `links.py` or the build, and the fix would edit an unedited text | Fixed: the brief asks for no link |

## Checked and found true

§3 holds IF-01 to IF-09, FR-01 to FR-44, QR-01 to QR-16, CON-01 to CON-14 and N1 to N7 in 6,425 words; §5.6 holds
ADR-001 to ADR-005 in 1,910; §6 holds NUM-01 to NUM-34; §8.4 has 41 bullets, 4, 5, 2, 21, 4 and 5; the workbench
design has 17 sections and 63 `WB-` rows. `src/nanopnp/` holds 80,973 lines of Python in 20 subpackages, `gui/`
21,422 and `validation/` 8,560, with 15,296 lines of JavaScript and CSS; Tier 1 has 115 test files and 32,563 lines
of Python, Tier 2 60 and 12,025. The two knowledge folders of the pack hold 3,430 and 3,360 words and no
implementation word. The clone is shallow, and `origin` publishes each `-alpha.N` tag from `v0.1.0-alpha.1` to
`v0.7.0-alpha.3`. The register has 59 rows in the form the plan gives, REV-279 is the highest and `GU-` is in no
register. `CHANGELOG.md`'s newest section is 0.7.0-alpha.3, which holds the 3,238 words. `core/paths.py` reads
`NANOPNP_STORE`, `nanopnp run` exists and both case files are where the plan says. `mkdocs.yml` warns on an omitted
file, excludes `plans/` and `code_reviews/`, and its *Project* section is indented as item 1's lines are, after the
survey's line. §8.3 holds the two measured rates. The physics reviewer is on Opus with `Read`, `Grep` and `Glob`.
The transcript path of Grounding D2 is where this session's sub-agents are written, with `tool_use` blocks in
`message.content`. §8.3's sums follow: 12 sessions, 7 to 13 hours and 16 touches for the review with its round, and
66, 54 to 107 and 102 for the phase. The decisions page moved by three rulings and eight plan rows. BB3 to BB5 are
rows added to record 52 in `rulings.md`'s form, each with its `holds-now.yaml` line, and BA10 carries its pointer.
§8.4.5 states the designers' exception. The plan has each section of `wp.md`, each item names its executor, and the
brief names both models and that the ship never chains.

## Not assessed

- That the `Plan` agent type starts without `CLAUDE.md` and the git status, that the Agent tool's `model` overrides
  the type's, and that `SendMessage` continues a finished agent (Grounding D2, D3): they cite Claude Code's
  documentation, which this review did not read. Item 4 has its fallback.
- What the `Plan` type's own prompt asks of an agent (finding 5).
- Whether 5,500 words can hold about 245 rows' worth of proposals: D6 ranks and groups them, and item 12 finds out.

The author's rulings BB3 to BB5 are unchanged by the fixes.
