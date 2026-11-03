# Code review 027: WP5.02, the framework spike and the visual-feedback workflow

Reviewed: PR 150, base `773bb65d873b08d81c235b6ac4aac4d94a713c8d`, head `4af195b1985766c6e2e15fd20ac9aa303ec59a0c`.
Level: xhigh, with `--fix`. Status: completed. Static review: no benchmark, sweep, cost study, `gate.sh` or
`pytest --nightly` was run by the reviewer; the fixes were gated afterwards.

The test scope was read first: `test_gui_screens.py` (VER-78, CON-09), the VER-57 case in `test_pqr.py` and the
fixture move in `tests/conftest.py` are all in scope; none was dropped.

## Findings

15 candidates; 10 fixed, 3 recorded as open items, 1 kept by specification, 1 partly fixed.

1. **A non-ASCII token raised `TypeError` in the guard** (correctness; `server.py`). `compare_digest` refuses a
   non-ASCII `str`, so a wrong token gave 500, not the 403 VER-78 requires. **Fixed:** compared as UTF-8 bytes; the
   contract test asserts the 403.
2. **One cookie name for every port of 127.0.0.1** (correctness; `server.py`). A second workbench overwrote the
   first's token. **Fixed:** the name carries a digest of the token.
3. **`boot_case` ended the server on any refusal but a schema one** (correctness; `states.py`). **Fixed** for exit 3
   and 4 refusals. `Link`'s `ValueError` and `KeyError` still propagate: REV-177.
4. **The link's residue key differed from Mol*'s** (correctness; `link.py`). A negative residue number or a blank
   chain was keyed otherwise than written to the PDB text, so picks were dropped. **Fixed:** one `_chain_id` and
   `residue_key` describe the PDB text.
5. **`Link.__init__` was quadratic in residues** (efficiency; `link.py`). **Fixed:** one pass over plain lists.
6. **Our static files were cached for an hour** (correctness of `--dev`; `pages.py`). **Fixed:** `max_cache_age=0`.
7. **`--dev` printed its ready line before the port was bound** (correctness; `server.py`). **Fixed:** a thread
   announces after the first successful connect.
8. **The fixture case wrote unquoted paths into YAML** (correctness; `charged_tube.py`). **Fixed:** JSON-quoted. The
   default citation `tests/conftest.py` stays: changing it changes the profile hash.
9. **The selected-fill measure misses `aria-pressed`** (tooling; `shoot.cjs`). **Not fixed:** REV-178.
10. **`track()` has no caller in `src`** (dead code; `server.py`). **Kept:** VER-78 (h) specifies it. `Link.limit`
    and `Link.units` were unread and are removed.
11. **numpy imported at module top** (convention; `link.py`, `charged_tube.py`). **Fixed.**
12. **Docstrings on private code** (convention). **Fixed:** comments instead.
13. **`READY_WAIT_S` held milliseconds** (convention; the test). **Fixed:** `READY_WAIT_MS`.
14. **`nanopnp gui` has no smoke test of its own** (test scope). **Not fixed:** REV-179.
15. **The SIGTERM leg leaked its process, and the dev poll loop spun on a non-200** (test hygiene). **Fixed.**

The cookie's name changed, so the plan's middleware list (`wp5.02-framework-spike.md`) states it.
