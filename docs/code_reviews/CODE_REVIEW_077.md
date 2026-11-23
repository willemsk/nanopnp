# Code review 077: WP6.03's plan, the instructions cut and the Copilot host retired

2026-11-23 · branch `claude/zen-gauss-iibx4a` at `065832b` on `main` (`939009b`) · scope: the plan commit's 11 files,
read from `git show HEAD`. Read in place: `.claude/skills/np-plan/` (`wp.md`, `review.md`, `rulings.md`, `project.md`,
`SKILL.md`), `.claude/skills/np-implement/`, `.claude/skills/np-ship/wp.md`, the steward, `.claude/workflow/` (the
core, `author.md`, `hosts.md`, `hosts/copilot.md`), the four hooks, `.claude/settings.json`, `.agents/`,
`.github/hooks/`, `.githooks/pre-push`, `.claude/scripts/` (`usage.py`, `links.py`, `clause.py`, `audit/`),
`pyproject.toml`, the three workflows, §8.4.2, §8.4.4, §8.4.5, records 25, 26, 49 and 50, `holds-now.yaml`, WP6.02's
audit and Outcome, REV-278's section and `CHANGELOG.md` · level: high, with `--fix` · status: completed.

Static review of a plan commit: no test and no `gate.sh` run. Read-only checks were run: the plan's word counts
against `wc -w`; `git grep` for every file that names the host, `hosts.md`, the adapter folder, the audit folder and
the session plan; every citation of a heading the plan moves; `clause.py` on nine of the verification row's
identifiers. After the fixes `decisions.py` and `index_records.py` were re-run, and `decisions.py --check`, `links.py` and
`duplicates.py` pass. The plan holds 3,349 words, 1,534 of them outside its
Grounding (829) and its Implementation details (986); its In brief holds 274. Each is within its cap.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | The plan's Grounding D2; item 5 | The plan says the core's *The package's PR and branch* "reads no `current.md`". Its step 2 ends "Read `current.md` and the plan from this tree", and `CLAUDE.md`'s *Implementation workflow* and `session-start.sh`'s summary say to read it too. Item 5 changed *Reading order* alone, so the measured session would still read the file's 700 words | Fixed: the grounding names the four places, and item 5 changes each |
| 2 | Important | D1, D8; item 8; row 5; §8.2.50 AZ18 | The limit's room is not in the plan. At D2's targets a first window reads 3,253 words of instructions, 302 of `knowledge/index.md` and this plan's 3,300, which leaves about 1,150 for clauses; the baseline's median is 1,192 and `clause.py AZ18` alone prints 487. A plan at its cap leaves 595. `np-implement/wp.md`'s *Load the brief* asks for every section the plan cites, so row 5 passes or fails by what the measured session chooses to print | Fixed: the grounding states the sums, and item 8 records the room a plan at its cap would have. The review turn then decided, in D2, that `/np-implement` reads a clause when the item that cites it starts; item 5 changes *Load the brief* so, and item 8 reads no clause before its first edit. The number stays the author's |
| 3 | Important | D3; Grounding D3; row 1 | D3 removes "every hook branch" that serves the host and the grounding lists three hooks. `format.sh` reads a `path` key and a raw `apply_patch` string, and `gate.sh` a string `tool_input`; both came with the host (`CHANGELOG.md`, the entry before `[0.6.0-alpha.8]`; §8.2.26 AB1). Neither holds the word, so row 1 does not see them, and the implementer would have to guess | Fixed: the grounding states both; D3 and item 1 keep them as they keep the refusal object, with no logic changed. The review turn kept this |
| 4 | Important | Row 2 | The oracle holds four checks and the command cell one. `checkpoint.sh save ship` without its plan and number exits 2 with the usage line, and with `NANOPNP_AUTO_SHIP=1` inherited it prints `on` and saves a checkpoint that the Stop hook then enforces | Fixed: each check has its command, the switch is emptied on the command line, and the row says to run it before item 4, because `off` drops a saved checkpoint |
| 5 | Important | Item 5; `.claude/skills/steward/SKILL.md`, *What CI runs* | The steward cites `CLAUDE.md`'s *Commands* for the per-push selection. Item 5 takes the selection out of that section and keeps the heading, so the citation would point at a section that no longer says it. The grounding listed citations by heading only | Fixed: the grounding names it, and item 5 sends it to §7.6 |
| 6 | Nit | Row 3 | The oracle asks that `links.py --anchors` name no changed file. `gate.sh run` does not run `links.py`, and CI runs it without `--anchors` | Fixed: the command is in the row |
| 7 | Nit | Row 1 | The pattern is `copilot` alone. `CLAUDE.md` ("a host where it does not fire", `hosts.md`), `justfile`, `np-implement/wp.md`, `np-ship/wp.md` and `usage.py` name the host without the word, and `hosts.md` names Antigravity | Fixed: the pattern also holds `antigravity`, `hosts\.md`, `another host` and `a host where` |
| 8 | Nit | Item 6 | Three places that state the rule were not in the item: `np-plan/wp.md`'s *Work items* ("as `CLAUDE.md`'s *Models* sets it"), which Grounding D5 lists; `np-implement/wp.md`'s opening line, which chains into `/np-ship` whenever the switch is set; and `checkpoint.sh`'s header | Fixed: item 6 names them |
| 9 | Nit | Item 1, step 3; the core's *Host coordination* | The section goes whole. Its third bullet holds a rule that is not the host's, to rebase on `origin/<head>` before each push, and no other section states it. Sessions on two machines still share a branch | Fixed: the rule moves into *Gate and push*, without "the other host" |
| 10 | Nit | The In brief | 277 words against 275. "Eleven times you act: five …, one …, one …" lists seven | Fixed: 274 words, and the three are named as among the eleven |
| 11 | Nit | `docs/plans/current.md`, *Not to be re-decided* | The commit shortened a bullet to "QR-16's gaps are carried to Phase 7 (§8.2.47; REV-274)". REV-274 is the five Qt details, which the bullet no longer names | Fixed: the bullet names both again; the In brief lost five words, and the file holds 699 |
| 12 | Nit | The Phase 6 plan, WP6.02's entry | "Live: AZ13's limit" names the number AZ18 replaced | Fixed: "the limit of AZ13 and AZ18"; the record quotes the line as it was |
| 13 | Nit | Grounding D1 and D6; row 6 | `current.md` holds 700 words at this head, not 698. "Ten files of code review 039's audit and two spent migrations" reads as twelve; the folder holds ten. Row 6 leaves out OPN-08, which item 3 cites | Fixed |

## Checked and found true

`CLAUDE.md` holds 2,342 words, the skill 103, the core 1,364, `np-implement/wp.md` 1,276 and `knowledge/index.md`
302. `.claude/settings.json` wires the hooks straight to `.claude/hooks/`, and `adapter.sh` is reached only from
`.agents/hooks.json` and `.github/hooks/nanopnp.json`. `session-start.sh` opens with the `COPILOT_CLI` block,
`switch_on` returns 1 under it, and `gate.sh` names Copilot in its header alone. The session plan has four links in
`review-items.md`, one in `CHANGELOG.md` and one line of `docs/plans/index.md`. `holds-now.yaml` gives AA1 to AA5,
AA7, AA8 and AB1 as the plan says, and AA6 and AV6 are already `superseded by AY5`. `release.yml` starts on `v*`
alone; hatch-vcs reads only tags that hold a digit, so `copilot-host` moves no version. `main` keeps each item's
commit, so the commit that deletes `hosts.md` reaches it and its parent holds the host. No test and no CI step reads
`CLAUDE.md`, a skill or a workflow file, except `links.py`. Nothing outside `.claude/scripts/audit/` runs it, and the
knowledge note is its one citation. `.claude/scripts/gui/` holds six files. `project.md` and REV-278 read as D7 says.
`checkpoint.sh save ship` reads no plan. `usage.py --reading` marks the first window, counts the tree's `CLAUDE.md`
and ends at an edit tool. Records 01, 11 and 42 hold rows added on a later date (review 075), so AZ18 to AZ21 may
join record 50. The decisions page's counts moved by the four rulings and the eight plan rows. The plan has each
section of `wp.md`, each item names its executor, and the brief names both models (§8.4.4).

## Not assessed

- That a skill's `model` field holds for one turn (Grounding D5): it cites Claude Code's documentation, which this
  review did not read.
- Whether D2's three targets can hold what each file must keep: that is item 5's work, and row 4 measures it.

The author's four rulings are unchanged by the fixes.
