# Close a phase

`/np-ship phase <n>` ships the close package of Phase n and tags the release (§8.2.16 R5; §8.4.1).

1. **Find the close package** in the phase plan, `docs/plans/phase-<n>-*.md`: its
   `### The close package`, or else the last package of `## Work packages`. From here, `wp.md` works
   on its WP number.
2. **Run `wp.md`** §0 to §3 on the close package's PR.
3. **Before the review, confirm the close** on this tree. Fix or report each miss:
   - Each other package of the phase is merged.
   - Each row of the phase plan's `## Open decisions` is resolved, or carried with its owner.
   - Each findings log of the phase has the header `closed`, and each `REV-nn` row that the phase
     owns is `fixed`.
   - The numbers of the end-of-phase report are run again on this tree. Never copy them from an
     Outcome.
   - `CHANGELOG.md` has the `[X.Y.0]` section, and `CITATION.cff` has its `version` and
     `date-released`.
   - `docs/plans/current.md` points at the next phase.
4. **Run `wp.md`** §4 to §6, or §5 and §6 if `wp.md` §0.3 sent you to §5.
5. **The tag.** The close gets the release tag `vX.Y.0` alone, with no `-alpha.N` (§8.4.1). After
   the author merges, `/np-ship phase <n>` runs `wp.md` §7 with this tag. The release workflow
   publishes the GitHub Release from the tag (`CONTRIBUTING.md`, *Versions and releases*).

Report as `wp.md` §6 does. Add the confirmations of the close, and the tag, pushed or printed.
