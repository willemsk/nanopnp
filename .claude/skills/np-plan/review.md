# Review a plan and summarise it for approval

Every level of `/np-plan` ends in two calls. The level's own call writes, commits, gates and pushes the
plan, opens its PR, reports and pauses. After the author compacts, `/np-plan <level> [n] review` reviews
the plan, fixes what the review finds, gates and pushes again, and ends with the manager's summary
(§8.2.33 AI2, AI3). The review reads the plan after a compaction, not through the context that wrote it.

## The pause

The level's commit names, in `docs/plans/current.md`, `/np-plan <level> [n] review` as the next step,
before the level's own next step. After the level's report:

1. Print a prompt in a `text` block. It holds `/compact`, the level and n, the plan's path, the PR, the
   commit, the close calls that the plan's text does not hold, and "resume with
   `/np-plan <level> [n] review`".
2. End the turn. The author compacts and resumes. A skill cannot run `/compact` itself.

## The review

1. **The head.** For `wp`, take the package's PR as the core's *The package's PR and branch* says. For
   another level, take the open PR whose title is the level's commit subject. Fetch it and check out
   its head as the core says. The tree is clean. Read the plan and `docs/plans/current.md` from it.
2. **The review.** Call the skill directly from this session, never inside an `Agent`:

   ```
   Skill(skill="code-review", args="medium --fix --max-findings all <head branch> -- Write the report to docs/code_reviews/CODE_REVIEW_NNN.md, NNN one above the highest present. Review of a plan commit. Check each claim the plan makes about the code against the code at this head, each decision against SPECIFICATION.md and the author's rulings, each verification row for how its test gets the object it checks, and the plan against its level's caps and sections in .claude/skills/np-plan/. Run no tests and no gate.sh: the review turn gates afterwards.")
   ```

   On Copilot, call the built-in `code-review` agent as `hosts/copilot.md`'s *Code review* says. If the
   review wrote no report, write `docs/code_reviews/CODE_REVIEW_NNN.md` in the shape of the latest one,
   with NNN one above the highest present.
3. **The fixes.**
   - A fix keeps every ruling of the author. A finding that would change one goes to the author as
     the core's *Putting a choice to the author* says, before the commit; the ruling is recorded as
     `rulings.md` says.
   - A finding not fixed is a `REV-nn` row with its section (`CLAUDE.md`, *Open items*), or one of the
     plan's open questions if it blocks the implementation.
   - A fix that changes specified behaviour amends the specification in the same commit (the core's
     *Normativity*).
   - Count the plan's words again against its level's caps, each with its 10% allowance. Trim prose
     only beyond it; never drop a required check or a grounding fact. If the caps cannot hold the
     fixes, split the package.
4. **The commit.** Commit `docs: <the level's commit subject>, review fixes`, with the identifiers in
   the body. `docs/plans/current.md` names the level's own next step. Gate and push (the core). Bring
   the PR's body to the tree's state (the core's *PR contract*): its In brief if a decision moved, and
   under **Verification** the review's report and its findings' outcomes.
5. **The summary.** Report the manager's summary below. Then stop.

## The manager's summary

The final report, in the chat, for the person who approves the plan and does not read code. Plain words.
Name a file, command or identifier only where the reader acts on it or will meet it, and say what it
is. About 1,000 words; never drop a decision, ruling or risk to meet the count.

1. **Title and one line.** `# <the level and n> for approval: <name>`, then what the plan delivers in one
   sentence. Then the cost in sessions, agent hours and your touches (§8.3), the release it lands in,
   and the decisions still open to the author.
2. **What you get.** What the reader will be able to do or will notice when the work lands.
3. **What it builds on.** What must be in place first, and what the plan satisfies or closes, in words,
   with the identifier in brackets.
4. **The decisions.** One short paragraph each, in plain words: what was chosen and why, and whether
   you ruled it or the plan decided it. Mark in bold each one that changes what an existing user sees.
5. **The rulings and the specification.** Each ruling taken in this round, in the author's terms, and
   each clause the plan amends.
6. **What the checks changed.** What reading the code and the review moved in the plan, one line each.
7. **How the work runs.** For `wp`, the items in groups, with the pauses and what goes to a sub-agent;
   for `phase` and `amend`, the package sequence, the provisional ones and what each waits on; for
   `project`, the phases with their releases.
8. **How we'll know it works.** Each verification row or completion criterion in one plain sentence.
9. **What it does not do.** Each deferral and who takes it.
10. **Risks.** A table `Risk | Guard`: each risk and how it would be noticed.
11. **What I need from you.** Approve, or name the decision to change; what the author must supply,
    and by when; the next command.
