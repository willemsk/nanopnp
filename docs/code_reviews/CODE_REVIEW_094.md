# Code review 094: a REV row is for an item that outlives its session (§8.2.58 BH1)

2026-11-26 · branch `claude/np-carry-wp-607-tyfnr4`, head `14d6dea` on base `00afebd` (the head CODE_REVIEW_093's
records left) · scope: one commit, 16 files, +63 and −31, read from `git diff 00afebd...14d6dea`, with the
statement in place of a plan: the author ruled (§8.2.58 BH1) that a `REV` row is kept only for an item that outlives
the session that finds it, and that a small finding, a doubt among them whose fix moves no ruling, is fixed in that
session; the commit states the rule and closes REV-296 and REV-297 by fixing them in `/np-chore`. It adds no
permission line. Against §8.4.4, §8.4.6, §8.2.8 H12, §8.2.56 BF5 and BF8, §8.2.57 BG2 and BG3, and the history
conventions of `np-plan/rulings.md`. Read in place: every statement of the open-item rule under `.claude/`,
`CLAUDE.md` and `specification/08-implementation-plan/`, `helper.md`, `np-carry/SKILL.md`, `np-shipper.md` and
`np-ship/wp.md` · reviewer: `np-reviewer`, Opus 5.5 at high effort · status: completed.

Static review: no `gate.sh run`. Probes: `decisions.py`, `duplicates.py` and `links.py` after the fixes, all
passing. No code under `src/` or `tests/` changed, so the physics and numerics axis has nothing to read, and no test is
due (§8.2.13 N1). Per BH1 itself, each finding below is small and fixed here; none is left to the author.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `.claude/agents/np-reviewer.md:32-35` | Axis 2, BH1. The new third bullet, "a doubt or a fix that would move a ruling, widen the package or is more than a small edit: do not fix it", catches every doubt, so it contradicts the second bullet, which fixes a small doubt; and it forbids a confirmed in-plan fix larger than a small edit, which the first bullet fixes and BH1 does not take away | Fixed: a small doubt that moves no ruling and keeps the scope is fixed; a fix that moves a ruling or widens the package, or a doubt whose fix is more than a small edit, is reported |
| 2 | Medium | `specification/history/57-…:17-18` | Axis 1, `np-plan/rulings.md` ("a superseded ruling gets only a pointer in its first cell … Its text stays"). The commit rewrote BG2's and BG3's consequences to what BH1 decided, so the register shows BH1's change under BG2 and BG3's date and record with no trace of the amendment | Fixed: BG2 and BG3 restored as ruled, each with a pointer to BH1 in its first cell; their `holds-now.yaml` entries name the amendment |
| 3 | Medium | `specification/history/58-…:15`; `holds-now.yaml` | Axis 2. BH1 says it "amends §8.2.56 BF5 and §8.2.50 AZ12's rows for such items", but AZ12 is the archive of closed items; the rule of open-item rows is §8.2.8 H12, which §8.4.6 itself cites beside BH1. Neither BF5 nor H12 carried the pointer or the `holds-now` note the convention asks for, and BH1's row did not name BG2 and BG3, which REV-296 and REV-297's fixes amend | Fixed: AZ12 corrected to H12; BH1 names BG2 and BG3; BF5 and H12 carry the pointer and their entries the amendment; BH1's entry names the agents, skills and workflows it changes |
| 4 | Medium | `.claude/skills/np-chore/SKILL.md:47-51` | Axis 2, REV-296. Step 7 now says "A format or lint failure this session fixes …", then the review of a later commit, then "A red CI follows the same rule": "the same rule" reads as the sentence before it, the review, and the commands of the format fix and the rerun after `np-builder`'s fix were dropped | Fixed: one sentence for a failed land or a red CI, with the two `ruff` commands, the failing log and "Then land again" |
| 5 | Low | §8.4.4, ship bullet and chore bullet | Axis 2, BH1. §8.4.4 kept "a finding it leaves to the author, and that outlives the session" but not who fixes a small finding the review leaves, which BH1 gives to `np-builder` with a medium-effort review of its diff; the chore bullet did not carry REV-296's land rule | Fixed: both bullets say it, citing BH1 |
| 6 | Low | `.claude/workflow/helper.md:76`; `.claude/agents/np-shipper.md:15` | Axis 2, the np-carry flow. A ship helper that meets a small finding the reviewer left hands back `WORKER` for `np-builder` (`wp.md` §4.1), and the builder's diff is reviewed at medium effort; `helper.md` asked for `effort: medium` only for a finding the author pulled in, and `np-shipper.md` said only "the reviewer fixes what it confirms" | Fixed: `REVIEW` names the small finding fixed after the review; the shipper sends a small finding left as `WORKER` and records no row |
| 7 | Low | `np-gui/review.md:13`; `np-gui/collect.md:17`; `np-plan/review.md:29`; `workflow/finish.md:31`; `np-implement/finish.md:71` | Axis 2, BH1. Five statements still left any finding open as a `REV` row with no test of whether it outlives the session | Fixed: each says a small finding is fixed and a row is for one that outlives the session, citing BH1 |
| 8 | Low | `docs/project/review-findings.md:102-103`; `review-items.md:1905-1923` | Axis 1, the register's form. The rows read "fixed by this chore in `<the commit's subject>`", which names no commit once read elsewhere; one **Fixed** note under REV-297 spoke for both, so REV-296's section, which archives on its own, had none | Fixed: rows name `/np-chore`, `14d6dea` and BH1; each section has its own note |
| 9 | Low | `CLAUDE.md`, `author.md`, §8.4.4, §8.4.6, `np-chore/SKILL.md` | Axis 1. Lines of up to 120 characters among neighbours wrapped at 100 to 110; `CLAUDE.md` *Open items* and §8.4.6 also dropped BH1's "a doubt among them whose fix moves no ruling" and "a ship and a chore" | Fixed: rewrapped, and the two qualifiers restored |
| 10 | Low | `specification/history/56-…:25` | Axis 1, `rulings.md`, met while adding finding 3's pointer. BF5's first cell named no amendment, though BF8 amended its review on 25 November 2026 and its `holds-now` entry says so | Fixed: the pointer names BF8 and BH1 |

The pass fixed ten findings and left none.

## Checked and found true

- **BF5 and BF8 pull-in.** A finding left to the author that outlives the session is still a row the author may pull
  in (BF5), fixed by `np-builder` with its diff alone reviewed at medium effort (BF8); BH1 only removes small findings
  from that path, and `np-ship/wp.md` §4.1 gives them the same fix and review.
- **The np-carry flow.** A helper never asks a worker mid-step: every hand-back ends it, and a fresh helper reads the
  note (§8.2.56 BF2). `wp.md` §4.1's `WORKER` hand-back for a small finding fits that; the main session lands the
  builder's commit before it serves the next `REVIEW` (BF11).
- **REV-296 and REV-297.** The skill now does what each recommendation says, and §8.4.4 says the same; both rows are
  `fixed`, and `decisions.md` moved them to the closed page (564 binding, 1,152 closed, 494 rulings).
- **The other statements.** `core.md`'s *Records* row, `author.md`, `np-ship/wp.md` §4.1 and §6, `np-ship/phase.md`,
  `np-implement/finish.md:41` (a deferral is a row) and `np-implement/wp.md` agree with BH1.

## Not assessed

- `just land` on this branch and its CI, which the session that started the review runs.
