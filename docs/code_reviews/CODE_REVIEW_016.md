# Code review: PR 130, WP5.01, the workbench design study

27 October 2026 · `2584fc7..8919806` (`ccr-fcb7bed5-l8xniv`) · effort: xhigh, with `--fix` · status:
completed

**Scope.** This was a static review. It covered `specification/` (FR-31 to FR-43 and QR-16; the
NOTEs beside P3, IF-09, QR-10, CON-09, ADR-004, RSK-13, VER-43, VER-44, VER-55, VER-60 and PHY-16;
§8.2.18, §8.2.19 and their pointers), `SPECIFICATION.md`, `CLAUDE.md`, `pyproject.toml` and
`mkdocs.yml`. It also covered `docs/design/workbench.md`, `docs/design/tokens.css`,
`docs/design/reviews/`, the WP5.01 plan, the Phase 5 plan, `current.md`, the REV and MOD rows and
sections, `knowledge/`, `CHANGELOG.md`, `.claude/scripts/gui/`, `.claude/skills/` and
`.claude/agents/`. The generated or superseded folders `docs/design/{generators,mockups,choices,
concepts,style}/` were read only to check a claim made in a file in scope.

## Summary

The package does what its plan says: tools, a design round, panels and mockups, the design document,
and the restated clauses. The checks of the plan's Outcome annotations hold, with one exception: the
counts of grabs, capabilities, findings, picks, shots, clauses and rows match what was delivered, but
the mockups' verdict counts do not. The 21 picks in the review record, and the choices
`workbench.md` makes from them, match the gallery's stored `verdicts` exactly; they were read back
with `ArtifactData`. Every ruling T1 to T8 and U1 to U5 is in the register or clause it names.
FR-31 to FR-43 and QR-16 are unique and each has its Appendix A row.

The defects found:

- **The render tools.** The shooter's self-check, which is the plan's oracle that "the shooter
  loads a WebGL page", cannot fail on a scene that does not draw. Its contrast check never reaches
  the SVG labels the mockups use.
- **Physics.** The NOTE written for U2 chooses the density's radii, which no ruling chose, and leaves
  out the Tier 2 golden that the change moves.
- **Requirements.** FR-39 contradicts that NOTE.
- **The history index.** It still lists eight rulings as open on WP5.01.

## What was fixed and what was run

Thirteen findings are fixed in the working tree, uncommitted; two are left to the author. Only fast
commands were run:

- `node --check` on the shooter;
- the edited shooter on one mockup page and on a host document whose renderer path was broken;
- the shooter's self-check (it passed, with `viewer.ready` true);
- `ruff check` and `ruff format --check` on `.claude/scripts/gui/`;
- `duplicates.py` and `clause.py FR-39`.

No test, gate, sweep or documentation build was run.

| Severity | Count |
|---|---:|
| High | 2 |
| Medium | 7 |
| Low | 6 |

## Findings and their outcome

| # | Location | Finding | Outcome |
|---|---|---|---|
| 1 | `.claude/scripts/gui/shoot.cjs`, `selfCheck`; `render.md` | `host_document` wraps `scene.init` in `try`/`catch`. A renderer that never arrives, or a WebGL context that fails (the "did not draw" case of item 1's Outcome), therefore sets `window.__nanopnp_viewer.error` and raises no page error. The self-check tested `page_errors` alone, so it passed on a blank page. The same blindness hid a blank HTML stand-in in `/np-gui render qt`. Reproduced: a host document with its renderer path broken gave no page error and `{ready: false, error: "ReferenceError: webgui is not defined"}`. | Fixed: each shot records `viewer`, the host document's flag. The self-check requires `viewer.ready`, and `render.md` treats an unready scene as a page error. |
| 2 | `specification/04-physics.md`, the NOTE for §8.2.19 U2 | "PDB2PQR's atoms with their PQR radii" chooses the density's radii, and U2 did not rule that. §5.3.1's `gaussian_vdw` NOTE (an author ruling) takes CHARMM Rmin/2 by residue and atom name. `charge.forcefield` also admits PEOEPB and SWANSON, whose PQR radii differ. The density, the contour and the mesh would then depend on the charge force field. | Fixed: each atom takes "the radius the §5.3.1 NOTE on `geometry.density` takes for it". Under the default, CHARMM, the radii are the same. |
| 3 | `specification/03-requirements.md`, FR-39 | "Assemble each molecular model on a shared mesh without rebuilding it" contradicts the U2 NOTE, under which a protonation state or a charge-level variant moves the density, the contour and the mesh. WB-11 asks for the reverse direction: one molecular model serving many continuum runs. | Fixed: a study reuses each built model without rebuilding it. It rebuilds only the stages that a changed value or a molecular variant moves, citing U2. |
| 4 | `specification/04-physics.md`, the same NOTE | The NOTE lists what U2's package amends but not VER-62. VER-62's golden pins example 07 and the charged 2WCD walks by the deployed mesh's hash. A protonated density moves those meshes, an unseen mesh fails in the reference environment, and VER-62 requires a ruling that re-pins the golden (§8.2.7 G10). | Fixed: the package re-pins VER-62's golden for each walk whose mesh it moves, or sets the switch on that walk, by the author's ruling. |
| 5 | `specification/07-verification/02-tier-1.md`, the NOTE for VER-60 | The NOTE replaces "the spin-box sentence" as a whole, so it drops that sentence's last clause, "a loaded pH of 7.25 is shown and not rewritten". A browser number field with a step can round that value as a spin box did. The fourth change also keeps "the licence notice has a row for each payload", which is the bundle's CON-11 notice. | Fixed: the replacement keeps the pH clause. The licence-notice clause is recorded in REV-141's section, which WP5.02 owns. |
| 6 | `specification/history/index.md`, *Where each ruling holds now* | S2, S3, S6, S11, S12, S21, S22 and S24 still read "open: WP5.01 …", although WP5.01 discharged each of them. S4 still pointed only to §8.1, although WB-14 reversed its "structure preparation stays out of the library". | Fixed: each points to its NOTE, FR row, §8.4 rule or design-document section. S4 and S5 also name FR-37, FR-38, FR-41 and FR-42. |
| 7 | `.claude/scripts/gui/shoot.cjs`, `checkPage` | The contrast check measures CSS `color` against DOM ancestors. SVG text is painted by `fill` over sibling shapes. A label drawn through `<use>` sits in a shadow tree the walk never reaches. Opacity on an element or its ancestors is ignored. Example: the 11 px charge signs on the residue discs of `mockups/a/01-molecular.html` were not reported at all, so the claims of "no failed contrast check" cover HTML text only. | Fixed in part: such text is listed per shot as `unmeasured` (`svg text` or `opacity`), and `render.md` reports it as not checked. It is still not measured. |
| 8 | `docs/design/reviews/2026-10-26-mockups.md`; the plan, item 14's Outcome | Both say "22 `fine` and 10 `change`". The record's own table, and the gallery's `verdicts` collection read back, hold 23 `fine` and 9 `change`. | Fixed in both files. |
| 9 | `.claude/scripts/gui/capture_qt.py`, `Capture.built` | When `build_charge` refuses (no charge offered, or a build that does not start), both tabs keep `_settled` true. The wait then returns at once, the Geometry rows and the Charge panes are grabbed unbuilt, and `missed` names nothing. | Fixed: a build that left either flag set is a `missed` entry quoting the status bar, and the state is not grabbed. |
| 10 | `.claude/scripts/gui/shoot.cjs`, `shoot` and `shootOne` | An exception in one entry, for example a screenshot or an `evaluate` that fails, ended the loop before `index.json` was written, so every shot of the render was lost. Each screen's record also copied every console and page error since the load, so one screen's error appeared on every later screen. | Fixed: a failing entry is recorded as not loaded and the run goes on. Each shot carries only the errors raised since the shot before it. |
| 11 | `specification/08-implementation-plan/04-development-process.md` §8.4.4 | §8.4.4 (from S17) says a restatement "replaces it only when that release ships" (v0.6). The ten NOTEs, `workbench.md` and §8.2.18 T5 replace the clause in the package that removes Qt. | Fixed: §8.4.4 adds that a clause gating code which the study's phase removes is replaced in the package that removes that code, citing T5. |
| 12 | `specification/03-requirements.md`, FR-38 | S4's charge-level mutation edits "a residue's protonation, charge or radius". FR-38, the Charge edit tool and the panels offer only a protonation state, on every chain. No WB or T ruling records that the charge and radius edits were cut. | Not fixed: the scope is the author's call. Rule it, or add a REV row, at `/np-ship`. |
| 13 | `docs/project/review-findings.md`, `modularity-findings.md`, headers | T1's `wontfix` status, now on five rows, is not in either register's status vocabulary (`open`, `accepted`, `fixed`, `deferred`, `post-1.0`, `declined`). | Fixed: both headers list `wontfix`. |
| 14 | `docs/design/tokens.css`, `--control-edge` | In the light theme, `#868c99` on `--sel` (`#ece7ff`) is 2.80:1. That is below the 3:1 the file's header claims for controls against their surface, and below the 3:1 REV-138 relies on ("`tokens.css` holds its own pairs at 3:1 by calculation"). An input or checkbox in a selected row therefore fails WCAG 1.4.11. Every other pair checked holds. | Not fixed: a token change re-renders every page and goes through `/np-gui`. |
| 15 | The WP5.01 plan; `workbench.md`; the Phase 5 plan; `render.md` | Several pointers and counts were left stale by late changes. Items 9 and 11 are ticked without their SHAs (§8.4.4). The *Verification* row expects seven tabs in `run`, but the script grabs four, as item 5's Outcome says. `workbench.md` says "FR-31 to FR-42" but goes on to list FR-43. The Phase 5 plan's WP5.03 still says "tabs", against WB-01. `render.md`'s id `<dir>-<stem>-<w>-<scheme>` gives `mockups/a/` and `mockups/b/` pages the same id. | Fixed: `4d37db9` and `363ca45` added; "the four a run fills in `run`"; "FR-31 to FR-43"; "its four suites"; the id is now the page's path under `docs/design/`, as `generators/manifest.py` writes it. |

## Checks that held

- **The Qt shell's verdicts.** The record has 22 shots, 20 marked `change` and 2 `keep`, and Q01
  to Q41 are listed and placed in the workbench.
- **The concept boards and the style tile.** Their marks agree with WB-01, WB-27, WB-30 and WB-31.
- **The tokens.** WB-18 and WB-31's spacing (6 and 8 px, compact 4 and 6 px), WB-21's 12 px floor
  and WB-23's motion under 200 ms are as ruled.
- **The restatements.** The NOTEs for IF-09, P3, QR-10, CON-09, ADR-004 and RSK-13 match the
  design document's *Restated clauses* table.
- **Item 2's text.** The `/np-gui` bullet in §8.4.4, the three agents in §8.4.5, `CLAUDE.md` and the
  two skill hooks carry the plan's text.
- **Lint.** `ruff` passes on both scripts.

## Decided after the review

Each applied fix was read against the specification and the plan in the shipping session, and all
thirteen were kept. Two were adjusted:

- **Finding 8.** The record and the plan keep the author's marks as given, 22 `fine` and 10 `change`,
  and add that one `change` was a slip that stands as `fine` (§8.2.18 T7), so 23 and 9.
- **Finding 3's script.** A stray space was dropped from `shoot.cjs`'s `controls` line.

The author ruled the two findings left open (§8.2.19 U6, U7):

- **Finding 12** is REV-142, fixed: FR-38 and the Charge edit row restore S4's charge and radius
  edits.
- **Finding 14** is REV-143, accepted: WP5.02 owns it, together with REV-138's non-text contrast
  measure.
