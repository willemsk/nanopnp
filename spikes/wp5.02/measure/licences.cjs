// licences.cjs: runtime licences of the React candidate's front-end dependency closure (D3 measure 5).
const fs = require('fs'), path = require('path');
const root = path.resolve(__dirname, '../react/node_modules');
const seen = new Map();
function walk(name) {
  if (seen.has(name)) return;
  const dir = path.join(root, name);
  if (!fs.existsSync(path.join(dir, 'package.json'))) { seen.set(name, '(not installed: optional)'); return; }
  const pkg = JSON.parse(fs.readFileSync(path.join(dir, 'package.json')));
  seen.set(name, `${pkg.version} ${typeof pkg.license === 'string' ? pkg.license : JSON.stringify(pkg.license || pkg.licenses)}`);
  for (const dep of Object.keys(pkg.dependencies || {})) walk(dep);
}
for (const top of process.argv.slice(2)) walk(top);
for (const [k, v] of [...seen].sort()) console.log(k.padEnd(40), v);
