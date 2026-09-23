# Outputs and quantities

`outputs:` in the case selects what a run reports. The extraction is one calculation (NUM-27), so
quantities reported together always come from the same solution by the same route.

| `outputs:` entry | Reports | Where |
|---|---|---|
| `current` | `current_A`, per-species `currents_A`, `conductance_S` | `run.json`, and printed |
| `transport_numbers` | `transport_number`, the cation fraction of the current, and `currents_A` | as above |
| `eof_rate` | `eof_m3_s`, the electro-osmotic volume flow rate | as above |
| `rectification` | the ratio of the current magnitudes at opposite biases | a sweep's `dataset.json` (below) |
| `analyte_force` | the axial force on an embedded analyte, by more than one route (§6.7) | as above |
| `fields` | the solution fields as XDMF with HDF5 heavy data (IF-07) | the report artefact, listed under `file` |

Every run also records the bias and the route agreement (below). It records how many times the
concentration clamp of PHY-13 was active, and, where a stabilisation mode is on, that mode's own
contribution to each current. These are the context that makes the quantities readable.

## Sign convention

The current is referenced to the grounded electrode: `boundary_conditions.ground`, `cis` by
default, with the bias applied to the other one. With `ground: cis`, a positive bias drives a
positive current, and the conductance `I / V` is positive at either sign of the bias (NUM-24).

## Two routes to the current

The ionic current is extracted twice, by the domain-indicator form (NUM-24) and by the variational
reaction flux (NUM-25), and the two must agree to a declared tolerance, species by species (NUM-26,
QR-04). If they do not, one of them is wrong and there is no telling which from the numbers, so no
current is reported and the run exits with code `4`. Each run records the pair and their relative
difference under `route_agreement`. The agreement is relative, so a run at exactly zero bias, where
the current is zero and both routes return round-off, fails it. Use a small nonzero bias instead.

The current is never taken from a cross-section integral of the flux: on a continuous finite-element
space that route converges more slowly and depends on where the cut is placed (`.knowledge/06`,
§7).

## Exported fields

With `fields` among the outputs, the report stage writes two XDMF files with HDF5 heavy data:
`fields_omega` over the whole domain and `fields_omega_w` over the fluid alone. A concentration of
zero inside a wall would look like a converged depletion, so fluid fields are never padded over a
solid. Values are SI, at the P2 node set, with each unit in the attribute's name: `phi_V`,
`c_<species>_mol_m3`, `u_m_s`, `p_Pa`, and `wall_distance_nm`. Coordinates are in nm. The
azimuthal `2π` is not applied, because exported fields are pointwise (the IF-07 NOTE). ParaView and
meshio read them; [example 04](../_generated/examples/04-python-api.md) does so from Python.
