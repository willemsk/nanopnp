# Code review 041: WP5.10's plan, the written knowledge's tools and rules

2026-11-08 · branch `claude/admiring-ride-s11d6x`, the plan commit `2e44d14` on `da395a7` · scope:
`docs/plans/wp5.10-the-written-knowledges-tools-and-rules.md`, `docs/plans/current.md`, `docs/plans/index.md` ·
focus: the plan's claims against the code, its decisions against §8.2.36 AL3 to AL7, AL14, AL24 and AL27, its
verification rows, its caps and sections · status: completed.

Static review of a plan commit (`/np-plan wp 5.10 review`, `/code-review medium --fix`). No test and no gate ran; the
review turn gates afterwards. The plan's claims were checked against the prototypes in `.claude/scripts/audit/`
(`decisions.py`, `architecture.py`, `links.py`, `index_records.py`, `scope.py`), `docs/scripts/generate.py`,
`mkdocs.yml`, `.claude/hooks/gate.sh`, `.github/workflows/ci.yml` and `tag.yml`, `CHANGELOG.md`, §5.1's table, §7.1,
§7.6, §8.4.1, Appendix A and `specification/history/index.md`. Confirmed as written: the 309 holds-now entries equal
the 309 ruling rows both ways; §5.1's 20 module rows equal the 20 subpackages; VER-78 is the highest identifier; the
29 ruff offences at `max-complexity = 15` and `max-args = 8`, one of them a test, and the 26 definitions item 1
lists; the 69 files that move and the 13 that stay; the gate's prose path, where the new check runs after
`ruff format --check`; the nine changelog paragraphs and the tags `v0.6.0-alpha.2` to `.9`. The word caps hold
before and after the fixes: 3,453 of 3,850 in all, 1,641 of 1,650 outside Grounding and Implementation
details, 956 of 1,100 in the details, and 268 of 275 in the In brief.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | High | D1; Item 5 | The prototype's `D_ROW` takes only `\| D1 \|`. Of 632 plan rows opening `\| D<n>`, it misses 158: every plan from wp41 on and all of Phase 5's, which write `\| D1 <name> \|`, this plan's `\| D1. <name> \|`, and wp42's `\| D14b \|`. Promoted as planned, the register leaves out every recent decision; the count 474 (and 1,096 kept) is the narrow one | Fixed: Grounding names the miss; Item 5 gives the widened pattern, with a letter suffix; the register holds about 1,250 rows, and the In brief says so |
| 2 | High | D4; Item 5 | `plans()` globs `docs/plans/*.md`; item 2 archives 69 plans before item 5 promotes the script, and the plan names the recursion for `duplicates.py` and `scope.py` only. The register would drop every archived plan's rows | Fixed: Item 5 reads `docs/plans/**/*.md`, skipping `index.md` and `current.md` |
| 3 | Medium | Item 2's done criterion | `links.py` promoted to read `git ls-files '*.md'` takes in `CODE_REVIEW_039/decisions.md`, which `scope.py:_own_output` left out: 984 broken relative links copied from other folders. "Names only the same two links" could not be met | Fixed: `links.py` leaves the attachments out, as `scope.py` does; Grounding records why |
| 4 | Medium | Plan, Item 5 | The quoted pointer `[decisions register](../../docs/project/decisions.md)` is a live link in the plan, resolved from `docs/plans/`: a third broken link that `links.py` would report | Fixed: the quoted link is a code span |
| 5 | Medium | Item 2 | The archive table "WP 1–6 → 0" does not say how a name's number is read; read as `wp(\d+)`, `wp5.01` to `wp5.09` parse as 5 and the live phase moves to `archive/phase-0/` | Fixed: the number is read by `^wp(\d+)-` |
| 6 | Medium | D1 grounding; Item 5 | The readers of the index's list are incomplete: `core.md`'s *Records* row ("its lines in `history/index.md`"), `rulings.md` step 2 and `project.md` step 1 read it for the rulings that bind; after the move they find a pointer | Fixed: Grounding and Item 5 name them |
| 7 | Low | Item 7 (item 6 after the swap) | The promoted `architecture.render` keeps the title "CODE_REVIEW_039: the architecture as the tree states it" and names the audit script; a Sonnet sub-agent was not told, and the site's page would carry the audit's title | Fixed: the title and first sentence are given |
| 8 | Low | Item 5 | `<` and `>` turned into entities inside code spans render as `&lt;`; the escape belongs outside code only | Fixed: masked as `generate.py` masks code |
| 9 | Low | Item 11; `CLAUDE.md` *Testing* | `CLAUDE.md` lists the architecture guards "(CON-10, CON-12, VER-61, VER-65, no backend import)"; §7.1's NOTE gains VER-79 and `CLAUDE.md` would not | Fixed: Item 11 adds it |
| 10 | Low | Item 5 | The index's pointer, copied to the site by `generate.py:rewrite_links`, resolves to a file not among the copied pages and is rewritten to a GitHub URL rather than the site's register page | No change: `generate.py` points every link from a copied page to a repository file it does not copy at GitHub, as each specification link into `docs/` resolves today; the register is on the site's Project navigation |
| 11 | Low | VER-79's first test | The guard parses §5.1's rows with a copy of `architecture.py`'s `TABLE_ROW` | Fixed in the review turn: items 6 and 7 swap, so the script moves first, and the test loads it by path and reads §5.1 with its `TABLE_ROW` |
| 12 | Low | Items 5 and 7 | Found in the review turn. The decisions page enters the navigation in item 7, two items after item 5 writes it and requires the strict build, which `validation.nav.omitted_files: warn` fails on a page outside the navigation | Fixed: item 5 adds the page's navigation entry and its row in `docs/project/index.md` |
| 13 | Low | Item 6 | Found in the review turn. `audit/architecture.py` imports `ROOT` from `scope` through `sys.path`; the Sonnet sub-agent of item 6 reads only its own details, which did not say to drop it | Fixed: item 6 sets `ROOT` as item 2 says |

AL14 counts eight Phase 5 entries; the plan moves nine because WP5.09 merged after the ruling. No change.
