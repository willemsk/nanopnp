# The reading baseline: what six packages read before their first edit

**Status: measured 22 November 2026 at WP6.02 item 2 (§8.2.50 AZ9, AZ10); the limit taken from it is ruled at item 5.**

`usage.py --reading` counts, for each window of a session, the words of project text read before the first `Edit`,
`Write` or `NotebookEdit`: the instruction files, the records and the tree's `CLAUDE.md` (AZ9). This record gives that
count for the twelve sessions of WP5.19, WP5.20, WP5.21, WP5.27, WP5.28 and WP6.01. The session service served all
twelve. Twelve `general-purpose` agents on Sonnet paged them with `list_events` (299 calls); the pages stayed on the
session's machine, and this record holds only numbers (AZ10).

## How a window is read from the pages

- **A page holds no typed prompt and no skill text.** A paged session's events start at its first assistant
  message. So a window opens at the session's start and after each compaction, and its command is read from the
  level file it reads: `np-plan/review.md`, `np-ship/*`, `np-implement/wp.md` or `np-plan/wp.md`, in that order of
  precedence; a plan session's first window is its plan. The words of the prompt and of a skill's `SKILL.md` (about
  100 to 300) are not counted. A window with no level file and no session kind to fall back on is "not known".
- **Fresh** means that no message precedes the window, or that its start holds under half the tokens of the message
  before it (D1). Every window below the start of a session is a compaction's, and all but one are fresh.
- **Not counted at all:** the 715 words of the two path-scoped rules, which arrive as attachments, and the tokens the
  app and its plug-ins load before the first message, which make up most of the 92,000 to 98,000 tokens at a
  session's start.
- A `Bash` command that only prints files of one class (`cat`, `head`, `tail`, `sed -n`, with `cd` and `echo`
  between) counts as those files; any other command's output counts as commands.

## The windows

The tokens are the context at the window's first message and at its first edit (or at its end, marked "no edit").

| Package | Window | Command (by the level file read) | Fresh | Project text | Instructions | Records | CLAUDE.md | Code | Commands | Tokens at start | Tokens at edit |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| WP5.19 | start | `np-plan wp` | yes | 29,996 | 4,526 | 23,140 | 2,330 | 10,915 | 32,071 | 92,913 | 419,958 |
| WP5.19 | start | `np-plan review` | yes | 13,976 | 4,269 | 7,377 | 2,330 | 3,157 | 18,785 | 97,507 | 269,370 |
| WP5.19 | start | `np-implement wp` | yes | 5,780 | 2,444 | 1,006 | 2,330 | 9,729 | 14,010 | 93,890 | 211,950 |
| WP5.19 | after compaction | `np-implement wp` | yes | 8,051 | 0 | 5,721 | 2,330 | 14,077 | 11,882 | 107,791 | 241,913 |
| WP5.19 | after compaction | `np-implement wp` | yes | 11,776 | 1,848 | 7,598 | 2,330 | 25,194 | 14,457 | 118,359 | 319,226 |
| WP5.19 | after compaction | `np-implement wp` | yes | 7,144 | 2,444 | 2,370 | 2,330 | 1,532 | 5,884 | 108,256 | 193,948 |
| WP5.19 | after compaction | `np-implement wp` | no | 11,691 | 2,796 | 6,565 | 2,330 | 0 | 15,987 | 108,839 | 237,087 |
| WP5.19 | after compaction | `np-implement wp` | yes | 7,835 | 1,415 | 4,090 | 2,330 | 247 | 12,224 | 116,073 | 212,151 |
| WP5.19 | after compaction | `np-ship wp` | yes | 7,595 | 3,613 | 1,652 | 2,330 | 847 | 19,184 | 111,954 | 252,373 |
| WP5.19 | after compaction | `np-ship wp` | yes | 5,364 | 3,034 | 0 | 2,330 | 0 | 8,410 | 110,339 | 160,303 |
| WP5.20 | start | `np-plan wp` | yes | 25,123 | 2,964 | 19,829 | 2,330 | 10,985 | 22,005 | 97,768 | 370,701 |
| WP5.20 | after compaction | `np-plan review` | yes | 10,042 | 3,760 | 3,952 | 2,330 | 468 | 12,561 | 109,795 | 209,833 (no edit) |
| WP5.20 | start | `np-implement wp` | yes | 10,456 | 2,444 | 5,682 | 2,330 | 4,567 | 13,511 | 96,404 | 249,348 |
| WP5.20 | after compaction | `np-implement wp` | yes | 10,748 | 2,443 | 5,975 | 2,330 | 17,255 | 4,344 | 108,908 | 256,080 |
| WP5.20 | after compaction | `np-implement wp` | yes | 10,970 | 4,685 | 3,955 | 2,330 | 0 | 8,223 | 115,258 | 202,092 |
| WP5.20 | after compaction | `np-implement wp` | yes | 6,887 | 0 | 4,557 | 2,330 | 6,297 | 23,603 | 115,842 | 356,848 |
| WP5.20 | after compaction | `np-ship wp` | yes | 9,360 | 4,595 | 2,435 | 2,330 | 1,391 | 6,871 | 116,387 | 194,485 |
| WP5.21 | start | `np-plan wp` | yes | 32,218 | 4,526 | 25,362 | 2,330 | 11,299 | 23,641 | 94,173 | 411,143 |
| WP5.21 | after compaction | `np-plan wp` | yes | 6,028 | 2,963 | 735 | 2,330 | 0 | 8,651 | 109,753 | 168,315 (no edit) |
| WP5.21 | start | `np-implement wp` | yes | 6,091 | 2,444 | 1,317 | 2,330 | 2,958 | 9,477 | 93,096 | 179,767 |
| WP5.21 | after compaction | `np-implement wp` | yes | 10,363 | 2,443 | 5,590 | 2,330 | 5,044 | 5,113 | 112,816 | 208,966 |
| WP5.21 | after compaction | `np-implement wp` | yes | 12,464 | 2,134 | 8,000 | 2,330 | 3,240 | 9,731 | 115,575 | 203,630 |
| WP5.21 | after compaction | `np-implement wp` | yes | 8,138 | 3,210 | 2,598 | 2,330 | 8,609 | 29,150 | 113,103 | 400,852 |
| WP5.21 | after compaction | `np-implement wp` | yes | 7,296 | 1,058 | 3,908 | 2,330 | 1,093 | 46,816 | 112,651 | 427,211 |
| WP5.27 | start | `np-plan wp` | yes | 11,774 | 3,472 | 5,972 | 2,330 | 3,682 | 41,923 | 95,112 | 377,191 |
| WP5.27 | after compaction | `np-plan review` | yes | 9,732 | 3,758 | 3,644 | 2,330 | 240 | 8,183 | 110,138 | 172,937 (no edit) |
| WP5.27 | start | `np-implement wp` | yes | 9,275 | 3,795 | 3,150 | 2,330 | 4,792 | 15,137 | 92,471 | 243,537 |
| WP5.27 | after compaction | `np-implement wp` | yes | 5,478 | 0 | 3,148 | 2,330 | 1,644 | 11,444 | 107,439 | 191,768 |
| WP5.27 | after compaction | `np-implement wp` | yes | 5,646 | 1,745 | 1,571 | 2,330 | 210 | 30,929 | 110,762 | 338,128 |
| WP5.28 | start | `np-plan wp` | yes | 16,073 | 4,773 | 8,970 | 2,330 | 0 | 27,852 | 96,288 | 258,213 |
| WP5.28 | after compaction | `np-plan review` | yes | 9,292 | 3,758 | 3,204 | 2,330 | 0 | 9,493 | 111,590 | 174,944 (no edit) |
| WP5.28 | start | `np-implement wp` | yes | 7,736 | 2,444 | 2,962 | 2,330 | 64 | 24,560 | 93,134 | 308,188 (no edit) |
| WP5.28 | after compaction | `np-implement wp` | yes | 9,383 | 1,213 | 5,840 | 2,330 | 94 | 13,696 | 102,482 | 195,569 |
| WP5.28 | after compaction | `np-ship wp` | yes | 6,828 | 3,142 | 1,356 | 2,330 | 0 | 4,193 | 105,348 | 153,099 |
| WP6.01 | start | `np-plan wp` | yes | 9,768 | 4,560 | 2,878 | 2,330 | 1,745 | 23,252 | 94,937 | 292,989 |
| WP6.01 | after compaction | `not known` | yes | 5,485 | 0 | 3,155 | 2,330 | 2,563 | 5,623 | 108,318 | 164,587 |
| WP6.01 | after compaction | `not known` | yes | 2,395 | 65 | 0 | 2,330 | 667 | 25,385 | 110,933 | 283,616 (no edit) |

## What a fresh `/np-implement` window reads

- **Project text:** 18 fresh `/np-implement` windows that reach an edit read a median of **8,095 words**, from 5,478
  to 12,464. The five that open an implementing session read a median of 7,736 (5,780 to 10,456; one of them
  reaches a compaction before its first edit); the fourteen after a compaction, which resume from the checkpoint's
  prompt, read a median of 8,095.
- **By source,** averaged over the 18: `CLAUDE.md` 2,330; files under `.claude/` 1,890 (the core with
  `np-implement/wp.md`, read together, is 2,444 where it is read); the package's plan 1,772; `clause.py`'s output
  1,192; other records 602; the review register 469; the phase plan 156; `current.md` 34.
- **Among the ten largest in at least half of them:** `clause.py`'s output (14 of 18 windows, a median of 1,192
  words) and the core with `np-implement/wp.md` (10 of 18, 2,444 words).
- **What this cleanup can shorten:** `CLAUDE.md`, `.claude/`, `current.md`, the package's plan and §8.4 hold a
  median of **78 %** of a window's project text (a mean of 71 %).
- **Context around it:** a window starts at 92,000 to 98,000 tokens, or 102,000 to 119,000 after a compaction, and
  reaches its first edit at 150,000 to 430,000. Project text is a small part of that: 8,000 words is about
  11,000 tokens. Command output (a median of about 13,000 words) and code are larger.

## The other kinds, reported

- **`/np-plan wp`**, its first window: a median of 20,598 words over six plans (9,768 to 32,218), with the design
  document, the phase plan and `clause.py` the largest; **all eleven fresh `/np-plan` windows,** reviews included: a
  median of 11,774 (6,028 to 32,218).
- **`/np-ship wp`:** four windows, a median of 7,212 (5,364 to 9,360).
- **This package's own window** (`/np-implement wp 6.02`, local transcript, before its first `Edit`): 8,897 words.
