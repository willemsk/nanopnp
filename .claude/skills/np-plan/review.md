# Review a plan and summarise it for approval

Every level of `/np-plan` ends in two calls. The level's own call writes, commits, gates and pushes the
plan, opens its PR, reports and pauses. After the author compacts, `/np-plan <level> [n] review` reviews
the plan, fixes what the review finds, gates and pushes again, and ends with the manager's summary
(§8.2.33 AI2, AI3). The review reads the plan after a compaction, not through the context that wrote it.
A work package's plan has no review run: its review is *The self-check* below, which its writer also
runs before the commit (§8.2.56 BF3).

## The review

1. **The head.** For `wp`, take the package's PR as the core's *The package's PR and branch* says. For
   another level, take the open PR whose title is the level's commit subject. Fetch it and check out
   its head as the core says. The tree is clean. Read the plan and `docs/plans/current.md` from it.
2. **The review.** For `wp`, run *The self-check* below and write its result as the report. For
   another level, call the skill directly from this session, never inside an `Agent`:

   ```
   Skill(skill="code-review", args="medium --fix --max-findings all <head branch> -- Write the report to docs/code_reviews/CODE_REVIEW_NNN.md, NNN one above the highest present. Review of a plan commit. Check each claim the plan makes about the code against the code at this head, each decision against SPECIFICATION.md and the author's rulings, each verification row for how its test gets the object it checks, and the plan against its level's caps and sections in .claude/skills/np-plan/. Run no tests and no gate.sh: the review turn gates afterwards.")
   ```

   If the review wrote no report, write `docs/code_reviews/CODE_REVIEW_NNN.md` in the shape of the
   latest one, with NNN one above the highest present. A self-check that finds nothing writes no
   report and commits nothing: go to step 5.
3. **The fixes.**
   - A fix keeps every ruling of the author. A finding that would change one goes to the author as
     *Putting a choice to the author* in `.claude/workflow/author.md` says, before the commit; the ruling is recorded as
     `rulings.md` says.
   - A small finding is fixed (§8.2.58 BH1). A finding not fixed, which outlives the session, is a
     `REV-nn` row with its section (`CLAUDE.md`, *Open items*), or one of the plan's open questions if
     it blocks the implementation.
   - A fix that changes specified behaviour amends the specification in the same commit (the core's
     *Normativity*).
   - Count the plan's words again against its level's caps, each with its 10% allowance. Trim prose
     only beyond it; never drop a required check or a grounding fact. If the caps cannot hold the
     fixes, split the package.
4. **The commit.** Commit `docs: <the level's commit subject>, review fixes`, with the identifiers in
   the body. `docs/plans/current.md` names the level's own next step. Gate and push (the core). Bring
   the PR's body to the tree's state (`.claude/workflow/finish.md`, *The PR contract*): its In brief if a decision moved, and
   under **Verification** the review's report and its findings' outcomes.
5. **The summary.** Report the manager's summary below. Then stop.

## The self-check

A fixed list, run by the session or helper that holds the plan, on the plan as committed or about to
be. Read the code it names at this head; run no tests. Each line passes, or is fixed, or is a finding
for step 3.

1. Each claim of `### Grounding` holds at this head: the symbol exists and does what the line says.
2. Each decision agrees with `SPECIFICATION.md` and the author's rulings, and its *Why/source* says
   "ruled by the author" with the ruling, or "decided by the plan".
3. Each choice that changes what a user sees, moves the scope or trades time against quality was put
   to the author (*Putting the decisions to the author* in `wp.md`).
4. Each work item names its files, its decisions, its executor and a done-criterion, which names
   its test files or "the land's push gate", never "Tier 2" or "the carried tests" alone, or for an
   item outside the test scope "the code and review say so"; an implementer
   can write it without opening a file the plan does not name or choosing between two behaviours.
5. Each verification row says how its test gets the object it checks; a decision that says *never*,
   *always* or *every* has one assertion per point of failure; each claimed in-scope `VER-`/`VAL-` has
   its row.
6. The sections of `wp.md`'s *What to write* are present, the counts are within *The caps* with
   their 10%, and the In brief is within 275 words, with no identifiers or backticks.
7. Each deferral in `### Out of scope` names its owner; each open question blocks the build.
8. A change of specified behaviour amends its clause in the same commit.

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
7. **How the work runs.** For `wp`, the model that planned it, then the items in groups, with the
   pauses and what goes to a sub-agent;
   for `phase` and `amend`, the package sequence, the provisional ones and what each waits on; for
   `project`, the phases with their releases.
8. **How we'll know it works.** Each verification row or completion criterion in one plain sentence.
9. **What it does not do.** Each deferral and who takes it.
10. **Risks.** A table `Risk | Guard`: each risk and how it would be noticed.
11. **What I need from you.** Approve, or name the decision to change; what the author must supply,
    and by when; the next command and the model it runs on.
