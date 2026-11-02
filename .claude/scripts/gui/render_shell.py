"""Render every screen of the browser workbench in every fixture state, light and dark.

    uv run python .claude/scripts/gui/render_shell.py <out-dir>

Starts one `nanopnp gui --no-browser --state <name>` per state, writes a manifest of screens
x schemes, runs `shoot.cjs` over it, and stops the servers by closing their standard input.
Exits with `shoot.cjs`'s status (2 if a page did not load), or 1 if a server did not start.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from nanopnp.gui.web import server
from nanopnp.gui.web.screens import SCREENS
from nanopnp.gui.web.states import STATES

SHOOT = Path(__file__).with_name("shoot.cjs")
VIEWPORT = [1280, 800]
SCHEMES = ("light", "dark")
READY = 'body[data-screen-ready="1"]'


def start(state: str) -> tuple[subprocess.Popen[str], str]:
    """Start the workbench in a state and return it with its first address."""
    process = subprocess.Popen(
        [sys.executable, "-m", "nanopnp.gui.web.server", "--no-browser", "--state", state],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    found = server.READY.match(process.stdout.readline().strip())
    if found is None:
        process.kill()
        raise SystemExit(f"the {state} server printed no ready line")
    return process, found.group(1)


def main(argv: list[str]) -> int:
    """Shoot the shell into the directory ``argv[0]``."""
    if len(argv) != 1:
        print(__doc__)
        return 64
    out = Path(argv[0])
    out.mkdir(parents=True, exist_ok=True)
    servers: list[subprocess.Popen[str]] = []
    manifest = []
    try:
        for state in STATES:
            process, first = start(state)
            servers.append(process)
            origin = first.split("/?")[0]
            for screen in SCREENS:
                for scheme in SCHEMES:
                    manifest.append(
                        {
                            "id": f"shell-{state}-{screen.id}-{scheme}",
                            "url": origin + screen.path,
                            "via": [first],
                            "ready": READY,
                            "viewport": VIEWPORT,
                            "scheme": scheme,
                            "wait_ms": 500,
                        }
                    )
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return subprocess.run(["node", str(SHOOT), str(out / "manifest.json"), str(out)]).returncode
    finally:
        for process in servers:
            if process.stdin is not None:
                process.stdin.close()
        for process in servers:
            process.wait(30)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
