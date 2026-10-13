import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createConsoleView } from '../android_agent/static/console.js';
import { messages } from '../android_agent/static/i18n.js';

function fixture(query = '') {
  const element = (dataset = {}) => ({
    dataset, hidden:false, textContent:'', attributes:{}, handlers:{},
    classList:{ toggle() {} }, focus() { this.focused = true; },
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    addEventListener(key, handler) { this.handlers[key] = handler; },
    closest() { return this.inNav; },
  });
  const ids = Object.fromEntries(['workspace-title','workspace-description','model-summary','task-empty'].map(id => [id, element()]));
  const panels = ['workspace','devices','settings'].map(panel => element({panel}));
  // A draft represents a mounted form node; switching must never replace it.
  panels[2].draft = {value:'unsaved-model'};
  const links = ['workspace','devices','settings','settings'].map(consoleView => element({consoleView}));
  links.slice(0,3).forEach(link => { link.inNav = true; });
  const shell = element(), urls = [];
  const document = {
    querySelectorAll(selector) { return selector === '[data-panel]' ? panels : links; },
    getElementById(id) { return ids[id]; }, querySelector() { return shell; },
  };
  let language = 'zh';
  const view = createConsoleView({document, translate:key => messages[language][key],
    location:{href:`http://localhost/?tokenless=1${query}`}, history:{replaceState(_state,_title,url) { urls.push(url); }}});
  return {view, panels, links, ids, shell, urls, language(value) { language = value; }};
}

test('navigation keeps mounted drafts, updates focus and exposes one panel', () => {
  const f = fixture(), draft = f.panels[2].draft;
  assert.equal(f.ids['workspace-title'].focused, undefined);
  f.links[2].handlers.click();
  assert.deepEqual(f.panels.map(p => p.hidden), [true,true,false]);
  assert.equal(f.links[2].attributes['aria-current'], 'page');
  assert.equal(f.links[0].attributes['aria-current'], undefined);
  assert.equal(f.ids['workspace-title'].focused, true);
  assert.equal(f.urls.at(-1).searchParams.get('view'), 'settings');
  assert.equal(f.urls.at(-1).searchParams.get('tokenless'), '1');
  f.view.select('workspace'); f.view.select('settings');
  assert.equal(f.panels[2].draft, draft);
  assert.equal(draft.value, 'unsaved-model');
  f.language('en'); f.view.translated();
  assert.equal(f.ids['workspace-title'].textContent, messages.en.modelSettings);
});

test('deep links and invalid views use a safe known panel', () => {
  assert.deepEqual(fixture('&view=devices').panels.map(p => p.hidden), [true,false,true]);
  for (const name of ['unknown','__proto__','constructor']) {
    const f = fixture(`&view=${name}`);
    assert.equal(f.shell.dataset.view, 'workspace');
    f.view.select(name);
    assert.equal(f.urls.at(-1).searchParams.has('view'), false);
  }
});

test('task empty state and model summary reflect service data including keyless models', () => {
  const f = fixture();
  for (const [agent, hidden] of [[{state:'idle',id:null},false],[{state:'planning',id:'id'},true],
    [{state:'completed',id:'id'},true],[{state:'failed'},true],[undefined,false]]) {
    f.view.status({agent}); assert.equal(f.ids['task-empty'].hidden, hidden);
  }
  f.view.settings({actor:{model:'local-vision',api_key_set:false}});
  assert.match(f.ids['model-summary'].textContent, /local-vision/);
  f.view.settings({actor:{model:'  '}});
  assert.equal(f.ids['model-summary'].textContent, messages.zh.configureModel);
});

test('HTML retains every module-bound ID and translates all declared presentation strings', () => {
  const html = readFileSync(new URL('../android_agent/static/index.html', import.meta.url), 'utf8');
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length, 'duplicate IDs break event binding');
  for (const file of ['app.js','tasks.js','firmware.js','usb.js','console.js']) {
    const source = readFileSync(new URL(`../android_agent/static/${file}`, import.meta.url), 'utf8');
    for (const match of source.matchAll(/(?:\$|getElementById)\('([^']+)'\)/g)) {
      assert.ok(ids.includes(match[1]), `${file}: missing ${match[1]}`);
    }
  }
  for (const match of html.matchAll(/data-i18n(?:-placeholder|-aria)?="([^"]+)"/g)) {
    for (const language of ['zh','en']) assert.ok(messages[language][match[1]], `${language}: ${match[1]}`);
  }
  assert.match(html, /<header[\s\S]*id="emergency-stop"[\s\S]*<\/header>/);
});
