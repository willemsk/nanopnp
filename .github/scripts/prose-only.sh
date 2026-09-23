#!/usr/bin/env bash
# Exit 0 if every path on stdin is prose, 1 if any is not.
#
# The one definition both the commit gate (.claude/hooks/gate.sh) and CI's
# `changes` job use to skip the lock check, mypy and pytest. A path is prose
# when it is Markdown and nothing reads it: *.md, except under
#   packaging/  LICENSES-BUNDLE.md ships in the bundle and the wheel and is
#               asserted by tests/tier1/test_gui_probe.py (CON-11);
#   src/, data/ package data;
#   examples/   the worked examples, whose READMEs tests/tier2/test_examples.py
#               executes (VER-46).
# docs/ is NOT prose as a directory: docs/sweeps/ and docs/validation/ hold the
# YAML that tests/tier1 reads (the section 8.3 reference sweep, the frozen
# cases, the probe grid). Only its Markdown is.
#
# Empty input is prose: there is nothing to test.
set -uo pipefail

while IFS= read -r path; do
    [[ -z $path ]] && continue
    case $path in
        packaging/* | src/* | data/* | examples/*) exit 1 ;;
        *.md) ;;
        *) exit 1 ;;
    esac
done
exit 0
