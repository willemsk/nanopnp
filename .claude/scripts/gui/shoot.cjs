// Shoot pages headless with Playwright's Chromium, and check each shot's contrast and target sizes.
//
//   node .claude/scripts/gui/shoot.cjs <manifest.json> <out-dir>
//   node .claude/scripts/gui/shoot.cjs --self-check <out-dir>
//
// The manifest is a JSON list of {id, url, viewport: [w, h], scheme: "light"|"dark", wait_ms,
// expand}. With `expand`, a CSS selector, the page is shot once per matching element's
// `data-screen` value, after setting `location.hash` to it, as `<id>-<screen>`. Writes
// `<out>/<id>.png` and `<out>/index.json`. Exits 0, or 2 if a page failed to load.
//
// CommonJS: Playwright is installed globally and found through NODE_PATH, which serves
// `require` and not `import`.

"use strict";

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");

const SCREEN_SETTLE_MS = 150;

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

  const contrast = [];
  for (const element of document.body.querySelectorAll("*")) {
    if (["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(element.tagName)) continue;
    const own = [...element.childNodes].some(
      (n) => n.nodeType === 3 && n.textContent.trim().length > 0,
    );
    if (!own || !visible(element)) continue;
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

  const targets = [];
  const controls = "a, button, input:not([type=hidden]), select, textarea, [role=button]";
  for (const element of document.body.querySelectorAll(controls)) {
    if (!visible(element)) continue;
    const rect = element.getBoundingClientRect();
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
  return { contrast, targets };
}

async function shootOne(browser, entry, out) {
  const [width, height] = entry.viewport || [1280, 800];
  const context = await browser.newContext({
    viewport: { width, height },
    colorScheme: entry.scheme === "dark" ? "dark" : "light",
  });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(String(error)));

  const records = [];
  let loaded = true;
  try {
    await page.goto(entry.url, { waitUntil: "load", timeout: 60000 });
  } catch (error) {
    loaded = false;
    pageErrors.push(`load failed: ${error.message}`);
  }
  const record = (id, url) => ({
    id,
    file: `${id}.png`,
    url,
    viewport: [width, height],
    scheme: entry.scheme || "light",
    console: [...consoleErrors],
    page_errors: [...pageErrors],
    contrast: [],
    targets: [],
  });

  if (!loaded) {
    records.push({ ...record(entry.id, entry.url), file: null });
    await context.close();
    return { records, loaded };
  }
  await page.waitForTimeout(entry.wait_ms || 0);

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
    const url = screen ? `${entry.url.split("#")[0]}#${screen}` : entry.url;
    records.push({ ...record(id, url), ...checks });
  }
  await context.close();
  return { records, loaded };
}

async function shoot(manifest, out) {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: ["--enable-unsafe-swiftshader"] });
  const index = [];
  let failed = false;
  try {
    for (const entry of manifest) {
      const { records, loaded } = await shootOne(browser, entry, out);
      index.push(...records);
      failed = failed || !loaded;
      for (const r of records) {
        const problems =
          r.page_errors.length + r.console.length + r.contrast.length + r.targets.length;
        console.log(`${r.id}: ${r.file || "not loaded"}${problems ? `, ${problems} findings` : ""}`);
      }
    }
  } finally {
    await browser.close();
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
  const ready = record.page_errors.length === 0 && status === 0;
  console.log(ready ? "self-check passed" : `self-check failed: ${record.page_errors.join("; ")}`);
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
