---
type: Specification
title: "5.3.5 Project folder"
description: "Specifies the workbench project: a plain folder of models, studies, inputs, runs and sweeps, and how a case file imports into it and a project exports."
---

#### 5.3.5 Project folder

NOTE (the project, FR-32, FR-34, FR-35, FR-39, IF-02, QR-08; §8.2.17 S11; §8.2.31 AG6; WB-54, WB-60; §8.2.33 AI9
to AI14; §8.2.38 AN5; §8.2.45 AU3; WP5.19, WP5.21): a workbench
**project** is a folder: `nanopnp-project.yaml` (`nanopnp/project/v0.6`, which holds the item index, the
open items, the current item, each suite's layout, the project's settings and the molecular model each continuum model
is built alone over where one was chosen (`built_with`; §5.3.1's NOTE on model files), and no physics), `models/molecular/`,
`models/continuum/`, `models/physics/`, `studies/`, `comparisons/` (until WP5.22; then `results.yaml`, below),
`inputs/`, `runs/<study>/<run>/`, `sweeps/` and `store/`. An item's name is its file's stem and its `name:`, and matches `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`.
The folder is the truth: a file the index lacks is appended on opening, and an indexed name without its
file is a problem, never a refusal to open. A run is `runs/<study>/<short key>`, and
`upto-<stage>-<short key>` when its walk stopped early. A continuum model's charge built alone in the
meso suite (`Project.charge_case`) writes its record in the store, as
`store/runs/<model>-upto-charge-<short key>`, from which its deployed charge is drawn; the store's
clean-up keeps it while its key is the model's (§8.2.42 AR8). `api.Project` is the library's whole
interface to it; the command line and the workbench add none.
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
contents and not its path (§5.3.2), so neither choice moves a key.
A study is made by `Project.new_study`, which pairs one model of each kind by name, and edited value by
value: `Project.set_study_value` sets a key the study owns, an override of a value its model gives, or
`models.<kind>` to another model of the project by its name; `Project.set_variable` defines a variable
by its value or its expression, with its unit; `None` removes each. Each writes the study only when it
reads as a case, so a refused value leaves the file's bytes; a value its models cannot run with is
written and listed among the problems at its path. `Project.study_values` lists what the Study suite
shows: each model's exposed values in model order, then each key the study sets, then each other
override, each with its owner, unit, range, the model's value and the study's.
A project **exports** (`Project.export`, `nanopnp project export`) into a missing or empty folder as
readable files: the project file, the items, `inputs/` with each input at its path there and each linked
input copied in and its items rewritten, each run's record, resolved case and manifest with its
`results/`, each result at its path in the stored report it belongs to, and each sweep's records. The
copied run record names the copy's directory and files, and the copy's store, which goes only with
`store=True`. An input the project cannot find, and two inputs that take one path in the copy, are
refused, naming both, before anything is written. The copy is written beside the destination and moved
into place whole, so a refused or failed export leaves nothing.
Until WP5.22, a **comparison** (`comparisons/<name>.yaml`, `nanopnp/comparison/v0.6`) holds `name`, `runs` (two run
folders of the project, first then second, relative to it), `quantity` (`potential` by default), `view`
(`difference`, the default, `maps`, `mirrored`, the two maps as one with the first reflected about the axis, or
`mesh`), `colour_map` and `range` (None by default), and no physics.
`Project.new_comparison` writes one over two runs, `Project.comparison` reads it and
`Project.set_comparison` sets its values, each written only once it reads back. A run it names that holds
no `run.json` is a problem at `runs`, never a refusal to open; an export copies the file unchanged, its
runs with it. Its difference (`post.fields.field_difference`) samples both runs onto one cell-centred
(r, z) grid of about 10⁶ cells over the overlap of their fluids' boxes, each run on the set its quantity
is solved on, and is NaN where either fluid lacks a cell's centre. From WP5.22, the project's **results**
are one file, `results.yaml` (`nanopnp/results/v0.6`) beside the project file, holding no physics: the tree
of results' data (a run, which may follow its study's newest, a sweep's runs, two runs compared, a
revolution about the axis), definitions (constants with their units, and variables from the library's
list or as expressions parsed as a study's variables are), probes and cuts, the quantities shown in their
order, and plot groups, each naming its data. A comparison file is read once into its data, and the
`comparisons/` folder goes; a variable is evaluated by the library at each sampled point (QR-13; WB-54,
WB-58, WB-60, WB-61). `Project.sweeps` lists a study's
sweeps. `Project.run_state` is `solved` while a run's solve is in the store, `removed` once a clean-up
took it, and `unsolved` for a walk that stopped short of it. `Project.rebuild` reproduces a run into
the project's store (§5.3.2's NOTE on reproduction), so its stage keys and every scalar it recorded come
back, compared at 10⁻⁶; a drift is returned, naming each value.
`Project.changes` lists each value of an item away from its default (the schema's, or a switch's
validated one) and each study override, with its kind, value, default and the model's value;
`Project.reset` removes the key from the item that sets it. `Project.problems` lists each missing file,
mismatched name and item refused on loading, and each study whose case does not resolve, as a study
its own physics model cannot run with (FR-35), with the case path of the refusal and the suite that
owns it. The workbench shows both and computes neither (VER-60).

NOTE (a project's settings, VER-78; WP5.15; §8.2.34 AJ9; §8.2.38 AN2, AN3): the workbench's settings are
one declared list (`nanopnp.gui.web.settings.SETTINGS`): each setting has its section, its scope (the
user's, the project's, or both), its default, its description and search words, and when it applies. A
later package or a plugin adds to the list. A user's values, key bindings and themes are per user, in
`workbench.yaml` under `NANOPNP_CONFIG`, else the operating system's configuration folder; each entry is
checked alone, and one that fails, or names no setting, is dropped with a warning. A project carries its
own values under `settings:` in its project file, and the project's value wins where the setting's scope
allows; in v0.6 only the store's size cap, the significant figures and the number style allow it. The
project file carries the values and does not check them; the workbench does. The recent projects are per
user, newest first, in `recent-projects` beside `workbench.yaml`. The layout is per project.
