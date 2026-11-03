"""VER-78: every state loads every screen of the workbench, and its server keeps its contract."""

from __future__ import annotations

import hashlib
import http.client
import os
import re
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.gui.web import server
from nanopnp.gui.web.screens import SCREENS, Screen
from nanopnp.gui.web.states import STATES

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Playwright

BROWSER_ARGS = ["--enable-unsafe-swiftshader", "--use-gl=angle", "--use-angle=swiftshader"]
READY_WAIT_MS = 90_000
STOP_WITHIN_S = 10


# Returns (playwright, browser), or skips, or fails where the gate requires a browser.
def _launch() -> tuple[Playwright, Browser]:
    sync = pytest.importorskip("playwright.sync_api")
    required = os.environ.get("NANOPNP_REQUIRE_BROWSER") == "1"
    handle = sync.sync_playwright().start()
    try:
        path = os.environ.get("NANOPNP_CHROMIUM")
        browser = handle.chromium.launch(args=BROWSER_ARGS, executable_path=path or None)
    except Exception as error:
        handle.stop()
        if required:
            pytest.fail(f"NANOPNP_REQUIRE_BROWSER=1 and no browser launches: {error}")
        pytest.skip(f"no browser: {error}")
    return handle, browser


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    handle, chromium = _launch()
    yield chromium
    chromium.close()
    handle.stop()


def _start(*arguments: str) -> tuple[subprocess.Popen[str], re.Match[str]]:
    process = subprocess.Popen(
        [sys.executable, "-m", "nanopnp.gui.web.server", "--no-browser", *arguments],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    assert process.stdout is not None
    line = process.stdout.readline().strip()
    found = server.READY.match(line)
    if found is None:
        process.kill()
        raise AssertionError(f"the first line of output is not the ready line: {line!r}")
    return process, found


@pytest.fixture(scope="module", params=STATES)
def running(request: pytest.FixtureRequest) -> Iterator[tuple[str, str]]:
    process, found = _start("--state", request.param)
    yield request.param, found.group(1)
    assert process.stdin is not None
    process.stdin.close()
    process.wait(STOP_WITHIN_S)


@pytest.mark.parametrize("screen", SCREENS, ids=lambda screen: screen.id)
def test_ver78_every_state_loads_every_screen_with_its_controls(
    running: tuple[str, str], browser: Browser, screen: Screen
) -> None:
    state, url = running
    errors: list[str] = []
    foreign: list[str] = []
    origin = url.split("/?")[0]
    page = browser.new_page(viewport={"width": 1000, "height": 640})
    page.on("pageerror", lambda error: errors.append(f"page error: {error}"))
    page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" else None)
    page.on(
        "request",
        lambda r: (
            foreign.append(r.url) if not r.url.startswith((origin, "data:", "blob:")) else None
        ),
    )
    page.goto(url)  # the token in the address sets the cookie every later request carries
    page.goto(origin + screen.path)
    page.wait_for_selector('body[data-screen-ready="1"]', timeout=READY_WAIT_MS)
    hidden = [
        name
        for name in screen.controls
        if not page.locator(f"[data-control={name}]").first.is_visible()
    ]
    page.close()
    assert hidden == [], f"{state}/{screen.id}: controls not visible"
    assert errors == [], f"{state}/{screen.id}"
    assert foreign == [], f"{state}/{screen.id}: a request left the origin"


def _status(
    url: str, path: str, *, host: str | None = None, cookie: str | None = None
) -> tuple[int, str | None]:
    port = int(re.search(r":(\d+)/", url).group(1))  # type: ignore[union-attr]
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Host": host} if host else {}
    if cookie:
        headers["Cookie"] = cookie
    connection.request("GET", path, headers=headers)
    response = connection.getresponse()
    return response.status, response.getheader("Set-Cookie")


def _outside_address() -> str | None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        address: str = probe.getsockname()[0]
    except OSError:
        return None
    finally:
        probe.close()
    return None if address.startswith("127.") else address


def test_ver78_the_server_keeps_its_contract() -> None:
    process, found = _start()
    url = found.group(1)
    token = url.split("token=")[1]
    port = int(re.search(r":(\d+)/", url).group(1))  # type: ignore[union-attr]
    try:
        address = _outside_address()
        if address is not None:
            with pytest.raises(OSError), socket.create_connection((address, port), timeout=3):
                pass
        assert _status(url, "/api/health")[0] == 403
        assert _status(url, f"/api/health?token={token}", host="evil.example")[0] == 403
        assert _status(url, "/api/health?token=wrong")[0] == 403
        status, cookie = _status(url, f"/api/health?token={token}")
        assert status == 200
        assert cookie is not None and "HttpOnly" in cookie and "SameSite=Strict" in cookie
        assert cookie.startswith(f"{server.COOKIE}_")
        assert _status(url, "/api/health", cookie=cookie.split(";")[0])[0] == 200
        assert _status(url, "/api/health?token=%C3%A9")[0] == 403
        assert process.stdin is not None
        started = time.monotonic()
        process.stdin.close()
        assert process.wait(STOP_WITHIN_S) == 0
        assert time.monotonic() - started < STOP_WITHIN_S
    finally:
        process.kill()
    terminated, _ = _start()
    try:
        terminated.send_signal(signal.SIGTERM)
        terminated.wait(STOP_WITHIN_S)
    finally:
        terminated.kill()


def test_ver78_the_reloading_server_prints_its_line_and_stops_with_its_input() -> None:
    process, found = _start("--dev", "--port", "0")
    try:
        token = found.group(1).split("token=")[1]
        for _ in range(60):
            try:
                if _status(found.group(1), f"/api/health?token={token}")[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            raise AssertionError("the reloading server never answered")
        assert process.stdin is not None
        process.stdin.close()
        assert process.wait(STOP_WITHIN_S) == 0
    finally:
        process.kill()


def test_ver78_the_server_cancels_the_solves_it_started() -> None:
    class Solve:
        running = True
        cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    solve = Solve()
    server.track(solve)  # type: ignore[arg-type]
    server._stop_children()
    assert solve.cancelled


def test_con09_the_vendored_molstar_is_unmodified() -> None:
    folder = Path(server.__file__).parent / "assets" / "molstar"
    notice = (folder / "NOTICE.md").read_text(encoding="utf-8")
    for name in ("molstar.js", "molstar.css"):
        digest = hashlib.sha256((folder / name).read_bytes()).hexdigest()
        assert digest in notice, f"{name} differs from the build NOTICE.md names"
