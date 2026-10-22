# Amend a phase

`/np-plan amend <n>` keeps a phase plan true. It is the only route for planning provisional
packages after an opening study reports (read its report and findings log, put the decisions it
raises to the author as `rulings.md` says, then replace the provisional entries), adding or
dropping a package mid-phase (the author's reason, its place, its identifiers), and re-planning
later phases (the rulings, §8.1's rows and any later plans or input notes).

The same two turns apply as for `phase.md`: the ruling round, then the write-up. Read what
`rulings.md`'s *What a phase inherits* lists, as far as the amendment reaches. New rulings get a new record, as
`rulings.md` says; a superseded ruling gains only a pointer. An amended package entry is rewritten
to its current scope, and its old text goes to the phase's record (`rulings.md`). Update the plan's
**Status**, `## Open decisions`, `## What the author supplies`, `## Verification`, the Execution
brief of every planned package the change moves, and `docs/plans/current.md`, all in the one
commit, `docs: amend the Phase <n> plan — <what changed>`. Gate, push and open its PR as
`rulings.md`'s *Finishing* says, report and stop.
