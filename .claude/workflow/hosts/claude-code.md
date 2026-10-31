# Claude Code host mapping

The shared contract is [the workflow core](../core.md); [the host index](../hosts.md) selects this
file. These are the established Claude Code instructions, not a claim that the outstanding live
regression (REV-168) has run.

## Questions

Use `AskUserQuestion`, at most four questions in one call. Give each two to four options with the
recommended one first and marked *(Recommended)*, and each option's consequence. If the tool is
unavailable, put the questions in one numbered message and end the turn.

## Agents and models

Use the `Agent` tool with the named type and model; pass the plan's tier and the agent's specified
effort. The tiers and executors are in the core. If `$ARGUMENTS` or `${CLAUDE_SKILL_DIR}` appears
literally, the arguments are the text after the command and the directory is
`.claude/skills/<name>/`.

## Code review

For `np-ship/wp.md` §4, call `Skill` directly in this session, never inside an `Agent`, with
`skill="code-review"` and arguments `xhigh --fix <pr-number> out=docs/code_reviews/`. Append
`--` and the static-review brief from §4. The direct skill starts its own review agent; inside an
`Agent` it returned no findings. The evidence, assessment and fix rules in §4 remain in force.

## CI

At `np-ship/wp.md` §4 or on the §0.3 resume path, subscribe with `subscribe_pr_activity`; follow
the steward's bounded wakes and cancel the subscription and fallback when it says. If subscription
or scheduling is unavailable, record the checkpoint, report the automation limit and hand off rather
than polling.

## Safety hooks

`.claude/settings.json` invokes `gate.sh` for `Bash` and `format.sh` after `Edit`, `Write` or
`MultiEdit`. With `COPILOT_CLI` unset, `gate.sh` emits its denial JSON, writes the reason on stderr
and exits 2 (§8.2.26 AB1); inability to emit the JSON also exits 2. If a Claude Code session
inherits `COPILOT_CLI`, the hook instead selects Copilot's exit-0 protocol; that case is unverified
(REV-166). Start Claude Code without that variable, and run the gates by hand if the hook environment
cannot be verified. A timeout lets the command through;
the gate's settings use `timeout: 1800`. The hook reads one command: never commit or push by typing
into an already running shell. The git-native `.githooks/pre-push` requires a passing push-gate stamp
when the clone sets `core.hooksPath`.

Run the gates in `CLAUDE.md` before committing and pushing. REV-168 still owns the live Claude
Code regression; the Copilot Phase 0 stop rule and manual gate are in its host mapping.

## Session operations

Start the gate with Bash `run_in_background`:
`.claude/hooks/gate.sh run > <log> 2>&1; echo "exit $?" >> <log>`. Wait in the same turn with
`until grep -q '^exit ' <log>; do sleep 10; done` in the foreground; repeat the wait after its
ten-minute limit. At a `/compact` checkpoint, complete and push the checkpoint, print its prompt
and end the turn. Use the session's scratchpad as `<s>`.

## GUI artefacts

For `np-gui publish`, load `artifact-design` and `artifact-capabilities`, declare `db` as the
latter says, publish the gallery and files with the Artifact tool, private by default. For
`collect`, use `ArtifactData` (`list`) on the `verdicts` collection. If the required artefact tools
are unavailable, stop and hand off; do not claim a gallery was published or collected.
