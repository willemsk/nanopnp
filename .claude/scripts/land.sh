#!/usr/bin/env bash
# Land the current branch: the core's *Gate and push*, steps 1 to 6, in order, stopping at the
# first failure (`.claude/workflow/core.md`; WP6.09 D7, §8.2.56 BF1).
#
#   land.sh [--lease <sha>]
#
# 1. Rewrites the decisions page and the indexes of the plans and reviews, and commits what they
#    wrote. 2. Checks that the tree is clean. 3. Runs the strict documentation build when a
#    documentation source changed since the last push, and commits the navigation it rewrote.
# 4. Rebases on `origin/<branch>` where it exists. 5. Runs the push gate. 6. Pushes, retrying
#    after 2, 4, 8 and 16 s.
#
# `--lease <sha>` is for a branch rewritten on `main` (the core, step 7): it skips the rebase and
# pushes with `--force-with-lease=<branch>:<sha>`.
#
# The last line is `land: pushed <sha>` or `land: failed at <step>`. The push goes through this
# script, not a typed `git push`, so the gate hook does not judge it: step 5 is the push gate
# itself, run on the tree that is pushed.
set -uo pipefail

fail() {
    echo "land: failed at $1"
    exit 1
}

lease=""
if [[ $# -eq 2 && $1 == --lease && -n $2 ]]; then
    lease=$2
elif [[ $# -ne 0 ]]; then
    fail "the arguments: land.sh [--lease <sha>], given: $*"
fi

cd "$(git rev-parse --show-toplevel)" || fail "the repository"
branch=$(git branch --show-current)
[[ -n $branch && $branch != main ]] || fail "the branch: not on a branch, or on main"

# 1. The registers.
echo "land: the registers"
uv run .claude/scripts/decisions.py || fail "the registers (decisions.py)"
uv run .claude/scripts/index_records.py || fail "the registers (index_records.py)"
registers=(docs/project/decisions.md docs/project/decisions-closed.md docs/plans docs/code_reviews docs/design/reviews)
if [[ -n $(git status --porcelain -- "${registers[@]}") ]]; then
    git add -- "${registers[@]}"
    git commit -q --no-verify -m "docs: the decisions page and the indexes" || fail "the registers' commit"
fi

# 2. A clean tree.
[[ -z $(git status --porcelain) ]] || {
    git status --short
    fail "a clean tree: commit or remove the changes above"
}

# 3. The documentation build, when a source changed since the last push (or since main).
git fetch -q origin main "$branch" 2>/dev/null || git fetch -q origin main || fail "the fetch"
if git rev-parse -q --verify "origin/$branch" >/dev/null; then
    since="origin/$branch"
else
    since="origin/main"
fi
sources='^(SPECIFICATION\.md|specification/|knowledge/|CHANGELOG\.md|examples/[^/]+/README\.md|data/corrections/|mkdocs\.yml|src/|docs/)'
changed=$(git diff --name-only "$since"...HEAD | grep -E "$sources" | grep -vE '^docs/(plans|code_reviews)/')
if [[ -n $changed ]]; then
    echo "land: the documentation build"
    uv run just docs || fail "the documentation build"
    if [[ -n $(git status --porcelain -- mkdocs.yml) ]]; then
        git add mkdocs.yml
        git commit -q --no-verify -m "docs: the navigation" || fail "the navigation's commit"
    fi
    [[ -z $(git status --porcelain) ]] || fail "the documentation build: it left changes besides mkdocs.yml"
fi

# 4. The rebase.
if [[ -z $lease ]] && git rev-parse -q --verify "origin/$branch" >/dev/null; then
    if ! git merge-base --is-ancestor "origin/$branch" HEAD; then
        echo "land: rebase on origin/$branch"
        git rebase -q "origin/$branch" || {
            git rebase --abort
            fail "the rebase on origin/$branch: resolve it by hand"
        }
    fi
fi

# 5. The push gate.
echo "land: the push gate"
.claude/hooks/gate.sh run || fail "the push gate"

# 6. The push.
args=(-u origin "$branch")
[[ -n $lease ]] && args=(--force-with-lease="$branch:$lease" -u origin "$branch")
for wait in 0 2 4 8 16; do
    sleep "$wait"
    if git push "${args[@]}"; then
        echo "land: pushed $(git rev-parse --short HEAD)"
        exit 0
    fi
done
fail "the push"
