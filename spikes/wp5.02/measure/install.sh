#!/usr/bin/env bash
# install.sh: what each candidate adds to a fresh venv, cold and warm cache (D3 measure 4).
set -euo pipefail
work=$(mktemp -d)
here=$(cd "$(dirname "$0")/.." && pwd)
timeit() { local s=$(date +%s.%N); "$@" >/dev/null 2>&1; echo "$(echo "$(date +%s.%N) - $s" | bc)"; }
for cand in "react:fastapi uvicorn" "nicegui:fastapi uvicorn nicegui"; do
  name=${cand%%:*}; pkgs=${cand#*:}
  for cache in cold warm; do
    uv venv -q "$work/$name-$cache" --python 3.14
    flag=""; [ "$cache" = cold ] && flag="--no-cache"
    t=$(timeit uv pip install -q $flag --python "$work/$name-$cache/bin/python" $pkgs)
    size=$(du -sk "$work/$name-$cache/lib/python3.14/site-packages" | cut -f1)
    count=$(ls "$work/$name-$cache/lib/python3.14/site-packages" | grep -c dist-info)
    echo "$name $cache install_s=$t added_KiB=$size distributions=$count"
  done
done
cd "$here/react"
echo "react frontend build: npm ci $(timeit npm ci) s, vite build $(timeit npx vite build) s, dist $(du -sk dist | cut -f1) KiB, node_modules $(du -sk node_modules | cut -f1) KiB"
rm -rf "$work"
