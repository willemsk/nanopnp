---
type: Specification
title: "5.3.3 Provenance manifest"
description: "Specifies the provenance manifest emitted with every result, sufficient alone to reconstruct the run, and the run directory naming."
---

#### 5.3.3 Provenance manifest

Emitted with every result artefact (FR-25, IF-08) and sufficient alone to reconstruct the run
(QR-08). The run directory holding it is `runs/<name>-<short hash>`, the hash covering the case
hash and the sha256 of every recorded input file, so an input regenerated at the same path yields a
new directory rather than overwriting the earlier run. The directory's `case.yaml` is the source
case file's bytes, verbatim; for a study (§5.3.1 NOTE on `models:`) it is the one complete case the study
resolved to, which holds no `models:` and runs as it is, and the manifest's model files and overrides
record what it was resolved from.

| Field group | Contents |
|---|---|
| Inputs | Content hash of every input file and every upstream artefact. A case that names a model (§5.3.1 NOTE on `models:`) adds the files `models.molecular` and `models.continuum` to the input files, each by path and content hash, and `overrides`: every value the study sets in a named model's keys, by dotted path, as `{model: <the model's value>, study: <the study's>}`; a case that names no model has no `overrides` key (FR-39, FR-25) |
| Environment | Package version, version of every library in §2.6, Python version, operating system |
| Geometry and mesh | Mesh hash, element counts, quality statistics, size-field settings |
| Charge | Q_net, force field, pH, titration method, conservation residual; with `charge.edits`, the variant's own record `variant_of`: its parent's protonation key, the edits, each residue that differs from the parent with its charges before and after, and `Q_net` of both. An edit is configuration and never a deviation (FR-38; §8.2.31 AG11) |
| Materials | Correction model names, version of each parameter data file, clamp activations |
| Solver | Physics model, element orders, continuation rungs, nonlinear and linear settings, iteration counts |
| Stabilisation | The stabilisation mode that produced the number, its tuning parameters and the provenance of each, and — where a mode is active — its own contribution to the current and the largest cell Péclet number per species (§6.4, NUM-12, NUM-13) |
| Deviations | Every switch set away from the validated default, including `dielectric_gradient_forces` (PHY-23) |
