## 5. Software design description

The subsections, one file each:

* [5.1 Architectural overview](01-architectural-overview.md) - The linear pipeline of cacheable stages and the module table: which subpackage owns what.
* [5.2 Pipeline stages](02-pipeline-stages.md) - Each stage's inputs, outputs, tools and gate; contour conditioning (§5.2.1), meshing and its size fields (§5.2.2), the embedded analyte (§5.2.3).
* [5.3.1 Case file](03-1-case-file.md) - The case file: an annotated example, the schema identifier and compatibility rule, and one NOTE per key block.
* [5.3.2 Artefacts and interchange formats](03-2-artefacts.md) - Lists the artefact each stage emits and its format, native or interchange.
* [5.3.3 Provenance manifest](03-3-provenance-manifest.md) - Specifies the provenance manifest emitted with every result, sufficient alone to reconstruct the run, and the run directory naming.
* [5.3.4 Sweep specification and dataset](03-4-sweeps.md) - Specifies sweeps, sets of runs described by their own declarative document that names a base case and the axes to vary.
* [5.3.5 Project folder](03-5-project-folder.md) - Specifies the workbench project: a plain folder of models, studies, inputs, runs and sweeps, and how a case file imports into it and a project exports.
* [5.4 Component design](04-component-design.md) - Specifies the component interfaces: the weak forms stated once against NGSolve, the correction-model interface and the physics-model interface.
* [5.5 Extension points](05-extension-points.md) - Specifies the two levels of pluggability, the registries for discretisation backends, and how each extension is added by one registration.
* [5.6 Architecture decisions](06-architecture-decisions.md) - Records the architecture decisions, beginning with NGSolve as the single production backend against which the weak forms are stated once (§5.4.1).
