"""The workbench's glossary: the terms of the *Glossary* of docs/design/workbench.md."""

from __future__ import annotations

from nanopnp.mesh.sizing import SIZES

__all__ = ["GLOSSARY"]

GLOSSARY: tuple[tuple[str, str], ...] = (
    (
        "Artefact",
        "What a stage writes: typed, stored, keyed by the hash of its inputs and settings.",
    ),
    (
        "Blocked",
        "A build a check stops, or a value the library declines at its field, shown with the "
        "rule, the value, the case path and a remedy.",
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
        "A saved project item pairing two runs: their difference, the two maps side by side or "
        "mirrored about the axis on one colour scale, or both on their meshes on one range.",
    ),
    (
        "Continuum model",
        "A library item built in the Meso and Continuum suites: the pore's outline drawn from a "
        "molecular model, the region and the mesh.",
    ),
    (
        "Default mesh sizes",
        "The element size each part of a generated mesh takes when none is typed: global "
        f"{SIZES.global_nm:g} nm, protein {SIZES.protein_nm:g} nm, electrolyte "
        f"{SIZES.electrolyte_nm:g} nm, the reservoir's arc {SIZES.arc_nm:g} nm, the pore's axis "
        f"{SIZES.axis_in_pore_nm:g} nm, and the wall a fifth of the Debye length, at most "
        "0.05 nm; the size scale multiplies each.",
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
        "Meso",
        "The suite between Molecular and Continuum that draws a continuum model's pore and charge "
        "from the molecular model it is built over, beside the molecule; it adds no kind of model.",
    ),
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
        "One of the six parts of the workbench: Molecular, Meso, Continuum and Physics, which "
        "build models, and Study and Analysis, which use them.",
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
