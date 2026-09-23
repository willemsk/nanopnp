# Correction data files

The corrections of the ePNP-NS model are **data, not code** (QR-14): the fitted coefficients of the
concentration- and wall-dependent diffusivity, mobility, viscosity, permittivity and density, and
the parameters of the steric flux. They live in YAML files under `data/corrections/`, ship inside
the package, and are listed by `nanopnp --env`. The functional forms they parameterise are specified
in §4.3 and documented, with the errata of the printed sources, in `.knowledge/01`; read them
[there](../_generated/model/knowledge/01-physics-epnpns.md), not here.

## Selecting one

A case names its parameter file twice over:

- `electrolyte.parameters` is the file the electrolyte's properties are drawn from;
- `electrolyte.corrections.<property>.model` selects, per property, either that file's fitted model
  or `none`. Each of the five properties also has two independent parts, `concentration` and
  `wall`, which can be switched separately.

`none` is a registered model that applies no correction. It is not a code path around the
correction, and it is how classical PNP-NS is expressed (PHY-21, PHY-22). The case-file editor and
the schema offer exactly the installed files, plus `none`.

## The shipped file

v0.5 ships one file, `willems2020_nacl`: NaCl at 298.15 K, as fitted and deployed in the reference
model of Willems *et al.* (2020). Every coefficient is taken from the COMSOL model report that
produced the published results, not from the rounded tables of the printed sources, and its
comments give the provenance and the transcription traps. It is shown verbatim on the [shipped
parameter files](../_generated/reference/correction-files.md) page.

Its concentration fits are valid over a stated range and are capped at their end value beyond it
(PHY-13). How often a run met that cap is recorded in its manifest.

## Another electrolyte

Adding an electrolyte means adding a file, not changing the solver (QR-14). The schema of the file,
`nanopnp/corrections/v1`, is the shipped file's own structure. No second electrolyte ships yet,
because fitting one is a scientific task in its own right, not a documentation example.
