// electron.cjs <nicegui|react>: open the candidate in the Electron window; one pick each way (D3 measure 6).
const { _electron } = require('playwright');
const path = require('path');
const kind = process.argv[2];
(async () => {
  const app = await _electron.launch({
    executablePath: path.resolve(__dirname, '../electron/node_modules/electron/dist/electron'),
    args: [path.resolve(__dirname, '../electron/main.cjs'), '--no-sandbox'],
    env: { ...process.env, SPIKE_CANDIDATE: kind },
    timeout: 120000,
  });
  const win = await app.firstWindow({ timeout: 120000 });
  const errors = [];
  win.on('pageerror', (e) => errors.push(e.message));
  await win.waitForSelector('body[data-screen-ready="1"]', { timeout: 120000 });
  const drawn = () => win.evaluate(() => Number(document.body.dataset.drawn || 0));
  const result = { kind, ready: true };
  let d0 = await drawn();
  await win.click('[data-residue="45"]');
  result.strip = await win.waitForFunction((n) => Number(document.body.dataset.drawn || 0) > n, d0, { timeout: 20000 }).then(() => true, () => false);
  await win.waitForTimeout(1500);
  d0 = await drawn();
  const box = await (await win.$('[data-control=map]')).boundingBox();
  await win.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.4);
  result.map = await win.waitForFunction((n) => Number(document.body.dataset.drawn || 0) > n, d0, { timeout: 20000 }).then(() => true, () => false);
  result.link = await win.evaluate(() => (document.body.innerText.match(/Residue \S+/) || [''])[0]);
  result.errors = errors.length;
  await win.screenshot({ path: process.env.SHOT || `/tmp/electron-${kind}.png` });
  await app.close();
  console.log(JSON.stringify(result));
})().catch((e) => { console.log(JSON.stringify({ kind, failed: String(e).slice(0, 300) })); process.exit(1); });
