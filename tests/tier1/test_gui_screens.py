"""VER-78: every state loads every screen of the workbench, and its server keeps its contract."""

from __future__ import annotations

import hashlib
import http.client
import json
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

from nanopnp.api.project import Project
from nanopnp.gui.web import server
from nanopnp.gui.web.screens import SCREENS, Screen
from nanopnp.gui.web.states import STATES

if TYPE_CHECKING:
    from playwright.sync_api import Browser, Page, Playwright

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


CLI = ["-c", "import sys; from nanopnp.cli import main; sys.exit(main(sys.argv[1:]))", "gui"]
MODULE = ["-m", "nanopnp.gui.web.server"]


def _start(
    *arguments: str, entry: list[str] = MODULE, config: Path | None = None
) -> tuple[subprocess.Popen[str], re.Match[str]]:
    # The settings and the last project are the user's, so a test server keeps its own.
    environment = {**os.environ, **({} if config is None else {"NANOPNP_CONFIG": str(config)})}
    process = subprocess.Popen(
        [sys.executable, *entry, "--no-browser", *arguments],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=environment,
    )
    assert process.stdout is not None
    line = process.stdout.readline().strip()
    found = server.READY.match(line)
    if found is None:
        process.kill()
        raise AssertionError(f"the first line of output is not the ready line: {line!r}")
    return process, found


@pytest.fixture(scope="module", params=STATES)
def running(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[tuple[str, str]]:
    config = tmp_path_factory.mktemp(f"config-{request.param}")
    process, found = _start("--state", request.param, entry=CLI, config=config)
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


def test_ver78_a_refused_item_is_in_the_problems_list_and_opens_its_suite(
    browser: Browser, tmp_path: Path
) -> None:
    process, found = _start("--state", "refused", entry=CLI, config=tmp_path)
    url = found.group(1)
    origin = url.split("/?")[0]
    page = browser.new_page(viewport={"width": 1000, "height": 640})
    try:
        page.goto(url)
        page.goto(origin + "/study?panel=problems")
        page.wait_for_selector('body[data-screen-ready="1"]', timeout=READY_WAIT_MS)
        entry = page.locator("[data-control=problem-item]", has_text="continuum/").first
        assert "radius_nm" in entry.inner_text()
        assert "1 problem" in page.locator("[data-control=problems-count]").inner_text()
        entry.click()
        page.wait_for_url(origin + "/continuum", timeout=READY_WAIT_MS)
    finally:
        page.close()
        assert process.stdin is not None
        process.stdin.close()
        process.wait(STOP_WITHIN_S)


@pytest.fixture
def workbench(browser: Browser, tmp_path: Path) -> Iterator[tuple[Page, str, Path]]:
    process, found = _start("--state", "empty", entry=CLI, config=tmp_path)
    url = found.group(1)
    page = browser.new_page(viewport={"width": 1000, "height": 640})
    page.goto(url)
    yield page, url.split("/?")[0], tmp_path
    page.close()
    assert process.stdin is not None
    process.stdin.close()
    process.wait(STOP_WITHIN_S)


def _ready(page: Page, url: str) -> None:
    page.goto(url)
    page.wait_for_selector('body[data-screen-ready="1"]', timeout=READY_WAIT_MS)


def test_ver78_a_theme_chosen_in_the_settings_holds_after_a_reload(
    workbench: tuple[Page, str, Path],
) -> None:
    page, origin, config = workbench
    _ready(page, origin + "/settings")
    page.locator("[data-control=settings-theme]").click()
    page.get_by_role("option", name="Dark").click()
    page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
    _ready(page, origin + "/molecular")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert "theme: dark" in (config / "workbench.yaml").read_text(encoding="utf-8")


def test_ver78_a_rebound_shortcut_runs_its_command_and_the_old_chord_nothing(
    workbench: tuple[Page, str, Path],
) -> None:
    page, origin, _ = workbench
    _ready(page, origin + "/settings")
    page.locator("[data-control=key-suite-molecular]").click()
    page.wait_for_function("window.frame.capturing")
    page.keyboard.press("Control+KeyW")  # a browser keeps it, so the settings refuse it
    page.get_by_text("kept by the browser").wait_for()
    assert "Alt+Shift+1" in page.locator("[data-control=key-suite-molecular]").inner_text()
    page.locator("[data-control=key-suite-study]").click()
    page.wait_for_function("window.frame.capturing")
    page.keyboard.press("Control+Alt+KeyY")
    page.wait_for_function(
        "document.querySelector('[data-control=key-suite-study]').innerText.includes('Ctrl+Alt+Y')"
    )
    _ready(page, origin + "/molecular")
    page.keyboard.press("Alt+Shift+Digit4")  # the old chord of the study suite
    page.wait_for_timeout(1000)
    assert page.url == origin + "/molecular"
    page.keyboard.press("Control+Alt+KeyY")
    page.wait_for_url(origin + "/study", timeout=READY_WAIT_MS)


def test_ver78_l_a_setting_found_by_its_word_sets_the_page_and_writes_its_file(
    workbench: tuple[Page, str, Path],
) -> None:
    page, origin, config = workbench
    _ready(page, origin + "/settings")
    page.locator("[data-control=settings-search]").fill("compact")
    page.locator("[data-control=setting-density]").wait_for()
    assert not page.locator("[data-control=setting-theme]").is_visible()
    page.locator("[data-control=settings-density]").get_by_text("Compact").click()
    page.wait_for_function("document.documentElement.dataset.density === 'compact'")
    assert "density: compact" in (config / "workbench.yaml").read_text(encoding="utf-8")
    _ready(page, origin + "/molecular?palette=compact")
    found = page.locator("[data-control=palette-item]", has_text="Settings: Density")
    assert found.is_visible()


def test_ver78_l_a_project_value_writes_the_project_file(browser: Browser, tmp_path: Path) -> None:
    project = Project.create(tmp_path / "project")
    process, found = _start(str(project.root), entry=CLI, config=tmp_path / "config")
    origin = found.group(1).split("/?")[0]
    page = browser.new_page(viewport={"width": 1000, "height": 640})
    try:
        page.goto(found.group(1))
        _ready(page, origin + "/settings?setting=significant_figures")
        page.locator("[data-control=settings-scope]").get_by_text("Project").click()
        figures = page.locator("[data-control=settings-significant_figures]")
        figures.fill("6")
        figures.press("Tab")
        page.locator("[data-control=reset-significant_figures]").wait_for()
        assert Project.open(project.root).settings == {"significant_figures": 6}
        assert not (tmp_path / "config" / "workbench.yaml").exists()
    finally:
        page.close()
        assert process.stdin is not None
        process.stdin.close()
        process.wait(STOP_WITHIN_S)


def test_ver78_m_a_suite_change_keeps_the_window_and_builds_the_molecule_once(
    browser: Browser, tmp_path: Path
) -> None:
    process, found = _start("--state", "charged-tube", entry=CLI, config=tmp_path)
    url = found.group(1)
    origin = url.split("/?")[0]
    page = browser.new_page(viewport={"width": 1000, "height": 640})
    try:
        page.goto(url)
        _ready(page, origin + "/study/charge")
        page.evaluate("window.marker = 'kept'")
        page.locator("[data-control=suite-study]").click()
        page.wait_for_url(origin + "/study", timeout=READY_WAIT_MS)
        page.wait_for_selector('body[data-screen-ready="1"]', timeout=READY_WAIT_MS)
        assert not page.locator("[data-control=molecule]").is_visible()
        page.locator("[data-control=open-charge]").click()
        page.wait_for_url(origin + "/study/charge", timeout=READY_WAIT_MS)
        page.wait_for_selector('body[data-screen-ready="1"]', timeout=READY_WAIT_MS)
        assert page.evaluate("window.marker") == "kept"
        assert page.evaluate("window.nano.builds") == 1
        assert page.locator("[data-control=molecule]").is_visible()
    finally:
        page.close()
        assert process.stdin is not None
        process.stdin.close()
        process.wait(STOP_WITHIN_S)


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


def test_ver78_the_command_line_entry_writes_its_ready_line_as_json() -> None:
    process = subprocess.Popen(
        [sys.executable, *CLI, "--no-browser", "--json"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert process.stdout is not None and process.stdin is not None
        record = json.loads(process.stdout.readline())
        assert server.READY.match(f"nanopnp-gui ready {record['ready']}")
        process.stdin.close()
        assert process.wait(STOP_WITHIN_S) == 0
    finally:
        process.kill()


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
