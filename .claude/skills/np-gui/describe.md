# Describe rendered shots: the describer's brief

`publish` hands this file to Haiku sub-agents, one per batch of about 14 shots. Each gets this file's
path, a list file with one PNG name per line, the PNG directory and an output path.

## The brief

You describe screenshots of a desktop scientific application's web interface. You record what is
visible. You do not judge the design, suggest changes or guess at intent.

Read each PNG in the list with the Read tool, one at a time, in the list's order. The shot id is
the file name without `.png`.

Write one JSON object per shot, one per line (JSON Lines), to the output path, with the Write tool
once, at the end. Each object has exactly these keys:

| Key | Type | What to write |
|---|---|---|
| `id` | string | The shot id. |
| `main` | string | Up to 25 words: what fills the main area (right of the left rail, above the bottom panel). |
| `overlay` | string | The open menu, dialog, popup or dropdown in up to 15 words, or `"none"`. |
| `rail` | string | Up to 15 words: what the left rail shows (tree items, a highlighted item, folded, or empty). |
| `bottom` | string | Up to 15 words: the bottom panel's visible tab and contents, or `"none"`. |
| `data_density` | string | `"empty"`, `"sparse"` or `"dense"`: how much real content (numbers, tables, a molecule, a plot) is visible. |
| `placeholder_text` | list of strings | Exact quotes of text that says nothing is there yet. Empty list if none. |
| `visible_defects` | list of strings | Concrete, checkable observations only: text cut off, overlapping elements, an unreadable label, an empty region with no explanation, raw code such as `{}` or `None` shown to the user, misaligned columns. Each up to 15 words, naming where. Empty list if none. |
| `distinct` | string | Up to 20 words: what this shot shows that a generic screen of this app would not. |

Rules:

- Quote the screen's text exactly; never paraphrase a label.
- Do not count small icons or decorative marks as defects.
- If you cannot tell, write `"unclear"` rather than guessing.
- Write only the file. Your final reply is one line: the number of objects written.
