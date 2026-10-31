# Code review 022 — workflow host seams

Reviewed on 31 October 2026 at the author's request, against
`docs/plans/workflow-host-seams.md` and the repository's standards.

- Base: `a1336553852acad86047b93cd3c24c2c7337565a`
- Reviewed head: `f5888bd5405613ca6d53454bc003c5ad178c1d7a`
- Pass: the two-axis `code-review` skill, with separate standards and specification reviewers.
- Status: completed. The write-tool hook paths and linked-worktree control remain unverified
  under REV-166; the review did not turn offline checks into live evidence.

## Standards

**Documented-standard violation.** Generic uses of “artifact” appeared in the GUI skill, host
index and mappings, and seam plan, contrary to `CONTRIBUTING.md`, *Style* (British spelling).
Changed to “artefact” outside official tool and skill names.

**Possible Duplicated Code.** The Copilot adapter and shared formatter both recognised the raw
patch header. The additional Copilot formatting path was removed, leaving the shared formatter.

**Possible Duplicated Code.** The static-review restrictions appeared both in
`.claude/skills/np-ship/wp.md` and in the Claude Code invocation. The host mapping now refers to
the single brief in §4.

## Spec

**Missing or partial — CI resume.** The Copilot CI mapping always checkpointed and stopped, so
`np-ship/wp.md` §0.3 could not act on completed CI, although §8.2.25 AA3 says it resumes when CI
ends. The mapping now reads live state on resume, hands off pending or blocked work, follows the
steward on failures, and reports a green, mergeable PR through §6.

**Missing or partial — review model.** The Copilot built-in reviewer had an effort but no model,
although §8.4.5 and AA7 require the model and effort at each sub-agent call. The mapping now names
the default Sonnet tier and `xhigh` effort.

**Unrequested scope — duplicate patch formatting.** `.github/hooks/nanopnp.json` routed
`apply_patch` to a second formatter despite the observed shared `Edit` hook. The Copilot host plan
calls for “One hook path, not two” (Phase 3). The additional route and adapter branch were removed;
the shared formatter remains the patch path.

**Implementation appears wrong — inherited host variable.** `gate.sh` selects the refusal protocol
solely from `COPILOT_CLI`, so a Claude Code hook inheriting that variable selects Copilot's exit-0
protocol instead of AB1's exit 2. That environment has not been probed. Recorded under REV-166;
the Claude Code mapping says to start without the variable and gate by hand when the hook
environment cannot be verified.

**Summary:** three standards findings addressed; three specification findings addressed and one
unverified safety case retained under REV-166.
