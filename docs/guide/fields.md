# Charge and permittivity fields

A pore's fixed charge, and optionally its dielectric, can be supplied as fields on a regular
`(r, z)` grid through `inputs.charge` and `inputs.eps_r`. Stage 7 deploys them on the mesh and gates
them. This page is about those supplied fields. A charge produced from a structure, by PDB2PQR,
PROPKA and smearing, is deposited on the mesh instead of read from a grid: see [From a structure
to a charge](charge.md).

## The field header

A field is named by a header document, `schema: nanopnp/field/v1`, with `format: field1` in the
case (the §5.3.1 `inputs.charge` NOTE). The header declares:

- **`quantity`** and **`units`**: what the numbers are (below);
- the **grid**: origin, spacing and shape;
- **`q_net_e`**: the net charge the producer knows the field carries, in elementary charges;
- **`axis_cutoff_nm`**: the axis guard of PHY-18;
- **`provenance`**: where the field came from;
- exactly one source of values: **`data:`**, a file on disk (`.npz` by default, OpenDX or CCP4
  through the optional GridDataFormats, or the reference model's own COMSOL grid table, read-only),
  or **`form:`**, a registered analytic form (`uniform`, `gaussian_ring`, `slab`) with typed
  parameters.

A form is how you supply a field with a known closed form: the Gaussian ring integrates to exactly
its charge, so `q_net_e` is exact. [Example 02](../_generated/examples/02-charged-pore.md) uses one.
A form is not an expression evaluated at solve time. That would be arbitrary code whose provenance
is a string.

## The three quantities

| `quantity` | Units | Meaning |
|---|---|---|
| `areal_charge_density` | `C/m^2` or `e/m^2` | charge per unit area of the `(r, z)` half-plane, azimuthally integrated |
| `volume_charge_density` | `C/m^3` or `e/m^3` | charge per unit volume |
| `solid_fraction` | `1` | the fraction of solid, in [0, 1], for the dielectric blend |

The units are declared, never inferred. The difference between the two charge quantities is a
geometric factor (the §4.4 NOTE), and a grid file cannot say which it holds.

**An absolute permittivity field is refused.** The fluid's permittivity depends on the local
concentration (PHY-11), which is solved for, so a static permittivity field would silently switch
that correction off while the run still reported ePNP-NS. Supply a solid fraction instead, and the
solver blends the protein's permittivity with the fluid's (PHY-12, PHY-20).

## The conservation gate

Stage 7 deploys the field on the mesh, and then checks that the charge it deployed is the charge that
was declared (PHY-19, QR-03). The check has two legs, because either can fail alone. The producer
leg compares the grid's own integral against `q_net_e`. The consumer leg compares the deployed
field's integral on the mesh against the grid's. Stage 7 also checks that the mesh resolves the
field (quadrature agreement), that nothing significant lies at the grid's boundary, and what the
axis guard removed. A field that fails exits with code `4`. It names which check failed, by how
much, and where, and the report lands in the manifest's charge group.

A field on a grid finer than the mesh can pass the producer leg and fail the consumer leg: the mesh
cannot carry it. Refine the mesh where the charge is, or smear the charge more widely.

A charge deposited from a structure is checked differently (the §4.4 NOTE on the producer path's
conservation report). Its two legs are exact by construction, it takes no axis guard, and its
per-plane check compares against the atoms rather than the grid. [The conservation
report](charge.md#the-conservation-report) describes it.
