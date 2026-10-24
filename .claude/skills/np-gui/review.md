# Review rendered screens

`/np-gui review [<r>]`, after `render`; with no argument, the newest `<s>/gui-render/*/`.

1. Give a new `gui-reviewer` agent (`.claude/agents/gui-reviewer.md`): the path `<r>`; the design
   document's path, or "none yet"; the job or the screens in question, by shot id; for a change, the
   diff's path (`git diff origin/main...HEAD > <r>/change.diff`). Ask for its findings only.
2. Write its reply to `<r>/review.md` unedited.
3. Decide each finding here, as the caller: fix it in this item, answer it in the gallery card, or
   leave it open as a `REV-nn` row (§8.4.6). Never soften one to close it. A `blocking` finding left
   open stops a mockup item (WP5.01 D3).
