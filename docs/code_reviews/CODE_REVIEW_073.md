# Code review 073: the Phase 6 plan and its rulings (§8.2.50)

2026-11-22 · branch `claude/loving-allen-ejewkc` at `6ac2d92` on `main` (`a7e5374`) · scope: the plan commit's 18
files, read from `git show HEAD`. Read in place: `.claude/skills/np-plan/` (`phase.md`, `rulings.md`, `review.md`,
`project.md`, `amend.md`), `.claude/workflow/author.md`, §8.2.49 and §8.2.50, §8.1, §8.3, §8.4.1, §8.4.5,
`holds-now.yaml`, `.github/workflows/ci.yml`, `.claude/scripts/usage.py` and `clause.py`, and the sources the plan
names · level: medium, with `--fix` · status: completed.

Static review of a plan commit: no test and no `gate.sh` run. Read-only checks were run: the plan's file and function
names against `src/nanopnp`; a count of the error classes (69); `physics/models.py`'s length (2,076 lines); REV-156's
figures against AZ6's; `ci.yml`'s triggers; §8.3's arithmetic against its rates; the published tags; `clause.py` on
VER-45, VER-61, VER-62, VER-65, FR-28, RSK-15 and OPN-08; the plan's and `current.md`'s word counts. After the fixes,
`decisions.py`, `duplicates.py` and `links.py` were re-run, and the plan holds 1,650 words without its report, its In
brief 263.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | The Phase 6 plan, WP6.02 and completion criterion 4 | Both rest on `usage.py` measuring what a session reads before its first edit. At this head `usage.py` measures sessions, agent hours, touches and tokens, of one transcript: this session's, or the newest on the host. It has no measure of reading, and a fresh cloud container holds no transcript of an earlier package session. The plan presented the baseline as a run of an existing tool, so WP6.02's plan would have met a criterion nothing can log | Fixed: WP6.02 extends `usage.py` to that measure before it takes the baseline; open decision 2 gains the baseline's transcripts, the author's at WP6.02's plan (AY8) |
| 2 | Important | The Phase 6 plan, WP6.01 and its verification row | The row asks the failing test "on the three platforms". `ci.yml`'s `platforms` job runs on a push to `main`, nightly and on a dispatch; a pull request's CI is one Linux leg. WP6.01's own pull request would therefore go green and merge with Windows never run, which is the failure REV-277 records, and `phase.md` asks that a package is verified by the end of its own PR | Fixed: WP6.01 names a dispatch of `ci.yml` on the branch, which shows the three legs before the merge. Open decision 4, whether a pull request's CI runs the Windows leg, stays WP6.01's plan's |
| 3 | Important | The Phase 6 plan, WP6.02 and WP6.03; §8.4.5 | AY7 rules that the cleanup package runs whole on Fable 5.2, and that a plan names the model. AZ4 splits the cleanup in two, and the plan named Fable 5.2 only for the rescoping round. `CLAUDE.md` gives `/np-implement` to Opus 5.5, so both cleanup packages would have been implemented on the model the author ruled against; §8.4.5 still read "the cleanup package" | Fixed: the plan says both cleanup packages run on Fable 5.2 (AY7); §8.4.5 names WP6.02 and WP6.03 |
| 4 | Nit | §8.2.8 H3, §8.2.49 AY1, §8.2.46 AV5; `holds-now.yaml` | §8.2.50 says H3's "Phase 6" is amended by AZ1, AY1's rule that Phase 6 changes no number by AZ2, and AV5's grouping by AZ4. `rulings.md` asks a pointer in the amended ruling's first cell; none was added, and AY1's line of `holds-now.yaml` did not name AZ2 | Fixed: the three first cells carry their pointer; AY1's line names AZ2; `decisions.py` re-run |
| 5 | Nit | §3, FR-35's NOTE | "Phase 6's refusals package": AZ3 makes it two steps, WP6.04's error base and WP6.16's rewording, and names the NOTE as where the ruling lands | Fixed: the NOTE names both and cites AZ3; AZ3's line of `holds-now.yaml` leads with the NOTE |
| 6 | Nit | The Phase 6 plan, *True of the codebase today* | "`RunResult.record` writes `run.json`": `record` returns the dict, and `RunResult.write` writes it | Fixed: the fact names `RunResult.write` |
| 7 | Nit | The Phase 6 plan, *Work packages* | "WP6.nn takes `v0.7.0-alpha.nn`" reads as `alpha.01`. §8.4.1 gives WP5.02 `v0.6.0-alpha.2`, and a numeric pre-release identifier takes no leading zero | Fixed: "WP6.02 takes `v0.7.0-alpha.2`" |
| 8 | Nit | The Phase 6 plan, the verification row of WP6.02 and WP6.03 | "`clause.py` resolves every identifier": `clause.py` prints the identifiers it is given and has no mode that collects them, so the row named a check with no object. After the cleanup removes history, a citation left dangling would pass | Fixed: the row asks each identifier WP6.02's plan lists |
| 9 | Nit | The Phase 6 plan, open decision 6 | "moves a compared quantity" is in quotation marks and no record holds the words. AM2's are "add it if it moves one of them" | Fixed: the row cites AM2's words |
| 10 | Nit | The rescoping round; `.claude/skills/np-plan/project.md` | AZ7 holds the round at `/np-plan project` with every requirement of §3 open. `project.md` plans "the phases after the phase in flight", reads §3's Release column alone and "decides only what spans phases". `phase.md` asks that a skill changes where a ruling changes the workflow; the commit changes none | Not fixed: outside the commit's files, and WP6.03 changes the instructions. Recorded as REV-278, proposed for WP6.03, whose entry in the plan names it |
| 11 | Nit | The Phase 6 plan, WP6.18 | `phase.md` says the close package is planned now; the plan lists it as one provisional line | No change: AZ7 rules WP6.04 to WP6.18 provisional, with no plan before the round. Not a defect |

Checked and found true: `ci.yml` has a `platforms` job, and REV-277 dates the Windows leg's last pass; `field_at`
reads linearly on a P2 cell's split, and `render_fields` writes the fields file through `post/export`; `SWITCHES` is
a tuple of four names; `_domain_force`, `classify` and `default_ladder` exist where named; 69 error classes;
`physics/models.py` holds 2,076 lines; AZ6's 761 s, 62 % and 24 % are REV-156's; the record's count of seven
questions (five recommendations, two against); §8.3's Phase 6 row is 18 packages times the stated rates, and the
plan's 15 and 75 sessions sum to it; no review row names Phase 6 without its package; each moved row agrees with
its *Placed* line and `holds-now.yaml`; WB-58 already reads a field by its cell's P2 basis; the plan's sections are
`phase.md`'s, its provisional rows carry no identifier, and its In brief has no backtick or identifier;
`current.md` holds 698 words.
