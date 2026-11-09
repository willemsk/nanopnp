# The author's page

A plan, a pull request and a choice put to the author are read by someone who does not code. Read this
file where a step writes an In brief or puts a choice to the author (§8.2.33 AI7; §8.4.4).

## The In brief

A phase plan, a work-package plan and a pull request start with this section:

```markdown
## In brief

About 250 words, up to 10% over (275), no backticks or identifiers; for a reader who does not code.

**What changes.** What the reader will notice, and why it matters.
**Cost.** The work in sessions, agent hours and your touches, from measured comparable packages (§8.3);
a cost to a user of the program, such as speed, a dependency or money, in plain units.
**What could go wrong.** Each risk, and how it would be noticed.
**Your call.** Each decision the author owns, as a question, with *Recommendation:* and one reason.
```

## Putting a choice to the author

Every choice the workflow puts to the author carries what a reader who does not code needs to judge
its impact: a ruling round, a work-package decision, a disputed review finding (§8.2.33 AI7). The
question dialog may be all the author sees, so the context lives in it, not in the chat.

- **The question** says, in the reader's words, what is decided, what happens today, and why it is
  open: what the specification, the phase or the design leaves undecided. An identifier only follows
  its words, in brackets.
- **Each option's description**, one or two sentences: what the user will see or do differently.
- **Each option's preview**, short lines in Markdown:
  - **You get:** the change for the user, with a concrete example: a command, a screen, a file;
  - **It costs:** sessions, agent hours and your touches (§8.3), and what it adds, delays or leaves
    out;
  - **Undo:** easy (a setting, or one later package), costly (a re-plan or a migration) or one-way
    (a file format users write, deleted data, a published release);
  - **It touches:** the later packages, other users and the clauses it moves, in words;
  - for the recommended option, **Why:** the one reason, and **It would change if:** what would make
    another option better.
  A layout or a screen gets a small text sketch in the preview.
- **At most three questions in a call**, the ones that change others first, two to four options
  each, the recommended option first with *(Recommended)*. Before the first call,
  the chat gets a short brief of the round: what is decided, what is settled already, and what each
  answer feeds.
- **When the author asks for more,** with a question back, a free answer that picks nothing, or
  "explain": give what was asked (an example, a sketch, the cost, what comparable tools do), then ask
  again. Never record a ruling the author did not make. If the context asked for is of a kind this
  list lacks, add it here in the same commit, so the next round gives it unprompted.
