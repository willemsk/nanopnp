# Publish a digest for the author's verdicts

`/np-gui publish <topic> [<r>...]`. The author marks at most 20 picks on a private page, each
standing for a group of near-identical shots; `collect` reads the marks back. One page per topic; a
new round republishes to the same URL. A render of a few dozen shots is too many to judge one by
one, and most of them repeat each other (WP5.15's collect, 11 November 2026).

## Choose the picks

1. **Group.** `uv run python .claude/scripts/gui/digest.py similar <r>/index.json...` prints the
   groups of light shots whose pictures barely differ: a screen that looks the same in several
   states is one group. A later render's `index.json` goes after the earlier one's and replaces its
   shots of the same id.
2. **Describe.** Split the light shots into batches of about 14 and start one Haiku sub-agent per
   batch, in one message, with the brief in `describe.md` beside this file. Each writes JSON Lines
   to `<s>/digest/<topic>/describe/`. The rows are what is visible, not a judgement; check by eye
   any defect you take into a card.
3. **Pick.** Choose at most 20, in this order, until each is covered:
   - each decision of the package a screen shows (the plan's D-rows), once, on its richest state:
     2WCD over a fixture, the dense screen over the empty one;
   - each reviewer finding the package fixed, where the fix is visible;
   - each open `REV-nn` or reviewer question the author can answer from a picture;
   - each describer defect you confirmed;
   - one dark shot of the frame, and dark again only where dark is the question (a menu's edge);
   - the empty state a new user meets.

   Look at every pick yourself before you write its card.
4. **Write `<s>/digest/<topic>/picks.json`**: `title`, `lede`, `round`, `groups` (`key`, `title`,
   `sub`), `decisions` (each D-row's id and a two-word name), and `picks`; `verdicts`, the words a card
   is marked with, is `["keep", "drop", "change"]` unless given, and a page of layouts to choose among
   gives `["prefer", "borrow", "reject"]`. Each pick has:
   - `id`, `group`, `title`, `decisions`;
   - `why`: one or two sentences on why this shot and not its group's others;
   - `look`: what to judge in it, naming each fixed finding and each open item it shows, and which
     part to ignore (a suite still drawn as text);
   - `stands_for`: shell patterns (`*`, `{a,b}`) for the shots its verdict covers.
5. **Build.** `uv run python .claude/scripts/gui/digest.py build <picks.json> <r>/index.json...
   <s>/gallery/<topic>/` writes `index.html` with the picks' PNGs. It refuses a shot left to no pick,
   a pick not in the render and more than 20 picks.

## Publish

6. Load the `artifact-capabilities` skill and the page guidance (`artifact-design`, or the Artifact
   tool's `quickstart`). Publish `index.html` with the PNGs through `files` and the `db` capability.
   Each verdict saves at once to the `verdicts` collection, keyed by the pick's id, with the fields
   `verdict` (`keep`, `drop` or `change`), `note` and `round`.
7. The first time, record the URL in `<s>/gallery/<topic>/url`; a later round passes it as `url`
   and bumps `round`. Print the URL. `/np-ship` puts it under the PR's **Verification**.

The full set, one card per shot, is built only when the author asks for it. Mockups, concept boards
and choice panels are few enough to publish whole: one card each, with the verdicts `fine` or
`change` for a mockup, `prefer`, `borrow` or `reject` for a concept board, and `A`, `B`, `either`
or `neither` for a choice panel, its two variants side by side.
