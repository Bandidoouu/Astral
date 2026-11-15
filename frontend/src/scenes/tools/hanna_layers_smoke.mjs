// Standalone local browser smoke check; uses installed Chrome and Node's built-in CDP socket.
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { createServer } from 'vite';

const directory = fileURLToPath(new URL('./.cache/hanna-layers/', import.meta.url));
await mkdir(directory, { recursive: true });
const root = fileURLToPath(new URL('../../../', import.meta.url));
const server = await createServer({ root, server: { host: '127.0.0.1', port: 5182, strictPort: true, watch: { ignored: ['**/src/scenes/tools/.cache/**'] } } });
await server.listen();
const browser = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--disable-extensions', '--no-first-run', '--no-default-browser-check',
  '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=9334',
  '--enable-unsafe-swiftshader',
  '--window-size=1440,1100', `--user-data-dir=${resolve(directory, 'node_modules/profile')}`, 'about:blank',
], { windowsHide: true, stdio: 'ignore' });
const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
let socket;
try {
  let tabs;
  for (let i = 0; i < 100; i++) {
    try { tabs = await (await fetch('http://127.0.0.1:9334/json')).json(); if (tabs.some(tab => tab.type === 'page')) break; } catch {}
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
      if (!request) return;
      clearTimeout(request.timer); requests.delete(message.id);
      message.error ? request.reject(new Error(JSON.stringify(message.error))) : request.resolve(message.result);
    }
    if (message.method === 'Network.requestWillBeSent' && /\.(jpg|gz)(\?|$)/.test(message.params.request.url)) resourceRequests.push(message.params.request.url);
    if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') errors.push(message.params.args.map(arg => arg.value ?? arg.description ?? '').join(' '));
    if (message.method === 'Fetch.requestPaused') send('Fetch.failRequest', { requestId: message.params.requestId, errorReason: 'BlockedByClient' }).catch(() => {});
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text + ': ' + message.params.exceptionDetails.exception?.description);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++next; const timer = setTimeout(() => { requests.delete(id); reject(new Error('CDP timeout: ' + method)); }, 25000); requests.set(id, { resolve, reject, timer }); socket.send(JSON.stringify({ id, method, params }));
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

  const waitFor = async (expression, message) => {
    for (let i = 0; i < 100; i++) { if (await evaluate(expression)) return; await delay(300); }
    throw new Error(message + ': ' + await evaluate("document.querySelector('.astral-terrain-controls')?.innerText"));
  };
  const reliefReady = "document.querySelector('.astral-layer-controls')?.textContent.includes('Earth: relief ready · Moon: relief ready · Mars: relief ready')";
  const normalReady = "document.querySelector('.astral-layer-controls')?.textContent.includes('earth: normal map ready · moon: normal map ready · mars: normal map ready')";
  const imagesReady = layer => layer === 'suitability'
    ? "document.querySelector('.astral-layer-controls')?.textContent.includes('Layer images: earth: color only · moon: ready · mars: ready')"
    : "document.querySelector('.astral-layer-controls')?.textContent.includes('Layer images: earth: ready · moon: ready · mars: ready')";
  const select = async (label, value) => {
    await evaluate(`(() => { const element = document.querySelector('select[aria-label="${label}"]'); Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set.call(element, ${JSON.stringify(value)}); element.dispatchEvent(new Event('change', {bubbles:true})); })()`);
    await delay(150);
  };
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Page.navigate', { url: 'http://127.0.0.1:5182/' });
  await waitFor(reliefReady, 'Packaged heights did not load');
  await waitFor(normalReady, 'Packaged normals did not load');
  await waitFor(imagesReady('color'), 'Visible colors did not load');
  await delay(800);
  await screenshot('01-visible-normals');
  console.log('All three packaged heights, colors and normal maps are ready.');
  await evaluate("Array.from(document.querySelectorAll('.astral-terrain-landmarks button')).find(button => button.textContent === 'Olympus Mons').click()");
  await delay(1700);
  for (const layer of ['height', 'shadows', 'topography', 'suitability']) {
    await select('Surface layer', layer);
    await waitFor(imagesReady(layer), layer + ' images did not load');
    await evaluate("document.querySelector('.astral-layer-reference').open = true");
    await delay(700);
    await screenshot('02-' + layer);
    console.log(layer + ': images loaded for every supported body.');
  }
  await select('Surface layer', 'color');
  await waitFor(imagesReady('color'), 'Color layer did not return');
  await waitFor(normalReady, 'Normal lighting did not return');
  await evaluate("document.querySelector('input[aria-label=\"Normal-map lighting\"]').click()");
  await waitFor("!document.querySelector('input[aria-label=\"Normal-map lighting\"]').checked", 'Mesh-normal toggle failed');
  await select('Height source', 'global');
  await waitFor(reliefReady, 'Global DEM option failed');
  await delay(400);
  await screenshot('03-global-dems');
  await select('Height source', 'packaged');
  await waitFor(reliefReady, 'Packaged DEM option failed');
  await evaluate("document.querySelector('input[aria-label=\"Normal-map lighting\"]').click()");
  await waitFor(normalReady, 'Normal lighting did not recover');
  const beforeReset = resourceRequests.length;
  await evaluate("document.querySelector('button[aria-label=\"Reset camera\"]').click()");
  await delay(700);
  if (resourceRequests.length !== beforeReset) throw new Error('Reset reloaded surface images');
  await evaluate("Array.from(document.querySelectorAll('button')).find(button => button.textContent.trim() === 'Terrain galaxy').click()");
  await delay(400);
  if (await evaluate("Boolean(document.querySelector('.astral-terrain-controls'))")) throw new Error('Surface controls leaked into galaxy');
  await evaluate("Array.from(document.querySelectorAll('button')).find(button => button.textContent.trim() === 'System').click()");
  await delay(500);
  await waitFor(normalReady, 'View change lost normals');
  console.log('Height sources, normal toggle, camera reset and view changes passed.');
  await send('Network.setCacheDisabled', { cacheDisabled: true });
  await send('Fetch.enable', { patterns: [{ urlPattern: '*normal_4k.jpg*', resourceType: 'Image', requestStage: 'Request' }] });
  await send('Page.reload', { ignoreCache: true });
  await waitFor(reliefReady, 'Missing normals disrupted relief');
  await waitFor("document.querySelector('.astral-layer-controls')?.textContent.includes('earth: normal map unavailable; mesh normals · moon: normal map unavailable; mesh normals · mars: normal map unavailable; mesh normals')", 'Missing normals did not fall back to mesh normals');
  await waitFor(imagesReady('color'), 'Missing normals disrupted colors');
  await screenshot('04-normal-fallback');
  await send('Fetch.disable');
  await send('Fetch.enable', { patterns: [{ urlPattern: '*textures/*/height*', resourceType: 'Fetch', requestStage: 'Request' }] });
  await send('Page.reload', { ignoreCache: true });
  await waitFor(reliefReady, 'Missing packaged heights did not use global fallback');
  await waitFor("document.querySelector('.astral-layer-controls')?.textContent.includes('earth: DEM fallback; mesh normals · moon: DEM fallback; mesh normals · mars: DEM fallback; mesh normals')", 'DEM fallback was not disclosed');
  await screenshot('05-height-fallback');
  await send('Fetch.disable');
  await send('Page.addScriptToEvaluateOnNewDocument', { source: "const get = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function(type,...args) { return type.startsWith('webgl') ? null : get.call(this,type,...args); };" });
  await send('Page.reload', { ignoreCache: true });
  await waitFor("Boolean(document.querySelector('.astral-scene-fallback')?.textContent.includes('WebGL is unavailable')) && document.querySelectorAll('button').length > 3", 'WebGL fallback did not preserve the interface');
  await screenshot('06-webgl-fallback');
  if (errors.length) throw new Error('Browser or shader errors: ' + errors.join('\n'));
  await writeFile(resolve(directory, 'results.json'), JSON.stringify({ errors, status: 'passed', layers: ['color','height','shadows','topography','suitability'] }, null, 2));
  console.log('All layer, lighting, height-source and fallback checks passed; no shader or browser errors.');
} finally {
  if (socket?.readyState === 1) {
    try { socket.send(JSON.stringify({ id: 99999, method: 'Browser.close' })); } catch {}
    await delay(300); socket.close();
  }
  browser.kill();
  await server.close();
}
