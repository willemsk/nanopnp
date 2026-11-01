# Run a design round with the author

`/np-gui grill <organisation | look-and-feel>`. The author must be present. The agendas and the
boards are WP5.01's (`docs/plans/wp5.01-workbench-design-study.md`, D2 and *Implementation
details*); a later round names its own.

## Prepare

Read the inputs: the verdicts collected so far, the author's areas (§8.2.17 S24), the personas P1 to
P3, S2, S6 and the design document so far. Write down the assumptions they leave open; each becomes
an agenda point or a question.

## Diverge

Draw the options before asking: for `organisation`, the concept boards; for `look-and-feel`, the
style tile. Render, review and publish them (`render mockups`, `review`, `publish`) and give the
author the URL before the first question.

## Grill

- One agenda point at a time, in the agenda's order. At most four questions per `AskUserQuestion`
  call, two to four options each, the recommended option first with *(Recommended)*, each option's
  consequence in its description.
- Walk a job through each answer before the next point: "where does the user click to change the
  salt, and what redraws?" A route that breaks is asked again.
- Challenge an answer that contradicts an earlier ruling or a clause, quoting both.
- Stop when every point has a ruling, or a deferral with its owner.

## Record

1. Each ruling is a row of the design document's decision log, in the author's words:
   `| # | Question | Ruling (author's words) | Consequence |`, numbered `WB-nn` on from the highest.
2. Play the rulings back in one message and ask the author to confirm them. Correct what they
   correct.
3. A ruling that changes a clause amends it in the same commit (WP5.01 D5).
