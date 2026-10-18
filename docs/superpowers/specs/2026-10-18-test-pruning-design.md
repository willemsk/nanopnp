# Test pruning and the test scope rule: design

*18 October 2026. The author's decisions are marked **(author)**. Calls made in the brainstorm without the
author's ruling are marked **(my call)** for the author to check.*

## Intent

Every work package ends with a pile of new tests, sometimes for doc-only changes. Each one has to be
written, gated, kept green and updated whenever the code moves, and most catch nothing the author would
miss. Development speed suffers for questionable benefit. The goal is a much smaller suite that tests the
essential machinery thoroughly, plus rules that stop the pile from growing back.

Measured on 18 October 2026: about 1,880 test functions (2,403 collected cases), about 48,000 lines of test
code against 50,000 lines of `src/`. Full tiers 1–2 with `--extended` take about 8 minutes on all cores.
Of tier 1's ~1,650 tests, about 770 check physics, numerics or core mechanisms, about 620 check interface
behaviour (mostly "refused, naming the key"), about 250 check the repository itself, and a few dozen
restate the code. Tier 2 (222 tests) is mostly analytic benchmarks and end-to-end walks.

## What drives the growth (to be removed)

1. CI's changed-line branch coverage gate (`diff-cover --fail-under=100`).
2. "Every VER-/VAL- the plan claims has a test named for it", in `wp-plan`, `wp-implement`, `wp-ship`,
   `phase-plan` and the PR template.
3. Knowledge claims tied to tests: §8.2 G3 (ledger of untested claims, `knowledge/pending.yaml`), G8
   (executable arithmetic gets a Tier-1 test).
4. Repository self-checks make doc, spec, plan, skill and knowledge edits run the test suite.
5. Review rounds that close findings by adding tests.
6. CONTRIBUTING's "no test is deleted to make a PR pass" read as "no test is ever deleted".

## Goals

- **The test scope rule (author).** A test is written only for code that could silently give a wrong answer
  or that drives a core mechanism:
  - *Physics and numerics*: weak forms, corrections, Newton and gates, stabilisation, quadrature, charge
    deposition, dielectric, wall distance, forces, QoI, scaling, continuation, mesh quality and sizing,
    analytic benchmarks, MMS.
  - *Core mechanisms (my call on the list)*: content hashing and cache keys, the artefact store, case
    resolution (which settings reach the solve), the stage walk and cancellation, warm start,
    reproducibility, the manifest's record of deviations, the solution state round-trip, number-stability
    goldens.
  - *Guards (author)*: the licence and architecture guards only: no `gmsh` import on the default path
    (CON-10), no forbidden mesher in the lock (CON-12), import layering (VER-61) and the backend guard
    (VER-65). Tests asserting that a module "imports no backend/numpy" belong here.
  - A refusal test stays only when the refusal is a numerical or physical gate (state gates, packing,
    quadrature floor, inf-sup pair, mesh quality, coarse-mesh refusal). Input-validation refusals and
    message wording go **(my call)**.
- **A thin smoke test per entry point (my call):** the CLI runs a case, the GUI window opens, a case file
  loads, `import nanopnp` works. One or two tests each, not a suite.
- **No coverage gate (author).** Remove the CI `coverage` job, `diff-cover`, the `# pragma: no cover -
  <reason>` convention and every instruction to write a test that executes a line. Existing pragmas may stay
  as harmless comments or be stripped **(builder's choice)**.
- **Requirement IDs need a test only for physics, numerics or core mechanisms (author).** Other VER rows
  remain normative behaviour but are discharged by the code and the review.
- **Per-push vs nightly (author).**
  - Every push (PR CI, push to `main`, `gate.sh run`): tier 1 plus the tier 2 analytic benchmarks, plus
    the quickstart example (example 01) **only while it solves in under 60 s**; past that it moves to
    nightly.
  - Nightly: everything else in tiers 1–2 (the 2WCD walks, examples 02–07, `slow` benchmarks) plus tier 3,
    on the platforms the nightly job already covers.
  - A tagged release requires a green nightly on the tagged commit (or a nightly run triggered on it).
- **Prevention (author): a judgement rule plus a reviewer step that deletes off-category tests.**
  - The rule, stated once in `CLAUDE.md` § Testing and in `.claude/rules/python.md` (for `tests/**`):
    the scope above, and "a new test's name or first line says which silent failure it catches". It
    replaces "write the tests with the item" everywhere.
  - The reviewer step is part of `/wp-ship`, before `/code-review` **(my call on placement)**: read the
    PR's added and changed tests against the scope rule and delete every off-category one, in its own
    commit `test: drop tests outside the test scope`. `/code-review`'s args gain one sentence: a finding is
    never fixed by adding an off-category test.
  - Plans' Verification sections list only in-scope tests; plan templates in `wp-plan` and `phase-plan`
    drop "done when <tests> pass" for out-of-scope items (done when the code and review say so).

## Non-goals

- Changing any physics, tolerance or oracle. No tolerance is loosened and no in-scope test weakened.
- Rewriting kept tests (e.g. stripping message assertions from a kept numerics test). Kept tests are kept
  as they are.
- Removing the WP43 tooling itself (test-impact selector, push guard, `same_tree.py`, `clause.py`); only
  the tests of it go. Whether the tooling earns its keep is a separate question.
- Tier 3 and tier 4 content.

## Anti-goals

- Losing a physics or numerics regression: a deletion that leaves a numerical claim ungated on every push
  or nightly is a failure even if CI goes green.
- Moving tests to nightly as a way to keep them. Nightly is for slow in-scope tests, not for off-category
  ones.
- A new meta-test that checks the test scope rule. The rule is enforced by review, not by a test.

## Constraints

- `SPECIFICATION.md` is normative; it changes in the same commits as the behaviour:
  - §7.6: rewrite the CI table and NOTEs to the per-push / nightly split; delete the coverage NOTE; replace
    `extended` with the new split; the runtime NOTE's "four ways only" no longer binds moving a walk to
    nightly.
  - §7.1–7.3: the tier descriptions follow the new scope.
  - VER rows that are pure repository self-checks are withdrawn, the way VER-73/74 were: VER-63
    (findings logs), VER-67 (release strings), VER-68 (knowledge bundle), VER-72 (source conventions,
    except any part that is an architecture guard), VER-75 (prose share), and the self-check parts of
    VER-45/VER-46 (the strict docs build stays in CI; executed examples move to nightly except 01).
    Interface VERs (e.g. VER-32, VER-38, VER-47, VER-76) stay normative with "verified at review".
  - A new §8.2 ruling block (§8.2.13, "the test scope", dated) records the author's decisions above,
    and G3, G8 and §8.2.11 L3's coverage clause are marked superseded by it.
- `knowledge/`: 380 `[tested: <test>]` markers exist. A marker naming a deleted test is retargeted to a
  surviving test that asserts the same claim, else becomes `[verified]` when the concept carries a source
  footnote, else the marker is dropped **(my call)**. `knowledge/pending.yaml` and its rule go. Log the
  change in `knowledge/log.md`.
- `prose-only.sh`: after the meta-tests go, Markdown under `SPECIFICATION.md`, `docs/`, `knowledge/` and
  `.claude/` is prose again (ruff only), except `docs/` still triggers the docs build in CI.
- Every file that names the removed rules changes with them: `CLAUDE.md`, `CONTRIBUTING.md` (keep "no
  tolerance slackened"; "deleted to make a PR pass" becomes "deleting a test outside the test scope is
  allowed"), `tests/README.md`, `.claude/rules/python.md`, the five skills, `.github/pull_request_template.md`,
  `.github/workflows/ci.yml`, `.github/actions/tier12/`, `.github/scripts/prose-only.sh`, `gate.sh`.
- `uv run pytest` must still be the per-push selection; markers stay under `--strict-markers`.

## Decided how

- **Marker (my call):** replace `extended` with `nightly`; walks and `slow` benchmarks carry it; the
  default `addopts` excludes it; `--extended` is removed and `-m nightly` (or a `--nightly` flag) selects
  it. Example 01 carries no marker while under 60 s.
- **Delivery (my call):** a standalone process change on branch `claude/confident-bell-uutfr8`, one PR,
  recorded by the §8.2.13 ruling, not a numbered work package. Commits in this order so each is
  reviewable: (1) rules, spec and skills; (2) CI and gate changes; (3) deletions, one commit per area
  (`gui`, `cli`/`case`/`io`, repository self-checks, remaining interface); (4) knowledge markers.
- **Expected size:** roughly half the current test functions remain, mostly tier 1 machinery and tier 2.
  No numeric target is set; the scope rule decides.

## Left to the builder

- The file-by-file and test-by-test deletion list, applied with the scope rule. Mixed files are pruned
  test by test; a file left with only fixtures is deleted. The survey tables from the brainstorm (tier 1
  classified per file) are a starting point, not a ruling.
- Whether the 60 s budget for example 01 is checked by a timing in CI or by the nightly report.
- Wording of the rule text, within the scope above.
- Cleaning up fixtures, helpers and test data left unused by the deletions.
