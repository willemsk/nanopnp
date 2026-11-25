#!/usr/bin/env bash
# Exit 0 if every path on stdin is prose, 1 if any is not.
#
# The one definition both the commit gate (.claude/hooks/gate.sh) and CI's
# `changes` job use to skip the lock check, mypy and pytest; both still run ruff
# and the decisions page's check, and the gate the `records` tests, which hold
# code to a Markdown record (the specification's clauses, the findings
# registers). A path is prose when it is Markdown that no other test reads: *.md,
# except under
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
# So is the workflow, everything under .claude/, which no test reads but one
# (section 8.2.56 BF11): tests/tier1/test_written_architecture.py loads
# .claude/scripts/decisions.py, so that script is not prose and a change to it
# runs the suite. Ruff still covers the workflow's scripts.
#
# Empty input is prose: there is nothing to test.
set -uo pipefail

while IFS= read -r path; do
    [[ -z $path ]] && continue
    case $path in
        src/* | data/* | examples/*) exit 1 ;;
        .claude/scripts/decisions.py) exit 1 ;;
        .claude/*) ;;
        *.md | specification/history/holds-now.yaml) ;;
        *) exit 1 ;;
    esac
done
exit 0
