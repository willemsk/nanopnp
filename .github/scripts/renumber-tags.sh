#!/usr/bin/env bash
# Re-create every tag .github/renumbered-tags.txt lists under its new name, on
# the same commit, with the tagger date and message of the tag it replaces
# (SPECIFICATION.md section 2.7, the Versioning NOTE; section 8.2.4 D1).
#
#   .github/scripts/renumber-tags.sh            # dry run: print what it would do
#   .github/scripts/renumber-tags.sh --apply    # create, push, then retire
#
# --apply needs a clone with every tag fetched (git fetch --tags) and push
# rights on origin. It pushes the new tags before it deletes any old one, so an
# interruption leaves both names rather than neither; re-running is safe. The
# old GitHub Release for v0.5.0 is deleted and the release workflow dispatched
# for v0.2.0, when the gh CLI is available; otherwise the two commands are
# printed for you to run.
set -euo pipefail

apply=false
[[ ${1:-} == --apply ]] && apply=true
root=$(git rev-parse --show-toplevel)
map="$root/.github/renumbered-tags.txt"

run() {
  if $apply; then "$@"; else printf '  would run:'; printf ' %q' "$@"; printf '\n'; fi
}

rename() {
  sed -e 's/v0\.5\.0/v0.2.0/g' -e 's/v0\.9\.0/v0.3.0/g' -e 's/\bv0\.5\b/v0.2/g'
}

new_tags=()
old_tags=()
while read -r new old; do
  [[ -z $new || $new == \#* ]] && continue
  if git rev-parse -q --verify "refs/tags/$new" > /dev/null; then
    echo "$new exists; not re-created"
  else
    git rev-parse -q --verify "refs/tags/$old" > /dev/null ||
      { echo "neither $new nor $old exists here; run git fetch --tags" >&2; exit 1; }
    commit=$(git rev-parse "$old^{commit}")
    date=$(git for-each-ref "refs/tags/$old" --format='%(taggerdate:iso-strict)')
    message=$(git for-each-ref "refs/tags/$old" --format='%(contents)' | rename)
    echo "$old -> $new on ${commit:0:10} ($date)"
    if $apply; then
      GIT_COMMITTER_DATE=$date git tag -a "$new" "$commit" -m "$message"
    fi
  fi
  new_tags+=("$new")
  old_tags+=("$old")
done < "$map"

# Three tags at most per push: a push of more than three triggers no workflow,
# and the tags must each be built. The milestone's Release is dispatched below.
for ((i = 0; i < ${#new_tags[@]}; i += 3)); do
  run git push origin "${new_tags[@]:i:3}"
done
for old in "${old_tags[@]}"; do
  if git ls-remote --exit-code --tags origin "refs/tags/$old" > /dev/null 2>&1 || ! $apply; then
    run git push origin ":refs/tags/$old"
  fi
  if git rev-parse -q --verify "refs/tags/$old" > /dev/null; then
    run git tag -d "$old"
  fi
done

if command -v gh > /dev/null; then
  if gh release view v0.5.0 > /dev/null 2>&1 || ! $apply; then run gh release delete v0.5.0 --yes; fi
  run gh workflow run release.yml -f tag=v0.2.0
else
  echo "gh is not installed. Delete the v0.5.0 Release on GitHub, then dispatch the Release"
  echo "workflow with tag v0.2.0 (Actions > Release > Run workflow)."
fi
$apply || echo "Dry run. Re-run with --apply to make these changes."
