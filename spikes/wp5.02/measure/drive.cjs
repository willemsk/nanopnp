// drive.cjs <base-url> [out-dir]: every state by URL, no human step (D3 measure 3).
const { chromium } = require('playwright');
const fs = require('fs');
const base = process.argv[2];
const out = process.argv[3];
const STATES = [
  { name: 'study', query: '', controls: ['tabs', 'tab-study', 'tab-sketcher', 'molecule', 'strip', 'strip-item', 'link-chip', 'unlink', 'map'] },
  { name: 'study-residue', query: '?residue=45', controls: ['molecule', 'strip', 'map'], after: (p) => p.waitForFunction(() => Number(document.body.dataset.drawn || 0) > 0, null, { timeout: 15000 }) },
  { name: 'study-unlinked', query: '?linked=0', controls: ['link-chip', 'unlink'], text: 'Unlinked' },
  { name: 'sketcher', query: '?tab=sketcher', controls: ['tabs', 'banner', 'sketcher-canvas'] },
];
(async () => {
  const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] });
  const rows = [];
  for (const state of STATES) {
    const page = await browser.newPage({ viewport: { width: 1100, height: 960 } });
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
    const t0 = Date.now();
    await page.goto(base + state.query);
    let ready = true;
    await page.waitForSelector('body[data-screen-ready="1"]', { timeout: 90000 }).catch(() => { ready = false; });
    if (ready && state.after) await state.after(page).catch(() => { ready = false; });
    const found = [];
    for (const c of state.controls) if (await page.locator(`[data-control="${c}"]`).first().isVisible().catch(() => false)) found.push(c);
    const textOk = state.text ? (await page.locator('body').innerText()).includes(state.text) : true;
    rows.push({ state: state.name, ready, ms: Date.now() - t0, controls: `${found.length}/${state.controls.length}`, textOk, errors: errors.length });
    if (out) { fs.mkdirSync(out, { recursive: true }); await page.screenshot({ path: `${out}/${state.name}.png` }); }
    await page.close();
  }
  console.log(JSON.stringify(rows));
  await browser.close();
})();
