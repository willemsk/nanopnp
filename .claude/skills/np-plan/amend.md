# Amend a phase

`/np-plan amend <n>` keeps a phase plan true. It is the only route for these changes:

- planning the provisional packages after an opening study reports: read its report and findings
  log, put the decisions it raises to the author as `rulings.md` says, then replace the provisional
  entries;
- adding or dropping a package in mid-phase: the author's reason, its place, its identifiers;
- planning the later phases again: the rulings, §8.1's rows, and the later plans or input notes.

It has the same two turns as `phase.md`: the ruling round, then the write-up.

1. Read what `rulings.md`'s *What a phase inherits* lists, as far as the amendment reaches.
2. New rulings get a new record, as `rulings.md` says. A superseded ruling gets only a pointer.
3. Rewrite an amended package entry to its current scope. Its old text goes to the phase's record
   (`rulings.md`).
4. In one commit, `docs: amend the Phase <n> plan — <what changed>`, update the plan's **Status**,
   `## Open decisions`, `## What the author supplies` and `## Verification`, the Execution brief of
   each planned package that the change moves, and `docs/plans/current.md`.
5. Gate, push and open its PR as `rulings.md`'s *Finishing* says. Report, and stop.
