#!/usr/bin/env bash
# start.sh <log> <port> <ngui|react>: start a candidate with stdin held open; its pid goes to <log>.pid.
log=$1; port=$2; kind=$3
cd "$(dirname "$0")/.."
if [ "$kind" = ngui ]; then
  mod="--with nicegui python -m ngui.main"
else
  mod="python -m react.main"
fi
sleep 100000 | uv run --project ../.. --with fastapi --with uvicorn $mod --port "$port" > "$log" 2>&1 &
echo $! > "$log.pid"
for _ in $(seq 60); do grep -q "ready" "$log" && exit 0; sleep 1; done
exit 1
