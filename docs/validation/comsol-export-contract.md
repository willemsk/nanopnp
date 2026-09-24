# The COMSOL export contract (VAL-03, VAL-04, RSK-14)

What the author produces from the reference model, and what `nanopnp validate ingest-golden`
will and will not accept. `SPECIFICATION.md` §7.4 governs; where this document and the
specification disagree, this document is the thing that is wrong.

Nothing here asks for a judgement call. Every number below either comes out of
`nanopnp validate export-grid`, or is a fact about the model only you can state — and the
ingest **refuses** a golden that leaves one of the latter unstated, rather than guessing.
That is the point: a guess made once is a guess repeated silently on every nightly run
thereafter.

## 0. What you need

```bash
uv run nanopnp validate export-grid docs/validation/probes/clya-reference.probe.yaml
```

prints the probe grid's hash and, per patch, the two `%Grid` axis lines **in metres**.
Paste those into COMSOL's Grid evaluation; do not retype them. A hand-entered extent is a
silently moved sample point, and the `probe_hash` cannot catch it — the document did not
change.

The five frozen cases are `docs/validation/cases/*.case.yaml`. They are frozen: editing one
changes its identity and invalidates every golden that declares it.

## 1. What to export

Five cases × two refinements × six fields × five patches.

**Cases** (§7.4 NOTE, author ruling of 18 September 2026):

| Case | Salt | Bias |
|---|---|---|
| `clya-0.05M-minus200mV` | 0.05 M | −200 mV |
| `clya-0.05M-plus200mV` | 0.05 M | +200 mV |
| `clya-0.5M-plus50mV` | 0.5 M | +50 mV |
| `clya-3M-minus200mV` | 3 M | −200 mV |
| `clya-3M-plus200mV` | 3 M | +200 mV |

**Refinements.** `published` is the mesh the model ships with. `refined_1` is **one uniform
refinement** of it, and is needed **for `clya-0.5M-plus50mV` only** — VAL-04 wants a bound on
the reference's own discretisation error (RSK-09), not a field of them. If licence access
allows only one refined case, that is the one.

**Fields.** Six per case, each a separate Grid evaluation:

| Our name | COMSOL expression | Unit — **exactly this string in the manifest** |
|---|---|---|
| `potential` | `V` | `V` |
| `c_Na+` | `cpos` | `mol/m^3` |
| `c_Cl-` | `cneg` | `mol/m^3` |
| `velocity_r` | `u` | `m/s` |
| `velocity_z` | `w` | `m/s` |
| `pressure` | `p` | `Pa` |

`mol/L` is **refused, not converted**. A silent factor of 1000 presents as a 99.9 %
discrepancy, which looks like a physics failure and is a units failure. Set COMSOL's unit to
SI before exporting, or say so and re-export.

If the model does not export `p` at all, **leave `pressure` out of the manifest entirely**.
The report then records it as unavailable and says so. Do not export zeros.

**Patches.** Five per field — `pore`, `mouth_cis`, `mouth_trans`, `reservoir`, `axis_line` —
because a COMSOL Grid evaluation takes one tensor-product grid and the probe grid is a union
of five. One file each.

## 2. File layout

One directory per case per refinement, anywhere under `$NANOPNP_REFERENCE_DATA`:

```
$NANOPNP_REFERENCE_DATA/comsol/clya-0.5M-plus50mV/published/
    manifest.yaml                  # section 3 below
    npgrid_clya_v8_NaCl_report.mph # the generating model, archived alongside (§7.4)
    potential__pore.txt
    potential__mouth_cis.txt
    potential__mouth_trans.txt
    potential__reservoir.txt
    potential__axis_line.txt
    c_Na+__pore.txt
    ...
```

Each `.txt` is one COMSOL interpolation table exactly as the Grid export writes it:

```
%Grid
<n_r values, the r axis, in metres>
<n_z values, the z axis, in metres>
%Data
<n_r values>      <- one row per z sample
...               <- n_z rows
```

Nothing else in the file. No extra `%Grid` block, no second table, no comment header:
`nanopnp.density.grid.read_grid` reads one table per file, and that reader is the one VAL-15
verified against the delivered 77 MB `prod5_clya_charge` table to 4.7 × 10⁻¹². Adopting a
second parser would put unverified code between the reference and every number this phase
reports.

**Row order is `[i_z, i_r]`** — one row per `z`, one value per `r`. No patch is square, so a
transposed export is a shape error at ingest rather than a field that is wrong everywhere
except on `r = z`.

## 3. `manifest.yaml`

```yaml
schema: nanopnp/golden/v1

case: clya-0.5M-plus50mV
# From: uv run nanopnp validate case-hash docs/validation/cases/clya-0.5M-plus50mV.case.yaml
case_hash: e266057d941a1893c57e86f00612d464f966a659641492fe17790074471b6b70

probe: clya-reference
# From: uv run nanopnp validate export-grid <the probe document>
probe_hash: 0d347ffcb1eb782eb87a1802ef4521b304ee2b72cdb2e2ce400689a3cbf4a9d4

refinement: published          # or refined_1
source: comsol

comsol_version: "COMSOL Multiphysics 5.4 (build 5.4.0.388)"
model_file: npgrid_clya_v8_NaCl_report.mph
export_date: "2026-09-18"

fields:
  potential:   {expression: V,    unit: V}
  c_Na+:       {expression: cpos, unit: mol/m^3}
  c_Cl-:       {expression: cneg, unit: mol/m^3}
  velocity_r:  {expression: u,    unit: m/s}
  velocity_z:  {expression: w,    unit: m/s}
  pressure:    {expression: p,    unit: Pa}

# NOT IN REPORT (.knowledge/09 section F). Only you know these two, and the
# ingest refuses a manifest that leaves either blank.
current_boundary: "the cis reservoir cap, boundary 196"
current_sign_reference: cis     # or trans -- see below

quantities:
  bias_V: 0.05
  current_A: 1.2345e-9
  currents_A: {Na+: 8.0e-10, Cl-: 4.3e-10}
  transport_number: 0.65
  conductance_S: 2.469e-8
  eof_m3_s: 3.1e-18
```

Take `case_hash` from the command, not from this page. It moved once, on 24 September 2026, when
the case schema moved to `nanopnp/case/v2` and the schema string left the key
(`SPECIFICATION.md` §5.3.2 NOTE). A golden declaring the earlier value, `7e9ca188…`, is
refused when it is compared, naming both hashes.

### The two declarations only you can make

**`current_boundary`** — which boundary `tds.ntflux_i` was evaluated on. The model report does
not carry it. Write the boundary number and a sentence a reader can act on.

**`current_sign_reference`** — `cis` or `trans`. §6.7's NOTE fixes our convention: positive
current flows trans → cis, referenced to the **grounded cis electrode**, which is the sign for
which an uncharged ohmic pore has `G = I/V > 0` at either sign of the bias. If the exported
current references the trans electrode instead, declare `trans`: the loader negates the
current, the per-species currents, the conductance and the EOF rate — and **prints that it
did** in every report. The transport number is a ratio of two quantities that flip together
and is left alone.

If you are unsure which it is: solve the uncharged-pore case, or check the sign of `I` at
positive bias against a pore you know is cation-selective. Guessing is the one thing that
makes a rectification ratio come out reciprocal with nothing to say so.

### What is optional

Everything under `quantities:` except `bias_V` and `current_A`. Omit a key you do not have;
the comparison records it as unavailable rather than silently covering one quantity fewer.

`rectification` is deliberately absent — it is a two-point ratio (§5.3.1 NOTE) formed from the
matched opposite-bias pair, not a property of either case.

## 4. Ingest

```bash
uv run nanopnp validate ingest-golden \
    "$NANOPNP_REFERENCE_DATA/comsol/clya-0.5M-plus50mV/published" \
    --probe docs/validation/probes/clya-reference.probe.yaml
```

writes `golden.npz` and `golden.manifest.json` beside the tables. It refuses, naming what is
wrong, if:

- a required declaration is missing or blank;
- a unit is not the one this build reads;
- `probe_hash` is not the probe document's;
- a declared field has no table, or a table's axes are not the patch's to 10⁻⁶ nm;
- a table's shape is not `(n_z, n_r)`.

Run it once per directory as the exports land. Everything it checks is checked **there**,
once, rather than on every nightly run.

## 5. What happens to it

Both `nanopnp validate compare` and `nanopnp validate report` re-check the `probe_hash` against
the `--probe` document they were given, and `load_golden` re-checks `golden.npz` and
`golden.manifest.json` against the `golden_hash` written with them. A golden read back is
therefore refused on the same three grounds it was ingested on, not only on the day it landed.

`nanopnp validate compare` samples our solution on the same probe grid and reports, per field,
the *r*-weighted relative L² (the VAL-01 quantity), the unweighted relative L² (which is what
sees the axis, where the `1/r` forms are fragile) and the located maximum. `nanopnp validate
report` runs the four-rung attribution ladder and decomposes the discrepancy into the parts we
chose and the part that could be a defect.

Tier 3 is **recorded, not gated** (§7.1, §7.6). Nothing you export here can fail a build.
