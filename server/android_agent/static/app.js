import { screenPoint } from './geometry.js';
import { messages } from './i18n.js';

const $ = id => document.getElementById(id);
let language = 'zh', token = '', csrf = '', status = null, frameId = null, blobUrl = '';
try { language = localStorage.getItem('language') || 'zh'; token = sessionStorage.getItem('access-token') || ''; } catch { /* storage optional */ }
if (!messages[language]) language = 'zh';
const t = key => messages[language][key] || key;
function message(text, success = false) { $('message').hidden = !text; $('message').textContent = text; $('message').classList.toggle('success', success); }
function translate() {
  document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  for (const role of ['actor', 'planner']) {
    const el = $(`${role}-key-status`);
    if (el.dataset.keySet !== undefined) el.textContent = t(el.dataset.keySet === 'true' ? 'keySaved' : 'keyMissing');
  }
  if ($('device-select').options.length) $('device-select').options[0].text = t('chooseDevice');
  $('language').textContent = language === 'zh' ? 'English' : '中文';
}
function headers(extra = {}) { return { 'X-Agent-Token': token, 'X-Agent-CSRF': csrf, ...extra }; }
async function api(path, body) {
  const response = await fetch(path, { headers: headers(body === undefined ? {} : { 'Content-Type': 'application/json' }), method: body === undefined ? 'GET' : 'POST', body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) $('access-section').hidden = false;
    const detail = Array.isArray(data.detail) ? data.detail.map(e => e.msg).join('\n') : data.detail;
    throw new Error(detail || response.statusText);
  }
  return data;
}
async function guarded(work) { try { return await work(); } catch (error) { message(error.message); return null; } }
async function refreshDevices() {
  const data = await api('/api/devices');
  $('device-select').replaceChildren(new Option(t('chooseDevice'), ''), ...data.devices.map(device => {
    const option = new Option(`${device.model || device.serial} (${device.state}, ${device.transport})`, device.serial);
    option.disabled = device.state !== 'device';
    return option;
  }));
  if (status?.serial) $('device-select').value = status.serial;
  $('device-diagnostic').textContent = data.devices.length ? '' : t('noDevices');
}
async function loadSettings() {
  const prefs = await api('/api/settings');
  for (const role of ['actor', 'planner']) {
    $(`${role}-base`).value = prefs[role].base_url;
    $(`${role}-model`).value = prefs[role].model;
    $(`${role}-key-status`).textContent = t(prefs[role].api_key_set ? 'keySaved' : 'keyMissing');
    $(`${role}-key-status`).dataset.keySet = String(prefs[role].api_key_set);
  }
  $('max-steps').value = prefs.max_steps; $('max-seconds').value = prefs.max_seconds;
  $('max-tokens').value = prefs.max_total_tokens; $('save-screenshots').checked = prefs.save_screenshots;
}
async function saveSettings() {
  const body = { max_steps: Number($('max-steps').value), max_seconds: Number($('max-seconds').value), max_total_tokens: Number($('max-tokens').value), save_screenshots: $('save-screenshots').checked };
  for (const role of ['actor', 'planner']) {
    body[role] = { base_url: $(`${role}-base`).value, model: $(`${role}-model`).value, clear_api_key: $(`${role}-clear-key`).checked };
    if ($(`${role}-key`).value) body[role].api_key = $(`${role}-key`).value;
  }
  await api('/api/settings', body);
  for (const role of ['actor', 'planner']) { $(`${role}-key`).value = ''; $(`${role}-clear-key`).checked = false; }
  await loadSettings(); message(t('saved'), true);
}
function hideFrame(detail) {
  frameId = null; $('live').removeAttribute('src'); $('screen-hint').hidden = false;
  if (detail) $('screen-hint').querySelector('p').textContent = detail;
  if (blobUrl) { URL.revokeObjectURL(blobUrl); blobUrl = ''; }
}
async function refreshFrame() {
  if (status?.serial && csrf && !document.hidden) {
    try {
      const response = await fetch('/api/frame.png', { headers: headers(), cache: 'no-store' });
      if (!response.ok) { const data = await response.json(); throw new Error(data.detail || 'Screen unavailable'); }
      const next = URL.createObjectURL(await response.blob());
      const old = blobUrl;
      await new Promise((resolve, reject) => {
        $('live').onload = resolve; $('live').onerror = reject; $('live').src = next;
      });
      blobUrl = next; if (old) URL.revokeObjectURL(old);
      frameId = Number(response.headers.get('X-Frame-Id')); $('screen-hint').hidden = true;
    } catch (error) { hideFrame(error.message); }
  }
  setTimeout(refreshFrame, 1000);
}
async function poll() {
  try {
    if (csrf) {
      status = await api('/api/status');
      $('connection-state').textContent = t('connected');
      $('mode-label').textContent = status.serial ? `${status.mode.toUpperCase()} · ${status.serial}` : t('noSelection');
      $('task-state').textContent = status.agent.state === 'idle' ? t('idle') : status.agent.state;
    }
  } catch (error) { $('connection-state').textContent = error.message; }
  setTimeout(poll, 1000);
}
async function initialize() {
  const session = await api('/api/session'); csrf = session.csrf;
  $('version').textContent = `v${session.version}`; $('access-section').hidden = true;
  status = await api('/api/status'); await loadSettings();
  await guarded(refreshDevices);
}
async function sendAction(action) {
  if (frameId) action.frame_id = frameId;
  return await api('/api/action', action);
}
const live = $('live');
const point = e => screenPoint(e.clientX, e.clientY, live.getBoundingClientRect(), live.naturalWidth, live.naturalHeight);
let down = null;
live.addEventListener('pointerdown', event => {
  if (!frameId || event.button !== 0) return;
  const position = point(event); if (!position) return;
  down = { ...position, time: performance.now(), frameId };
  live.setPointerCapture(event.pointerId); event.preventDefault();
});
live.addEventListener('pointerup', event => {
  if (!down) return;
  const from = down, to = point(event); down = null;
  if (live.hasPointerCapture(event.pointerId)) live.releasePointerCapture(event.pointerId);
  if (!to) return;
  const duration = Math.round(performance.now() - from.time), distance = Math.hypot(to.x - from.x, to.y - from.y);
  const action = distance > 20 ? { action:'swipe', x1:from.x, y1:from.y, x2:to.x, y2:to.y, duration_ms:Math.min(5000, Math.max(100, duration)) }
    : duration >= 600 ? { action:'long_press', x:from.x, y:from.y, duration_ms:Math.min(5000,duration) } : { action:'tap', x:from.x, y:from.y };
  action.frame_id = from.frameId;
  guarded(() => api('/api/action', action));
});
live.addEventListener('pointercancel', () => { down = null; });
live.addEventListener('lostpointercapture', () => { down = null; });
let wheelTime = 0;
live.addEventListener('wheel', event => {
  event.preventDefault();
  if (!frameId || performance.now() - wheelTime < 350) return;
  const position = point(event); if (!position) return;
  wheelTime = performance.now(); guarded(() => sendAction({ action:'scroll', ...position, lines:event.deltaY > 0 ? -3 : 3 }));
}, { passive:false });
document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => guarded(() => sendAction({ action:button.dataset.action }))));
$('refresh-devices').addEventListener('click', () => guarded(refreshDevices));
$('select-device').addEventListener('click', () => guarded(async () => {
  await api('/api/devices/select', { serial:$('device-select').value }); status = await api('/api/status'); hideFrame(); message(t('selected'),true);
}));
$('pair-form').addEventListener('submit', event => { event.preventDefault(); guarded(async () => {
  await api('/api/adb/pair', { address:$('pair-address').value.trim(), code:$('pair-code').value }); $('pair-code').value = ''; message(t('paired'),true);
}); });
$('connect-form').addEventListener('submit', event => { event.preventDefault(); guarded(async () => { await api('/api/adb/connect', { address:$('connect-address').value.trim() }); await refreshDevices(); }); });
$('discover').addEventListener('click', () => guarded(async () => {
  const data = await api('/api/adb/discover');
  $('discovered-services').replaceChildren(...data.services.map(service => {
    const li = document.createElement('li'), button = document.createElement('button');
    const pairing = service.kind.includes('pairing');
    button.textContent = `${pairing ? t('pairAddress') : t('connectAddress')}: ${service.address}`;
    button.addEventListener('click', () => { $(pairing ? 'pair-address' : 'connect-address').value = service.address; });
    li.append(button); return li;
  })); if (!data.services.length) message(t('noServices'));
}));
$('text-form').addEventListener('submit', event => { event.preventDefault(); guarded(async () => { await sendAction({ action:'type', text:$('input-text').value }); $('input-text').value = ''; }); });
$('key-form').addEventListener('submit', event => { event.preventDefault(); guarded(() => sendAction({ action:'key', key:$('input-key').value })); });
$('settings-form').addEventListener('submit', event => { event.preventDefault(); guarded(saveSettings); });
async function stop() { const result = await api('/api/stop', {}); message(t('stopped') + result.release, true); }
$('emergency-stop').addEventListener('click', () => guarded(stop));
document.addEventListener('keydown', event => { if (event.key === 'Escape') guarded(stop); });
$('language').addEventListener('click', () => { language = language === 'zh' ? 'en' : 'zh'; try { localStorage.setItem('language',language); } catch { /* optional */ } translate(); });
$('access-login').addEventListener('click', () => guarded(async () => { token = $('access-token').value; try { sessionStorage.setItem('access-token',token); } catch { /* optional */ } await initialize(); }));
translate(); guarded(initialize); poll(); refreshFrame();
