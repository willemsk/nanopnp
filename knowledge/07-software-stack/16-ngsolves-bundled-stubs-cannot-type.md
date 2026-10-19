---
type: Library Behaviour
title: 16. NGSolve's bundled stubs cannot type-check, so the aliases in `core/typing.py`
  are `Any`
description: NGSolve's bundled stubs cannot type-check, so the aliases in core/typing.py
  are Any.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
tested_with:
  ngsolve: 6.2.2606
  mypy: 2.3.1
verified:
---

## 16. NGSolve's bundled stubs cannot type-check, so the aliases in `core/typing.py` are `Any` {#16-ngsolves-bundled-stubs-cannot-type-check-so-the-aliases-in-coretypingpy-are-any}

NGSolve 6.2.2606 ships pybind11-stubgen output (24 `.pyi` files) but no `py.typed` marker, so mypy
skips them (PEP 561) and every NGSolve name resolves to `Any`. Supplying the marker only exposes that
`ngsolve/__init__.pyi` (shipped in the Linux wheel; the macOS and Windows wheels carry none) does not parse (it ends in `ngslib =` and `ngsolve =` with empty right-hand
sides). Netgen ships no stubs. The aliases of `core/typing.py` therefore stay `Any` and name what a
value is, until upstream ships stubs that parse behind a marker (source: `core/typing.py`).

