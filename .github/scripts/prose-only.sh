#!/usr/bin/env bash
# Exit 0 if every path on stdin is prose, 1 if any is not.
#
# The one definition both the commit gate (.claude/hooks/gate.sh) and CI's
# `changes` job use to skip the lock check, mypy and pytest. A path is prose
# when it is Markdown and nothing reads it: *.md, except under
#   src/, data/ package data, THIRD-PARTY-LICENSES.md among it, which
#               tests/tier1/test_gui_selftest.py asserts (CON-11);
#   examples/   the worked examples, whose READMEs tests/tier2/test_examples_*.py
#               executes (VER-46);
# docs/ is NOT prose as a directory: docs/sweeps/ and docs/validation/ hold the
# YAML that tests/tier1 reads (the section 8.3 reference sweep, the frozen
# cases, the probe grid). Only its Markdown is, and CI's documentation build runs
# on every change regardless.
#
# specification/history/holds-now.yaml is prose too: the one reader is
# .claude/scripts/decisions.py, whose --check the gate and CI run on every change.
#
# Empty input is prose: there is nothing to test.
set -uo pipefail

while IFS= read -r path; do
    [[ -z $path ]] && continue
    case $path in
        src/* | data/* | examples/*) exit 1 ;;
        *.md | specification/history/holds-now.yaml) ;;
        *) exit 1 ;;
    esac
done
exit 0
