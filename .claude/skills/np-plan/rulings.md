# The ruling round and the records

`phase`, `amend` and `project` read this file. `wp` reads it when the author rules while a package is
planned. A ruling that changes a clause amends that clause in the same commit, and the ruling's row
names the clause.

## Versions agree

Before a new version is named, these agree: §2.7 and its Versioning NOTE, §3's Release column,
§8.1, `CHANGELOG.md`, `current.md` and the published tags (`git ls-remote --tags origin 'v0.*'`; a
hosted clone is shallow). One minor version per phase. A disagreement goes into the round.

## What a phase inherits

1. `knowledge/index.md`, then `.claude/rules/physics-numerics.md` and `.claude/rules/python.md` (a
   path-scoped rule does not load while you write only Markdown).
2. `SPECIFICATION.md` §8.1: Phase n's row and its GUI and documentation increments. Then §8.4 and
   `specification/history/index.md`, for the rulings that already bind Phase n. Read a record only
   where a ruling bears on the phase. Cite a ruling already taken; never ask it again.
3. The previous phase plan: its `## End-of-phase report` (above all what it **carries**), its open
   `## Open decisions` rows, and each **Live for later packages** line in its delivered summaries and
   WP Outcomes.
4. §10's open `OPN-` items and §9's `RSK-` register: which of them this phase retires or can close.
5. Each input note under `docs/plans/` that names this phase. Its decisions bind; its open questions
   join the round.
6. Appendix A: the requirements tagged for this phase's version and not yet discharged.

## Draft the decisions

A phase decision is one that more than one package depends on, or one the author must own: the order
of evidence, a choice that each later package inherits, scope and deferrals, a new dependency, a spec
amendment, versioning and the close. Always cover these:

- **The gate, pre-registered.** Each completion criterion names its test, its tolerance and where the
  tolerance was argued, and a predicted value where one is possible. It also names the **fallback on
  a miss**: investigate, argue the tolerance again (a spec amendment, never a quiet slackening), or
  waive and carry.
- **What the author supplies**: archive data, rulings that only the author can give, observations by
  a person (QR-10). Give each the package that needs it and what happens if it does not arrive.
- **Who merges and who tags.** The author merges. A session can be unable to push tags, so say
  whether the close tags or prints the commands. Say whether it takes the release tag alone, with no
  `-alpha.N` (as §8.2.5 E5 ruled for Phase 3).

Draft each decision as one question with its identifiers. Give two to four options, each with its
consequence for correctness, scope, gate cost and the clause it amends. Put the recommendation first,
with the reason. Also draft:

- the **work-package sequence**;
- the numbered **completion criteria**. Each is checkable by a named test in the test scope of
  §8.2.13 N1, or by the code and review for an item outside it, or by a named observation;
- what the phase **excludes**, and where each excluded item goes.

## Put it to the author

Ask through `AskUserQuestion`, at most four questions in a call. Each question carries the clause at
stake, the cost of each option and what is already ruled. First ask the decisions that change the
package sequence, then the sequence, then the rest. Record a prose ruling in the author's words. If
`AskUserQuestion` is not available, put the questions in one numbered message and end the turn. If
the author volunteers a scope change, it is a ruling: record it, then check again what it moves.

Stop when each decision is ruled, or left open with an owner. Never write the plan on a guess. Ask
each unruled decision that affects correctness, or carry it into `## Open decisions` with the package
that must settle it.

## Where the rulings are written (§8.2.16 R3, R4, R11, R12)

- **A ruling round is a new record**, `specification/history/<kk>-<slug>.md`, with `<kk>` one above
  the highest present. It starts with the front matter `type: Ruling Record`, `title` and
  `description`. Then come `#### 8.2.<k> <title>, agreed <date>`, a paragraph on how the round was
  taken, and the table `| # | Decision | Consequence | Clause changed, and when |`. Rulings continue
  the letter series, numbered from 1.
- `specification/history/index.md` lists the record as `* [title](file) - description`. One
  `* <id> - <where it holds now>` line per ruling follows: its clause, `open: <the package that lands
  it>`, `spent` or `superseded by <id>`.
- Each ruling amends its clause in the same commit. If a ruling sets a standing rule of process with
  no clause of its own, restate it in §8.4, with a pointer to the ruling (R3).
- **A ruling taken at a package's plan, on a record's date, is a row added to that record**, marked
  *Added <date>, at WP<n>'s plan.* A superseded ruling gets only a pointer in its first cell, such as
  *Its command names are amended by R12.*; its text stays.
- **A phase plan states its current scope** (R4). Rewrite an amended package entry to what holds now,
  with no `Amended` blockquote. Append the amendment's text to `docs/plans/phase-<n>-record.md` as
  `## Amended <date> (§8.2.<k> <ids>)`, with the entry quoted as it was. If the record is missing,
  create it with `phase-4-record.md`'s header: a title, a paragraph saying that it is read on demand,
  and `---`.

## Finishing

Gate and push (the core). Open or reuse the branch's PR against `main`, and do not ask. Its base is
`main` and its title is the commit's subject. Its body is an In brief (the core's template), the
rulings, what the level names, the open decisions, the checks run, and the attribution footer. If you
cannot create the PR, report the blocker and the pushed branch.
