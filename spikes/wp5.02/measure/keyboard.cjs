// keyboard.cjs <url>: the strip is reachable and operable by keyboard alone (QR-16).
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1100, height: 960 } });
  await p.goto(process.argv[2]);
  await p.waitForSelector('body[data-screen-ready="1"]', { timeout: 90000 });
  await p.waitForTimeout(1500);
  const d0 = await p.evaluate(() => Number(document.body.dataset.drawn || 0));
  await p.focus('[data-residue="8"]');
  await p.keyboard.press('Tab'); await p.keyboard.press('Tab');
  const focused = await p.evaluate(() => document.activeElement.dataset.residue);
  await p.keyboard.press('Enter');
  const ok = await p.waitForFunction((n) => Number(document.body.dataset.drawn || 0) > n, d0, { timeout: 15000 }).then(() => true, () => false);
  console.log(JSON.stringify({ focused, enter_selects: ok, status: await p.evaluate(() => (document.body.innerText.match(/Residue \S+/) || [''])[0]) }));
  await b.close();
})();
