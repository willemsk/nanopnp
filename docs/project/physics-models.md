# Adding a physics model

A physics model is one class and one registration (FR-20, QR-14). The geometry, mesh, charge,
solver, post-processing, sweep, provenance and interface layers read what the model declares and
nothing else, so a model added this way runs from a case file to the report with no other edit.
This page is for developers; the normative statement is §5.4.3 of the
[specification](https://github.com/willemsk/nanopnp/blob/main/SPECIFICATION.md) and its NOTE on
what a model declares. It walks `poisson`, the smallest shipped model, as the worked example.

Users do not write weak forms (N1). A new model is a change to the package, reviewed like any
other, and it must be verified before it is trusted.

## The two halves

**The declaration** is a frozen `ModelDeclaration`, registered with the model's name. It is read
before anything is built, because case validation decides whether a case can run before a mesh is
read. It is per *name*, not per class: `epnp-ns`, `pnp-ns` and `pnp` share one class and differ in
what they admit.

| Field | What reads it | What it decides |
|---|---|---|
| `options` | `resolve` | Which of the case-derived keywords reach the builder (the resolved `model_options`) |
| `switches` | `resolve` | The values of `flow`, `variable_density`, `inertia` and `dielectric_gradient_forces` the model honours; any other value is refused |
| `solids` | `resolve`, the mesh gate | Whether `physics.solid_permittivities` means anything, and whether a mesh may carry a solid domain |
| `coefficients` | `resolve`, the solve | Whether `inputs.charge` (`fixed_charge`) and `inputs.eps_r` (`solid_fraction`) are accepted and passed |
| `wall_distance` | the mesh gate, the solve | Whether the PHY-02 distance field is computed, gated and passed |
| `strategies` | `resolve` | The values of `numerics.continuation` the model admits; `default_ladder` only for `epnp-ns` and `pnp-ns`, the models NUM-18 ends at, which `register_model` enforces |
| `quantities` | `resolve`, stage 11 | The `outputs:` words it provides; `fields` is admitted for every model |
| `transport` | stage 11, the ladder, the GUI | Whether it is reached as a `TransportModel` |
| `reports_newton` | stage 10 | Whether its `solve` takes a Newton `callback` |

**The built model** satisfies the `PhysicsModel` protocol: its `name` (the registered name), its
`fields`, `species` (empty for one field), `boundary_conditions`, `scales` (the NUM-09 scale set),
`provenance`, `essential_boundaries(boundaries)`, `relative_permittivity(solution)`, `space`,
`cold_state`, `residual_form` and `solve`. A model declaring `transport` also satisfies
`TransportModel`, the members of the coupled models that QoI extraction, the NUM-18 ladder, the
IF-07 export and the MMS harness read. Consumers reach it through `transport_model(solution)`,
which consults the declaration and refuses a model that does not declare transport.

## The worked example: `poisson`

`poisson` solves `−∇·(ε₀ε_r∇φ) = ρ_pore` over the whole domain, with no mobile ions (the PHY-21
NOTE on the electrostatic models). It is the configuration VAL-06 compares with APBS.

**The equation, in the mesh's units.** On the NUM-09 scales, `φ̃ = φ/V_T` and
`ρ̃ = ρ a²/(ε₀ ε_r,f⁰ V_T)` with `a = 1 nm`, the weak form is

```text
∫ ε̃ ∇φ̃·∇v r dr dz = ∫ ρ̃_pore v r dr dz,    ε̃ = ε_r / ε_r,f⁰
```

`ε̃` is 1 in the fluid, which is ion-free water at `ε_r,f⁰` whatever the permittivity correction
says (author ruling 13), and `ε_s/ε_r,f⁰` in each solid. The material split and the §4.4 `χ` blend
are `relative_permittivity_field`, the same function the coupled models use, so the two cannot
assign a solid differently.

**The class.** `PoissonModel` is a frozen dataclass carrying the electrolyte (for `ε_r,f⁰` and the
temperature of the scale set), the concentration, the element order, the fluid pattern and
`solid_permittivities`. Its `residual_form` is the stiffness term less the source:

```python
def residual_form(
    self, space, measures, *, fixed_charge=None, solid_fraction=None, state=None, **kwargs
):
    _reject_unknown(kwargs, f"{self.name!r}.residual_form")
    trial, test = space.TnT()
    permittivity = self.permittivity(space.mesh, solid_fraction=solid_fraction)
    residual = poisson_operator(
        trial, test, measures, permittivity=permittivity, extra_order=RADIAL_WEIGHT_ORDER
    )
    if fixed_charge is not None:
        residual -= charge_source(fixed_charge, test, measures, extra_order=RADIAL_WEIGHT_ORDER)
    return residual
```

Three conventions carry over to any model:

- **Refuse what you do not understand.** The protocol's `**kwargs` lets models with different
  vocabularies share one interface, and `_reject_unknown` stops that becoming silence: a keyword a
  model ignores would run a different problem from the one asked for.
- **Accept `state`.** A restore rebuilds every model's residual through one call and passes the
  state, which a stabilised coupled model needs and `poisson` ignores.
- **Say what the quadrature is.** NGSolve estimates an integrand's order from its trial and test
  functions and does not see the `r` weight, so at P2 an axisymmetric stiffness term is integrated
  one order short. `poisson` adds that order, `RADIAL_WEIGHT_ORDER`; without it the three-layer
  capacitor is 3 % off next to the axis, and with it the error is round-off.

`solve` assembles the Jacobian of that same residual and takes one exact step from the essential
data. The source is then integrated by the same form as the operator, as the coupled models carry
`ρ̃_pore` inside their residual.

**The builder and the declaration.**

```python
register_model(
    "poisson",
    _build_poisson,
    ModelDeclaration(
        options=("order", "solid_permittivities"),
        switches={
            "flow": (False,),
            "variable_density": (False,),
            "inertia": (False,),
            "dielectric_gradient_forces": (False,),
        },
        solids=True,
        coefficients=("fixed_charge", "solid_fraction"),
    ),
)
```

Every builder receives `electrolyte` and `concentration_M` beside the declared options, and may
refuse a configuration by raising `ValueError` or `TypeError`: `resolve` builds the model once and
reports the refusal naming `physics.model`. The model it returns must answer to the name it is
registered by, because every consumer finds the declaration by that name; `create` refuses one
that does not. Building must not import NGSolve, because resolving a
case is how the command line validates it. The declaration above then decides the rest without
further code:

- a case switching `flow` on, or supplying `outputs: [current]`, is refused naming `poisson`, the
  key and what is admitted;
- `physics.solid_permittivities` and `inputs.charge` are accepted, and the solve passes the charge
  as `fixed_charge` on the model's own `scales`. A charge deposited from a structure reaches the
  model the same way, as the element-wise field stage 7 deposited, and a structure case protonates
  only for a model that declares `fixed_charge` ([From a structure to a
  charge](../guide/charge.md#which-models-take-a-charge));
- the mesh gate asks for the potential's boundaries and the two electrodes, and not for the
  distance sources or any concentration boundary;
- `numerics.continuation` must be `none`, and stage 11 records the bias with an empty selection;
- the IF-07 export writes `φ` and `ε_r` from the model's `scales` and `relative_permittivity`.

## The rule, and its one exemption

No module outside `physics/` may name a model class, compare with a registered model name, or spell
one as a literal. `tests/tier1/test_model_interface.py` walks the package source to enforce it and
shows the walk firing on the code that should trip it. The exemption is `default_ladder` in
`solve/continuation.py`: §6.5 defines the NUM-18 ladder as a path through named models, so the
ladder names them. It is a strategy a model admits, not a branch on the model. The schema's default
`physics.model` and the validated default case write the validated model down as data, and may
spell its name.

The same file proves the claim end to end. A forwarding class, defined in the test, subclassing no
shipped model and registered at run time, runs stages 10 to 12 from a case file and reproduces
`pnp` bit for bit.

## Before a model is trusted

A registered model runs; that does not make it right. Verify it the way the shipped ones are:
an analytic benchmark that localises an error to a single term first (for `poisson`, the
three-layer capacitor in `tests/tier2/test_poisson_layers.py`, whose exact solution the P2 space
contains), then a comparison against an independent code. Anything that departs from the validated
model goes behind a switch, default off, and is recorded in the provenance of every result.
