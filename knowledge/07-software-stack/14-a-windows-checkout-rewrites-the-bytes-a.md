---
type: Library Behaviour
title: 14. A Windows checkout rewrites the bytes a hash identifies
description: A Windows checkout rewrites the bytes a hash identifies.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 14. A Windows checkout rewrites the bytes a hash identifies **[tested: pending]** {#14-a-windows-checkout-rewrites-the-bytes-a-hash-identifies}

GitHub's Windows runners, and most Windows installs of git, check out with `core.autocrlf=true`, so
every text file in the index arrives with CRLF line endings. Any hash over a checked-out file's
bytes then differs by platform. `file_hash` is such a hash, and it is the version of a correction
file (FR-25) and part of the stage-8 materials key: on WP17's branch the VER-47 materials keys,
recorded on Linux, failed for all 13 corpus cases on Windows alone, and converting
`data/corrections/willems2020_nacl.yaml` to CRLF reproduces the same 13 failures on Linux.

A wheel is not affected — it ships the committed bytes — but a source checkout is, and that is what
CI and developers run. `.gitattributes` marks `data/**` `-text`, as it already did the vendored
renderer, so a checkout keeps the committed bytes (LF for the YAML, CRLF for the verbatim
`clya_as_radial_geometry.csv`). A new directory of files identified by their hash needs the same
line.

