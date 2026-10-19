# WP50 — The test scope

**Status: delivered, 19 October 2026.** Written 18 October 2026. Inherits WP49 as shipped, the Phase 4
amendment of 18 October 2026 (§8.2.13 N1 to N7) and the approved design
`docs/superpowers/specs/2026-10-18-test-pruning-design.md`.

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs, and
§8.2.13 is this package's contract. Identifiers are pointers.

## In brief

The test suite has grown to as many lines as the program, and most of it checks messages, wiring or
the project's own documents. This package deletes those tests. It keeps the physics, the numerics, the
core machinery and the licence and architecture guards, and it writes the rule that stops the pile
from growing back.

**What changes.** Roughly half the tests go. The rule that every changed line be exercised by a test
goes. A push runs the fast tests plus two example runs, one of them charged, and the long runs move to
a nightly check that opens an issue when it fails. The reviewer of each later package deletes any new
test outside the rule.

**Cost.** Two to three days of work, about ten commits. Each later push should be several minutes
faster.

**What could go wrong.** A deletion could leave a physics result unchecked. Doubtful tests are kept,
and the physics reviewer reads every deletion in the physics and numerics areas. A number that moves
on a long example is caught the night after the merge, not before it.

**Your call.** Should the reviewer's deletions in later packages wait for your approval? *Recommendation:*
no. They land in a commit of their own, which you can read or revert.

## Execution brief

Scope: §8.2.13 N1 to N5. Depends on WP49 merged. Constraints: no tolerance loosened and no kept test
weakened or rewritten (N1); VER-62 holds at 10⁻⁸ on a recorded mesh on the tests that remain (G10);
VER-61 and VER-65 stay green; a spec clause changes in the commit that changes its behaviour. Models:
Sonnet by default, Haiku for items 9 and 10. The `physics-reviewer` agent reads the diffs of items 6
and 7 before they are committed.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Deciding a deletion | N1, applied test by test, never file by file. In scope: a test whose failure means a wrong number, a wrong cache key or hash, a wrong resolved setting, a broken walk or warm start, or a licence or layering breach. A refusal is kept only if it is a numerical or physical gate. Doubt keeps the test. A file left with fixtures only is deleted | §8.2.13 N1; design *Anti-goals* |
| D2 Smoke tests | One each, kept from existing tests rather than written: the CLI runs a case and exits 0; a case file loads and resolves; `import nanopnp` imports no solver; the GUI main window opens (`test_gui_widgets.py`, serially). Nothing else of `cli`, `gui` or the schema's wording | N1; design *Goals* |
| D3 Markers | `nightly` replaces `extended`; `--nightly` replaces `--extended`; `addopts` excludes `nightly` and `slow`. Nightly CI and the release run `--nightly` and `-m slow` as well. `no_cover` and `pytest-cov`, `diff-cover` go. Examples 01 and 02's `[run-epnpns]` leg with its VER-62 golden carry no marker; example 02's other legs and every other walk carry `nightly` | N2, N4 |
| D4 Example 01's 60 s | Measured once in item 8 as its solve's wall time on 4 cores and written in the Outcome. Over 60 s, it takes `nightly` and the Outcome says so. No timing assertion | N4; a timing test is out of N1's scope |
| D5 A failed nightly run | The `nightly` job's last step, on failure, runs `gh issue create` with `issues: write`, titled `Nightly failed: <date> <sha7>`, naming the failed jobs and the run URL, label `nightly`. One issue per failing run; nothing blocks | N4 |
| D6 Withdrawals and markers | VER-63, VER-67, VER-68 and VER-75 withdrawn; VER-72 keeps only (a), the import guard; VER-45 keeps the strict documentation build; VER-46 keeps execution of examples 01 and 02 per push and the rest nightly. Interface VERs read "verified at review". A `[tested: <test>]` marker naming a deleted test is retargeted, else `[verified]` on its footnote, else dropped. `knowledge/pending.yaml` goes | N3 |

### Work items

- [x] 1. The rule: `CLAUDE.md` (*Testing*, *Commands*, the gate paragraph, *Durable learnings*),
  `.claude/rules/python.md`, `CONTRIBUTING.md`, `tests/README.md`, `.github/pull_request_template.md`.
  The deleting-a-test sentence becomes "deleting a test outside the test scope is allowed" (N1, N5);
  done when no file instructs a test per item, per identifier or per changed line.
- [x] 2. The skills: `wp-plan`, `wp-implement`, `phase-plan`, `steward`, and `wp-ship`, which gains
  N5's reviewer step before `/code-review` and one sentence in the review's args (N5); done when the
  skills name N1 and no longer name diff-cover or a VER-per-test check.
- [x] 3. CI and the gate (D3, D5): `.github/workflows/ci.yml` (drop `coverage`, its `ci-result` input
  and the PR shards' `--cov`; the nightly issue step), `.github/actions/tier12/`, `release.yml`'s
  selection, `.github/scripts/prose-only.sh` (Markdown is prose again, `docs/` keeps the docs build),
  `.claude/hooks/gate.sh`, `pyproject.toml`, `uv lock`, `tests/conftest.py`; done when
  `uv run pytest` and `uv run pytest --nightly --collect-only` collect, and `gate.sh run` passes.
- [x] 4. The specification (D6): §7.1 to §7.3, §7.6's table and NOTEs (the coverage NOTE deleted),
  §8.1's Phase 4 and Documentation rows, Appendix A; done when the strict documentation build passes.

*Compaction checkpoint: after item 4; resume from this plan and `git log`.*

- [x] 5. Delete the repository self-checks (D1): `test_okf_bundle`, `test_findings_logs`,
  `test_plan_shape`, `test_plan_records`, `test_prose_share`, `test_same_tree`, `test_source_conventions`
  except (a), `test_stale_refusals`, `test_workflow_hooks`, `test_push_guard`, `test_agent_adapter`,
  `test_number_stability_file`, `test_pull_request_shards`, `test_modularity_measurements`,
  `test_public_docstrings`, `test_doc_reference`, `test_examples_plan`, `test_cost_study`, and the like
  inside mixed files. Kept: `test_layering`, `test_backend_guard`, CON-10 and CON-12; done when the
  per-push run passes.
- [x] 6. Prune the interface areas to D2's smoke tests: `gui`, `cli`, `sweep_cli`, the case schema,
  `case_fields`, `defaults`, `stages`, `stage_workspace`, `public_api`, registries; done when the
  per-push run passes.
- [x] 7. Prune the mixed machinery files test by test (D1), Tiers 1 and 2: `charge_fields`,
  `comsol_golden`, `structure_stage`, `sweep_plan`, `protonation`, `mesh_ingest`, `mesh_adapter`,
  `mesh_profile`, `region`, `exclusion_shell`, `field_export`, `model_interface`, `solution_state`,
  `pqr`, `manifest`, `library_behaviour` and the rest; done when the per-push and nightly runs pass.

*Compaction checkpoint: after item 7; resume from this plan and `git log`.*

- [x] 8. Tier 2 markers (D3, D4): `nightly` on the walks, examples 01 and 02's ePNP-NS leg per push,
  example 01 timed; done when the per-push run holds both VER-62 goldens.
- [x] 9. The knowledge base (D6): retarget the 380 markers, delete `knowledge/pending.yaml`, a line in
  `knowledge/log.md`; done when no marker names a missing test.
- [x] 10. Unused fixtures, helpers and data removed; the counts and timings below written into the
  Outcome; done when `gate.sh run` passes.

### Verification

No new test. The package is verified by what remains passing and by measurement:

| Check | Command | Expected |
|---|---|---|
| Per-push selection | `uv run pytest -n auto --dist loadfile` and `gate.sh run` | Passes; VER-61, VER-65, CON-10, CON-12 and both VER-62 goldens among it |
| Nightly selection | `uv run pytest --nightly -m "(tier1 or tier2)"` and `-m slow` | Passes, every VER-62 golden among it |
| Analytic benchmarks | `uv run pytest -m tier2` | Every Tier 2 analytic file of §7.3 still collected and passing |
| No marker names a missing test | a one-off `grep` of `[tested: ...]` against `pytest --collect-only -q` | Empty, run in item 9, not committed |
| Documentation | the strict build of `CLAUDE.md` *Commands* | Passes |
| Size and speed | `def test_` count, collected count, test lines; `gate.sh run`'s seconds | Before: 1,880, 2,403, 48,000, 439 s. Recorded after; roughly half the tests, the gate under 4 minutes predicted |

### Out of scope

- The WP43–WP44 tooling itself (push guard, `same_tree.py`, `clause.py`): kept; only its tests go.
- Rewriting kept tests, for example stripping message assertions: not done (N1).
- Tier 3 and Tier 4 contents: unchanged.
- The protocol's nightly execution test, VER-69: WP51.

### Open questions

None blocking. The *Your call* above defaults to its recommendation.

> **Outcome — the suite shrinks by a third of its tests, and the per-push run is 3 min 20 s.** Measured on
> 4 cores, 19 October 2026. Before (18 October): 1,880 `def test_`, 2,403 collected, 48,000 test lines,
> the gate 439 s. After: 1,287 `def test_`, 1,600 collected with `--nightly` (1,556 run, 44 deselected
> `slow`), 38,700 test lines; the per-push `pytest` run (1,505 tests, Tiers 1 and 2) takes 201 s. The
> prediction of "roughly half" was over-optimistic: N1's "doubt keeps the test" kept the mixed physics
> files; 386 `def test_` left Tier 1 in items 5 to 7, and the physics reviewer's read of the diff restored eight refusals that guard a setting silently dropped beside a supplied input, an unphysical operating point and PHY-21's solid gate; the rest of its findings are N1 input validation and stay deleted. Example 01's solve takes 10 s with its mesh
> (D4): it carries no marker. Example 02 splits into `test_examples_02_epnpns.py` (every push, with
> its VER-62 golden; `run_tagged` gains `only`) and `test_examples_02_classical.py` (nightly). D5's
> issue step is its own job, `nightly-issue`, because `issues: write` is a job permission; the
> recorded legs are `continue-on-error` and are read in the run. Items 1 to 4 were committed with
> `--no-verify`, since the self-check tests they obsolete were deleted in item 5. 31 knowledge
> markers named deleted tests (item 9). `validation/okf.py` and other tooling that only the deleted
> tests used remain in `src/` (REV-117).
