# Code review 043: WP5.11's plan, the specification's text and the agent instructions

2026-11-09 · branch `claude/sleepy-carson-oomrxu`, the plan commit `a1dfe59` on `69d961c` (head `17ebf87`, a merge
that keeps the plan's tree) · scope: `docs/plans/phase-5/wp5.11-the-specifications-text-and-the-agent-instructions.md`,
`specification/history/37-wp511s-plan-the-specification-against-the-code.md`, `holds-now.yaml`, the Phase 5 plan and
record, `current.md`, `docs/plans/index.md`, `docs/project/decisions.md` · focus: each claim about the code checked
at this head, each decision against the specification and §8.2.36 and §8.2.37, each check for how it gets the
object it checks, the plan against `.claude/skills/np-plan/wp.md`'s sections and caps · status: completed.

Static review (`/code-review medium --fix`). No test and no `gate.sh` ran; the review turn gates. Probed: the stage
registry (`core/stages.py`) matches Grounding D3 edge for edge; `NewtonSettings` has the floor 10⁻¹², the growth ×2
and the per-field update test, and an increment-gate violation cuts the damping and re-raises at the minimum;
`physics/coefficients.py` refuses a length other than the 1 nm mesh unit; `CorrectionChoice.model` defaults to
`none`; `mesh/sizing.py` has `min(0.05 nm, λ_D/5)`; `test_corrections.py` pins 0.3790; VER-79's `TABLE_ROW`
matches only `` `name/` `` rows; `validate case` checks that each named file exists and resolves without reading
them; item 7's clause command, run as written, exits 0 over Appendix A and 320 ruling letters. The lists of
Grounding D1 hold 147 distinct findings, none twice. Before the fixes the plan held 2,863 words, 1,500 outside
*Grounding* and *Implementation details* and 440 inside the latter; after the review's fixes 2,992, 1,521 and 514, and after the review turn's three, 3,100, 1,557 and 584 by `wc`'s
count with headings, within the caps (3,850, 1,650 and 1,100).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | *Verification*; item 4 | "VER-79 runs in the gate" is false for item 4's commit: a Markdown-only commit is prose to `prose-only.sh`, and the commit hook then runs no pytest, so a §5.1 table row broken at item 4 passes until the push | Fixed: item 4 runs `uv run pytest tests/tier1/test_written_architecture.py`; the push gate runs it again |
| 2 | Medium | Item 2; D6 | Item 2 adds REV-223 to REV-225, but the plan runs `decisions.py` only at item 11; the commit hook's decisions check refuses item 2's commit | Fixed: item 2 re-runs `decisions.py` |
| 3 | Medium | Item 6, item 9; `holds-now.yaml` AM4 | AM4 holds at "§8.4.6, `/np-ship phase`", but no item edits §8.4.6: item 9 names only `.claude/` files, and item 6, whose range holds §8.4, lists AM3 and AM5 alone. The record would say the ruling holds where the text does not | Fixed: item 6 writes AM4's end states as a §8.4.6 bullet, inside the SHALL count |
| 4 | Medium | Item 9's executor | Item 9 goes to a Sonnet sub-agent, yet it carries AM4's close check, AL16's line in `CLAUDE.md` and REV-222's C3 and E5, which choose one home per procedure and move two core sections. `np-plan/wp.md` keeps an item that needs judgement on normative text in the main session | Fixed in the review turn: AM8's option sent "the mechanical items" to Sonnet and kept on Opus the edits that move or reword a rule, so item 9 is main for AM4, AL16 and REV-222's four, and list 9's fixed edits and AL14's pointers go first to Sonnet; item 9's details name C3's homes (§8.4.4 holds both rules, AL17) |
| 5 | Medium | Implementation details, item 9 | `AGENTS.md` "keeps its sentence and loses `@CLAUDE.md`", but the sentence reads "If your agent does not expand the `@CLAUDE.md` import above": it would point at an import that is gone | Fixed: the sentence loses its clause on the import |
| 6 | Low | Implementation details, item 5 | "Less the live `inputs:` lines (the comments kept)" leaves `inputs:` with only comments, which YAML reads as null and `CaseDocument.inputs` refuses | Fixed: Example A drops the `inputs:` key; the two comments stay as comments |
| 7 | Low | Implementation details, item 2 | NUM-04's inertia row reads `∫ ϱ (u·∇)u·v`; with `physics.variable_density` off the code passes `mass_density=1.0`, so the row carries `ϱ₀`, not the corrected `ϱ` | Fixed: the row names `ϱ₀` for that case |
| 8 | Low | Implementation details, item 2's NOTE | With density continuity not assembled, `u·∇ϱ` need not vanish, so the assembled `ϱ (u·∇)u` also differs from PHY-07's `(u·∇)(ϱu)`; REV-223's NOTE names only the missing weak term | Fixed in the review turn: the NOTE adds that the assembled `ϱ (u·∇)u` is PHY-07's `(u·∇)(ϱu) = ϱ (u·∇)u + u (u·∇ϱ)` only where `u·∇ϱ = 0`. It names a second consequence of the gap AM2 ruled into REV-223 and changes no ruling; `physics.inertia` is on by default, so it applies on the default path |
| 9 | Low | Items 2 and 4 | Measurements and AUD-119's argument move into `knowledge/` concepts with no `knowledge/log.md` line (`CLAUDE.md`, *Durable learnings*: "Add a line to `knowledge/log.md`") | Fixed: item 2's details require the marker kept and a log line, at items 2 and 4 |
| 10 | Low | Execution brief; D1 | "The 148 listed under *Grounding*": the lists hold 147; the 148th is AUD-67, closed by this commit | Fixed: both say 147 and AUD-67 |
| 11 | Low | Grounding D3 | The plan says the `06` description and ADR-001 say "behind a thin internal interface"; they say "behind the abstraction of §5.4.1" | Fixed |
| 12 | Low | Grounding D4 | `mkdocs.yml`'s navigation is listed beside the index and the map as a place a new §5 file is added; `docs/scripts/generate.py` writes it | Fixed: the two hand-listed places named, the navigation generated |
| 13 | Low | Grounding D5 | The reference's weak term is quoted as `d(rho,r)`; the knowledge base has `d(spf.rho, r)` | Fixed |
| 14 | Low | Grounding D2 | AM1 rewrites a passage "where a test pins it", but the grounding names code modules for NUM-16, NUM-17, NUM-09, PHY-13 and PHY-22 and no pinning test for "the rest" | Fixed: each finding's reader row names its pinning test, with two examples |
| 15 | Low | `docs/project/decisions.md` | AM6 and AM7, ruled 19 October 2026, are dated 2026-11-09 there, because `decisions.py` dates a row by its history file | Fixed in the review turn: `decisions.py` dates a row that opens *Ruled <date>* as it dates one that opens *Added <date>*, and `np-plan/rulings.md` states the form; AM6 and AM7 now read 2026-10-19 |

The decisions page is re-rendered for D1's new wording and for AM6 and AM7's dates.
