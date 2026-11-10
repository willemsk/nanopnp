# Review rendered screens

`/np-gui review [<r>]`, after `render`; with no argument, the newest `<s>/gui-render/*/`.

1. Start a new `gui-reviewer` agent (`.claude/agents/gui-reviewer.md`). Give it:
   - the path `<r>`;
   - the design document's path, or "none yet";
   - the job or the screens in question, by shot id;
   - for a change, the diff's path (`git diff origin/main...HEAD > <r>/change.diff`).

   Ask for its findings only.
2. Write its reply to `<r>/review.md` unedited.
3. Decide each finding here, as the caller. Fix it in this item, answer it in the gallery card, or
   leave it open as a `REV-nn` row (§8.4.6). Never soften a finding to close it. A `blocking` finding
   left open stops a mockup item (WP5.01 D3).
4. Where the host has the `impeccable:impeccable` skill, run its `critique` over the same `<r>` PNGs and
   the change (`<r>/change.diff`). Write its reply to `<r>/critique.md` unedited. A host without the
   plugin skips this step and says so in its report (§8.2.34 AJ6).
5. Decide each critique finding as step 3 decides the reviewer's. The design document, `tokens.css` and
   the rulings win over the plugin's rules. Answer a finding against a ruling by citing it (it flags
   Inter, ruled by WB-21); never fix it against the ruling.
