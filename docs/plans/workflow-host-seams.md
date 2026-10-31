# Plan: separate workflow intent from host mechanics

Planning, not requirements: `SPECIFICATION.md` governs. This is outside the work-package sequence
and follows [the Copilot host plan](copilot-host.md); it does not close REV-166 by itself.

## In brief

**What changes.** The workflow keeps one set of project rules. A short host index directs each
assistant to its own instructions for carrying those rules out. The skills describe what must
happen rather than assuming a particular assistant's tool names.

**Cost.** A small documentation and workflow revision, plus the outstanding hands-on host checks.
Existing hook adapters change only where an observed difference requires it; no new adapter
framework is proposed.

**What could go wrong.** A shared description could hide a weaker review or an unavailable tool, or
a hook could allow an unsafe action. Each host's capability and its limits stay explicit, and the
live hook checks remain a prerequisite for trusting them.

**Your call.** The author chose to document the seams and adjust existing adapters only where
needed. No other decision waits on the author in this plan.

## Position and constraints

The current worktree has uncommitted REV-166 changes on top of the Copilot-host implementation:
the shared WSL hook was probed, the exit-0 Copilot refusal was ruled in §8.2.26 AB1, and
`format.sh` handles the observed patch payload. REV-166 remains **accepted**, not fixed. Its
remaining probes and the manual-gate rule are in `docs/project/review-items.md` and
`.claude/workflow/hosts.md`. Do not assume a fresh session inherits these uncommitted files.

The project rules stay in `.claude/`, the specification remains normative, and one host drives a
branch at a time (§8.4.4; §8.2.25 AA1 to AA4). Copilot's narrower review and CI hand-off remain
explicit; unavailable artifact tools stay unavailable. No new executable host-adapter layer,
third host, GUI port, application code or dependencies are in scope. Antigravity's existing
adapter behaviour is a regression constraint, not a claim that it is a supported workflow host.

### Grounding

- `.claude/workflow/core.md` has common sequencing and directs non-Claude hosts to `hosts.md`.
  The latter currently mixes host selection, Copilot mappings, shared coordination rules, setup and
  unresolved probes.
- `.claude/skills/np-plan/rulings.md` and `.claude/skills/np-gui/grill.md` name Claude's
  `AskUserQuestion`, then add Copilot's one-question substitute.
- `.claude/skills/np-ship/wp.md` embeds a Claude review-skill call and PR subscription, with
  host-specific replacements in `hosts.md`; `.claude/skills/steward/SKILL.md` repeats the CI
  hand-off. Copilot's built-in reviewer does not assess everything the other review covers.
- The five `SKILL.md` entry points use `$ARGUMENTS` and `${CLAUDE_SKILL_DIR}` with host fallbacks.
  `hosts.md` also maps agent/model invocation, background processes, compaction, GitHub tools,
  scratch space and artifact publishing.
- `.claude/hooks/gate.sh`, `.agents/hooks/adapter.sh` and `.github/hooks/nanopnp.json` are the
  existing refusal implementations. `session-start.sh` resolves the primary checkout from the
  Git common directory and can fetch or fast-forward it. A probe in an ordinary linked worktree
  would therefore touch that clone's primary checkout.

## Finish the REV-166 probe safely

This is the route to a fresh session; it is not evidence that the unprobed hooks work.

1. In the current worktree, prepare a **separate disposable clone** under a specifically named
   scratch directory. Clone the current committed branch locally, then copy the relevant
   uncommitted tracked changes and explicitly selected untracked fixtures into the clone; verify
   the copied diff against this worktree. A clone alone copies `HEAD`, not these changes. Never
   copy credentials, `.venv` or unrelated untracked files. Give the clone its own `.git`; verify
   its absolute Git common directory and primary checkout are inside the scratch clone. Its
   `origin`, if retained for app repository recognition, is for reads only: do not push from it.
2. Put the temporary `.github/hooks/probe.json`, `.claude/settings.local.json` and their recorder
   **in the scratch clone before starting the agent**. Open that clone as its own WSL repository
   in the app and start a fresh session on its exclusively owned checkout, using the app's branch
   workspace if available. Unlike a new worktree, it sees the untracked probe files at startup;
   no Claude session shares this checkout. Confirm the app identifies it as a repository, not a
   folder. If that setup is unavailable, stop and report it rather than substituting a CLI probe
   and calling it an app result. The ordinary linked-worktree path still needs its own control
   once a safely gated snapshot can be made available to it.
3. Record only the event, source, ordering/timing, tool name, argument types and safe sentinel
   arguments, plus whether `COPILOT_CLI` and `CLAUDE_PROJECT_DIR` are set. Do **not** dump the
   environment or unrestricted payloads. Exercise harmless shell, patch create/update/move,
   a GitHub MCP read, and a distinct create tool and `write_bash` only if offered. Record the
   actual payload shapes and whether each hook source fires; concurrent events give a partial
   order, not an invented total order.
4. For each loaded pre-tool source, use a harmless sentinel command to compare structured exit-0
   denial and exit-2 denial, including the agent-visible reason. Independently set a 60-second
   timeout for that source (`timeout` in Claude settings, `timeoutSec` in GitHub hook JSON), sleep
   40 seconds and deny; record timestamps and whether the command
   was blocked. A pass shows that the 30-second default did not cut that probe short, not that
   1,800 seconds was measured. If no refusal is obeyed or the configured timeout is not honoured,
   the Phase 0 stop rule applies: no Copilot commits until fixed.
5. To identify a GitHub MCP **write** tool, only attempt a deliberately invalid destination and
   harmless sentinel content, with a pre-tool probe intended to deny it; if validation prevents
   the hook from seeing the call, record that. Do not write to a real repository or rely on a
   possibly missing hook to prevent a real mutation. If `write_bash`, write tools or another
   required surface are unavailable, record them as **unverified**; do not infer their payloads
   from a read tool or an offline replay.
6. Copy only sanitised observed fixtures and results back to this worktree. Replay each fixture
   against the actual hook, correct discrepancies with the corresponding specification change
   where needed, and record the result in REV-166 and the host mapping. Remove only the named
   probe files and scratch clone after confirming their paths. Set REV-166 `fixed` only when
   every required source and applicable tool is evidenced; otherwise leave it open and keep the
   manual-gate rule. REV-167 and REV-168 remain separate.

## Proposed host seam

Keep `.claude/workflow/hosts.md` as the stable entry point. Make it a short index that identifies
the current host from reliable session context and directs it to
`.claude/workflow/hosts/claude-code.md` or `.claude/workflow/hosts/copilot.md`. An unknown host or
an unverified safety capability must not be treated as supported: stop on an unknown host; for
Copilot with REV-166 still open, follow the existing manual-gate rule unless the Phase 0 stop rule
has fired. Do not guess a host from a single variable. Keep cross-host invariants in `core.md`,
not duplicated in both host files. The host files contain the actual tool invocation, availability,
failure behaviour and evidence date, with links back to the shared contract.

| Seam | Shared intent | Host-specific mapping and limits |
|---|---|---|
| Questions | Obtain each author decision without assuming an answer | Tool, choice shape, batching and permitted fallback |
| Agents and models | Dispatch the named reviewer or executor at the specified tier; consume its result | Tool, model ID, effort and instruction inheritance |
| Review and CI | Record the reviewed revisions, completed scope, findings and any unassessed work; hand off or monitor CI according to the ruling | Review invocation and coverage; subscription or Copilot's checkpoint-and-stop |
| Safety hooks | Gate commits and pushes, deny with a reason, preserve timeout and failure rules | Payload and denial protocol, hook loading and git-native guard; explicit unverified paths |
| Session operations | Preserve checkpoint, branch ownership and scratch isolation | Background wait, compaction, worktree restrictions and scratch location |
| GUI artifacts | Publish and collect only when the required capability exists | Claude artifact tools; Copilot explicitly stops for unsupported levels |

These are instruction seams, not a promise that every harness can perform every operation. A
capability matrix identifies **supported**, **partial**, **unavailable** or **unverified**, and
names the required hand-off. In particular, do not present Copilot's high-confidence review as a
standards or specification review.

## Work items

Executor: the main implementation session, Sonnet by default (§8.4.5). No implementation is part
of this plan.

1. **Probe and inventory.** Carry out the REV-166 procedure above. Inventory each host-specific
   construct in the core, four `np-*` skills and steward, with its current rule and evidence. Documentation
   restructuring may proceed while a tool is unavailable, but it must not close that open item or
   claim the missing evidence.
2. **Split the host mapping.** Create the index and two host files; move shared coordination rules
   to `core.md` and keep each host-specific fact in one place. Update `CLAUDE.md` and references.
   If §8.4.4 or §8.4.5 no longer describes the layout, amend the current clause in the same commit;
   preserve existing dated rulings and add an author ruling only if behaviour changes.
3. **Make skill instructions host-neutral.** Replace concrete invocation instructions at the
   seams above with the shared intent and the host-file reference. Preserve questions, review
   evidence, test scope, CI failure classes, unsupported operations and checkpoints. Adjust an
   existing hook or adapter only for an observed mismatch, keeping both hosts' and Antigravity's
   established protocols.
4. **Verify and record.** Walk `/np-plan`, `/np-implement`, `/np-ship`, `/np-gui` and steward for
   each host: each operation resolves to one instruction, including its unavailable and
   partial-capability path. Replay sanitised hook fixtures and the existing refusal, timeout and
   formatting checks where applicable. Review the diff against the previous contracts; run the
   repository gate and strict documentation build when their inputs change. Do not add off-scope
   tests (§7.1). Record unfinished evidence in its existing REV row and never mark it fixed by
   documentation alone.

**Done when:** both hosts can find their instructions without reading the other's mechanics;
every listed seam preserves its existing outcome or names its limitation; safety claims have live
evidence or remain open; the specification and navigation match the chosen layout.

## Execution record

The host index selects a single mapping and records capability limits. The core owns branch and
worktree coordination. The inventory and its destinations are:

| Surface | Shared intent | Host mapping and evidence |
|---|---|---|
| `/np-plan` | Route the level; ask and record each author ruling | Questions and argument expansion in each host file; Copilot batching is limited to one question per call |
| `/np-implement` | Execute each named work item and checkpoint | Agent/model dispatch, scratch and compaction in each host file; Copilot agent metadata remains REV-167 |
| `/np-ship` | Record review scope and evidence, fix findings, hand off or monitor CI | Claude Code review skill and subscription; Copilot's narrower review and CI hand-off; live regression remains REV-168 |
| `/np-gui` | Render, review, publish, collect and grill | GUI artifacts in each host file; Copilot cannot publish or collect, so grill cannot complete there |
| Steward | Classify failures and keep a bounded checkpoint | Host CI mapping; Copilot checkpoints and stops instead of subscribing |
| Safety | Gate commits and pushes, retain denial and timeout rules | Host safety sections; both sources' fresh-session probe evidence and remaining write-tool surfaces in REV-166 |

An independent scratch clone was opened as a WSL app repository branch workspace. Fresh-session
recorder probes observed both sources' shell, patch and MCP-read events, refusal forms and a
40-second denial under a 60-second timeout. The actual write-tool paths and a linked-worktree
control remain unverified. REV-166 remains accepted with its manual-gate rule; its record gives the
evidence and the limits.
