# WP51 — The user-testing protocol

**Status: planned, not started.** Written 19 October 2026. Inherits WP50 as shipped (§8.2.13 N1 to N6)
and the protocol package's amendments (§8.2.7 G7, §8.2.8 H2).

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

The program is tidied; now its author tests it as a user would, before anyone else relies on it. This
package writes what those sessions follow: a protocol, five scripted tasks a nanopore modeller would
set, and an empty log for what the author finds.

**What changes.** A set of pages under the project's documents: how to run a session, five tasks (the
command line from nothing to a reproduced current, the physics switches, the numerics, the Python
interface, and a voltage sweep) and the findings log. Every command in the tasks is run each night,
so the tasks cannot go out of date before the sessions.

**Cost.** Two to three days of work. A push does not grow.

**What could go wrong.** A task could hint at a weakness the tester should meet unprompted; each
task states the goal and the expected behaviour, never the trap. A task could quietly run nothing; the
nightly check fails a task with no runnable step.

**Your call.**
- Should the sessions run against the installed package, built fresh from the tagged release, rather
  than the development checkout? *Recommendation:* yes; installing is part of what a user meets.

## Execution brief

Scope: the Phase 4 plan's *User-testing protocol* section, with its amendments; §8.2.7 G7 as
superseded by §8.2.13 N4 (the scripts run nightly); §8.2.6 F3 (sessions the author runs); §8.2.8 H2
(a task touching `with_section` and stage registration, for `MOD-11`). Depends on WP50 merged.
Claims VER-69 (proposed in the Phase 4 plan; §8.2.9 I2), on VER-46's pattern. Tag `v0.5.0-alpha.17`. Models: Sonnet
by default; Haiku for item 1. No physics or numerics code changes, so no `physics-reviewer` pass is
required; a session's stated expectation that names a physical property is read against
`knowledge/01-physics-epnpns/` by the implementer.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Form and home | `docs/user-testing/protocol.md`, `docs/user-testing/findings.md`, and one self-contained directory per session, `docs/user-testing/sessions/NN-<slug>/`, holding a `README.md` and the case and Python files it uses (no `../` paths). Commands sit in `<!-- example: run -->` or `<!-- example: refused -->` console blocks, so `src/nanopnp/validation/examples.py` executes them unchanged; Python code lives in files beside, run by `$ python <file>.py`, never in a fenced block. `mkdocs.yml`'s `exclude_docs` gains `user-testing/` (the strict build warns on a page outside the nav) | G7: verbatim, as an example's (VER-46). One runner, no second extractor to keep correct |
| D2 The sessions | Five, each a 20 to 40 minute task on cylinder meshes from `nanopnp mesh cylinder`: **01** command line, from nothing to an inspected and reproduced current, then one setting changed; **02** physics, the same charged pore classical and ePNP-NS, every correction `none`, and two salt concentrations; **03** numerics, three meshes of falling size, the stabilisation mode and the continuation rungs read from the manifest, and one gate refusal (exit 4); **04** the Python API: `run_case` with progress and a cancel, `run_document(..., upto=...)`, a substituted input, the exported fields, a case edited with `with_section` and a stage added with `core.stages.register`, both imported from their internal modules (H2); **05** a bias sweep with warm start, planned, run and collected. No PDB entry and no PROPKA step: those take minutes and examples 06 and 07 cover them | F3's four areas, with the sweep as the modeller's routine use. The 2WCD walks would put minutes of waiting into a session |
| D3 What a session states | The task as a modeller would set it; the starting point; the steps; the outcome expected, stated as a property of the model (rectification near unity with symmetric reservoirs, `t₊ > ½` in a negatively charged lumen, a current that changes less between the finer pair of meshes than between the coarser pair, deviations listed when a correction is `none`), never a transcribed number; and a closing prompt naming the log. No session names a known weakness or a `MOD-nn`/`REV-nn` row. The protocol tells the tester to build the wheel from the tagged tree and install it, with the `examples` extra, into a fresh environment, and to time-box each session | VER-46: no number in the documentation is a result unless an example asserts it. F3: the tester did not write the code, so a hint would spoil the finding |
| D4 The findings log | `findings.md`, front matter as `docs/project/modularity-findings.md`'s (`prefix: UT`, `status: open`, areas `install`, `cli`, `api`, `physics`, `numerics`, `docs`), a table `ID \| Area \| Severity \| Status \| Ruling \| Finding`, and its legend: severity `high` for a wrong or unusable result, `medium` for a task that needs knowledge the documentation does not give, `low` for friction; status `open` until the second amendment rules it. WP51 writes no row | G4's shape; its check is withdrawn and the close reads the log at review (§8.2.13 N3) |
| D5 VER-69's test | `tests/tier2/test_user_testing_sessions.py`, marked `nightly`, parametrised over the glob of session directories, so a new session is run without an edit. Per session: copy it with `copy_example`, run its `run` then its `refused` tags with `run_tagged`; assert the session has at least one tagged command, that every `$ ` line of a `console` block in its README sits in a tagged block, and that every command exits as its tag expects. Exit status is the oracle; no number is asserted. VER-69's row is added to §7's table and Appendix A in the item that adds the test | N4 runs the scripts nightly. The silent failure caught is a protocol gone stale, or a session whose mis-tagged blocks run nothing. Asserting the expected properties would duplicate VER-46 and is the tester's job |
| D6 The dry run and a defect | The implementer's run of D5's test is G7's dry run and records no `UT-nn`. Once, by hand, a session copy with one command broken is run and must fail; the result goes in the Outcome, not a committed test (a refusal is tested only where it is a physical gate, N1). This replaces the broken-script oracle the Phase 4 plan gave VER-69. A failure that is the script's error is fixed in the script. One that is the program's becomes a `REV-nn` row (H12), fixed in its own commit when it touches one module, otherwise put to the author before the package ends; the session is never rewritten to step around it | G7; N1; H12 |

### Work items

- [ ] 1. `docs/user-testing/protocol.md` (setup from the wheel, order, time box, how to record, what a
  dry run may not do), `docs/user-testing/findings.md` with no rows, `mkdocs.yml`'s `exclude_docs`
  (D1, D3, D4); done when the code and review say so, and the strict documentation build passes.
- [ ] 2. `tests/tier2/test_user_testing_sessions.py` and `docs/user-testing/sessions/01-command-line/`;
  VER-69's row in `SPECIFICATION.md` §7 and Appendix A (D2, D5); done when
  `uv run pytest tests/tier2/test_user_testing_sessions.py` passes.
- [ ] 3. `docs/user-testing/sessions/02-physics/` and `03-numerics/` (D2, D3); done when the same
  command passes.

*Compaction checkpoint: after item 3; resume from this plan and `git log`.*

- [ ] 4. `docs/user-testing/sessions/04-python-api/` with its `.py` files, and `05-sweep/` (D2, D3,
  H2); done when the same command passes.
- [ ] 5. The dry run and the broken-command check (D6); the nightly runtime of the five sessions on
  four cores in the Outcome; `docs/plans/current.md` and the Phase 4 plan's WP51 section marked
  delivered; done when `.claude/hooks/gate.sh run` passes and the test passes with `--nightly`.

### Verification

| Test | Tier | Identifier | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| `test_session_scripts_run_verbatim[<session>]` (VER-69 is named in the commit body, not the test: `CLAUDE.md`), one per session directory | 2, `nightly` | VER-69 | Each of the five sessions: at least one tagged command; each `run` command exits 0 and each `refused` command exits 4 (`EXPECTED_EXIT`) | Exit codes, IF-02 | `uv run pytest tests/tier2/test_user_testing_sessions.py` |

D6's broken-command check is a one-off, recorded in the Outcome. The sessions' expected properties are
the tester's to check and are asserted by no test (D3, D5).

### Out of scope

- The sessions themselves, and every `UT-nn` row: the author's (F3, G7).
- The `MOD-11` choice: a fix package, after the sessions (H2).
- The fix packages, from WP52, the documentation increment and the close: the second
  `/phase-plan amend 4`.
- Putting the sessions on the documentation site: documentation increment 4, if the author rules so.

### Open questions

None blocking. The *Your call* item defaults to its recommendation; a contrary ruling changes the setup
text only. The author ruled on 20 October 2026 that the tasks stay off the documentation site until the
documentation increment (D1).
