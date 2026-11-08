# Task walks 13 to 16: the three personas of §2.4 at docs/index.md, and a site reader opening Model

Walker: a Sonnet 5.5 sub-agent at low effort, holding only each walk's path. Return saved verbatim.

All paths are under /home/user/nanopnp. Each walk started afresh at its starting file. A page opened in two walks is counted in both. No searches were run.

## Walk 13 (P1: switch off the ion diffusivity correction from Python)

(1) Pages
| Step | Page | Words | Led there by | Gave |
|---|---|---|---|---|
| 1 | docs/index.md | 501 | start | "Script it from Python" row names guide/python.md, example 04 and the API reference. "The model" row names model/index. |
| 2 | docs/guide/python.md | 1216 | index row "The Python interface" | The objects: `Case.load`, `case.with_({...dotted path: value})`, `Session(store).run(case)`, `result.current_nA`, `result.quantities`. It does not say how to switch a correction off or what the value is. |
| 3 | examples/04-python-api/README.md (docs/_generated/examples/04-python-api.md) | 494 | python.md "runnable tour" | Nothing about corrections. It shows `with_` and `upto=` only. |
| 4 | docs/guide/provenance.md | 599 | python.md "Provenance and deviations" | The validated default is every correction on. Deviations are listed in the manifest. "A correction not named in the case defaults to `none`." |
| 5 | docs/guide/case-files.md | 757 | provenance.md "Case files" | The path `electrolyte.corrections.diffusivity.wall`. A case that names no correction is classical PNP-NS. Example 01 names them. |
| 6 | docs/model/index.md | 493 | index row "The model" | Table: `electrolyte.corrections.<property>.model` is specified by PHY-22 (independent switches) and PHY-10 to PHY-13 (forms and coefficients); `.concentration` and `.wall` by PHY-10 and PHY-11. |

(2) Stalls
- Step 2, python.md: "A field is named by its dotted path or by the leaf name it ends in". The page never says which path or value turns a correction off.
- Step 3, example 04: I opened it because python.md calls it "the runnable tour". It gave nothing for the question.
- Step 4: python.md names "Provenance and deviations" only as where `result.manifest` is read. Nothing says it holds the switch story.
- Step 5, case-files.md: "Each correction's schema default is `none`" conflicts with the question's "default run". The default run is the validated model only if the case names the corrections as example 01 does. I did not open example 01 or the case-file reference, so the exact off value for `electrolyte.corrections.diffusivity.model` is not confirmed. I inferred `"none"`.
- Step 6: I never opened the model page's `_generated/reference/case-file.md` link, so I did not see the switch's allowed values.

(3) Answer, partly answered.
- Objects: `Case` (or `Case.load`), `case.with_({"electrolyte.corrections.diffusivity.model": "none"})` (a path inferred from case-files.md), and `Session(...).run(case)` for each case. Compare `result.current_nA` and `result.conductance_nS`, or `result.quantities`.
- The comparison run's manifest lists the switch under `deviations`.
- The correction is specified in PHY-22 (switchable, with "off" a named model, `f_D^c = f_D^w = 1`) and in PHY-10 to PHY-13 (forms and coefficients). The exact value to set, and the validated-default baseline, I could not confirm from these pages.

(4) Totals: 6 pages, 4060 words, 27856 chars, about 6964 tokens.

## Walk 14 (P2: voltage sweep on a cluster, and reproducibility)

(1) Pages
| Step | Page | Words | Led there by | Gave |
|---|---|---|---|---|
| 1 | docs/index.md | 501 | start | "Run a sweep on a cluster" row links sweeps.md and example 05. |
| 2 | docs/guide/sweeps.md | 772 | index row "Sweeps and HPC" | The sweep YAML (`schema: nanopnp/sweep/v0.5`, axis `boundary_conditions.bias_V`). `sweep plan`, then one SLURM job array per wave running `sweep run <plan.json> --index <point>`, then `sweep collect --csv`. |
| 3 | examples/05-clya-reference/README.md (docs/_generated/examples/05-clya-reference.md) | 674 | sweeps.md "Example 05" | The ClyA case. The `render_slurm.py` submission, with `afterany` dependencies between waves. |
| 4 | docs/guide/concepts.md | 839 | index row "Understand what a run is made of" | Every run writes `case.yaml`, `run.json` and `manifest.json`. Points to Provenance. |
| 5 | docs/guide/provenance.md | 599 | concepts.md "Provenance and deviations" | The manifest's eight groups. `nanopnp reproduce <run directory>` re-solves in a fresh store and compares every scalar; it exits 0 only if all agree. |

(2) Stalls
- Step 2: sweeps.md says "see `docs/sweeps/phase1-reference.sweep.yaml`". That is a repository path, not a link.
- Step 3: example 05 pins a frozen case. The page does not say how a user's own ClyA case file differs from it.
- Step 4: nothing on the sweep, HPC or ClyA pages mentions reproducibility or links to provenance. The index row for concepts says only "what a run is made of", so following it for reproducibility was a guess, not something a link told me.
- Step 5: neither sweeps.md nor example 05 says whether `nanopnp reproduce` works on a sweep member. I did not open running.md.

(3) Answer
- Write a `sweep/v0.5` document whose base is the ClyA case file, with an axis `boundary_conditions.bias_V` and its values and origin.
- Run `nanopnp sweep plan`, then submit one dependent SLURM job array per wave. Each element runs `nanopnp sweep run <plan.json> --store <store> --index <point>`. Then run `nanopnp sweep collect <plan.json> --csv`.
- Each member's run directory holds `manifest.json`. `nanopnp inspect` reads it and `nanopnp reproduce <run dir>` re-solves and compares every scalar.
- Whether `reproduce` applies to sweep members is unstated.

(4) Totals: 5 pages, 3385 words, 21740 chars, about 5435 tokens.

## Walk 15 (P3: choose a pore, set salt and voltage, read a current, no Python)

(1) Pages
| Step | Page | Words | Led there by | Gave |
|---|---|---|---|---|
| 1 | docs/index.md | 501 | start | The third persona (laboratory) is "served by the desktop shell from a development install". Installers come later. |
| 2 | docs/guide/desktop.md | 1417 | index row "Use the desktop application" | `nanopnp-gui case.yaml` needs the `gui` extra. It is a development install or a pip install. It edits a case file, so a case file is required. Installers come after v1.0. A Windows bundle exists only for the packaging probe. |
| 3 | docs/getting-started.md | 517 | index row "Run your first case" | Install is `pip install "nanopnp[gui] @ git+https://github.com/willemsk/nanopnp"`, which needs Python 3.11 to 3.14. It is not on PyPI. |
| 4 | docs/guide/notebooks.md | 290 | getting-started.md "interactive notebooks" | marimo notebooks need the `notebook` extra and a checkout. They are not a file-free route. |

(2) Stalls
- Step 2: the admonition is titled "v0.2: a development install" while the index says v0.5.0 is released. The version label looks stale.
- Step 2: `nanopnp-gui case.yaml` shows a case file as the argument. The page does not say whether the shell starts without one, nor how "choose a pore" works without writing a file.
- Step 3: the index row "Run your first case" does not say it is the install page.
- Step 4: I followed getting-started's pointer to the notebooks hoping for a no-file route. I did not find one.

(3) Answer: not today as the lab frames it.
- A desktop shell exists, but only from a development install. That install needs Python and pip, or `uv` and a checkout, plus the `gui` extra (PySide6).
- It edits and runs a case file. I found no statement that the lab can start from an empty form and avoid files.
- Installers and a bundled shell are post-v1.0. The only double-clickable Windows build is of the packaging probe.

(4) Totals: 4 pages, 2725 words, 17667 chars, about 4417 tokens.

## Walk 16 (Model reader: exact wall function on the ion diffusivity)

(1) Pages
| Step | Page | Words | Led there by | Gave |
|---|---|---|---|---|
| 1 | docs/model/index.md | 493 | start | Warns that the wall function's sign has been copied wrongly. Says the COMSOL model report governs where sources disagree. The `.wall` row points to PHY-10 and PHY-11. The page links the specification and the knowledge index. |
| 2 | SPECIFICATION.md (docs/_generated/model/specification.md) | 1017 | model/index "The specification" | A map only, with no equations. Gives the identifier-to-file row (`PHY-nn` is in `specification/04-physics.md`) and a precedence rule. |
| 3 | specification/04-physics.md (docs/_generated/model/specification/04-physics.md) | 6761 | SPECIFICATION.md "Identifier to file", PHY row | PHY-11, PHY-12 and the §4.6 errata. See the answer below. |

(2) Stalls
- Step 1: model/index.md says "Read the equations in the records themselves" and names the knowledge errata file only as inline code, not a link. I did not follow it.
- Step 2: the specification link leads to a map page with no physics. It cost a hop.
- Step 3: the clause sits inside a 6,761-word page with no anchor in any link. The sign and coefficient took reading most of it.
- I did not open the knowledge base (`knowledge/01-physics-epnpns/`), so I did not check it against the specification.

(3) Answer
- PHY-11 gives the wall function for D_i and μ_i as `f^w(d̄) = 1 − exp(−P₁(d̄ + P₂))`, with `d̄ = d/(1 nm)`.
- The sign is `(d̄ + P₂)`, a plus. For η it is `(d̄ − P₂)` with a minus.
- PHY-12 gives P₁ = 6.2 nm⁻¹ and P₂ = 0.01 nm. The check values are f(0) = 0.06 and f(0.75 nm) = 0.99.
- §4.6 errata rows 1 and 2 reject the thesis's `(d̄ − P₂)` and the readings 62 and 0.62 of the coefficient. The driver is clamped to max(d̄, 0) (PHY-02 NOTE).
- Authority: where sources disagree, the COMSOL model report (`npgrid_clya_v8_NaCl_report.mph`) governs (spec §1.6, repeated in model/index.md and SPECIFICATION.md). Beyond that the specification is normative and governs the plans, the documentation and the code. §4 is backed by `knowledge/01-physics-epnpns/`.

(4) Totals: 3 pages, 8271 words, 55911 chars, about 13978 tokens.
