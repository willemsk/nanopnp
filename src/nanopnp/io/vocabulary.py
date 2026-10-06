"""The field names every layer shares: the solved fields a mesh, a model and an export name.

One home for the names (REV-03, WP38 D9). The lowest reader is stage 6's mesh
gate, which asks a mesh for each field's essential boundaries, so the names live
in the base rather than in ``mesh`` or ``physics``. A species' concentration is
named by the model's own rule, :func:`nanopnp.physics.models.concentration_field_name`,
and is not here.
"""

from __future__ import annotations

POTENTIAL = "potential"
"""Name of the potential field, shared by every model."""

VELOCITY = "velocity"
"""Name of the velocity field of the flow-carrying models."""

VELOCITY_AXIS = "velocity_axis"
"""Key of the axis constraint ``u_r = 0`` among a model's essential boundaries.

:meth:`nanopnp.physics.models.PhysicsModel.essential_boundaries` returns it. The
one essential set that is not a whole field: the axis constrains one component
of ``u`` and leaves ``u_z`` natural (NUM-06), so it is reported beside the
velocity's own no-slip set rather than folded into it."""

PRESSURE = "pressure"
"""Name of the pressure field of the flow-carrying models."""

PRESSURE_MEAN = "pressure_mean"
"""Name of the scalar multiplier fixing the pressure level; see ``pressure_constraint``
in :mod:`nanopnp.physics.models`."""
