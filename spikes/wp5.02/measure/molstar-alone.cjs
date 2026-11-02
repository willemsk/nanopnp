// molstar-alone.cjs <url>: the Mol* selection repaint with neither front end in the loop (the floor of measure 2).
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1100, height: 960 } });
  await p.goto(process.argv[2]);
  await p.waitForSelector('body[data-screen-ready="1"]');
  await p.waitForTimeout(1500);
  const times = [];
  for (const k of ['45', '46', '49', '51', '53']) {
    times.push(Math.round(await p.evaluate((k) => new Promise((r) => { const t = performance.now(); document.body.dataset.drawn0 = ''; (window.nano.structure(), 0); const L = nano.lib; const s = nano.structure(); const q = L.Queries.generators.atoms({ residueTest: c => String(L.StructureProperties.residue.auth_seq_id(c.element)) === k }); const loci = L.StructureSelection.toLociWithSourceUnits(q(new L.QueryContext(s))); nano.viewer.plugin.managers.structure.selection.fromLoci('set', loci); requestAnimationFrame(() => requestAnimationFrame(() => r(performance.now() - t))); }), k)));
    await p.waitForTimeout(1500);
  }
  console.log('Mol* selection alone, ms to two frames:', times.join(' '));
  await b.close();
})();
