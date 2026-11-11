// Shoot pages headless with Playwright's Chromium, and check each shot's contrast and target sizes.
//
//   node .claude/scripts/gui/shoot.cjs <manifest.json> <out-dir>
//   node .claude/scripts/gui/shoot.cjs --self-check <out-dir>
//
// The manifest is a JSON list of {id, url, viewport: [w, h], scheme: "light"|"dark", wait_ms,
// expand, via, ready, click}. With `expand`, a CSS selector, the page is shot once per matching element's
// `data-screen` value, after setting `location.hash` to it, as `<id>-<screen>`. `via` lists
// addresses to load first, so that a server's token cookie is set; `ready` is a selector awaited
// (90 s) after the load, as the workbench's `body[data-screen-ready="1"]`. `click` lists selectors
// clicked in order once the page is ready, each awaited (30 s) and followed by a short settle, so
// that a menu, a dialog or a folded rail is open when the page is shot. Entries that share a server
// (the first address of `via`) run in order, since a server's state carries from one shot to the
// next; the servers' entries run side by side, `NANOPNP_SHOOT_JOBS` at a time (default: one fewer
// than the CPUs, at most 3; more starves the software-GL pages, and a menu opens after the shot's
// wait). `index.json` keeps the manifest's order. Writes
// `<out>/<id>.png` and `<out>/index.json`; a shot's `viewer` is the shell's host-document flag, or
// null on another page, and `unmeasured` lists the text the contrast check could not measure.
// Exits 0, or 2 if a page failed to load.
//
// CommonJS: Playwright is installed globally and found through NODE_PATH, which serves
// `require` and not `import`.

"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

const DEFAULT_JOBS = Math.max(1, Math.min(3, os.cpus().length - 1));
const SCREEN_SETTLE_MS = 150;
const CLICK_SETTLE_MS = 400;
const QUIET_MS = 150;
const SETTLE_EXTRA_MS = 2000;

// Run inside the page: WCAG 2.2 1.4.3 (contrast) and 2.5.8 (target size, minimum), measured.
function checkPage() {
  const parse = (text) => {
    const match = text.match(/rgba?\(([^)]+)\)/);
    if (!match) return null;
    const parts = match[1].split(/[\s,/]+/).filter(Boolean).map(Number);
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  };
  const over = (top, bottom) => ({
    r: top.r * top.a + bottom.r * (1 - top.a),
    g: top.g * top.a + bottom.g * (1 - top.a),
    b: top.b * top.a + bottom.b * (1 - top.a),
    a: 1,
  });
  const luminance = (c) => {
    const channel = (v) => {
      const s = v / 255;
      return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);
  };
  const ratio = (a, b) => {
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  };
  const hex = (c) =>
    "#" + [c.r, c.g, c.b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");
  const selector = (element) => {
    const parts = [];
    let node = element;
    while (node && node.nodeType === 1 && parts.length < 4) {
      let part = node.tagName.toLowerCase();
      if (node.id) {
        parts.unshift(`${part}#${node.id}`);
        break;
      }
      const classes = [...node.classList].slice(0, 2);
      if (classes.length) part += "." + classes.join(".");
      const parent = node.parentElement;
      if (parent) {
        const same = [...parent.children].filter((c) => c.tagName === node.tagName);
        if (same.length > 1) part += `:nth-of-type(${same.indexOf(node) + 1})`;
      }
      parts.unshift(part);
      node = parent;
    }
    return parts.join(" > ");
  };
  const visible = (element) => {
    const rect = element.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return false;
    const style = getComputedStyle(element);
    return style.visibility !== "hidden" && style.display !== "none" && Number(style.opacity) > 0;
  };
  // The canvas behind a page that paints no background of its own.
  const root = () => {
    const scheme = getComputedStyle(document.documentElement).colorScheme || "";
    const dark = scheme.includes("dark") && matchMedia("(prefers-color-scheme: dark)").matches;
    return dark ? { r: 18, g: 18, b: 18, a: 1 } : { r: 255, g: 255, b: 255, a: 1 };
  };
  const background = (element) => {
    const layers = [];
    for (let node = element; node && node.nodeType === 1; node = node.parentElement) {
      const colour = parse(getComputedStyle(node).backgroundColor);
      if (colour && colour.a > 0) {
        layers.push(colour);
        if (colour.a >= 1) break;
      }
    }
    return layers.reduceRight((below, layer) => over(layer, below), root());
  };

  // Opacity below 1 on the element or an ancestor fades the text by an amount the layer walk
  // cannot place, so such text is reported as not measured rather than passed.
  const faded = (element) => {
    for (let node = element; node && node.nodeType === 1; node = node.parentElement) {
      if (Number(getComputedStyle(node).opacity) < 1) return true;
    }
    return false;
  };

  const contrast = [];
  const unmeasured = [];
  for (const element of document.body.querySelectorAll("*")) {
    if (["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(element.tagName)) continue;
    const own = [...element.childNodes].some(
      (n) => n.nodeType === 3 && n.textContent.trim().length > 0,
    );
    if (!own || !visible(element)) continue;
    // SVG text is painted by `fill` over sibling shapes, neither of which the walk above sees.
    const reason = element instanceof SVGElement ? "svg text" : faded(element) ? "opacity" : "";
    if (reason) {
      unmeasured.push({
        selector: selector(element),
        text: element.textContent.trim().slice(0, 60),
        reason,
      });
      continue;
    }
    const style = getComputedStyle(element);
    const back = background(element);
    const fore = parse(style.color);
    if (!fore) continue;
    const measured = ratio(over(fore, back), back);
    const size = parseFloat(style.fontSize);
    const large = size >= 24 || (size >= 18.66 && Number(style.fontWeight) >= 700);
    const needed = large ? 3 : 4.5;
    if (measured < needed) {
      contrast.push({
        selector: selector(element),
        text: element.textContent.trim().slice(0, 60),
        ratio: Math.round(measured * 100) / 100,
        needed,
        foreground: hex(over(fore, back)),
        background: hex(back),
        font_px: size,
      });
    }
  }

  // Text drawn through <use> lives in a shadow tree the loop above never reaches.
  for (const use of document.body.querySelectorAll("use")) {
    if (!visible(use)) continue;
    const ref = use.getAttribute("href") || use.getAttribute("xlink:href") || "";
    const target = ref.startsWith("#") ? document.getElementById(ref.slice(1)) : null;
    if (!target) continue;
    for (const text of target.querySelectorAll("text")) {
      const words = text.textContent.trim();
      if (words) unmeasured.push({ selector: selector(use), text: words.slice(0, 60), reason: "svg text" });
    }
  }


  // 1.4.11: a control's edge or fill, its focus ring, a selected item's fill and a colour bar's
  // ends each need 3:1 against the surface behind them. A control with neither edge nor fill is
  // identified by its text and is not measured; a native checkbox, radio or range draws itself.
  const NON_TEXT = 3;
  const nontext = [];
  const surface = (element) => background(element.parentElement || document.body);
  const nontextFinding = (element, kind, fore, back) => {
    const measured = ratio(fore, back);
    if (measured >= NON_TEXT) return;
    nontext.push({
      selector: selector(element),
      kind,
      ratio: Math.round(measured * 100) / 100,
      needed: NON_TEXT,
      foreground: hex(fore),
      background: hex(back),
    });
  };
  const edge = (style) => {
    const width = parseFloat(style.borderTopWidth);
    const colour = parse(style.borderTopColor);
    if (width > 0 && style.borderTopStyle !== "none" && colour && colour.a > 0) return colour;
    const outline = parse(style.outlineColor);
    if (parseFloat(style.outlineWidth) > 0 && style.outlineStyle !== "none" && outline) return outline;
    return null;
  };
  const sideEdge = (style) => {
    for (const side of ["Right", "Bottom", "Left"]) {
      const colour = parse(style[`border${side}Color`]);
      if (parseFloat(style[`border${side}Width`]) > 0 && style[`border${side}Style`] !== "none" && colour && colour.a > 0) return colour;
    }
    return null;
  };
  const SELECTED = "[aria-selected=true], [aria-pressed=true], [aria-current]:not([aria-current=false])";
  const edged = "input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=range]), select, textarea, button, [role=switch]";
  for (const element of document.body.querySelectorAll(edged)) {
    if (!visible(element)) continue;
    // A selected control's fill marks the selection: the pass below measures its marker.
    if (element.matches(SELECTED)) continue;
    const back = surface(element);
    const style = getComputedStyle(element);
    const line = edge(style);
    const fill = parse(style.backgroundColor);
    const filled = fill && fill.a > 0;
    if (line) nontextFinding(element, "edge", over(line, back), back);
    else if (filled) nontextFinding(element, "fill", over(fill, back), back);
  }
  // A selected item (aria-selected, aria-pressed or aria-current) is told apart by a marker: its
  // edge or its fill, whichever reaches 3:1 against the surface behind it. A selected item with
  // neither drawn is told apart by weight or text alone, which 1.4.11 does not accept.
  for (const element of document.body.querySelectorAll(SELECTED)) {
    if (!visible(element)) continue;
    const back = surface(element);
    const style = getComputedStyle(element);
    // A marker may be one edge only: a bar along any side counts.
    const line = edge(style) || sideEdge(style);
    const fill = parse(style.backgroundColor);
    const markers = [];
    if (line) markers.push(["selected edge", over(line, back)]);
    if (fill && fill.a > 0) markers.push(["selected fill", over(fill, back)]);
    if (markers.length === 0) {
      nontext.push({ selector: selector(element), kind: "selected, no marker", ratio: 1, needed: NON_TEXT, foreground: hex(back), background: hex(back) });
      continue;
    }
    const [kind, colour] = markers.reduce((best, next) => (ratio(next[1], back) > ratio(best[1], back) ? next : best));
    nontextFinding(element, kind, colour, back);
  }
  for (const element of document.body.querySelectorAll("[data-colorbar]")) {
    if (!visible(element)) continue;
    const stops = (getComputedStyle(element).backgroundImage.match(/rgba?\([^)]+\)/g) || []).map(parse);
    if (stops.length < 2) continue;
    const back = surface(element);
    for (const [name, stop] of [["colour bar start", stops[0]], ["colour bar end", stops[stops.length - 1]]]) {
      nontextFinding(element, name, over(stop, back), back);
    }
  }
  // The focus ring, after the pass above: focusing changes the page, so it is last, and undone.
  // An element out of the tab order (tabindex -1, a menu's own box) takes focus only from a script;
  // its shadow is elevation, not a ring.
  for (const element of document.body.querySelectorAll(edged + ", a[href], [tabindex]:not([tabindex='-1'])")) {
    if (!visible(element) || element.disabled) continue;
    element.focus({ preventScroll: true });
    if (document.activeElement !== element) continue;
    const style = getComputedStyle(element);
    const back = surface(element);
    let ring = null;
    if (style.outlineStyle !== "none" && parseFloat(style.outlineWidth) > 0) ring = parse(style.outlineColor);
    else if (style.boxShadow !== "none") ring = parse(style.boxShadow);
    if (ring && ring.a > 0) nontextFinding(element, "focus ring", over(ring, back), back);
    element.blur();
  }

  const targets = [];
  const controls = "a, button, input:not([type=hidden]), select, textarea, [role=button]";
  for (const element of document.body.querySelectorAll(controls)) {
    if (!visible(element)) continue;
    // A visually hidden element (a skip link before it takes focus) is no pointer target.
    if (getComputedStyle(element).clipPath === "inset(50%)") continue;
    let rect = element.getBoundingClientRect();
    // A checkbox or radio is hit through its label too, so the larger of the two is its target.
    if (element.type === "checkbox" || element.type === "radio") {
      for (const label of element.labels || []) {
        const box = label.getBoundingClientRect();
        if (box.width * box.height > rect.width * rect.height) rect = box;
      }
    }
    if (rect.width < 24 || rect.height < 24) {
      const inline =
        element.tagName === "A" && getComputedStyle(element).display === "inline";
      targets.push({
        selector: selector(element),
        text: (element.textContent || element.value || "").trim().slice(0, 40),
        width: Math.round(rect.width * 10) / 10,
        height: Math.round(rect.height * 10) / 10,
        // A link inside a sentence is excepted by 2.5.8; the reviewer decides.
        inline,
      });
    }
  }
  return { contrast, nontext, targets, unmeasured };
}

// The shell's host document reports whether its scene initialised (gui/render.py, READY_FLAG): a
// renderer that never arrived or a WebGL context that failed is caught there, not a page error.
function viewerState() {
  const flag = window.__nanopnp_viewer;
  if (typeof flag !== "object" || flag === null) return null;
  return { ready: Boolean(flag.ready), error: String(flag.error || "") };
}

// Sleep `floor` ms, as every shot did, then wait on for a page that is still changing, at most
// SETTLE_EXTRA_MS: an animation or transition runs, the fonts are loading, or the DOM changed less
// than QUIET_MS ago. A server answering late, as with several pages open at once, would otherwise
// be shot half drawn, a menu mid-fade. A page already still returns after two frames.
async function settle(page, floor, entry) {
  await page.waitForTimeout(floor);
  if (!entry.ready) return;
  await page.evaluate(
    ([limit, quiet]) =>
      new Promise((resolve) => {
        const begin = performance.now();
        let changed = begin - quiet;
        const watch = new MutationObserver(() => {
          changed = performance.now();
        });
        watch.observe(document.documentElement, {
          subtree: true,
          childList: true,
          attributes: true,
          characterData: true,
        });
        const tick = () => {
          const now = performance.now();
          const moving = document
            .getAnimations()
            .some((a) => a.playState === "running" || a.playState === "pending");
          if ((now - changed >= quiet && !moving && document.fonts.status === "loaded") || now - begin >= limit) {
            watch.disconnect();
            resolve();
          } else requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      }),
    [SETTLE_EXTRA_MS, QUIET_MS],
  );
}

// One worker's browser context and its page, kept from shot to shot: a page that is navigated again
// keeps the scripts Chromium has compiled (the workbench loads Mol*, Quasar and Tailwind), where a
// fresh context compiles them anew, about a second a shot. Each shot sets the viewport and colour
// scheme it names, and starts with the storage of the previous page cleared and no error recorded.
class Seat {
  constructor(browser) {
    this.browser = browser;
    this.context = null;
    this.page = null;
    this.consoleErrors = [];
    this.pageErrors = [];
  }

  async open(entry) {
    const [width, height] = entry.viewport || [1280, 800];
    const colorScheme = entry.scheme === "dark" ? "dark" : "light";
    if (this.page === null) {
      this.context = await this.browser.newContext({ viewport: { width, height }, colorScheme });
      this.page = await this.context.newPage();
      this.page.on("console", (message) => {
        if (message.type() === "error") this.consoleErrors.push(message.text());
      });
      this.page.on("pageerror", (error) => this.pageErrors.push(String(error)));
    } else {
      await this.page
        .evaluate(() => {
          try {
            localStorage.clear();
            sessionStorage.clear();
          } catch (error) {
            // about:blank and a file page have none to clear.
          }
        })
        .catch(() => {});
      await this.page.setViewportSize({ width, height });
      await this.page.emulateMedia({ colorScheme });
    }
    this.consoleErrors.length = 0;
    this.pageErrors.length = 0;
    return this;
  }

  // After a page that did not load or a shot that failed, the next shot starts afresh.
  async discard() {
    const context = this.context;
    this.context = null;
    this.page = null;
    if (context) await context.close().catch(() => {});
  }
}

async function shootOne(seat, entry, out) {
  const [width, height] = entry.viewport || [1280, 800];
  const { context, page, consoleErrors, pageErrors } = await seat.open(entry);

  const records = [];
  let loaded = true;
  try {
    // A request in the context's cookie jar takes the launch token's cookie as a page load would,
    // without drawing the page.
    for (const address of entry.via || []) await context.request.get(address, { timeout: 60000 });
    await page.goto(entry.url, { waitUntil: "load", timeout: 60000 });
    if (entry.ready) await page.waitForSelector(entry.ready, { timeout: 90000 });
    // After the ready wait: a click on a page whose socket has not connected is lost.
    for (const selector of entry.click || []) {
      await page.waitForSelector(selector, { state: "visible", timeout: 30000 });
      await page.click(selector, { timeout: 30000 });
      await settle(page, CLICK_SETTLE_MS, entry);
    }
  } catch (error) {
    loaded = false;
    pageErrors.push(`load failed: ${error.message}`);
  }
  // Each shot carries the errors raised since the previous shot, the first one those of the load.
  let seenConsole = 0;
  let seenPage = 0;
  const record = (id, url) => {
    const shot = {
      id,
      file: `${id}.png`,
      url,
      viewport: [width, height],
      scheme: entry.scheme || "light",
      console: consoleErrors.slice(seenConsole),
      page_errors: pageErrors.slice(seenPage),
      viewer: null,
      contrast: [],
      nontext: [],
      targets: [],
      unmeasured: [],
    };
    seenConsole = consoleErrors.length;
    seenPage = pageErrors.length;
    return shot;
  };

  if (!loaded) {
    records.push({ ...record(entry.id, entry.url), file: null });
    await seat.discard();
    return { records, loaded };
  }
  await settle(page, entry.wait_ms || 0, entry);

  const screens = entry.expand
    ? await page.$$eval(entry.expand, (elements) =>
        elements.map((e) => e.getAttribute("data-screen")).filter(Boolean),
      )
    : [null];
  for (const screen of screens) {
    const id = screen ? `${entry.id}-${screen}` : entry.id;
    if (screen) {
      await page.evaluate((hash) => {
        location.hash = hash;
      }, screen);
      await page.waitForTimeout(SCREEN_SETTLE_MS);
    }
    await page.screenshot({ path: path.join(out, `${id}.png`) });
    const checks = await page.evaluate(checkPage);
    const viewer = await page.evaluate(viewerState);
    const url = screen ? `${entry.url.split("#")[0]}#${screen}` : entry.url;
    records.push({ ...record(id, url), viewer, ...checks });
  }
  return { records, loaded };
}

// The server an entry's shots share: the first address it loads, else its own page.
function serverOf(entry) {
  const address = (entry.via || [])[0] || entry.url;
  return /^https?:/.test(address) ? new URL(address).origin : address;
}

async function shootSafely(seat, entry, out) {
  try {
    return await shootOne(seat, entry, out);
  } catch (error) {
    await seat.discard();
    // One page that cannot be shot is recorded as failed; the other pages keep their records.
    const records = [
      {
        id: entry.id,
        file: null,
        url: entry.url,
        viewport: entry.viewport || [1280, 800],
        scheme: entry.scheme || "light",
        console: [],
        page_errors: [`shoot failed: ${error.message}`],
        viewer: null,
        contrast: [],
        nontext: [],
        targets: [],
        unmeasured: [],
      },
    ];
    return { records, loaded: false };
  }
}

// The log line of each shot, written as its entry finishes: the order is the shooting's.
function report(records) {
  for (const r of records) {
    const problems =
      r.page_errors.length +
      r.console.length +
      r.contrast.length +
      r.nontext.length +
      r.targets.length +
      (r.viewer && !r.viewer.ready ? 1 : 0);
    console.log(`${r.id}: ${r.file || "not loaded"}${problems ? `, ${problems} findings` : ""}`);
  }
}

async function shoot(manifest, out) {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: ["--enable-unsafe-swiftshader"] });
  const results = new Array(manifest.length);
  const chains = new Map();
  manifest.forEach((entry, position) => {
    const key = serverOf(entry);
    if (!chains.has(key)) chains.set(key, []);
    chains.get(key).push(position);
  });
  const queue = [...chains.values()];
  const jobs = Math.max(1, Number(process.env.NANOPNP_SHOOT_JOBS) || DEFAULT_JOBS);
  const work = async () => {
    const seat = new Seat(browser);
    for (let chain = queue.shift(); chain; chain = queue.shift()) {
      for (const position of chain) {
        results[position] = await shootSafely(seat, manifest[position], out);
        report(results[position].records);
      }
    }
    await seat.discard();
  };
  try {
    await Promise.all(Array.from({ length: Math.min(jobs, queue.length) }, work));
  } finally {
    await browser.close();
  }
  const index = [];
  let failed = false;
  for (const { records, loaded } of results) {
    index.push(...records);
    failed = failed || !loaded;
  }
  fs.writeFileSync(path.join(out, "index.json"), JSON.stringify(index, null, 2) + "\n");
  return failed ? 2 : 0;
}

// A unit-square P1 scene through the shell's own host_document, as the field viewer writes it.
const SELF_CHECK_PAGE = `
import sys
from pathlib import Path
from netgen.geom2d import unit_square
from ngsolve import Mesh, H1, GridFunction, x, y
from ngsolve.webgui import Draw
from nanopnp.gui.render import RENDERER_SOURCE, host_document
import json
mesh = Mesh(unit_square.GenerateMesh(maxh=0.1))
gf = GridFunction(H1(mesh, order=1))
gf.Set(x * y)
scene = Draw(gf, mesh, show=False).GetData()
Path(sys.argv[1]).write_text(host_document(json.dumps(scene), renderer=RENDERER_SOURCE, title="unit square"), encoding="utf-8")
`;

async function selfCheck(out) {
  fs.mkdirSync(out, { recursive: true });
  const page = path.resolve(out, "unit-square.html");
  execFileSync("uv", ["run", "python", "-c", SELF_CHECK_PAGE, page], { stdio: "inherit" });
  const status = await shoot(
    [{ id: "unit-square", url: pathToFileURL(page).href, viewport: [800, 600], wait_ms: 1500 }],
    out,
  );
  const [record] = JSON.parse(fs.readFileSync(path.join(out, "index.json"), "utf8"));
  const drew = record.viewer !== null && record.viewer.ready;
  const ready = record.page_errors.length === 0 && status === 0 && drew;
  const reasons = [
    ...record.page_errors,
    ...(drew ? [] : [`the scene did not draw: ${record.viewer ? record.viewer.error : "no flag"}`]),
  ];
  console.log(ready ? "self-check passed" : `self-check failed: ${reasons.join("; ")}`);
  return ready ? 0 : 1;
}

async function main(argv) {
  if (argv[0] === "--self-check" && argv.length === 2) return selfCheck(argv[1]);
  if (argv.length !== 2) {
    console.error("usage: shoot.cjs <manifest.json> <out-dir> | --self-check <out-dir>");
    return 64;
  }
  const manifest = JSON.parse(fs.readFileSync(argv[0], "utf8"));
  return shoot(manifest, argv[1]);
}

main(process.argv.slice(2)).then(
  (code) => process.exit(code),
  (error) => {
    console.error(error);
    process.exit(1);
  },
);
