"""The workbench's local server: loopback only, one ready line, a token, stops with its input."""

from __future__ import annotations

import argparse
import hmac
import os
import re
import secrets
import signal
import socket
import sys
import tempfile
import threading
import webbrowser
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from http import cookies
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

import uvicorn
from fastapi import FastAPI

from nanopnp.core.public import __version__
from nanopnp.gui.web.pages import install
from nanopnp.gui.web.states import STATES, Workbench, boot, boot_case

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


def build_app(token: str, bench: Workbench) -> Guard:
    """Return the FastAPI app, with the screens of ``bench`` installed, behind its guard.

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

    install(app, bench, token)
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


_DEV_ENVIRONMENT = (
    "NANOPNP_GUI_TOKEN",
    "NANOPNP_GUI_WORK",
    "NANOPNP_GUI_CASE",
    "NANOPNP_GUI_STATE",
)


def _watch_input(server: uvicorn.Server | None) -> None:
    sys.stdin.read()
    if server is not None:
        server.should_exit = True
    else:
        os.kill(os.getpid(), signal.SIGINT)  # the reloading supervisor stops on it


def _boot(case: str | None, state: str | None, work: Path) -> Workbench:
    if case:
        return boot_case(Path(case), work)
    return boot(state or "empty", work)


def dev_app() -> Guard:
    """Return the app of a ``--dev`` worker, which the reloading supervisor starts afresh.

    The supervisor passes the launch token, the folder that keeps the store between reloads, and
    the case or state in environment variables.
    """
    token, work, case, state = (os.environ.get(name) for name in _DEV_ENVIRONMENT)
    assert token is not None and work is not None
    guard = build_app(token, _boot(case, state, Path(work)))
    port = int(os.environ["NANOPNP_GUI_PORT"])
    guard.hosts = frozenset({f"{HOST}:{port}", f"localhost:{port}"})
    return guard


def _serve_dev(args: argparse.Namespace, token: str, work: Path) -> None:
    """Serve with reload: a change to a page, a style sheet or the bridge restarts the worker."""
    port = args.port
    if port == 0:  # a reloading server keeps one address, so it is chosen before the first worker
        with socket.socket() as probe:
            probe.bind((HOST, 0))
            port = probe.getsockname()[1]
    os.environ.update(
        NANOPNP_GUI_TOKEN=token,
        NANOPNP_GUI_WORK=str(work),
        NANOPNP_GUI_PORT=str(port),
        NANOPNP_GUI_CASE=str(args.case or ""),
        NANOPNP_GUI_STATE=args.state or "",
    )
    url = f"http://{HOST}:{port}/?token={token}"
    print(f"nanopnp-gui ready {url}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    threading.Thread(target=_watch_input, args=(None,), daemon=True).start()
    uvicorn.run(
        "nanopnp.gui.web.server:dev_app",
        factory=True,
        host=HOST,
        port=port,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)],
        reload_includes=["*.py", "*.css", "*.js"],
        log_level="warning",
    )


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
    parser.add_argument("case", nargs="?", type=Path, help="a case file, walked to its charge")
    parser.add_argument(
        "--state", choices=STATES, help="a fixture state in place of a case (the screens' tests)"
    )
    parser.add_argument("--port", type=int, default=0, help="the port; 0 picks a free one")
    parser.add_argument(
        "--no-browser", action="store_true", help="print the address and open nothing"
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="reload on a change to the screens' source",
    )
    args = parser.parse_args(argv)
    if args.case is not None and args.state is not None:
        parser.error("give a case file or --state, not both")

    token = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="nanopnp-gui-") as work:
        if args.dev:
            _serve_dev(args, token, Path(work))
            return 0
        guard = build_app(token, _boot(str(args.case or ""), args.state, Path(work)))
        config = uvicorn.Config(guard, host=HOST, port=args.port, log_level="warning")
        server = _Server(config, guard, token, browser=not args.no_browser)
        threading.Thread(target=_watch_input, args=(server,), daemon=True).start()
        server.run()
    return 0


if __name__ == "__main__":  # pragma: no cover - run as a script, never imported by a test
    sys.exit(main())
