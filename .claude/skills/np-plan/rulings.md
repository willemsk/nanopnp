# The ruling round and the records

Read by `phase`, `amend` and `project`, and by `wp` when the author rules while a package is
planned. A ruling that changes a clause amends that clause in the same commit, and the ruling's row
names the clause.

## Draft the decisions

A phase decision is one that more than one package depends on or the author must own: order of
evidence, a choice every later package inherits, scope and deferrals, a new dependency, a spec
amendment, versioning and the close. Always cover:

- **the gate, pre-registered.** Each completion criterion names its test, tolerance and where the
  tolerance was argued, a predicted value where one can be made, and the **fallback on a miss**:
  investigate, re-argue the tolerance (a spec amendment, never a quiet slackening), or waive and
  carry;
- **what the author supplies**: archive data, rulings only they can give, observations by a person
  (QR-10), each with the package that needs it and what happens if it does not arrive;
- **who merges and who tags.** The author merges. A session may not be able to push tags, so say
  whether the close tags or prints the commands, and whether it takes the release tag alone, with
  no `-alpha.N` (as §8.2.5 E5 ruled for Phase 3).

Draft each decision as one question with its identifiers, two to four options (consequence for
correctness, scope, gate cost, clause amended) and a recommendation first, with why. Also draft the
**work-package sequence**, the numbered **completion criteria** (each checkable by a named test, in
the test scope of §8.2.13 N1, or by the code and review where the item is outside it, or by a named
observation) and what the phase **excludes**, with where each goes.

## Put it to the author

Ask through `AskUserQuestion`, at most four questions a call, each carrying the clause at stake,
the cost of each option and what is already ruled. Ask the decisions that change the package
sequence first, then the sequence, then the rest. Record a prose ruling in the author's words.
Without `AskUserQuestion`, put the questions in one numbered message and end the turn. A scope
change the author volunteers is a ruling: record it, then re-check what it moves.

Stop when every decision is ruled or left open with an owner. Never write the plan on a guess: an
unruled correctness-relevant decision is asked, or carried into `## Open decisions` with the
package that must settle it.

## Where the rulings are written (§8.2.16 R3, R4, R11, R12)

- **A ruling round is a new record**, `specification/history/<kk>-<slug>.md`, `<kk>` one above the
  highest present. It opens with the front matter `type: Ruling Record`, `title` and `description`,
  then `#### 8.2.<k> <title>, agreed <date>`, a paragraph on how the round was taken, and the table
  `| # | Decision | Consequence | Clause changed, and when |`. Rulings continue the letter series,
  numbered from 1. The record is listed in `specification/history/index.md` as
  `* [title](file) - description`, followed by one `* <id> - <where it holds now>` line per ruling:
  its clause, `open: <the package that lands it>`, `spent` or `superseded by <id>`. Each ruling
  amends its clause in the same commit; one that sets a standing rule of process with no clause of
  its own is restated in §8.4, pointing to the ruling (R3).
- **A ruling taken at a package's plan, on a record's date, is a row added to that record**, marked
  *Added <date>, at WP<n>'s plan.* A superseded ruling gains only a pointer in its first cell, such
  as *Its command names are amended by R12.*; its text stays.
- **A phase plan states its current scope** (R4). An amended package entry is rewritten to what
  holds now, with no `Amended` blockquote, and the amendment's text is appended to
  `docs/plans/phase-<n>-record.md` as `## Amended <date> (§8.2.<k> <ids>)`, quoting the entry as it
  stood. A missing record is created with `phase-4-record.md`'s header: a title, a paragraph saying
  it is read on demand, and `---`.
