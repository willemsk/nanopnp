"""The workbench's glossary: the terms of the *Glossary* of docs/design/workbench.md."""

from __future__ import annotations

__all__ = ["GLOSSARY"]

GLOSSARY: tuple[tuple[str, str], ...] = (
    (
        "Artefact",
        "What a stage writes: typed, stored, keyed by the hash of its inputs and settings.",
    ),
    (
        "Case file",
        "One complete description of a run, which the command line runs; the unit of "
        "reproducibility.",
    ),
    (
        "Changed mark",
        "A filled diamond on a value set away from its default; an outlined one on a study's "
        "override.",
    ),
    (
        "Comparison",
        "A saved project item pairing two runs on one colour scale, side by side or as their "
        "difference.",
    ),
    (
        "Continuum model",
        "A library item built in the Continuum suite: the protein geometry, the region and the "
        "mesh.",
    ),
    (
        "Exposed value",
        "A value a model declares for the other suites, with its name, unit, range and default, "
        "such as a physics model's concentration and bias; the Study suite lists it first.",
    ),
    (
        "Gate",
        "A check a stage passes before its artefact is used, such as the orientation gate or the "
        "mesh's quality gate.",
    ),
    (
        "Later phase",
        "A tool drawn with its banner and no working control: designed, not built yet.",
    ),
    (
        "Library",
        "The project's models, studies and comparisons, each reused without being rebuilt.",
    ),
    ("Live link", "Two views that select together until unlinked."),
    (
        "Molecular model",
        "A library item built in the Molecular suite: the prepared structure, its ensemble and "
        "protonation.",
    ),
    (
        "Override",
        "A value a study sets in place of a named model's, for a sweep or a ramp. It is recorded "
        "in the manifest beside the model's value, and a value equal to the model's is none.",
    ),
    (
        "Physics model",
        "A library item built in the Physics suite: the equations, the electrolyte, the boundary "
        "conditions and their discretisation, reused across pores.",
    ),
    ("Project", "The folder that holds the library, the runs, the store and the project file."),
    ("Queue", "The builds and runs waiting, running and done, always on screen."),
    (
        "Refusal",
        "A value or a build the library declines, shown at its field with the rule, the value, the "
        "case path and a remedy.",
    ),
    (
        "Resolved case file",
        "The one complete case file a study's run resolves to, written with its manifest.",
    ),
    ("Route", "A guided path through the suites, a layer over them."),
    (
        "Rung",
        "One step of the continuation ladder, from an easy problem to the one asked for; a run "
        'shows "rung x of N".',
    ),
    ("Schematic", "A drawing that shows where a field lies, not its values."),
    ("Store", "Where artefacts are kept, keyed by their hash."),
    (
        "Study",
        "A Study-suite item pairing one molecular, one continuum and one physics model with its "
        "overrides and sweep, and running it.",
    ),
    (
        "Suite",
        "One of the five parts of the workbench: Molecular, Continuum and Physics, which build "
        "models, and Study and Analysis, which use them.",
    ),
    ("Switch", "A setting away from its validated default, recorded in every result's manifest."),
    ("Tool", "One task in a suite, with its settings docked beside its live view."),
    (
        "Variant",
        "A model derived from a parent and shown as its difference from it, such as a residue's "
        "charge changed.",
    ),
)
"""Each term and its meaning, in the design document's order."""
