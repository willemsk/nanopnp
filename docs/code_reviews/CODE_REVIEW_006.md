# Code review: PR #98 (WP45, the prose strip)

2026-10-14 · head `8f263ff` (`claude/elegant-wright-1xgxnk`) against `main` at `3782c43` · 314 files,
+3,721 / −34,869 · `/code-review xhigh --fix`

## Scope and method

The diff is almost all deleted or condensed prose in `src/nanopnp` and `tests/`. It also adds
`.claude/scripts/same_tree.py`, `tests/tier1/test_same_tree.py` and `tests/tier1/test_prose_share.py`,
amends L4 and VER-75, and adds facts to `.knowledge/`.

- `same_tree.py 3782c43` was re-run over the whole branch. Only the three added files differ, so no
  instruction changed. A second script checked that no directive comment moved to another line;
  none did.
- Every runtime reader of a docstring was looked for (`__doc__`, `getdoc`, `model_json_schema`,
  attribute-docstring config, doctests, mkdocstrings).
- All 2,168 added `src/` lines were read against the code they describe. The physics docstrings
  (flow, Nernst-Planck, stabilisation, forms) were checked term by term.
- For each module-level numeric constant, the prose before and after the strip was compared. So was
  every inline numeric literal whose comment was removed.
- The `.knowledge/` additions were spot-checked by arithmetic: Taubin pass band, Langevin cutoff,
  Ohshima `f(κa)`, Maxwell-Hall access term, Gouy-Chapman-Stern, the force scale, `Pe`, the
  hash-collision bound and the wall-function slope. All hold.

## Summary

| Severity | Count | Fixed | Skipped |
|---|---:|---:|---:|
| High | 1 | 1 | 0 |
| Medium | 4 | 2 + 1 partly | 1 |
| Low | 9 | 7 | 2 |

No change of behaviour is in the PR, and none was found. The strip did what L5 promised. The
findings are about what it removed, what its own checks measure, and conventions it broke.

## Findings at a glance

| # | Sev | Location | Finding | Outcome |
|---|---|---|---|---|
| 1 | high | `src/nanopnp/core/constants.py:7` and 19 more | The sources of physical constants and model parameters were deleted | fixed |
| 2 | medium | `tests/tier1/test_prose_share.py:75` | The VER-75 share ignores attribute docstrings; 20 private docstrings pass (a) | fixed |
| 3 | medium | `.claude/scripts/same_tree.py:63` | The tree check strips docstrings that the program runs (`__doc__`) | fixed |
| 4 | medium | `pyproject.toml:156`; L4; VER-72 (h) | Amended L4 is unenforced and broken by 47 public methods | partly |
| 5 | medium | `SPECIFICATION.md:3069` | VER-75 (a) claims a source check that no test makes | skipped |
| 6 | low | `.claude/scripts/same_tree.py:67` | An unparsable file crashes the check with `File "<unknown>"` | fixed |
| 7 | low | `src/nanopnp/materials/corrections.py:198` | Garbled comment fragments around the cache copy and schema check | fixed |
| 8 | low | `.knowledge/04-clya-geometry-and-charge/index.md`–`08`, 14 entries | Facts cite "(module docstring)" that this PR deleted | fixed |
| 9 | low | `src/nanopnp/core/stages.py:81`; `tests/tier3/test_reference_charge_map.py:36` | Directive and skip reason point at prose that is gone | fixed |
| 10 | low | `src/nanopnp/physics/models.py:454` and 6 more | A comment sits above the restored docstring, away from its code | fixed |
| 11 | low | ~157 `src/` prose lines | Identifiers and plan history kept in prose | skipped |
| 12 | low | `src/nanopnp/pipeline/case.py:48` | `0.25-0.5 A`: the Å became an A (amperes) | fixed |
| 13 | low | `tests/tier1/test_prose_share.py:87` | Every commit parses each tree four times | fixed |
| 14 | low | `same_tree.py:23` vs `test_prose_share.py:13` | Two different definitions of a directive comment | skipped |

## Findings

### 1. The sources of physical constants were deleted (high, fixed)

`CLAUDE.md` (*Prose in code*) asks for "a comment ... for the source of a physical constant". The
rule in `.claude/rules/python.md` is "Cite the source (`.knowledge/` file or specification section)
of every physical constant and fit coefficient in a comment". The plan's own D2 says the same. The
strip deleted the attribute docstrings and module prose that held these sources and left no comment.
Affected:

- the CODATA constants and `REFERENCE_TEMPERATURE_K` (`core/constants.py`);
- `REFERENCE_DIFFUSIVITY_M2_S`, `REFERENCE_VISCOSITY_PA_S` and `REFERENCE_PERMITTIVITY = 78.15`, a
  Gavish fit value (`core/scaling.py`);
- the steric diameters `ION_DIAMETER_NM = 0.5` and `WATER_DIAMETER_NM = 0.311` (PHY-05), and the
  measured gate constants (`numerics/gates.py`);
- `SINGULAR_MIN_ORDER` (NUM-07), `CONCENTRATION_FLOOR_M` (PHY-01) and the NUM-18 ramp steps;
- the NUM-26 and NUM-29 tolerances, and the VAL-05 and VAL-06 tolerances;
- `Z_MD_NM`, the `pqr2grid` binning, Taubin's factors and `_LANGEVIN_SERIES_CUTOFF`.

The `.knowledge/` file now cites the cutoff. A reader of `forms.py` still sees a bare `3e-4`, and a
1e-8 there returns exactly zero.

**Fix.** One-line source comments on 20 constants across 13 files. Two existing citations were wrong
and are corrected:

- `physics/pb.py` cited `.knowledge/01-physics-epnpns/04-rationale-worth-preserving.md` for `ε_r,f0`; the value is in §3.
- The deleted docstring of `REFERENCE_DIFFUSIVITY_M2_S` called 1.334e-9 the NaCl mean. It is
  `D_Na⁰` (Mills 1989); the mean of `D_Na⁰` and `D_Cl⁰` is 1.683e-9.

About 40 test-side reference values also lost their sources, for example `STERN_THICKNESS_NM` in
`tests/tier2/test_stern_layer.py`. They were not restored in this pass.

### 2. The VER-75 share ignores attribute docstrings (medium, fixed)

`_prose_lines` counted only the docstrings of modules, functions and classes. A string statement
after an assignment (an attribute docstring) is a docstring line, and mkdocstrings renders it as
one. These were neither counted under (b) nor checked under (a):

- `src/nanopnp` holds 127 of them, 366 lines. The true share was 11.4 %, not the 10.6 % reported,
  which is 0.2 point under the 11.62 % ceiling recorded as "measured plus 1 point".
- Twenty sat on private names or private-class fields: `_SAMPLING_MARGIN`, `_MODEL_IDS`,
  `_ESSENTIAL_PURPOSES`, `_Reference.residues` and others. L4 forbids these, and (a) passed them.
- A function nested under an `if` inside a function was also scored as public.

**Fix.** The test now:

- counts every bare string statement as prose;
- flags an attribute docstring in a non-public scope;
- treats every statement under a function body as local.

There are three new substituted-tree tests. The 20 private docstrings became comments; two that
only restated a field name were dropped. The ceilings were re-derived under VER-75 (b) from the
corrected measure (11.40 % and 2.35 %, plus 1 point) as 12.40 % and 3.35 %. The plan's Outcome and
REV-92 now say so. The baseline 33.0 % and the 10.6 % in `CHANGELOG.md` are a like-for-like pair by
the old measure, and were not changed.

### 3. The tree check strips docstrings the program runs (medium, fixed)

`differences()` deletes every docstring before comparing. `src/nanopnp/cli/__init__.py:911` builds
`nanopnp --help`'s description from `__doc__.splitlines()[0]`, and
`tests/tier2/data/merge_number_stability.py` does the same. A reworded first line in either passes
L5 and changes the program. That contradicts L5's "No behaviour can change, proved mechanically".
D2 handled `cli/__init__.py` by hand, but the tool does not hold the line.

**Fix.** A module that reads `__doc__` must keep its docstring's first line. There is a new test.
Still unguarded: a pydantic model's class docstring feeds `model_json_schema()`'s `description`. No
consumer reads it today; the GUI test reads only the bounds.

### 4. Amended L4 is unenforced and broken (medium, partly fixed)

L4, `CLAUDE.md` and `python.md` now require "a docstring on every public function, class and
method of `src/`". Nothing checks this:

- D101–D107 stay ignored in `pyproject.toml`, under the stale comment "a docstring only on the
  public API".
- VER-72 (h) still checks only `nanopnp.PUBLIC`.
- L4's own consequence column still says "Docstring rules D101 to D107 ... are turned off".

`ruff --select D102` finds 47 public methods with no docstring, for example
`core/stages.py:152` `CancelFlag.cancelled`, the `NumpyOps` and `NGSolveOps` methods in
`materials/forms.py`, and 17 in `physics/stabilisation.py`. Most of these predate the PR. The PR
and the plan still state that every public method keeps a docstring.

**Fix.** The stale `pyproject.toml` comment now cites L4 and VER-72 (h). Not done: turning D102 on,
writing the 47 docstrings and extending VER-72 (h). They need an L4 ruling.

### 5. VER-75 (a) claims a check that no test makes (medium, skipped)

The amended VER-75 (a) reads "Read from the source ...: a function or class carries a docstring
only if ..., and no docstring holds a derivation or a history (L4)". `test_prose_share.py` checks no
such property, and none can be read mechanically. The identifier claims a discharge it lacks. The
spec wording is the author's, so this was not changed.

### 6. An unparsable file crashes the tree check (low, fixed)

`normalised_tree` called `ast.parse(source)` with no handler. A strip that empties a body without
leaving `...` raised a `SyntaxError` at `File "<unknown>"`. The docstring promises "the file named
on standard output". **Fix:** `does not parse` is now reported per file, with a test.

### 7. Garbled comment fragments in `load_corrections` (low, fixed)

`materials/corrections.py:198-200` read `# copied: the extra="allow" blocks keep their extra values
by reference` above the copy and `# before validation, so a future schema fails naming ...` above
the schema check. Each sentence had lost its subject. **Fix:** both are rewritten as sentences.

### 8. `.knowledge/` cites deleted docstrings (low, fixed)

Fourteen new entries in `.knowledge/04-clya-geometry-and-charge/index.md`–`08` give "Source: `tests/...py` (module docstring)". This
PR cut those docstrings to one line, so the cited source no longer holds the fact. **Fix:** each now
reads "(module docstring at `3782c43`, before WP45)".

### 9. Two references point at prose that is gone (low, fixed)

- `core/stages.py:81`: the directive reads `# noqa: N818 - see the docstring: this is not a
  failure`, and the condensed docstring no longer said so.
- `tests/tier3/test_reference_charge_map.py:36`: the skip reason says "see the module docstring",
  whose one-line remnant no longer said where the 77 MB table comes from.

**Fix:** both docstrings now carry the fact. The directive and the reason string are untouched, so
the edit stays prose-only.

### 10. Comments above restored docstrings (low, fixed)

Items 19a–19f inserted docstrings below an existing first-line comment. In seven functions the
comment now precedes the docstring, separated from the code it explains:

- `physics/models.py:454`;
- `materials/models.py:103`;
- `pipeline/checks.py:861`;
- `post/forces.py:703`;
- `io/store.py:170`;
- `gui/widgets/viewer.py:66`;
- `validation/stability.py:94`.

In `physics/models.py`, ten lines lie between the comment and `ion_free = ...`. **Fix:** each
comment is moved below its docstring.

### 11. Identifiers and history kept in prose (low, skipped)

The `CLAUDE.md` rule is "Identifiers live in test names and commit messages". L4 adds "no
derivation, history". About 93 `src/` docstrings and 64 `src/` comments still carry `FR-`, `NUM-` or
`WPnn Dn` references, for example `(WP23 D3)` and `(WP29 D3)`. The 156 test-module docstrings start
with an identifier. Some of these are the source citations that `python.md` asks for, so the line
between the two rules is the author's to draw, alongside REV-91. The new test file's `(VER-75 b)` was
removed with finding 2.

### 12. `0.25-0.5 A` (low, fixed)

The deleted docstring of `GRID_SPACING_RANGE_NM` said Å. The condensed comment says `A`, which
reads as amperes. **Fix:** Å, with the section cited.

### 13. Every commit parses each tree four times (low, fixed)

The four whole-tree tests each re-scanned `src/nanopnp` or `tests/`, and each scan parsed every
file twice, about 6.4 s in every commit hook. **Fix:** one parse per file, and a cached `_scan_tree`
per root. The four now take about 2.4 s.

### 14. Two definitions of a directive comment (low, skipped)

- `same_tree.py` matches `#\s*(type:|noqa|...)` anywhere, plus shebang and coding lines.
- `test_prose_share.py` matches six prefixes and nothing else.

So a shebang is code to one and prose to the other. VER-75 (b) names the six, so aligning the two
is a spec question.

## Considered and rejected

- **The CLI description changed.** It did not: `cli/__init__.py`'s first line is unchanged, and so
  is `merge_number_stability.py`'s.
- **A directive moved to another line.** It did not; the per-line pairs are identical.
- **A docstring now trails code.** It does not: no function has a string statement after its first.
- **Doctests were lost.** There were none (`>>>` appears in no removed line).
- **A test was weakened.** It was not. The tree check passes on every test file, so no assertion,
  parametrisation or name changed.
- **`.knowledge/04-clya-geometry-and-charge/index.md`'s "1.25 % consumer leg" contradicts the test's 0.99 %.** It does not: §3.2
  states that the 1.25 % is the reference's own consumer leg.

## Verification of the fixes

- `same_tree.py HEAD` on the working tree: only `same_tree.py`, `test_prose_share.py` and
  `test_same_tree.py` change a syntax tree. Every `src/` edit is prose.
- `ruff check`, `ruff format --check`, `mypy src/` and `uv lock --check` pass.
- `test_prose_share.py` and `test_same_tree.py` pass with the new cases (29 tests).
- Tier 1, in parallel without `test_gui_widgets.py`: 1,999 passed, 1 skipped.
- Not run: `gate.sh run`, Tier 2 and the documentation build. The parent session runs
  them before pushing.
