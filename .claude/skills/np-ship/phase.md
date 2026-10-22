# Close a phase

`/np-ship phase <n>` ships Phase n's close package and tags the release (§8.2.16 R5; §8.4.1).

1. **Resolve the close package** from the phase plan, `docs/plans/phase-<n>-*.md`: its
   `### The close package` or the last package of `## Work packages`. Its WP number is the `<n>`
   `wp.md` works on from here.
2. **Run `wp.md`** §0 to §3 on the close package's PR.
3. **Before the review, confirm the close**, on this tree, and fix or report each miss:
   - every other package of the phase is merged;
   - each row of the phase plan's `## Open decisions` is resolved or carried, with its owner;
   - each findings log of the phase has its header `closed`, and every `REV-nn` row the phase owns is
     `fixed`;
   - the end-of-phase report's numbers are re-run on this tree, never copied from an Outcome;
   - `CHANGELOG.md` has the `[X.Y.0]` section, and `CITATION.cff` its `version` and
     `date-released`;
   - `docs/plans/current.md` points at the next phase.
4. **Run `wp.md`** §4 to §6.
5. **The tag.** The close takes the release tag `vX.Y.0` alone, with no `-alpha.N` (§8.4.1).
   `/np-ship phase <n>` after the author merges runs `wp.md` §7 with it. The release workflow
   publishes the GitHub Release from the tag (`CONTRIBUTING.md`, *Versions and releases*).

Report as `wp.md` §6 does, adding the close's confirmations and the tag, pushed or printed.
