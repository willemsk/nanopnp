---
type: Ruling Record
title: "8.2.33 WP5.08's plan: a user's colour themes, agreed 5 November 2026"
description: "Records the author's ruling at WP5.08's plan: the workbench's settings offer a theme selector and a colour modifier, as a modern code editor's do, so a user chooses among the shipped light and dark themes and themes of their own and edits each colour of one; a user's theme sets its own contrast."
---

#### 8.2.33 WP5.08's plan: a user's colour themes, agreed 5 November 2026

Ruling by the author on 5 November 2026, at `/np-plan wp 5.08`, after WP5.07's merge. T8 (§8.2.18) has a user adjust or
choose a theme, its colours, density, spacing and the 3D view's background, saved per user. The plan asked through
`AskUserQuestion` whether the frame's settings offer the light and dark modes, the density, the spacing and the 3D
background, with a user's own colours deferred past v0.6, or also a colour theme of the user's own, checked against the
contrast target. The author chose the second, in their words: "Also allow a color themes. I think this can be like the
theme selector/modifier under settings of many modern IDEs." While the plan was written, the author
added: "User set themes define their own contrast, no need for us to worry about that." The letter
series continues at AI.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AI1 | **The settings offer a theme selector and a colour modifier, as a modern code editor's do.** A user chooses the system's choice of the shipped light and dark themes, either one, or a theme of their own, a plain file saved per user that names its base, light or dark, and the colour tokens it changes. A shipped theme is read-only; it is duplicated to be modified. Each colour of a user's theme is edited in the settings. A user's theme sets its own contrast: the workbench does not check it | QR-16's target binds the shipped themes, which the render check measures; a user's theme is the user's choice. About two days in WP5.08, with no contrast measure in the shell | QR-16, in this commit; the theme itself, open: WP5.08 |
