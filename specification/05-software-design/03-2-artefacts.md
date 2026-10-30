---
type: Specification
title: "5.3.2 Artefacts and interchange formats"
description: "Lists the artefact each stage emits and its format, native or interchange."
---

#### 5.3.2 Artefacts and interchange formats

| Stage | Artefact | Format |
|---|---|---|
| 1 | Aligned ensemble: coordinates in nm, atom table (element, name, residue name, number and insertion code, chain) and axis-transform record | Native `.npz` (float32 coordinates) with its header record; exported as a PDB topology with a DCD trajectory (IF-04; WP18): a trajectory file carries no atom table and no gate record |
| 2, 3 | Density map (3D, float32), and the reduced (r, z) mean with its Cₙ-averaged and raw azimuthal variance | Native `.npz` with its header record; exported to, and read from, OpenDX or CCP4 via GridDataFormats (LGPL) (IF-05), the (r, z) grids as `RadialGrid`s with a singleton axis (WP19) |
| 7 | Protonation: the per-frame atom table (identity, coordinates in nm in stage 1's frame, charge, radius), `Q_net`, and each titratable residue's charge, PROPKA pKa, histidine tautomer and any unapplied state, per frame | Native `.npz` with its header record; exported as a PQR in ångströms, one `MODEL` per frame where there is more than one. Produced, it is keyed on the stage-1 key and the protonation parameters, among them the PDB2PQR argument list, and each frame is also stored under its own key, the digest of the heavy-atom PDB PDB2PQR is given, so a changed frame selection re-protonates only the new frames; the PDB2PQR and PROPKA versions are recorded beside the key. Supplied, it is keyed on the file's contents and, beside `structure:`, the stage-1 key (WP27) |
| 7 | ρ_pore, dielectric and exclusion fields | OpenDX or CCP4 via GridDataFormats (LGPL) (IF-05). Keyed on each field's grid digest and physical declarations, on the mesh, and on what its gates are evaluated at: the element order of the conservation quadrature and, with a dielectric field, the names of the solid materials its per-material means are classified by. A deposited charge (PHY-16 NOTE on the deposition) is two entries. Its lattice is `nanopnp/charge-grid/v0.5`, keyed on the protonation artefact, `charge.smearing`'s sharpness and spacing, the patch half-width, the frame shift and the kernel, and not on the mesh, so a mesh-convergence sweep re-deposits without re-summing. Stage 7's artefact adds the protonation and lattice keys to its inputs and the deposit's element order and per-plane weight to its gates. Its payload is the `nanopnp/field/v0.5` document and its `.npz` lattice, which read back through `inputs.charge`, and the element-wise coefficients with a digest of the element geometry they belong to, which no other mesh is given (WP28). Stage 7's artefact is `nanopnp/fields/v0.5` and its lattice `nanopnp/charge-grid/v0.5`: their `v1` payload and summaries recorded wall-clock seconds, and an entry served from the store carries its summary into the manifest unchanged, so a changed summary contract is a changed schema version, as a changed payload contract is (WP32, VER-23) |
| 4 | Conditioned polyline | `nanopnp/profile/v0.5` YAML: the vertex table with its provenance block (§5.2.1). The conditioning and gate record is in the artefact's summary (WP20) |
| 5 | Tagged (r, z) region | `nanopnp/region/v0.5` YAML: a declarative record of the model-frame profile, the membrane with its derived inner edge, the reservoir and the tag counts, from which the OCC region is rebuilt deterministically (WP21): a record hashes by content, where a BRep's bytes need not be stable |
| 6 | Mesh | Gmsh MSH 4.1 archival, any meshio (MIT) format on read (IF-06). A supplied mesh is keyed on its canonical contents; a generated one on its recipe, the stage-5 key and the resolved size fields, with its content hash recorded beside the key (WP21) |
| 8 | Resolved material coefficient set | Correction file references and evaluated parameters |
| 9 | Resolved case document | YAML, schema `nanopnp/case/v0.5` |
| 10 | Field set, iteration history | XDMF with HDF5 heavy data (IF-07) |
| 11, 12 | Scalar QoIs, profiles, figures, dataset, manifest | Result store record, figure files, manifest |
| — (a sweep, §5.3.4) | Collected dataset over the members of a sweep | Result store record, schema `nanopnp/sweep/v0.5` |

Every artefact carries a content hash over a canonical serialisation of its payload and the
parameters that produced it. The hash is the cache key: a stage whose input hashes and parameters
are unchanged is not recomputed, and a hand-substituted artefact registers as a changed input.
MSH 4.1 is archival because it is the only format in the toolchain carrying physical-group tags,
higher-order elements and mixed element types without loss.

NOTE (canonical serialisation): the hash is taken over the *validated* artefact payload and the
producing parameters, not over their file text. Mappings are serialised with sorted keys, sequence
order is preserved as meaning, floats are encoded by `float.hex()` with `-0.0` normalised to `0.0`,
arrays by dtype, shape and a digest of their contiguous bytes, and input files by the digest of
their contents rather than by their path. Wall-clock fields such as `created_at` are recorded beside
the hash and excluded from it, so that re-running a case reproduces the hash. A stored hash is
re-computed on load as a cross-check: a mismatch means the artefact was edited by hand, which FR-27
permits, and is recorded in the manifest as a substituted input rather than aborting the run. This
encoding is also the on-disk form of the manifest and the run record of §5.3.3, which are written
through it so that the file a reader sees and the bytes that were hashed cannot disagree; a decoder
for the float encoding SHALL therefore exist beside it, because a consumer comparing recorded
numbers against live ones otherwise compares two encodings and reads a present number as a missing
one.

NOTE (workspace locality): a run given an artefact store SHALL write every file it produces inside
that store, scratch included, and SHALL NOT fall back to the process-default store root for the
files a stage writes before its artefact is put away. FR-24's job array runs many members
concurrently, each with its own store; a member whose scratch mesh went to the process default
would leave the artefact and the file it points at in different stores, and QR-06 could not
attribute either to the member that produced it. The scratch directory of a stage is the workspace
it was given, and the walk gives every stage a fresh `<run scratch>/<stage>` directory, so two runs
of a case never share one. A stage SHALL refuse to write into a workspace that already holds files,
naming them and the `overwrite_workspace` switch, because a second run would overwrite a file the
first run's artefact still references; a caller that means to replace them constructs the stage with
`overwrite_workspace=True`, or sets it on the `Session` that runs the case (§8.2.23 Y4). A stage constructed without a workspace
SHALL refuse to write scratch, naming the `workspace` argument, rather than choose a directory of
its own; describing and keying it need none (REV-25, REV-55, REV-98; WP46). The store puts an
artefact by building its whole directory beside the final one and renaming it into place, so
concurrent writers of one key leave one complete entry, the first, whose record and payload
agree; a later writer returns that entry (REV-18; WP46).

NOTE (solution payload, warm start): the stage-10 artefact's payload SHALL be a self-describing
coefficient record — one array per field component, together with the discrete wall-distance
coefficient vector and a descriptor — rather than a backend-native binary. The distance field is
*stored* and not recomputed on restore: a residual reassembled against a freshly solved distance
field is a different operator, so re-solving it would make a restored state depend on the machine
that restored it. The descriptor SHALL carry the mesh content hash, the ordered field names, each
field's element type, order, domain restriction and degree-of-freedom count, the physics model and
its options, the wall-distance sources and saturation distance, the stabilisation mode (§6.4) and
the digest of the case's *solve-relevant* provenance defined in the NOTE below; restore SHALL
compare it key by key and abort naming the first difference with both values (QR-12), never adapt.
That digest is deliberately not the case document's own hash: `name:` and `outputs:` move the
document hash and move no field, so a gate keyed on it would refuse a converged state to a run
differing only in what it intends to report — and would refuse precisely the stage-10 cache entry
the store had just served that run. A coefficient vector loaded into a space that differs in any of these
is silently a different function and there is no residual it would fail to reduce. Because the
payload is excluded from the content hash, a change to this payload contract has to move the key by
another route, or a stale cache entry would read as a hit whose payload the loader cannot open. Every
artefact schema is pinned at `nanopnp/*/v0.5` (§8.2.9 G6), so a schema bump is not that route: stage
10's key carries an `algorithm_revision` (`SOLVE_ALGORITHM_REVISION`, in the case provenance and the
manifest), which a change that moves a converged number or this payload SHALL bump (REV-71). The
other stages' payloads have no such counter; a change to one is the author's ruling on a store
invalidation (REV-77).

NOTE (warm start from a neighbour, FR-24): the gate above is stated for reloading a run's *own*
converged state, where every descriptor key must match. A sweep warm-starts one operating point from
another, and two of those keys differ by construction — the solve-provenance digest carries the bias
and everything else that keys a solve, and the model record carries the §6.3 scale set, which is a
function of the concentration. The descriptor's keys SHALL therefore be partitioned into those that
determine the **space** — the mesh, the ordered field record with each field's element, order,
domain restriction and degree count, the total degree count, the boundary sets that fix which degrees
of freedom are constrained, the declared field set, and the NUM-02 variable branch — and those that
determine the **operator**. A warm-start load SHALL gate the space keys exactly as a restore does and
SHALL record every operator key that differed; it SHALL NOT read the stored wall-distance vector,
the operator being assembled belonging to the target run. The NUM-02 branch is in the first set
because a log-variable model and a primitive one declare the same field names at the same order with
the same degree count and mean different things by them, so no shape test would catch the confusion.
The partition SHALL be enumerated in both directions against the descriptor a solve actually
produces, so that a key added later fails verification rather than silently becoming ungated.

The warm-start source SHALL be recorded in the run provenance (FR-25) and SHALL NOT enter the
stage-10 artefact key. Two members differing only in where Newton started must key one artefact, or
the store would hold two entries for one converged state and the QR-08 reproduction would compare a
warm result against a cold key. That is admissible only because it is *asserted*: a converged state
that depended on its starting point is a defect, and the verification of FR-24 measures the
difference between the warm and cold paths rather than assuming it away.

NOTE (what keys a solve): the parameters of the stage-10 artefact SHALL be the resolved case's
provenance restricted to what can change a converged field. The case's `name:` and its `outputs:`
selection are excluded: neither reaches the mesh, the operator or the boundary data, and a key
carrying them re-solves a converged case because the run asked for one more quantity to be
reported — on the reference pore, minutes of work discarded for a question about post-processing.
Both remain in the §5.3.3 manifest, which records what was asked for and not only what was
computed, and both remain in the stage-11 key, where `outputs:` does change the artefact. The
`schema:` string is excluded for the same reason: a v1 document and its
lossless v2 upgrade describe one run (§5.3.1), and a key that told them apart would re-solve every
converged case in a store because the loader, not the case, had changed. The v1 key **did** carry
the string, so this exclusion moved the stage-10 key, the VER-34 restore digest and the Tier-3 case
identity of every v1 case once, at the move to v2 (author ruling, correcting
WP17 D6, which had assumed the three would survive): a solve stored under a v1 key is a miss and
re-solves once, and a golden declaring a v1 `case_hash` is refused naming both hashes. The stage-8
materials key never carried the schema and survives. The exclusion is what makes this the last move
of the schema to re-key a solve.

NOTE (QR-08, reproduction): the check that a run reproduces its scalar quantities of interest from
its manifest SHALL re-enter the solve rather than be served from the artefact store. Run against a
populated store the check reduces to a dictionary lookup and asserts nothing; it is therefore
performed against a fresh store, with the store miss and the re-entry into the nonlinear solve
themselves asserted. The agreement required is the nonlinear relative tolerance of §5.3.1
(`1 × 10⁻⁶`), and the *measured* difference is reported alongside the verdict, so that the figure
across operating systems is on the record rather than inferred from a pass. The check SHALL be
reachable as a command over a run directory and not only as a test: a promise only the project's own
test harness can exercise is not one a user holding an archived result can rely on. Drift in an
*input* is fatal and names the file, a reproduction against moved contents being a different
calculation reported as the same one; drift in a recorded library version is reported and not fatal
unless the caller asks for a strict environment, because a version that moved a number is caught by
the quantity comparison, which is the assertion that matters.
