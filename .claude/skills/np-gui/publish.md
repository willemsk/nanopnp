# Publish a gallery for the author's verdicts

`/np-gui publish <topic> [<r>]`. The author marks each shot on a private page; `collect` reads the
marks back. One page per topic; a new round republishes to the same URL.

1. Load the `artifact-design` and `artifact-capabilities` skills; declare the `db` capability as the
   latter says.
2. Write `<s>/gallery/<topic>/index.html` and copy the PNGs beside it, published through `files`
   (a mockup page's `tokens.css` too). One card per shot: the picture, the shot id, its state, two
   lines on what it shows, and the reviewer's findings for it from `<r>/review.md`. Each card has a verdict control and a note field. The verdicts are:
   - `keep`, `drop`, `change` for today's screens;
   - `fine`, `change` for a mockup;
   - `prefer`, `borrow`, `reject` for a concept board;
   - `A`, `B`, `either`, `neither` for a choice panel. Its card carries both variants' pictures side by
     side, stacked on a phone.

   Each change saves at once to the `verdicts` collection. The document id is the shot id, and the
   fields are `verdict`, `note` and `round`.
3. Publish with the Artifact tool (private by default). The first time, record the URL in
   `<s>/gallery/<topic>/url`; later rounds pass it as `url` and bump `round`.
4. Print the URL. `/np-ship` puts it under the PR's **Verification**.
