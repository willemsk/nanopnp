# The browser-path count (WP6.05, D7)

**Status: measured 24 November 2026 at WP6.05 item 6. The author ruled the rule and its threshold as BD4 / BC15.**

D7 asks whether the local push gate may skip the browser tests. The rule applies if 34 or more of the last 100
pushes could not have changed a browser test. This record gives the count. It holds numbers only.

## What was counted

- **A push** is one `pull_request` run of `ci.yml` with a new head sha. A repeated sha is one push.
- **Its paths** run from the branch's previous pushed head, if that head is an ancestor of the new one. They run
  from the branch's merge base with `main` where there is no previous head, or the branch was rebased.
- **A push that does not count** has only prose paths (`.github/scripts/prose-only.sh`), or no paths at all.
- **The last 100 counted pushes** are taken, newest first.
- **A push is skippable** when none of its paths matches the browser pattern: `src/*`, `data/*`, `examples/*`,
  `docs/design/*`, `tests/data/*`, `tests/conftest.py`, `tests/tier1/conftest.py`,
  `tests/tier1/test_gui_screens.py`, `pyproject.toml`, `uv.lock`, `.claude/hooks/gate.sh`, `.github/scripts/*`.
- **`k`** is the skippable pushes by delta. **`k_branch`** is the same count on the whole branch: its paths run
  from the merge base with `main` to the push's head. The rule is tested on `k`.

## The figures

| | |
|---|---|
| Date | 2026-11-24 |
| `main` | `8a927523c8c930d76bd9c275c63481da324b3fae` |
| Runs read | 400 of 613 (4 pages of 100) |
| Distinct shas | 399 (one sha was repeated) |
| Shas dropped as unfetchable | 0 (all 399 fetched) |
| Pushes passed over as prose-only or empty | 62 (of 162 walked, newest first) |
| Pushes counted | 100 (from 2026-11-24T18:38:50Z back to 2026-11-04T20:40:33Z) |
| Branches among them | 46 |
| `k` | **32** of 100 |
| `k_branch` | **23** of 100 |

The window of 100 lies in the first two pages. Pages 3 and 4 supply the previous heads of branches that began
before it. A branch whose previous head lies beyond page 4 would take its merge base with `main` instead. The
count does not look for one.

One counted push is a merge commit, `17ebf87` on `claude/sleepy-carson-oomrxu`: its delta holds what the merge
brought in from `main`, so it is not skippable by delta, and it is skippable on its whole branch (14 paths). It
is the only counted push that is skippable on its whole branch and not by delta, so no reading of a push raises
`k` above 33, still below 34.

## By branch

| Branch | Pushes counted | Skippable by delta | Skippable on the whole branch |
|---|---:|---:|---:|
| `ccr-ffafd419-mwhw6f` | 5 | 2 | 0 |
| `claude/beautiful-hawking-sqa62e` | 5 | 1 | 0 |
| `ccr-79014567-29nzhs` | 4 | 1 | 0 |
| `ccr-797cfb5c-04dgls` | 4 | 1 | 0 |
| `ccr-9b77d38b-j3hc4f` | 4 | 0 | 0 |
| `ccr-dbee00a1-kqe1yy` | 4 | 2 | 0 |
| `ccr-ff91f6e7-ohlzgc` | 4 | 1 | 0 |
| `claude/hopeful-hamilton-3xq15p` | 4 | 0 | 0 |
| `claude/sleepy-carson-oomrxu` | 4 | 3 | 4 |
| `ccr-0bd2808a-l1k5c2` | 3 | 3 | 3 |
| `ccr-4b90fcd6-fjrv03` | 3 | 0 | 0 |
| `ccr-7f71a93c-ebh88d` | 3 | 3 | 3 |
| `ccr-867a032b-mcjt88` | 3 | 0 | 0 |
| `claude/charming-feynman-ns36cy` | 3 | 3 | 3 |
| `claude/upbeat-fermat-2idwx5` | 3 | 0 | 0 |
| `claude/wp-5-17-implement-0junxj` | 3 | 0 | 0 |
| `ccr-169567e1-txa9pn` | 2 | 0 | 0 |
| `ccr-7c47497f-c6db5h` | 2 | 0 | 0 |
| `ccr-a184c192-2cslg6` | 2 | 1 | 0 |
| `ccr-eb7edaa4-ck187i` | 2 | 2 | 2 |
| `claude/gallant-goldberg-dt74nq` | 2 | 0 | 0 |
| `claude/gifted-hopper-bxr8bg` | 2 | 1 | 0 |
| `claude/inspiring-gates-v05nh5` | 2 | 0 | 0 |
| `claude/keen-turing-g32u0j` | 2 | 0 | 0 |
| `claude/wizardly-wozniak-353gtq` | 2 | 0 | 0 |
| `claude/wp-5-07-implement-67cuqd` | 2 | 0 | 0 |
| `claude/wp-6-04-findings-review-ada48p` | 2 | 0 | 0 |
| `ccr-1df7b52e-xmkcc4` | 1 | 1 | 1 |
| `ccr-2e0edb08-u4c476` | 1 | 1 | 1 |
| `ccr-55e66f77-s0t613` | 1 | 1 | 1 |
| `ccr-7f42d119-nlqnbh` | 1 | 1 | 1 |
| `ccr-b14869a5-8mshj5` | 1 | 0 | 0 |
| `claude/adoring-albattani-iw6y0g` | 1 | 0 | 0 |
| `claude/inspiring-carson-p9b9uc` | 1 | 1 | 1 |
| `claude/loving-allen-ejewkc` | 1 | 1 | 1 |
| `claude/nice-franklin-h4k3zg` | 1 | 0 | 0 |
| `claude/np-gui-collect-pptskh` | 1 | 0 | 0 |
| `claude/np-plan-amend-6-8e71eb` | 1 | 1 | 1 |
| `claude/np-plan-wp-5-28-apae19` | 1 | 0 | 0 |
| `claude/pensive-lovelace-1cc77i` | 1 | 0 | 0 |
| `claude/pensive-meitner-3b4nge` | 1 | 0 | 0 |
| `claude/practical-cerf-81g9zz` | 1 | 1 | 1 |
| `claude/quirky-clarke-ctfb7z` | 1 | 0 | 0 |
| `claude/relaxed-hypatia-2s4fyk` | 1 | 0 | 0 |
| `claude/serene-pascal-dmnl60` | 1 | 0 | 0 |
| `claude/trusting-bell-hhyxbe` | 1 | 0 | 0 |

## The commands

The runs were paged with the GitHub tool `actions_list` (`list_workflow_runs`, owner `willemsk`, repo `nanopnp`,
`ci.yml`, event `pull_request`, 100 per page, pages 1 to 4). Each page was saved as it came; the pages are
scratch files and are not kept. A repeated sha kept its earliest run. Then:

```bash
git fetch --unshallow origin main
git rev-parse origin/main
# every distinct sha, fetched; one that fails is dropped and counted
cut -f3 shas.tsv | xargs -P 8 -I{} sh -c 'git fetch -q origin {} && echo ok {} || echo FAIL {}'
```

The count itself, run over `shas.tsv` (created_at, branch, sha), oldest first within each branch:

```bash
for each branch, for each sha oldest first:
    if prev is set and `git merge-base --is-ancestor prev sha`:  base=prev
    else:                                                         base=$(git merge-base sha origin/main)
    delta=$(git diff --name-only --no-renames $base sha)
    whole=$(git diff --name-only --no-renames $(git merge-base sha origin/main) sha)
    counts=no  if delta is empty or `.github/scripts/prose-only.sh` exits 0 on it
    skippable_delta  = no delta path matches the browser pattern (bash `case` globs)
    skippable_branch = no whole path matches the browser pattern
    prev=sha
sort the pushes newest first; take the first 100 that count; add up the two columns
```

The script was a scratchpad helper. It is not kept in the repository.

## The verdict

**k = 32 < 34: the rule does not apply, and BC15 is spent.** The push gate keeps the browser tests. On the whole
branch the figure is lower, `k_branch` = 23, so the whole-branch reading does not change the verdict.
