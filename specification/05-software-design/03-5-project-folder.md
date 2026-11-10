---
type: Specification
title: "5.3.5 Project folder"
description: "Specifies the workbench project: a plain folder of models, studies, inputs, runs and sweeps, and how a case file imports into it and a project exports."
---

#### 5.3.5 Project folder

NOTE (the project, FR-32, FR-34, FR-35, IF-02; §8.2.17 S11; §8.2.33 AI9 to AI14): a workbench
**project** is a folder: `nanopnp-project.yaml` (`nanopnp/project/v0.6`, which holds the item index, the
open items, the current item and each suite's layout, and no physics), `models/molecular/`,
`models/continuum/`, `models/physics/`, `studies/`, `comparisons/`, `inputs/`, `runs/<study>/<run>/`, `sweeps/` and
`store/`. An item's name is its file's stem and its `name:`, and matches `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`.
The folder is the truth: a file the index lacks is appended on opening, and an indexed name without its
file is a problem, never a refusal to open. A run is `runs/<study>/<short key>`, and
`upto-<stage>-<short key>` when its walk stopped early. `api.Project` is the library's whole interface
to it; the command line and the workbench add none.
A case file **imports** into a project (`Project.import_case`, `nanopnp project import`) split by the
ownership table of §5.3.1's `models:` NOTE into a molecular model, a continuum model, a physics model and a study, and the
study resolves to the case it was split from, so every stage's key but the first is the original's.
A value the case writes as an expression stays in the study, and the model that owns it holds its resolved
number, so the models form a case alone.
A case whose `models:` names files imports those files too, each under its `name:`: an identical file
is reused, a different file of a taken name is stored as `<name>-2`, and the study names the copies. An
input file is **copied** into `inputs/` and written relative to the item, or **linked** where it lies
(`link=True`) and written absolute; `Project.embed` copies a linked input in and rewrites each item that
names it. A different file of a taken input name is refused, naming both. A key hashes an input's
contents and not its path (§5.3.2), so neither choice moves a key. A project
**exports** (`Project.export`, `nanopnp project export`) into a missing or empty folder as readable
files: the project file, the items, `inputs/` with each linked input copied in and its items rewritten,
each run's record, resolved case and manifest with its `results/` copied from the files `run.json`
names, and each sweep's records. The store goes only with `store=True`. An input the project cannot
find is refused before anything is written.
`Project.changes` lists each value of an item away from its default (the schema's, or a switch's
validated one) and each study override, with its kind, value, default and the model's value;
`Project.reset` removes the key from the item that sets it. `Project.problems` lists each missing file,
mismatched name and item refused on loading, with the case path of the refusal and the suite that owns
the item. The workbench shows both and computes neither (VER-60). A user's settings, key bindings and
themes are per user, under `NANOPNP_CONFIG`, else the operating system's configuration folder; the
layout is per project.
