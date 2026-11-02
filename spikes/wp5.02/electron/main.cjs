// A minimal desktop wrapper: spawn the server, read its ready line, load the address (AF1).
const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

app.commandLine.appendSwitch('no-sandbox');
app.commandLine.appendSwitch('enable-unsafe-swiftshader');
app.commandLine.appendSwitch('use-angle', 'swiftshader');

const spike = path.resolve(__dirname, '..');
const module_ = process.env.SPIKE_CANDIDATE === 'nicegui' ? ['--with', 'nicegui', 'python', '-m', 'ngui.main'] : ['python', '-m', 'react.main'];
const child = spawn('uv', ['run', '--project', path.resolve(spike, '../..'), '--with', 'fastapi', '--with', 'uvicorn', ...module_, '--port', '0'], { cwd: spike, stdio: ['pipe', 'pipe', 'inherit'] });
let buffer = '';
child.stdout.on('data', async (chunk) => {
  buffer += chunk;
  const match = buffer.match(/nanopnp-gui ready (\S+)/);
  if (match && !app.__loaded) {
    app.__loaded = true;
    await app.whenReady();
    const win = new BrowserWindow({ width: 1200, height: 960, webPreferences: { contextIsolation: true } });
    win.loadURL(match[1]);
  }
});
app.on('window-all-closed', () => app.quit());
app.on('will-quit', () => { child.stdin.end(); });
