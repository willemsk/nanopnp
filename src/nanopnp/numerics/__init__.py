"""Linear-solver adapters, damped Newton, state and increment gates, the axisymmetric measure.

The solver kernel (SPECIFICATION.md section 5.1, section 8.2.8 H11): it imports only
:mod:`nanopnp.core`, so the weak forms of :mod:`nanopnp.physics` and the ladder of
:mod:`nanopnp.solve` both import it downward.
"""
