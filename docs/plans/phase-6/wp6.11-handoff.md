# WP6.11 hand-off, ship (the pulled-in items fixed)

## Step

Ship, after the two items the author pulled in (REV-303, REV-302) were fixed on PR #230. Their review comes next.

## Done

- 1f720ee fix: PHY-23's terms and NUM-28's split take a permittivity wall fit's gradient (REV-303 fixed).
- a84efce perf: the kernel compiles each slot's integrand (REV-302 fixed).
- This note.

## Measured

- REV-302, 118-element cylinder, one thread, after 1f720ee: one `Apply` and one `AssembleLinearization` under PHY-23,
  39.8 s (`reference`) and 19.1 s (`supg`) before; 0.38 s and 0.28 s after. Without PHY-23, uncompiled: 0.73 s and
  0.40 s.
- `supg` streamline slot, Na+: 8.2 s; the decrement's drift dropped from the lagged wind 2.6 s, from the trial wind
  4.5 s; `Freeze()` on the lagged state 8.2 s.
- Compiled against uncompiled, twelve variants: residual 0 difference, Jacobian at most 1.3e-17 relative.
- REV-303: VER-81's force split with a permittivity wall fit holds to 1e-12 relative; without the `d` part it misses
  by 1.7e-16 N on a 2.5e-12 N total (two variants fail).
- Tests run: `tests/tier1/test_forces.py`, `tests/tier1/test_nernst_planck.py` (pass); the commit hook's Tier 1 on
  both commits (pass).

## Decided

- REV-303 also takes the wall part in the Nernst–Planck decrement's gradient of `∂ε~_r/∂c~_i` (`state_gradient` serves
  both), and PHY-22's check admits a wall fit alone as something for PHY-23's switch to switch.
- A wall distance given as a composite coefficient (not a number or a grid function) now raises from `ngs.grad` where
  the permittivity varies and the force or decrement is built; the pipeline always passes a grid function.
- REV-302 compiles every slot (all models), not only the stabilisation's.

## Open

None.

## Next

1. The main session hands `np-reviewer` (`effort: medium`) the diff `c598dcd..a84efce` alone (§8.2.56 BF8).
2. Then update the PR #230 body (Deliberately not done: drop REV-302 and REV-303), hand back `WAIT, land: yes`, and
   read CI on the landed head (`np-ship/wp.md` §5).
