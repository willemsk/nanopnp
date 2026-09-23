# Provenance and deviations

Every run writes `manifest.json` beside the case and the run record (FR-25, §5.3.3). It is written
through the same canonical encoding the hashes are taken over, so the file you read and the bytes
that were hashed cannot disagree. Floats are stored as exact hexadecimal, which `nanopnp inspect`
decodes for reading.

## The eight groups

| Group | Records |
|---|---|
| `inputs` | every input file, including the case, the mesh and any field, by content hash |
| `environment` | the nanopnp version, Python, the platform, and the versions of the numerical libraries |
| `geometry_and_mesh` | the mesh's content hash, counts, groups and the mapping applied to them, and its quality statistics |
| `charge` | the supplied fields, their declared and deployed charge, and every conservation check |
| `materials` | the correction parameter file and version, and how often the concentration clamp was active |
| `solver` | the element orders, the nonlinear and linear settings, and the continuation ladder rung by rung |
| `stabilisation` | the mode that produced the numbers, its parameters, and its own contribution to the current |
| `deviations` | every switch set away from the validated model |

Read it with `nanopnp inspect <run directory>`, or `--json` for a parser.

## Deviations from the validated model

The published agreement with experiment was obtained with one specific configuration: the
**validated default**, every correction on at its fitted parameters, the Borukhov steric flux,
variable-density flow with inertia, and no dielectric-gradient force (PHY-21, PHY-22). Every switch
in the case that differs from it is listed under `deviations`, with the value the run used and the
validated default beside it. The case-file reference shows each switch's validated default.

A deviation is not an error. Classical PNP-NS, an ablation, or an opt-in extra term are legitimate
runs. But a number from a run with deviations was not produced by the model that was validated, and
its manifest says so where nobody can miss it. Some deviations come from what is supplied rather
than from a switch: a mesh carrying an ion-exclusion shell is one, because the validated model has
no Stern layer. Those are listed under `deviations.contributed`.

The schema's own defaults are **not** the validated defaults. A correction not named in the case
defaults to `none`. See [Case files](case-files.md).

## Reproducing a run

```console
$ nanopnp reproduce <run directory>
```

This re-solves the archived `case.yaml` into a fresh temporary store, so nothing is served from
cache and Newton really runs again. It then compares every scalar the run recorded against the
reproduction, to a relative tolerance (`--tolerance`), and exits `0` only if every scalar agrees
(QR-08). Differences in library versions, interpreter or platform are reported beside the result;
`--strict-environment` makes them failures. The input files must still be where the case names them.
