## 5. Software design description

The subsections, one file each:

* [5.1 Architectural overview](01-architectural-overview.md) - Describes the linear pipeline of pure, cacheable stages, each emitting a typed, content-hashed artefact that can run and be inspected standalone.
* [5.2 Pipeline stages](02-pipeline-stages.md) - Tabulates each pipeline stage with its inputs, outputs, tools and validation gate.
* [5.3 Data design](03-1-case-file.md) - Specifies the case file as one declarative YAML document, the unit of reproducibility from which everything else is derived.
* [5.3.2 Artefacts and interchange formats](03-2-artefacts.md) - Lists the artefact each stage emits and its format, native or interchange.
* [5.3.3 Provenance manifest](03-3-provenance-manifest.md) - Specifies the provenance manifest emitted with every result, sufficient alone to reconstruct the run, and the run directory naming.
* [5.3.4 Sweep specification and dataset](03-4-sweeps.md) - Specifies sweeps, sets of runs described by their own declarative document that names a base case and the axes to vary.
* [5.4 Component design](04-component-design.md) - Specifies the physics/ design: weak forms written once against a thin internal interface, with one production NGSolve implementation.
* [5.5 Extension points](05-extension-points.md) - Specifies the two levels of pluggability, the registries for discretisation backends, and how each extension is added by one registration.
* [5.6 Architecture decisions](06-architecture-decisions.md) - Records the architecture decisions, beginning with NGSolve as the single production backend behind the abstraction of §5.4.1.
