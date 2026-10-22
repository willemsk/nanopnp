---
type: Ruling Record
title: "8.2.15 The work-package plan grounded in the code, agreed 22 October 2026"
description: "Records the ruling on WP51's plan, agreed 22 October 2026, which read the plan against the code, finding points an implementer could guess at."
---

#### 8.2.15 The work-package plan grounded in the code, agreed 22 October 2026

A ruling by the author after WP51's plan was written. Read against the code, that plan had left an
implementer to guess at points that could have broken it. It would have recorded the solve's Newton
steps through a hook only some callers supply. It would also have drawn a supplied mesh from a
payload that only a generated mesh carries. Fitting the fixes under L7's cap took cutting the plan's
own prose. The letter series continues at Q.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| Q1 | *Its caps are extended by §8.2.16 R11.* **A work-package plan is grounded in the code, and holds at most 2,500 words outside its Outcome annotations, of which at most 1,500 lie outside its `### Grounding` section.** The grounding pass reads, for each decision and work item, the code it changes or relies on. Grounding records, by symbol: what that code does today; the call path the change rides on, and whether it runs on the default path; the shape of what it reads and writes; every variant of its input; the registry and layering rows it adds; and how each test obtains the object it checks. These are facts, not design. Six decisions, the In brief's 250 words and no `## Design` heading stand | The implementer re-decides nothing the plan could have settled, and a plan that guessed is caught before the work starts, not by a failing gate. The added budget buys only facts, so the decisions stay as short as L7 made them | Supersedes L7's 1,500-word cap. The `wp-plan` and `wp-implement` skills and `CLAUDE.md`, in this commit |
