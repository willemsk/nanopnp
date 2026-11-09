# WP5.11 — The specification's text and the agent instructions

**Status: in progress, items 1 to 3 done.** Planned 9 November 2026, at `69d961c`. Inherits §8.2.36 AL8 to AL12, AL14 and
AL16 to AL18 and AL21, AM1 to AM12 ruled at this plan and its review (§8.2.37), CODE_REVIEW_039's register and its scripts in
`.claude/scripts/audit/`, and REV-216 and REV-222.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md), entry WP5.11. `SPECIFICATION.md` governs; an
identifier here is a pointer, never a restatement. Where the two disagree, this plan is wrong.

## In brief

**What changes.** The specification and the instructions the project's agents follow are corrected where last
week's audit found them adrift: about 150 passages, most a stale name, count, pointer or piece of history. The
design diagram is redrawn in the order the program runs. The case-file example becomes two, each of which the
program accepts. The physics and numerics text is brought to what the program does and its tests check. Three
places where the program itself may fall short of the model are recorded as open items for Phase 6, which
compares against the published results. The agent instructions state each procedure once. History and
measurements leave the reading paths for their records.

**Cost.** About four more sessions and four to seven hours of agent work, the main work on the more capable model at
about twice the price; you act about ten times. The plan and its review took two sessions and an hour and a half.
No program change; no result moves.

**What could go wrong.** An edit could change a requirement's meaning unnoticed: each specification file's count
of requirements is compared before and after, each difference traced to a ruled finding, and the review reads
every normative edit. A move could break a link or lose a number: the link check, the strict site build and a
check that each moved measurement stands in its destination would show it. An example could stop being accepted:
the program validates each.

**Your call.** Is the reviewed plan ready to approve? *Recommendation:* yes; you ruled each choice that changes a
meaning, and the rest follow the code or a ruling.

## Execution brief

**Scope.** The 148 findings of CODE_REVIEW_039, the 147 of *Grounding* D1's lists and AUD-67, under AL8 to AL12, AL14, AL16 to AL18,
AL21 and AM1 to AM7; REV-222 (AM9); REV-216; the register's states. AM10 to AM12, the cost's units, landed
with the plan's review; item 11's changelog entry names them. **Depends on** WP5.10, merged (PR #171).
WP5.12 takes every other live finding. WP5.13 then edits §5.3.1's `models:` and `variables:` NOTEs (AL23), which
stay in place here. **Pointers:** §2; §3 (CON-05, CON-06); §4; §5.1 to §5.6; §6; §7.1, §7.2, §7.6; §8.4.1,
§8.4.4 to §8.4.6; Appendices A and B. **Implementing session:** Opus, high effort, main only (AM8); item 9's fixed edits and item 10
on Sonnet sub-agents. **No test** (§8.2.13 N1; the phase entry): each item is done when the code and review say
so, with the counts of D7.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1. The set | WP5.11 applies, whole, each live finding whose edit changes `specification/`, `SPECIFICATION.md`, `.claude/`, a root file, `docs/plans/` or `docs/project/modularity.md`: the 147 of Grounding D1's lists, and AUD-67. WP5.12 takes the rest, and by name the errata AUD-73, AUD-86, AUD-340 and AUD-341, AUD-286 (AL20's checklist) and AUD-387 by its second option | Ruled by the author (AL24's files). Decided by the plan: §4.6's evidence cells follow `knowledge/01`'s renumbering, so the errata land together |
| D2. Meaning | An edit lands without asking when it makes the text agree with the code, a clause or a ruling; removes history, a spent statement or a duplicate; or adds a pointer, title or description. AM1 to AM9 are the meaning changes. Any other change to a SHALL, a number the code or a test reads, or a decision stops the item and goes to the author. Where a finding offers two edits, Grounding D2 picks | Ruled by the author (AL21; AM1 to AM9). Decided by the plan: the test of meaning |
| D3. The ruled texts | AL9 and AL12 as their rulings word them, CON-06 as AUD-21 proposes. AL10: the diagram draws the registry's `inputs` edges, stage 9 feeding every stage; §5.2's Stage cells carry the registry names and the FR, so the two 7s are told apart. AL11: a structure case and a mesh-input case, each validated. AL8: AUD-237 to AUD-239. AL14: five restatements point at `CONTRIBUTING.md`. AL16: `CLAUDE.md`'s line | Ruled by the author (AL8 to AL12, AL14, AL16) |
| D4. Where a moved text goes | AUD-113's parts (3) to (5) and AUD-82 go to §5.2's design notes for stages 7, 1 and 2–3; part (8) to a new §5.3.5. AUD-119's argument goes to `knowledge/04/02` §2.2, the AUD-244 narratives to `phase-5-record.md`, and *The pause* to `np-plan/SKILL.md`. A measurement leaves a NOTE only once its destination concept holds it. AUD-143's and AUD-32's pending NOTEs stay beside their clauses and state the change. The core's *The In brief* and *Putting a choice to the author* go to `.claude/workflow/author.md` | Ruled by the author (AL17, AL18, AM9). Decided by the plan: AL17 homes a rule at its clause, and the design document names those NOTEs the home, so AUD-143's row is applied in place, not moved |
| D5. The gaps | REV-223 (PHY-07's density continuity, high), REV-224 (NUM-28's `ρ_pore E`, medium) and REV-225 (three underived tolerances, low), each `accepted`, owned by Phase 6. NUM-04 states the assembled flow forms with a NOTE naming REV-223, and NUM-28 a NOTE naming REV-224. REV-216 `fixed`; REV-222 `fixed` | Ruled by the author (AM2, AM9) |
| D6. The records | One commit per item, its AUD ids in the body; item 11 adds one `fix:wp511-<item>` row per finding to `raw/dispositions.tsv`, one row per category to `raw/commits.tsv`, and re-runs `register.py` and `maps.py`. AUD-67 is fixed by this plan's commit. `holds-now.yaml` names the clauses for AL8 to AL12, AL14 and AM1 to AM9, and leaves AL16 to AL18 and AL21 open for WP5.12. Changelog `[0.6.0-alpha.11]` | Decided by the plan: CODE_REVIEW_039 section 11, as WP5.10 recorded AUD-251 |
| D7. The counts | SHALL counts per specification file before item 1 and after item 7, each difference traced to a finding. `clause.py` over every identifier of Appendix A and every ruling letter. The §5.3.1 examples validated. `links.py`, `duplicates.py`, `decisions.py --check`, the strict build | Decided by the plan, after AL29: an edit whose failure is silent gets a count |

### Grounding

**D1.**
- `docs/code_reviews/CODE_REVIEW_039/findings.md` (at `3427617`) holds 312 findings `your call`; *Where* gives
  `a5039af`'s lines. A finding's evidence and full lists are its reader's row in `raw/reader-<src>.md` (SPA-19's
  40 citations, for example). At `69d961c` all 148 still stand. Moved or reworded, so the edit is adapted:
  AUD-60, 83 (the NOTE labels carry clause ids since `f03d05a`; AUD-83's moved NOTEs relabel to PHY-19), 244,
  246, 256, 257, 259, 263 to 265, 268, 272, 273, 279, 280, 373, 375 to 377, 379, 383. Half done: AUD-245 (the
  date chain remains), AUD-247 (the four sections are unnamed), AUD-378 (only P₂'s unit; §4 states
  `d̄ = d / (1 nm)` at PHY-11).
- List 1, item 1: AUD-17, 19 to 47, 203, 375 to 377, 379.
- List 2, item 2: AUD-50 to 60, 65, 66, 68 to 72, 74 to 78, 81 to 85, 87, 89, 209, 378.
- List 4, item 4: AUD-96 to 100, 107 to 111, 119, 121, 122, 318, 324, 373, 374.
- List 5, item 5: AUD-49, 102, 103, 106, 112 to 118, 123.
- List 6, item 6: AUD-128 to 132, 134 to 137, 140 to 151, 380, 381.
- List 9, item 9: AUD-252 to 254, 256, 257, 259, 262 to 266, 268, 272 to 274, 276 to 280, 383.
- List 10, item 10: AUD-237 to 239, 244 to 247.
- WP5.12's by D1's rule: AUD-61 to 64, 90, 91, 94, 95, 307, 384 to 386, and every KGE, KNU, KST, KPH and DOC row
  not listed.

**D2.**
- AM1's twelve and what pins each. NUM-16: `numerics/newton.py` (floor 10⁻¹², growth ×2, `rtol` on the per-field
  update). NUM-17: `newton.py` and `numerics/gates.py` (cut, abort at the minimum damping). Each finding's
  reader row names the test that pins it (`raw/reader-spb.md`), such as `test_newton.py` or
  `test_knowledge_arithmetic.py` (Re). NUM-09:
  `physics/coefficients.py` (L₀ = 1 nm, others refused). PHY-12: `test_corrections.py` (0.3790). PHY-13: the
  concentration is clamped and the fit read at 5.3 M. PHY-22: `io/defaults.py` `SWITCH_PATHS`, where an omitted
  `electrolyte.corrections` is `none` and a deviation. The rest: Re 6 × 10⁻⁴; NUM-26's 4 × 10⁻⁶; NUM-30's
  `min(0.05 nm, λ_D/5)`; Na⁺ 1.21–1.67 and Cl⁻ 1.13–1.28 × kT/e (`knowledge/01/03` §3.0); Pe 0.385 at ε_r 78.15.
- Picks: AUD-22 FR-24; AUD-28 delete; AUD-46 letter FR-30 (a)–(d), FR-39 (a)–(f); AUD-81 "(observed on 3.7.1)";
  AUD-84 the producer path conserves by construction, no new SHALL; AUD-130 the nightly floor; AUD-135 reword;
  AUD-136 "(inactive)"; AUD-140 and AUD-145 in `07-verification/index.md`; AUD-149 front matter on the 05, 07 and
  08 indexes; AUD-150 VAL-11 to FR-21 and FR-22, VAL-12 to VAL-14 unmet; AUD-257 grill follows *Putting a
  choice to the author*, reading `author.md` (item 9's E5 first); AUD-259 §8.4.4 says WP5.15; AUD-373 each §5.2 row names its FR; AUD-381 a test-file
  column in §7.3.

**D3.**
- `core/stages.py`, in registration order with `inputs`: case 9 (`case_path`); structure 1; protonation 7
  (structure); density 2 (structure, protonation); symmetry 3 (density); contour 4 (structure, symmetry); region 5
  (contour); mesh 6 (region); charge 7 (mesh, protonation, region); materials 8; solve 10 (charge, materials,
  mesh); qoi 11 (charge, mesh, solve); report 12 (charge, mesh, qoi, solve). Every stage after 9 also reads
  `case`. §5.1 draws 9 last, fed by 6 to 8; §5.2's stage-9 row emits an "assembled discrete problem".
- VER-79's `TABLE_ROW` matches only `` `name/` `` rows, so AUD-100's `case.py` row leaves it unchanged. `gui/`
  still reads "Desktop application"; AUD-100's item writes the workbench (AF4).
- §5.3.1's example is refused for `inputs.mesh` beside `structure:` and for `geometry.analyte` on a generated
  mesh; without both it validates. `examples/05-clya-reference/clya-0.5M-plus50mV.case.yaml` is a mesh-input
  case that validates.
- CON-06 says "behind a thin internal interface", as do §5.4.1's lead and the `04` description; the `06`
  description and ADR-001 say "behind the abstraction of §5.4.1"; the §5.4.1 NOTE states H3. The phase plan's verification row allowed AL9 alone; this commit adds AL12
  and AM1 to AM5.
- `CLAUDE.md` *Before doing anything*: "The concepts under `knowledge/01-physics-epnpns/` are normative."
- AL14's restatements: `core.md` *Two lanes*; `np-implement/wp.md`'s changelog bullet; `np-ship/wp.md` §1 and its
  tag paragraph; `np-ship/phase.md` step 1; `np-plan/rulings.md` *Versions agree*.

**D4.**
- AUD-113's eight parts, by NOTE label at `69d961c`: (1) `nanopnp/case/v0.6`; (2) `charge.ph`; (3) a relative
  path; (4) `structure:`; (5) `geometry.pore`'s binning paragraphs; (6) a group that claims itself; (7) a solid
  without a permittivity; (8) the project.
- A §5 file is listed by hand in `05-software-design/index.md` and `SPECIFICATION.md`'s map; `docs/scripts/generate.py`
  writes `mkdocs.yml`'s navigation from the files.
- `knowledge/04-clya-geometry-and-charge/02-model-geometry-and-conventions.md` §2.2 is the exclusion shell's
  concept. `phase-5-record.md` holds dated sections; REV-216 is the plan over its word target.
- `np-plan/SKILL.md` step 4 reads `review.md` on every call; four level files say "as `review.md`'s *The pause*
  says". No hook reads it.
- The design document's *Restated clauses* says each restatement is a NOTE beside its clause.
- REV-222: C2, identifiers cited bare in `.claude/skills/` and `.claude/workflow/`; C3, the push procedure in
  `CLAUDE.md`, `core.md`, `steward/SKILL.md`, `hosts/copilot.md`, `np-ship/wp.md`, and the two-lane rule in
  `CLAUDE.md`, `core.md`, §8.4.4 and three skills; E5, `/np-ship wp`'s step 4 uses *Putting a choice*, and every
  PR body uses *The In brief*; E6, `AGENTS.md`'s first line is `@CLAUDE.md`, and `hosts/copilot.md`'s table says
  so.

**D5.**
- The coupled flow residual, `physics/models.py`, assembles the viscous and pressure terms;
  `continuity_term` with `mass_density`, `−∫ q ϱ̃ d̂iv ũ r` (PHY-07's velocity continuity); `inertia_term`,
  `Re ∫ ϱ̃ (ũ·∇)ũ·v r`, under `inertia`; and the body forces. No term carries `u·∇ϱ`, the reference's
  `(u*d(spf.rho, r) + w*d(spf.rho, z))*test(p)` (`knowledge/09-…/04-physics-settings.md`). NUM-04 states constant-density
  Stokes.
- The highest REV is REV-222. A row is
  `| REV-nn | area | severity | status | source | [title](review-items.md#anchor) |` with a section.

**D6.**
- `raw/dispositions.tsv` is `id<TAB>status<TAB>note<TAB>extra_where`, keyed by the reader id (`SPA-05`);
  `raw/commits.tsv` is `category<TAB>sha`. `register.py --at <sha>` writes `findings.md`; `maps.py <sha>` writes
  the map and the list.

**D7.**
- `clause.py` takes many identifiers and exits non-zero on any it cannot define.

### Implementation details

**Item 1.** CON-05 reads as AL9 states; §2's phrase: "ion-specific rather than mean-concentration-driven
property models". CON-06 reads AUD-21's text. Count first, into a scratch directory `$S`:
`for f in SPECIFICATION.md specification/*.md specification/0*/*.md; do echo "$f $(grep -o SHALL "$f" | wc -l)"; done > $S/shall-before.txt`.

**Item 2.** NUM-04 gains, under the flow form, `+ ∫ ϱ (u·∇)u·v r dr dz` under `physics.inertia` (`ϱ₀` with
`physics.variable_density` off) and the
continuity row `−∫ q ϱ d̂iv u r dr dz` under `physics.variable_density`, with "constant-density Stokes is both
off". Then: "NOTE (NUM-04, PHY-07; §8.2.37 AM2): PHY-07's density continuity, the reference's hand-added
`∫ (u·∇ϱ) q r dr dz`, is not assembled, so the assembled `ϱ (u·∇)u` is PHY-07's `(u·∇)(ϱu)` only where
`u·∇ϱ = 0`. REV-223, measured in Phase 6." NUM-28: "NOTE (NUM-28; §8.2.37 AM2): where
PHY-16 deposits charge in the fluid, `∇·T_M` also carries `ρ_pore E`, which the consistency terms omit. REV-224,
Phase 6." The REV rows: REV-223 physics, high; REV-224 numerics, medium; REV-225 numerics, low (the floor
10⁻¹², the cap `V_T`, NUM-08's deviation); each `accepted`, source CODE_REVIEW_039, its section saying what to
measure. The commit re-runs `decisions.py` for the REV rows (the core's *Gate and push*). A fact moved into a
`knowledge/` concept keeps its marker and adds a `knowledge/log.md` line, here and at item 4.

**Item 4.** Draw each edge of Grounding D3 once. Stage 9 stands first with one line, "feeds every stage". Name
each box `[n name]`. `gui/`: "The browser workbench (NiceGUI, `gui/web/`), and the PySide6 shell until WP5.21". The commit hook runs no
pytest on a Markdown-only commit, so run VER-79 by hand: `uv run pytest tests/tier1/test_written_architecture.py`.

**Item 5.** Example A is today's block less the `inputs:` key and its live lines (the `profile` and `pqr`
comments kept as comments; an `inputs:` with only comments is null and refused),
`analyte:` and `analyte_force`. Example B, after it, under "A case that takes a supplied mesh": `schema`, `name`,
`inputs` (`mesh` with its groups, `charge`, `eps_r`), `electrolyte`, `boundary_conditions`, `physics`, `numerics`
less `mesh:`, and `outputs` less `analyte_force`. Check each: write it to `$S/<a|b>/case.yaml`, `touch` each path
it names, and run `uv run nanopnp validate case $S/<a|b>/case.yaml`, which exits 0.

**Item 7.** Count after: re-run item 1's loop into `shall-after.txt`; `diff` the two. Clause check:
`uv run .claude/scripts/clause.py $(grep -ohE '\b(IF|FR|QR|CON|PHY|NUM|VER|VAL|ADR|RSK|OPN)-[0-9]+\b' specification/a-traceability-matrix.md | sort -u) $(grep -ohE '^\| *[A-Z]{1,2}[0-9]+\b' specification/history/*.md | tr -d '| ' | sort -u) > /dev/null`.

**Item 9.** `CLAUDE.md`'s line: "§4 of `SPECIFICATION.md` states the model's equations and governs them; the
concepts under `knowledge/01-physics-epnpns/` back it." `AGENTS.md` loses `@CLAUDE.md`, and its sentence the clause on that import;
`hosts/copilot.md`'s row follows. `author.md` takes the two core sections verbatim; the core points to it; each
level and `np-ship/wp.md` step 4 read it where they write an In brief or put a choice. C2: an identifier cited
alone gains its words first, as the core requires. C3: §8.4.4 holds both rules (AL17). The push's mechanics
stay in `CLAUDE.md`'s *Commands* and, for Copilot, `hosts/copilot.md`; `core.md`'s *Gate and push* keeps the
order and points to them; `steward/SKILL.md` and `np-ship/wp.md` point to the core. `core.md`'s *Two lanes*
keeps a session's conduct and points to §8.4.4; `CLAUDE.md` and the skills point to the core.

**Item 11.** A disposition row: `SPA-05<TAB>fix:wp511-spec-1-3<TAB>WP5.11 item 1 (§8.2.36 AL9)<TAB>`. One
category per item: 1 `wp511-spec-1-3`, 2 `wp511-spec-4-6`, 4 `wp511-spec-5`, 5 `wp511-spec-5-3`, 6
`wp511-spec-7-12`, 9 `wp511-agents`, 10 `wp511-plans`; AUD-67 is `wp511-rulings`, this plan's commit. AUD-52, 56
and 69 are fixed by their NOTE and REV row. Then `uv run .claude/scripts/audit/register.py --at HEAD` and
`uv run .claude/scripts/audit/maps.py HEAD`.

### Work items

- [x] 9c11662 1. `SPECIFICATION.md`, `specification/01` to `03` (D1 to D3): list 1, CON-05, CON-06; the SHALL count
  before; done when the code and review say so and the strict build passes. **Executor:** main
- [x] 0c9e3d2 2. `specification/04-physics.md`, `06-numerics.md`, `.claude/rules/physics-numerics.md`,
  `knowledge/06-numerics-fem/04-stabilisation.md`, `docs/project/review-findings.md`, `review-items.md` (D2, D4,
  D5): list 2, AM1's twelve, the two NOTEs, REV-223 to REV-225; done when the code and review say so and each
  measurement cut from a NOTE stands in its concept. **Executor:** main
- [x] 3. Compaction checkpoint. **Executor:** main
- [x] c9e43f4 4. §5.1, §5.2, §5.4 to §5.6, `knowledge/04-clya-geometry-and-charge/02-model-geometry-and-conventions.md`,
  `knowledge/07-software-stack/01-fem-backend-ngsolvenetgen.md` (D3, D4): list 4, AL10, AL12; done when each diagram edge is a registry
  edge and VER-79 passes. **Executor:** main
- [x] 8118ca8 5. §5.3.1 to §5.3.4 and the new `03-5-project-folder.md` with its three listings (D3, D4): list 5, AL11,
  AUD-113's moves; done when both examples validate and the strict build passes. **Executor:** main
- [x] 4d3efd8 6. §7 to §12 and the appendices (D2): list 6, AM3, AM5, and AM4's end states as a §8.4.6 bullet; done when
  the code and review say so.
  **Executor:** main
- [ ] 7. The counts (D7); done when every SHALL difference is traced to a finding and the clause check exits 0.
  **Executor:** main

  > **Outcome — 526 SHALLs before, 517 after, each difference traced.** §3 −4: CON-06's reach clause +1
  > (AUD-21), five SHALLs of the pending CON-08, CON-09 and CON-11 restatements −5, now stated as changes
  > (AUD-32). §4 −4: step 3's three NOTEs to §5.2 (AUD-82), the producer-path SHALL (AUD-84). §5.2 +27:
  > those three, and 24 moved from §5.3.1 (AUD-113). §5.3.1 −27: the 24, and three spent refusals of a walk
  > past an undelivered stage (AUD-113). §6 0: NUM-16's cut +1 (AUD-51), NUM-31's −1 (AUD-65). §8.1 −1: the
  > spent Phase 2 SHALL (AUD-147). The clause check over Appendix A's identifiers and every ruling letter
  > exits 0; both §5.3.1 examples validate; `links.py`, `duplicates.py`, `decisions.py --check` and the
  > strict build pass.
- [ ] 8. Compaction checkpoint. **Executor:** main
- [ ] 9. `.claude/`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `README.md` (D3, D4): list 9, AL14, AL16, AM4,
  REV-222's four; done when `links.py` passes and each changed procedure is stated in one file. **Executor:**
  main for AM4, AL16 and REV-222's four, which move and reword rules; list 9's fixed edits and AL14's pointers
  go first to `general-purpose` on Sonnet, and main reads its diff
- [ ] 10. `docs/plans/phase-5/`, `docs/project/modularity.md` (D3, D4): list 10, AL8, REV-216; done when
  WP5.01 to WP5.10 read as title, merged line and live constraints, the record holds each narrative
  byte-identical, and `links.py` passes. **Executor:** `general-purpose` on Sonnet
- [ ] 11. The records (D5, D6): the dispositions, commits and register; `holds-now.yaml`; REV-216 and REV-222
  `fixed`; `decisions.py`; `CHANGELOG.md`; done when no finding of the lists reads `your call` and
  `decisions.py --check` passes. **Executor:** main
- [ ] 12. The Outcome, both Status lines, `current.md`, the PR body; done when the code and review say so.
  **Executor:** main

### Verification

No test is in scope (§8.2.13 N1; the phase entry). The checks, at items 7 and 11 and before the push:

```bash
uv run .claude/scripts/links.py
uv run .claude/scripts/duplicates.py
uv run .claude/scripts/decisions.py --check
uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict
```

with item 7's SHALL diff and clause check, item 5's two validations and item 4's VER-79 run. The push gate
runs VER-79 again.

### Out of scope

- WP5.12: every other finding, AL13, AL15, AL19, AL20's checklist (AUD-286 with it) and the errata.
- Phase 6: REV-223 to REV-225's measurements and any code they call for. WP5.13: §5.3.1's `models:` and
  `variables:` NOTEs (AL23). Any change under `src/`, `tests/` or `data/`.

### Open questions

None blocks the work.
