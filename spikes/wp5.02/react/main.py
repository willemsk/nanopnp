"""The React candidate's server: the shared API plus the built front end."""

from __future__ import annotations

import argparse
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from server.app import app
from server.run import serve

HERE = Path(__file__).resolve().parent
MOLSTAR = HERE / "node_modules" / "molstar" / "build" / "viewer"
TOKENS = HERE.parents[2] / "docs" / "design"

# Mounted after the /api routes, so those win.
app.mount("/vendor/molstar", StaticFiles(directory=MOLSTAR), name="molstar")
app.mount("/tokens", StaticFiles(directory=TOKENS), name="tokens")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    app.mount("/", StaticFiles(directory=HERE / "dist", html=True), name="dist")
    serve(app, args.port)


if __name__ == "__main__":
    main()
