// Standalone local browser smoke check; uses installed Chrome and Node's built-in CDP socket.
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { createServer } from 'vite';

const directory = fileURLToPath(new URL('./.cache/browser/', import.meta.url));
await mkdir(directory, { recursive: true });
const root = fileURLToPath(new URL('../../../', import.meta.url));
const server = await createServer({ root, server: { host: '127.0.0.1', port: 5181, strictPort: true, watch: { ignored: ['**/src/scenes/tools/.cache/**'] } } });
await server.listen();
const browser = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--disable-extensions', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=9333',
  '--enable-unsafe-swiftshader', '--use-angle=swiftshader',
  '--window-size=1440,1100', `--user-data-dir=${resolve(directory, 'node_modules/profile')}`, 'about:blank',
], { windowsHide: true, stdio: 'ignore' });
const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
let socket;
try {
  let tabs;
  for (let i = 0; i < 100; i++) {
    try { tabs = await (await fetch('http://127.0.0.1:9333/json')).json(); if (tabs.some(tab => tab.type === 'page')) break; } catch {}
    await delay(200);
  }
  if (!tabs) throw new Error('Chrome debugger unavailable');
  socket = new WebSocket(tabs.find(tab => tab.type === 'page').webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let next = 0;
  const requests = new Map();
  const errors = [];
  const resourceRequests = [];
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const request = requests.get(message.id);
      requests.delete(message.id);
      message.error ? request.reject(new Error(JSON.stringify(message.error))) : request.resolve(message.result);
    }
    if (message.method === 'Network.requestWillBeSent' && /\.(jpg|gz)(\?|$)/.test(message.params.request.url)) resourceRequests.push(message.params.request.url);
    if (message.method === 'Fetch.requestPaused') send('Fetch.failRequest', { requestId: message.params.requestId, errorReason: 'BlockedByClient' }).catch(() => {});
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text + ': ' + message.params.exceptionDetails.exception?.description);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++next; requests.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async expression => {
    const response = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
    return response.result.value;
  };
  const screenshot = async name => {
    const result = await send('Page.captureScreenshot', { format: 'png' });
    await writeFile(resolve(directory, `${name}.png`), Buffer.from(result.data, 'base64'));
  };
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Page.navigate', { url: 'http://127.0.0.1:5181/' });
  let ready = false;
  for (let i = 0; i < 120; i++) {
    ready = await evaluate("document.querySelector('.astral-terrain-controls p')?.textContent.includes('Earth: relief ready · Moon: relief ready · Mars: relief ready')");
    if (ready) break;
    await delay(500);
  }
  if (!ready) throw new Error('Relief did not load: ' + await evaluate('document.body.innerText'));
  console.log('All three height resources loaded in browser.');
  await delay(1500);
  await screenshot('overview');
  if (!await evaluate("document.body.innerText.includes('PRECOMPUTED')")) throw new Error('Offline model results are not identified');
  await evaluate("document.querySelector('.match-chip').click()");
  await delay(1800);
  if (!await evaluate("Boolean(document.querySelector('[aria-label=\"Selected match details\"]'))")) throw new Error('Match inspection did not open details');
  await screenshot('inspected-match');
  await evaluate("document.querySelector('a.brand').click()");
  await delay(300);
  console.log('Precomputed model badge and match inspection/focus completed.');

  for (const [name, label] of [['earth', 'Himalaya'], ['moon', 'South Pole–Aitken'], ['mars', 'Olympus Mons']]) {
    await evaluate(`Array.from(document.querySelectorAll('.astral-terrain-landmarks button')).find(button => button.textContent === ${JSON.stringify(label)}).click()`);
    await delay(1800);
    // Zoom toward the selected body's camera target using the real wheel handler.
    const bounds = await evaluate("(() => { const r=document.querySelector('canvas').getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()");
    await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: bounds.x, y: bounds.y, deltaX: 0, deltaY: -800 });
    await delay(1200);
    await screenshot(name);
    console.log(`${label}: selection, focus and wheel zoom completed.`);
  }
  const setExaggeration = async value => {
    await evaluate(`(() => { const input = document.querySelector('input[aria-label="Vertical exaggeration"]'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, ${value}); input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); })()`);
    await delay(1500);
    const output = await evaluate("document.querySelector('.astral-terrain-controls output').textContent");
    if (!output.startsWith(`${value}×`)) throw new Error('Exaggeration control did not update: ' + output);
  };
  await setExaggeration(30);
  const center = await evaluate("(() => { const r=document.querySelector('canvas').getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()");
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: center.x, y: center.y, button: 'left', clickCount: 1 });
  for (let step = 1; step <= 8; step++) {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: center.x + step * 36, y: center.y + step * 3, button: 'left', buttons: 1 });
    await delay(60);
  }
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: center.x + 288, y: center.y + 24, button: 'left', clickCount: 1 });
  await delay(1000);
  await screenshot('mars-profile-30x');
  await setExaggeration(1);
  await screenshot('mars-profile-1x');
  const beforeReset = resourceRequests.length;
  await evaluate("document.querySelector('button[aria-label=\"Reset camera\"]').click()");
  await delay(1800);
  if (resourceRequests.length !== beforeReset) throw new Error('Reset reloaded globe resources');
  await screenshot('reset');
  await evaluate("Array.from(document.querySelectorAll('button')).find(button => button.textContent.trim() === 'Terrain galaxy').click()");
  await delay(1200);
  if (await evaluate("Boolean(document.querySelector('.astral-terrain-controls'))")) throw new Error('System controls leaked into galaxy');
  await screenshot('galaxy');
  await evaluate("Array.from(document.querySelectorAll('button')).find(button => button.textContent.trim() === 'System').click()");
  await delay(1500);
  console.log('Vertical exaggeration 30×/1×, orbit drag, camera reset and view changes completed.');
  const status = await evaluate("document.querySelector('.astral-terrain-controls p').textContent");
  await send('Network.enable');
  await send('Fetch.enable', { patterns: [{ urlPattern: '*height.gz*', resourceType: 'Fetch', requestStage: 'Request' }] });
  await send('Network.setCacheDisabled', { cacheDisabled: true });
  await send('Page.reload', { ignoreCache: true });
  let unavailable = false;
  for (let i = 0; i < 60; i++) {
    unavailable = await evaluate("(document.querySelector('.astral-terrain-controls p')?.textContent.match(/relief unavailable/g) ?? []).length === 3");
    if (unavailable) break;
    await delay(300);
  }
  if (!unavailable) throw new Error('Missing DEM did not preserve the color-only fallback');
  await screenshot('dem-fallback');
  await send('Fetch.disable');
  await send('Page.addScriptToEvaluateOnNewDocument', { source: "const originalGetContext = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function(type, ...args) { return type.startsWith('webgl') ? null : originalGetContext.call(this, type, ...args); };" });
  await send('Page.reload', { ignoreCache: true });
  let fallback = false;
  for (let i = 0; i < 60; i++) {
    fallback = await evaluate("Boolean(document.querySelector('.astral-scene-fallback')?.textContent.includes('WebGL is unavailable')) && document.querySelectorAll('button').length > 3");
    if (fallback) break;
    await delay(300);
  }
  if (!fallback) throw new Error('WebGL fallback did not leave the outer interface available');
  await screenshot('webgl-fallback');
  console.log('Missing DEM and unavailable WebGL fallbacks completed.');
  await writeFile(resolve(directory, 'results.json'), JSON.stringify({ status, errors }, null, 2));
  if (errors.length) throw new Error('Browser exceptions: ' + errors.join('\n'));
  console.log('No browser exceptions. Screenshots: ' + directory);
} finally {
  if (socket?.readyState === 1) socket.close();
  browser.kill();
  await server.close();
}
