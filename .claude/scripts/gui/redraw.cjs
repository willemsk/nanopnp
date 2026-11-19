// Time Meso's Charge map redraw after a pick on the (r, z) map: decision D11, the 200 ms line
// (ruling AG7; WB-23).
//
//   node .claude/scripts/gui/redraw.cjs <address> [--continuum <name>] [--picks 20] [--gap-ms 1500]
//        [--warmup 3] [--headed] [--json] [--trace <file>]
//
// <address> is the line a served project prints, `nanopnp-gui ready <address>`, for a project whose
// continuum model's charge is built (a 2WCD project): serve it with
// `uv run python -m nanopnp.gui.web.server --no-browser --project <folder>`. The script loads that
// address first, which sets the token cookie, then `/meso/charge`. `--continuum` names the
// continuum model whose charge map is picked on; it is the one the page itself draws when the
// option is left out. It picks residues on the map by
// clicking canvas pixels at their charged atoms, alternating between a few residues so that each
// pick redraws. Per pick it records, from the pointer's release:
//   - the markers' paint: `body[data-screen-ready]` going to "0" and back to "1";
//   - Mol*'s second frame after the selection: the next increment of `body[data-drawn]`;
//   - Mol*'s own share: that frame less the moment the page called `nano.show`.
// The markers' paint is split into its parts: the server's handling (the release to the page's
// `nano.plane` call), the drawing's fetch (its Resource Timing entry, start to response end) and the
// canvas's own paint (the response end to the markers' paint).
// The whole repaint is the later of the first two. The line binds the markers' paint and the whole
// repaint, the median and the nearest-rank p95 of each. `--warmup` picks come first and are not
// counted. `--json` prints one object (the picks' timings, medians, p95s, GPU string, viewport) in
// place of the text report. `--trace` writes a Chromium performance trace of the counted picks, to
// profile a miss.
//
// Run it on a machine with a GPU, which the headless software renderer is not: `--headed` opens a
// window that uses the real GPU. Point NODE_PATH at a global Playwright (`NODE_PATH=$(npm root -g)`);
// NANOPNP_CHROMIUM names a Chromium executable to use. The report names the GPU the page got.
// Exits 0 once the picks are timed, whether or not the line is met, and 1 with a message if the
// page never readies, a pick never paints (30 s) or no pick point is found.
//
// CommonJS: Playwright is installed globally and found through NODE_PATH, which serves
// `require` and not `import`.

"use strict";

const { chromium } = require("playwright");

const VIEWPORT = { width: 1440, height: 900 };
const READY_MS = 90000;
const PICK_TIMEOUT_MS = 30000;
const LINE_MS = 200;
const CANDIDATES = 6;

class Failure extends Error {}

function parse(argv) {
  const options = { picks: 20, gapMs: 1500, warmup: 3, headed: false, json: false, trace: null, continuum: null, url: null };
  const number = (name, text) => {
    const value = Number(text);
    if (!Number.isInteger(value) || value < 0) throw new Failure(`${name}: ${text} is not a whole number`);
    return value;
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const value = () => {
      if (i + 1 >= argv.length) throw new Failure(`${arg} takes a value`);
      i += 1;
      return argv[i];
    };
    if (arg === "--picks") options.picks = number(arg, value());
    else if (arg === "--gap-ms") options.gapMs = number(arg, value());
    else if (arg === "--warmup") options.warmup = number(arg, value());
    else if (arg === "--trace") options.trace = value();
    else if (arg === "--continuum") options.continuum = value();
    else if (arg === "--headed") options.headed = true;
    else if (arg === "--json") options.json = true;
    else if (arg.startsWith("--")) throw new Failure(`unknown option ${arg}`);
    else if (options.url === null) options.url = arg;
    else throw new Failure(`unexpected argument ${arg}`);
  }
  if (!options.url) throw new Failure("usage: redraw.cjs <address> [options]; see the head comment");
  if (options.picks < 1) throw new Failure("--picks must be at least 1");
  return options;
}

// Nearest rank: the smallest value with at least p of the sample at or below it.
function percentile(values, p) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.max(0, Math.ceil(p * sorted.length) - 1)];
}

function summary(values) {
  values = values.filter((v) => v !== null);
  return { count: values.length, median: percentile(values, 0.5), p95: percentile(values, 0.95) };
}

// Run in the page: the timings of one pick are written to window.__redraw.cur.
function instrument() {
  const state = { cur: null };
  window.__redraw = state;
  const stamp = (field) => {
    if (state.cur && state.cur[field] === null) state.cur[field] = performance.now();
  };
  document.getElementById("plane").addEventListener(
    "pointerup",
    () => {
      if (state.armed) {
        state.armed = false;
        state.cur = { up: performance.now(), plane: null, hidden: null, painted: null, show: null, drawn: null };
      }
    },
    true,
  );
  performance.setResourceTimingBufferSize(1000);
  const plane = window.nano.plane;
  window.nano.plane = function (...args) {
    stamp("plane");
    return plane.apply(this, args);
  };
  const show = window.nano.show;
  window.nano.show = function (...args) {
    stamp("show");
    return show.apply(this, args);
  };
  const body = document.body;
  let drawn = body.dataset.drawn;
  let ready = body.dataset.screenReady;
  new MutationObserver(() => {
    if (body.dataset.screenReady !== ready) {
      ready = body.dataset.screenReady;
      if (ready === "0") stamp("hidden");
      else if (ready === "1" && state.cur && state.cur.hidden !== null) stamp("painted");
    }
    if (body.dataset.drawn !== drawn) {
      drawn = body.dataset.drawn;
      if (state.cur && state.cur.show !== null) stamp("drawn");
    }
  }).observe(body, { attributes: true, attributeFilter: ["data-screen-ready", "data-drawn"] });
}

async function gpuOf(page) {
  return page.evaluate(() => {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    if (!gl) return { renderer: null, vendor: null, note: "no WebGL context" };
    const info = gl.getExtension("WEBGL_debug_renderer_info");
    if (!info) return { renderer: null, vendor: null, note: "WEBGL_debug_renderer_info is unavailable" };
    return { renderer: gl.getParameter(info.UNMASKED_RENDERER_WEBGL), vendor: gl.getParameter(info.UNMASKED_VENDOR_WEBGL) };
  });
}

// Residues the pick will alternate between: each with a charged atom's point at which the server
// ranks that residue first, so that a click there selects it.
async function candidates(page, continuum) {
  const keys = await page.$$eval("[data-control=charge-strip-item]", (items) =>
    items.map((item) => item.textContent.trim().split(/\s+/)[0]),
  );
  if (!keys.length) throw new Failure("the charge screen lists no residues");
  return page.evaluate(
    async ({ continuum, keys, want }) => {
      const found = [];
      for (const key of keys) {
        if (found.length >= want) break;
        const drawing = await (await fetch(`/api/meso/${continuum}/charge/plane?residue=${encodeURIComponent(key)}`)).json();
        const layer = drawing.layers.find((l) => l.id === "residue" && l.kind === "points");
        if (!layer || !layer.points_nm || layer.points_nm.length < 2) continue;
        for (let k = 0; k + 1 < layer.points_nm.length; k += 2) {
          const [r, z] = [layer.points_nm[k], layer.points_nm[k + 1]];
          const ranked = await (await fetch(`/api/meso/${continuum}/residues?r=${r}&z=${z}`)).json();
          if (ranked.length && ranked[0].key === key) {
            found.push({ key, r, z });
            break;
          }
        }
      }
      return found;
    },
    { continuum, keys, want: CANDIDATES },
  );
}

// The canvas pixel of a data point, page coordinates; null where it lies off the canvas.
async function pixelOf(page, point) {
  return page.evaluate(({ r, z }) => {
    const canvas = document.querySelector("#plane canvas");
    const box = canvas.getBoundingClientRect();
    const [x, y] = window.nano.canvas.toScreen(r, z);
    if (x < 0 || y < 0 || x > box.width || y > box.height) return null;
    return { x: box.left + x, y: box.top + y };
  }, point);
}

async function pick(page, point) {
  const pixel = await pixelOf(page, point);
  if (!pixel) throw new Failure(`residue ${point.key}: its atoms lie off the canvas`);
  await page.evaluate(() => {
    window.__redraw.cur = null;
    window.__redraw.armed = true;
    performance.clearResourceTimings();
  });
  await page.mouse.move(pixel.x, pixel.y);
  await page.mouse.down();
  await page.mouse.up();
  try {
    await page.waitForFunction(
      () => {
        const cur = window.__redraw.cur;
        return Boolean(cur && cur.painted !== null && cur.drawn !== null);
      },
      null,
      { timeout: PICK_TIMEOUT_MS, polling: 50 },
    );
  } catch (error) {
    throw new Failure(`a pick of ${point.key} did not paint and draw within ${PICK_TIMEOUT_MS / 1000} s`);
  }
  const cur = await page.evaluate(() => {
    const cur = window.__redraw.cur;
    const entry = performance
      .getEntriesByType("resource")
      .find((e) => e.name.includes("/charge/plane") && e.startTime >= cur.up);
    return { ...cur, fetchStart: entry ? entry.startTime : null, fetchEnd: entry ? entry.responseEnd : null };
  });
  const tenth = (value) => Math.round(value * 10) / 10;
  const markers = tenth(cur.painted - cur.up);
  const molstar = tenth(cur.drawn - cur.up);
  return {
    residue: point.key,
    markers_ms: markers,
    server_to_plane_ms: cur.plane === null ? null : tenth(cur.plane - cur.up),
    fetch_start_ms: cur.fetchStart === null ? null : tenth(cur.fetchStart - cur.up),
    fetch_end_ms: cur.fetchEnd === null ? null : tenth(cur.fetchEnd - cur.up),
    fetched_ms: cur.fetchEnd === null ? null : tenth(cur.fetchEnd - cur.fetchStart),
    canvas_paint_ms: cur.fetchEnd === null ? null : tenth(cur.painted - cur.fetchEnd),
    molstar_ms: molstar,
    whole_ms: Math.max(markers, molstar),
    molstar_share_ms: tenth(cur.drawn - cur.show),
  };
}

async function measure(options) {
  const launch = { headless: !options.headed, args: ["--enable-unsafe-swiftshader"] };
  if (process.env.NANOPNP_CHROMIUM) launch.executablePath = process.env.NANOPNP_CHROMIUM;
  const browser = await chromium.launch(launch);
  try {
    const page = await browser.newPage({ viewport: VIEWPORT });
    const errors = [];
    page.on("pageerror", (error) => errors.push(String(error)));
    let continuum = options.continuum;
    page.on("request", (request) => {
      const match = request.url().match(/\/api\/meso\/([^/]+)\/charge\/plane/);
      if (match && !continuum) continuum = decodeURIComponent(match[1]);
    });
    await page.goto(options.url, { waitUntil: "load" });
    const origin = new URL(options.url).origin;
    await page.goto(`${origin}/meso/charge`, { waitUntil: "load" });
    try {
      await page.waitForSelector('body[data-screen-ready="1"]', { timeout: READY_MS });
      await page.waitForSelector("[data-control=charge-strip-item]", { timeout: 30000 });
    } catch (error) {
      throw new Failure(`the charge screen did not ready within ${READY_MS / 1000} s (a served project with a continuum model whose charge is built is needed)`);
    }
    if (!continuum) throw new Failure("the page did not fetch a charge drawing: no continuum model to pick residues of");
    const points = await candidates(page, continuum);
    if (points.length < 2) throw new Failure(`found ${points.length} pick points; at least two residues are needed`);
    await page.evaluate(instrument);
    const gpu = await gpuOf(page);
    const picks = [];
    const total = options.warmup + options.picks;
    let tracing = false;
    for (let i = 0; i < total; i += 1) {
      if (i === options.warmup && options.trace) {
        await browser.startTracing(page, { path: options.trace, screenshots: false });
        tracing = true;
      }
      const timed = await pick(page, points[i % points.length]);
      if (i >= options.warmup) picks.push(timed);
      await page.waitForTimeout(options.gapMs);
    }
    if (tracing) await browser.stopTracing();
    return { picks, gpu, continuum, errors };
  } finally {
    await browser.close();
  }
}

function report(options, result) {
  const { picks } = result;
  const markers = picks.map((p) => p.markers_ms);
  const molstar = picks.map((p) => p.molstar_ms);
  const whole = picks.map((p) => p.whole_ms);
  const share = picks.map((p) => p.molstar_share_ms);
  const measures = {
    markers_paint: summary(markers),
    server_to_plane: summary(picks.map((p) => p.server_to_plane_ms)),
    drawing_fetched: summary(picks.map((p) => p.fetched_ms)),
    canvas_paint: summary(picks.map((p) => p.canvas_paint_ms)),
    molstar_second_frame: summary(molstar),
    whole_repaint: summary(whole),
    molstar_own_share: summary(share),
  };
  const holds = (m) => m.median < LINE_MS && m.p95 < LINE_MS;
  const met = { markers_paint: holds(measures.markers_paint), whole_repaint: holds(measures.whole_repaint) };
  return { options, result, measures, met };
}

function text({ result, measures, met }) {
  const { gpu } = result;
  const ms = (v) => `${v.toFixed(1)} ms`;
  const row = (label, m) =>
    m.count
      ? `${label.padEnd(30)} median ${ms(m.median).padStart(10)}   p95 ${ms(m.p95).padStart(10)}   n=${m.count}`
      : `${label.padEnd(30)} not recorded`;
  const lines = [
    `Redraw after a pick, ${result.picks.length} picks on continuum model ${result.continuum}`,
    row("Markers' paint", measures.markers_paint),
    row("  server to nano.plane", measures.server_to_plane),
    row("  drawing fetched", measures.drawing_fetched),
    row("  canvas paint", measures.canvas_paint),
    row("Mol*'s second frame", measures.molstar_second_frame),
    row("Whole repaint (the later)", measures.whole_repaint),
    row("Mol*'s own share", measures.molstar_own_share),
    `GPU: ${gpu.renderer ? `${gpu.renderer} (${gpu.vendor})` : `unavailable (${gpu.note})`}`,
    `Viewport: ${VIEWPORT.width} x ${VIEWPORT.height}`,
    `Markers' paint, median and p95 under ${LINE_MS} ms: ${met.markers_paint ? "yes" : "no"}`,
    `Whole repaint, median and p95 under ${LINE_MS} ms: ${met.whole_repaint ? "yes" : "no"}`,
  ];
  if (result.errors.length) lines.push(`Page errors: ${result.errors.length}, first: ${result.errors[0]}`);
  return lines.join("\n");
}

async function main() {
  const options = parse(process.argv.slice(2));
  const done = report(options, await measure(options));
  if (options.json) {
    console.log(
      JSON.stringify({
        continuum: done.result.continuum,
        count: done.result.picks.length,
        viewport: VIEWPORT,
        gpu: done.result.gpu,
        picks: done.result.picks,
        measures: done.measures,
        line_ms: LINE_MS,
        line_met: done.met,
        page_errors: done.result.errors,
      }),
    );
  } else {
    console.log(text(done));
  }
}

main().catch((error) => {
  console.error(error instanceof Failure ? `redraw: ${error.message}` : error);
  process.exit(1);
});
