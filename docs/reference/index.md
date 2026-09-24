# Reference

Everything in this section except the correction-data page is **generated** at build time from the
code it describes, so it cannot drift from it (VER-45):

| Page | Generated from |
|---|---|
| [Case file](../_generated/reference/case-file.md) | the `nanopnp/case/v2` schema: every editable field, its type, default, accepted values and validated default |
| [Command line](../_generated/reference/cli.md) | the argument parser: every command and option |
| [Exit codes](../_generated/reference/exit-codes.md) | the exit-code enumeration: every class, and which exception maps to which |
| [Python API](../_generated/reference/api.md) | the docstrings of the public surface, `nanopnp.__all__` |
| [Shipped parameter files](../_generated/reference/correction-files.md) | `data/corrections/*.yaml`, verbatim |

A Tier-1 test asserts each generated page against its source in both directions: a field, a
command, an exit class or a public name the page omits fails it, and so does one the page invents.
