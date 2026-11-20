# Code review 066: the sixth Phase 5 amendment, every open item placed

2026-11-20 · branch `ccr-b14869a5-8mshj5`, the plan commit `8847925` on `d62c609` · scope: the commit's 61 files. The
Phase 5 plan's status, In brief, design decisions, WP5.21 to WP5.28, open decisions, supply rows and verification table;
the record's new *Amended 20 November 2026* section; §8.2.46 and its `holds-now.yaml` lines; §8.3's shell row; the
review register's placements; and the renumbering across the tree. Checked against the code at this head:
`gui/web/tools.py:_plain`, `api/project.py:_error_path`, `gui/web/physics_tools.py:problem_path`, `post/fields.py:field_at`,
`gui/web/molview.py`'s representations, `structure/stage.py:align`, `.claude/scripts/gui/redraw.cjs`'s flags, NiceGUI's
shipped chart elements, and the raise sites per subpackage · level: medium, with `--fix` · status: completed.

Static review: no `gate.sh` and no test run; the review turn gates afterwards.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `docs/plans/phase-5/phase-5-record.md`, the amendment's quoted status | The old status's "WP5.22, WP5.23 and the close" was renumbered to "WP5.24, WP5.26 and the close". The old WP5.23 there is the route, which AV4 renumbers to WP5.27; WP5.26 is the polish pass, which did not exist | Fixed: "WP5.24, WP5.27 and the close" |
| 2 | Important | Phase 5 plan, WP5.25 | The entry says *every* refusal left follows FR-35's NOTE, but names only `mesh/`, `geometry/`, `charge/`, `density/`, `structure/`, `numerics/`, `solve/`, `post/` and `sweep/`, about 440 raise sites at this head. `physics/` (39), `materials/` (20, among them `electrolyte.py`'s unknown correction driver), `core/` (22), `symmetry/` (3) and `api/` beyond `project.py` (26) hold the other 110 of REV-254's "about 550", and no package took them | Fixed: the entry names them; REV-254's placement says so. §8.2.46 AV1's consequence keeps its list of nine; the plan states the scope that FR-35's NOTE asks |
| 3 | Important | `docs/plans/sessions/copilot-host.md` | AV6 rules that the Copilot host's session plan owns REV-166 to REV-168 and runs before the close. The register's rows point to the plan, but the plan was not changed: it never names REV-167, the close or the hand-run gate meanwhile | Fixed: a paragraph under its header states the ownership, the deadline and the carry |
| 4 | Nit | Phase 5 plan, verification row of WP5.25 | The row checks "a refusal opens its field by its case path" through VER-78's `refused` state. That state holds one refusal of the layers WP5.18 already rewrote; no test reaches a refusal of the modules WP5.25 rewrites, or any of the three readers that must stop parsing words | Fixed: a mesh gate's refusal, raised in a Tier 1 test, carries its case path and file as fields (a numerical gate, within N1's scope); VER-78's `refused` state holds a refusal WP5.25 rewrites and opens its field by the path; the three readers' reading of the fields is checked at review (N3) |
| 5 | Nit | Phase 5 plan, verification row of WP5.27 | "A new model of each kind resolves and keys as an imported one" cites FR-39, the study's overrides and sweeps; a project's named models are FR-32 | Fixed: FR-32 |
| 6 | Nit | `specification/history/43-…md` description and its index line | AV4 keeps §8.2.43's descriptions at their numbers, yet the description's performance clause moved from WP5.22 to WP5.24, so it now says the performance package is WP5.24 and the packages were renumbered "WP5.21 to WP5.24", in which WP5.24 was the close | Fixed by the review turn: AV4 names §8.2.43's descriptions and the record's paragraph of 18 November among the sentences that keep their numbers, whole. The description, its index line and the record's paragraph say WP5.22 again; AS2's row, a ruling, keeps WP5.24 |
| 7 | Nit | Phase 5 plan, whole | `phase.md` sets a target of 1,500 words without the report (§8.2.11 L7). The plan stood at 7,015 words and the amendment brings it to about 8,200: the delivered packages' entries stay in full | Fixed in part by the review turn: the narratives of WP5.12 to WP5.21 moved verbatim to `phase-5-record.md`, as AL18 ruled for WP5.01 to WP5.11, each entry keeping its title, merged line and live constraints: 8,206 words to 5,133. The rest is live; cutting it or restating the target is the author's, REV-271 |
| 8 | Nit | Phase 5 plan, In brief, *Your call* | The template asks each decision as a question with a recommendation and one reason. The Copilot checks ("whenever suits you, before the close") and the colleague carry neither | Fixed by the review turn: each item is a question with its recommendation and reason; the first paragraph trimmed to hold 273 words |
| 9 | Nit | `specification/history/holds-now.yaml`, AJ8 | The plan opens WP5.22, WP5.23 and WP5.26 with a round under AJ8, while AJ8 holds "open: WP5.15 to WP5.21", and AJ8 rules suite packages | Fixed by the review turn: the three entries cite §8.4.4, whose "a package that changes a screen uses it" governs their rounds; AJ8 keeps its reach, the suite packages |

Checked and found true: WP5.21 merged and only `v0.6.0-alpha.19` published among the v0.6 tags; the three place
readers exist where the plan names them, and read places from words; `post/fields.py:field_at` reads linearly on the
split, as REV-270 says; Molecular's and Meso's views draw through `molview.py`'s representations; NiceGUI ships
`plotly` and `echart`; `redraw.cjs` has `--headed` and `--trace` and picks only on the charge map, which WP5.24
extends; `structure/stage.py:align` exists for WP5.23's variation; every review row not `fixed`, `declined` or
`wontfix` (54) names a package, a provisional Phase 6 package, a later phase, post-1.0 or the Copilot session plan;
§8.3's shell row counts WP5.15 to WP5.28, 14 packages at six sessions; §8.1's 18 packages from WP5.11 sum to it; the
In brief holds 273 words and `current.md` 700; no `.py` file or test names an old number.

Nine findings: three important and five nits fixed, one nit fixed in part with REV-271 for its rest. None changes a ruling of the author.
