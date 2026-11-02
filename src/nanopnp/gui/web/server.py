"""The workbench's local server: loopback only, one ready line, a token, stops with its input."""

from __future__ import annotations

import argparse
import hmac
import re
import secrets
import socket
import sys
import threading
import webbrowser
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from http import cookies
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

import uvicorn
from fastapi import FastAPI

from nanopnp.core.public import __version__

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from nanopnp.gui.solver import SolverProcess

__all__ = [
    "COOKIE",
    "HOST",
    "READY",
    "Guard",
    "build_app",
    "main",
    "track",
]

HOST = "127.0.0.1"
"""The only interface the server binds (ADR-004's NOTE, the desktop wrapper)."""

READY = re.compile(r"^nanopnp-gui ready (http://127\.0\.0\.1:\d+/\?token=[\w-]+)$")
"""The one line a wrapper reads from standard output to learn the address."""

COOKIE = "nanopnp_token"

_FORBIDDEN = b"forbidden: a foreign Host, or neither the launch token nor its cookie"
_CHILDREN: list[SolverProcess] = []


def track(process: SolverProcess) -> None:
    """Register a running solve, so the server cancels it when it stops."""
    _CHILDREN.append(process)


def _stop_children() -> None:
    for process in _CHILDREN:
        if process.running:
            process.cancel()
    _CHILDREN.clear()


class Guard:
    """ASGI middleware: refuse a foreign Host, and a request without the launch token.

    A page opened with ``?token=`` receives the token as an ``HttpOnly``, ``SameSite=Strict``
    cookie, so that its later requests and its websocket carry it without the query.
    """

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token
        self.hosts: frozenset[str] = frozenset()

    def _allowed(self, scope: Scope) -> tuple[bool, bool]:
        """Return ``(allowed, set_cookie)`` for a request."""
        headers = {key.lower(): value for key, value in scope["headers"]}
        if headers.get(b"host", b"").decode("latin-1") not in self.hosts:
            return False, False
        query = parse_qs(scope["query_string"].decode("latin-1")).get("token", [""])[0]
        if hmac.compare_digest(query, self.token):
            return True, True
        jar: cookies.SimpleCookie = cookies.SimpleCookie()
        jar.load(headers.get(b"cookie", b"").decode("latin-1"))
        morsel = jar.get(COOKIE)
        return morsel is not None and hmac.compare_digest(morsel.value, self.token), False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Pass an allowed request on; answer any other with 403."""
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        allowed, set_cookie = self._allowed(scope)
        if not allowed:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
                return
            await send(
                {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                }
            )
            await send({"type": "http.response.body", "body": _FORBIDDEN})
            return
        if not set_cookie or scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def with_cookie(message: Message) -> None:
            if message["type"] == "http.response.start":
                value = f"{COOKIE}={self.token}; HttpOnly; SameSite=Strict; Path=/"
                message = {
                    **message,
                    "headers": [*message["headers"], (b"set-cookie", value.encode())],
                }
            await send(message)

        await self.app(scope, receive, with_cookie)


def build_app(token: str) -> Guard:
    """Return the FastAPI app behind its guard.

    The guard learns its allowed Host values once the port is bound, so the caller sets
    ``guard.hosts`` before serving.
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        _stop_children()

    app = FastAPI(title="nanopnp workbench", lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Say that the server is up, and which version of nanopnp runs it."""
        return {"status": "ok", "version": __version__}

    return Guard(app, token)


class _Server(uvicorn.Server):
    """A uvicorn server that announces the address it bound, once, on standard output."""

    def __init__(self, config: uvicorn.Config, guard: Guard, token: str, *, browser: bool) -> None:
        super().__init__(config)
        self._guard = guard
        self._token = token
        self._browser = browser

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        """Bind, then name the address (see ADR-004's NOTE for the wrapper that reads it)."""
        await super().startup(sockets)
        if not self.started:
            return
        port = self.servers[0].sockets[0].getsockname()[1]
        self._guard.hosts = frozenset({f"{HOST}:{port}", f"localhost:{port}"})
        url = f"http://{HOST}:{port}/?token={self._token}"
        print(f"nanopnp-gui ready {url}", flush=True)
        if self._browser:
            webbrowser.open(url)


def _watch_input(server: uvicorn.Server) -> None:
    sys.stdin.read()
    server.should_exit = True


def main(argv: Sequence[str] | None = None) -> int:
    """Serve the workbench on the loopback interface until standard input closes or a signal.

    A desktop wrapper starts this with ``--no-browser --port 0``, reads the ready line, loads
    its address, and closes the standard input to stop the server.
    """
    parser = argparse.ArgumentParser(
        prog="nanopnp gui",
        description="Serve the workbench on 127.0.0.1. The server prints one line, "
        "'nanopnp-gui ready <url>', and stops when its standard input closes or on "
        "SIGINT or SIGTERM.",
    )
    parser.add_argument("--port", type=int, default=0, help="the port; 0 picks a free one")
    parser.add_argument(
        "--no-browser", action="store_true", help="print the address and open nothing"
    )
    args = parser.parse_args(argv)

    token = secrets.token_urlsafe(32)
    guard = build_app(token)
    config = uvicorn.Config(guard, host=HOST, port=args.port, log_level="warning")
    server = _Server(config, guard, token, browser=not args.no_browser)
    threading.Thread(target=_watch_input, args=(server,), daemon=True).start()
    server.run()
    return 0


if __name__ == "__main__":  # pragma: no cover - run as a script, never imported by a test
    sys.exit(main())
