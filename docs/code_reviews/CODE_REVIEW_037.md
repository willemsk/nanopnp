# Code review 037: WP5.09, the physics model

Reviewed head `6581140a86e2ba7baee0600bc098726e1f0a5dfe` against base `1e7fa2e837a8846ed1ca97f09bcedb0460847771`
(PR 165), branch `claude/keen-turing-g32u0j`. Status: completed. Static review at `xhigh` with `--fix`. Fifteen findings;
fourteen fixed, one answered without a change. No physics or numerics file changed, and no open item is recorded.

| # | Where | Finding | Outcome |
|---|---|---|---|
| 1 | `gui/web/pages.py:current_suite` | The root page maps an item kind to its suite by its own table, which knew only `comparison`. Once a physics model is chosen in the rail, `current` is `physics/<name>`, and every later visit to `/` redirects to `/physics`, a page that does not exist; D4 sends a physics item to the Continuum suite. | Fixed: it reads the kind with `split_reference` and the suite from `ITEM_SUITES`; a current item that is no reference opens the Molecular suite. |
| 2 | `io/models.py:_exposed_entry` | An `exposes:` entry with no `name`, `name: null` or `name: true` was turned into the text `None` or `True`, which matches `[A-Za-z][A-Za-z0-9_]*`, so it was accepted under a name its author never wrote. §5.3.1 refuses an entry whose name does not match. | Fixed: the name reaches the check as written, and anything but a string is refused. |
| 3 | `io/models.py:_EXPOSED_NAME` | `^…$` with `match` accepts a name that ends in a newline (`salt\n`, from a YAML block scalar), since `$` matches before a final newline. | Fixed: `fullmatch`. |
| 4 | `io/models.py:exposed_values` | `numeric_paths()` holds a mapping of numbers as one entry, so `physics.solid_permittivities` passed as a numeric field: it was exposed with a mapping as its default and no range check, while an entry of it (`….protein`) is refused. | Fixed: a mapping of numbers is refused as not a numeric field. Exposing one entry of it is not supported; the NOTE does not ask for it. |
| 5 | `io/models.py:_exposed_entry` | Unknown keys were sorted as found; YAML reads `yes:` or `1:` as a non-string key, and a mix with a string key raised `TypeError`, which neither `Case.load` nor `Project.problems()` turns into a refusal. | Fixed: the keys are sorted as text. |
| 6 | `api/project.py:import_case`, `cli/workbench.py` | The docstring and the `project import` help still said a case imports as a study and "the two models". | Fixed: "the models". |
| 7 | `io/case_paths.py:schema_bounds` | It repeated `field_bounds` beside it, and where both a `ge` and a `gt` are declared it kept the last rather than the tightest. | Fixed: both read one `_bounds`, which keeps the tightest. |
| 8 | `io/models.py:exposed_values` | The generic path was rebuilt with a literal `"0"` where `case_paths.SEQUENCE_INDEX` names it. | Fixed: `SEQUENCE_INDEX`. |
| 9 | `io/models.py:exposed_values` | Every model-file read, once per study load and once per sweep member, rebuilt the frozenset of numeric paths. | Fixed: `_exposable_paths` is cached. |
| 10 | `api/project.py:_body` | The header keys a model file holds beside its kind's keys were a second literal; this package had to add `exposes` to both. | Fixed: `_body` reads `io.models.HEADER_KEYS`. |
| 11 | `api/project.py`, `gui/web/frame.py`, `gui/web/pages.py` | The kind-to-suite table was written three times (`_SUITE_OF`, the third column of `KINDS`, and finding 1's inline table), which is why the third missed physics. | Fixed: one public `io.project.ITEM_SUITES`, read by all three; `KINDS` keeps the rail's titles. |
| 12 | `gui/web/frame.py:listed_changes`, `io/models.py` | `listed_changes` spelt the kinds again beside `KINDS`; two refusals spelt "molecular, continuum, physics" beside `MODEL_KINDS`. | Fixed: they read `KINDS` and `MODEL_KINDS`. |
| 13 | `tests/tier2/test_named_models.py:_study` | The private helper's changed line carried a docstring; `CLAUDE.md`, *Prose in code*: "A test or private code has none." | Fixed: removed. |
| 14 | `tests/tier1/test_models.py:split_case`, `tests/tier1/test_project.py` | `split_case` rebuilt `io.models.SCHEMAS` by hand; the FR-34 test made `models/physics`, which `Project.create` already makes. | Fixed: `SCHEMAS`; the `mkdir` removed. |
| 15 | `io/models.py:exposed_values` | A declared range is checked against the schema's default when the model does not set the value, and the refusal calls that default "the model's value". | No change: the default is the value the model resolves to, which the range guides; the check is the NOTE's intent. |

Test scope: the four test files the PR changes were read against `CLAUDE.md`'s *Testing* and §8.2.13 N1. The two new
tests name the silent failure they catch; none was dropped, weakened or added. The fixes add no test: findings 2 to 5
are refusals of a malformed `exposes:` list, which N1 leaves to review.

Checked on the fixes: `ruff check`, `ruff format --check`, `mypy src/`, `tests/tier1/test_models.py`,
`test_project.py`, `test_case_leaves.py`, `test_layering.py` and `test_variables.py` (103 passed), and
`tests/tier1/test_gui_screens.py` (5 passed; the 39 browser tests skipped, no browser installed here). By hand: the
quick-start imported into a project lists its continuum and physics changes, and `physics/qs` made current maps to the
Continuum suite. `gate.sh run`, with the browser tests, follows in `/np-ship`.
