// redraw.cjs <url> [--shell]: click-to-redraw, 20 picks each way after one warm-up (D3 measure 2).
const { chromium } = require('playwright');
const url = process.argv[2];
const quantile = (xs, q) => { const s = [...xs].sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.ceil(q * s.length) - 1)]; };
const summary = (xs) => ({ n: xs.length, median: +quantile(xs, 0.5).toFixed(1), p95: +quantile(xs, 0.95).toFixed(1), max: +Math.max(...xs).toFixed(1) });
(async () => {
  const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1100, height: 960 } });
  await page.goto(url);
  await page.waitForSelector('body[data-screen-ready="1"]', { timeout: 90000 });
  await page.waitForTimeout(1500);
  // t0: the click event's own timestamp. dom: first change under the map. drawn: data-drawn after two frames.
  await page.evaluate(() => {
    window.__t = { t0: 0, dom: 0, drawn: 0 };
    document.addEventListener('click', (e) => { window.__t = { t0: e.timeStamp, dom: 0, drawn: 0 }; }, true);
    new MutationObserver(() => { if (window.__t.t0 && !window.__t.dom) window.__t.dom = performance.now(); })
      .observe(document.querySelector('[data-control=map]'), { subtree: true, childList: true, attributes: true });
    new MutationObserver(() => { if (window.__t.t0 && !window.__t.drawn) window.__t.drawn = performance.now(); })
      .observe(document.body, { attributes: true, attributeFilter: ['data-drawn'] });
  });
  const keys = await page.$$eval('[data-control=strip-item]', (els) => els.map((e) => e.dataset.residue));
  const extent = await (await page.request.get(new URL('/api/map/extent', url).href)).json();
  const pixel = async (key) => {
    const body = await (await page.request.get(new URL(`/api/residue/${key}`, url).href)).json();
    const [r, z] = body.markers[0];
    return { x: (r - extent.r_low) / (extent.r_high - extent.r_low), y: (extent.z_high - z) / (extent.z_high - extent.z_low) };
  };
  const settle = () => page.waitForTimeout(1500);
  const read = () => page.evaluate(() => window.__t);
  const stripPick = async (key) => {
    await page.click(`[data-residue="${key}"]`);
    await page.waitForFunction(() => window.__t.drawn > 0, null, { timeout: 15000 });
    const t = await read(); await settle(); return t;
  };
  const mapPick = async (key) => {
    const box = await (await page.$('[data-control=map]')).boundingBox();
    const p = await pixel(key);
    await page.mouse.click(box.x + p.x * box.width, box.y + p.y * box.height);
    await page.waitForFunction(() => window.__t.drawn > 0, null, { timeout: 15000 });
    const t = await read(); await settle(); return t;
  };
  await stripPick(keys[3]); await mapPick(keys[7]);
  const pool = keys.filter((_, i) => i % 3 === 0).slice(0, 20);
  const strip = [], map = [];
  for (const key of pool) strip.push(await stripPick(key));
  for (const key of pool.slice().reverse()) map.push(await mapPick(key));
  const ms = (rows, field) => rows.map((t) => t[field] - t.t0);
  const out = {
    url, drawn: { strip: summary(ms(strip, 'drawn')), map: summary(ms(map, 'drawn')) },
    dom: { strip: summary(ms(strip, 'dom')), map: summary(ms(map, 'dom')) },
  };
  console.log(JSON.stringify(out));
  await browser.close();
})();
