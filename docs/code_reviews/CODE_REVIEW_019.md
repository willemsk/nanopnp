# Code review: PR 135, WP55, the user-testing protocol

29 October 2026 · `adedce4..46af376` (`claude/blissful-darwin-3msw8e`) · effort: xhigh, with `--fix` · status:
completed

**Scope.** A static review of the WP55 branch: `docs/user-testing/` (protocol, findings log, five sessions), the
nightly test `tests/tier2/test_user_testing_sessions.py` (VER-69), the specification row, the knowledge-base
correction, the plan, `current.md` and the changelog. No `src/` change.

## Summary

The sessions state goals and physics, not numbers, and every command runs. Eleven findings: the weaknesses were in
what the nightly oracle can see and in session 04's state handling, not in the physics.

- **Session 04** kept `store/` between starts, so a second start no longer showed the cancel at the solve;
  the final cell relied on cell order; `selectivity.py` crashed at zero bias, where the transport number is `None`.
- **The test** parametrised over READMEs, not directories, and judged "untagged" by command content, so a
  mis-tagged block went unseen whenever the same command appeared in a tagged one.
- **The sweep session's oracle**: `sweep run` exits 0 on a non-converged point unless `--fail-fast` is given, so
  the nightly could pass on a table with gaps.
- **Records**: the plan's Outcome described the session-02 fix backwards; `current.md` still said "planned"; the
  changelog dated an untagged release; one knowledge sentence has no marker.

## What was fixed and what was run

Eight are fixed. Seven were applied by the review: `notebook.py` empties `store/` at start and exports a
`registered` flag the last cell reads; `selectivity.py` gives the verdict "undefined" at zero bias; session 04's
README says the store is emptied; the test parametrises over session directories, asserts the README exists and cuts
the tagged blocks out before scanning for untagged lines; the plan Outcome and `current.md` are corrected. The
shipping session added `--fail-fast` to session 05's `sweep run` and a clause in step 2, and removed the date from
the unreleased changelog heading. Both session tests (04, 05) were run after the changes and pass (12.7 s, 23.0 s).

## Not fixed

1. **The rectification sentence in the knowledge base has no marker or source.** Open: REV-155.
2. **Session 04's "Then try" variation cannot work by editing `selectivity.py` alone** (`inputs.require('solve')`
   against a registration of `('case','qoi')`; the guard keeps the cached registration). Possibly the friction the
   session exists to expose. Open: REV-155.
3. **The console-fence parser duplicates `validation/examples.py`.** Needs a `src/` change. Open: REV-155.
