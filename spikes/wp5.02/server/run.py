"""Serve an app on loopback; print the ready line; stop when stdin closes (AF1)."""

from __future__ import annotations

import sys
import threading

import uvicorn


class Server(uvicorn.Server):
    """A uvicorn server that announces the port it bound."""

    async def startup(self, sockets=None) -> None:  # noqa: ANN001
        await super().startup(sockets)
        port = self.servers[0].sockets[0].getsockname()[1]
        print(f"nanopnp-gui ready http://127.0.0.1:{port}/", flush=True)


def serve(app, port: int = 0) -> None:  # noqa: ANN001
    server = Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))

    def watch() -> None:
        sys.stdin.read()
        server.should_exit = True

    threading.Thread(target=watch, daemon=True).start()
    server.run()
