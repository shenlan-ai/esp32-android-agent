// Browser acceptance against the explicit offline fixture only. No product dependency.
// Usage: node scripts/check_console_ui.mjs http://127.0.0.1:8906 [playwright-package-directory]
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { messages } from '../server/android_agent/static/i18n.js';

const target = new URL(process.argv[2] || 'http://127.0.0.1:8906');
assert.ok(['127.0.0.1','localhost'].includes(target.hostname), 'offline loopback fixture required');
const require = createRequire(import.meta.url);
const { chromium } = require(process.argv[3] ? resolve(process.argv[3], 'playwright') : 'playwright');
const browser = await chromium.launch({channel:'msedge', headless:true});
const out = resolve('.runtime-local/console-interaction');
await mkdir(out, {recursive:true});
const context = await browser.newContext({viewport:{width:1440,height:900}, reducedMotion:'reduce'});
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
const nav = view => page.locator(`nav [data-console-view="${view}"]`);
async function visible(selector) { await page.locator(selector).waitFor({state:'visible'}); }
async function ready() {
  await visible('.access a[href="/demo/reset"]');
  await page.waitForFunction(() => document.querySelector('#connection-state').dataset.service === 'connected');
  await page.waitForFunction(() => document.querySelector('#live').naturalWidth > 0);
}
async function state(value) {
  await page.waitForFunction(expected => document.querySelector('#task-state').textContent === expected, messages.zh[`state_${value}`], {timeout:20000});
}
try {
  await page.goto(target.href); await ready();
  assert.match(await page.locator('.access:visible').innerText(), /DEMO/);
  // All subsequent actions use the offline fixture, never a real board or model.
  await nav('settings').focus(); await page.keyboard.press('Enter');
  await page.locator('#actor-model').fill('unsaved-draft');
  await nav('workspace').click(); await nav('settings').click();
  assert.equal(await page.locator('#actor-model').inputValue(), 'unsaved-draft');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'workspace-title');
  await page.locator('#actor-model').fill('DEMO saved vision');
  await page.locator('#settings-form button.primary').click();
  await visible('#message.success');
  await page.reload(); await ready();
  assert.equal(await page.locator('#actor-model').inputValue(), 'DEMO saved vision');
  await page.locator('#actor-model').fill('draft-on-failure');
  await page.route('**/api/settings', route => route.request().method() === 'POST'
    ? route.fulfill({status:503,contentType:'application/json',body:'{"detail":"DEMO save unavailable"}'}) : route.continue());
  await page.locator('#settings-form button.primary').click(); await visible('#message:not(.success)');
  assert.match(await page.locator('#message').innerText(), /DEMO save unavailable/);
  assert.equal(await page.locator('#actor-model').inputValue(), 'draft-on-failure');
  assert.equal(new URL(page.url()).searchParams.get('view'), 'settings');
  await page.unroute('**/api/settings');
  await page.locator('#language').click();
  assert.equal(await page.locator('html').getAttribute('lang'), 'en');
  assert.match(await nav('devices').innerText(), /connection/i);
  await page.locator('#language').click();
  await nav('devices').click();
  for (const id of ['board-setup','firmware-setup','usb-setup']) await page.locator(`#${id}>summary`).click();
  for (const id of ['fw-identify','fw-confirm','configure-usb','use-ble','save-calibration']) {
    if (id === 'save-calibration') await page.locator('#device-panel details').filter({has:page.locator('#save-calibration')}).last().locator(':scope > summary').click();
    await visible(`#${id}`);
  }
  assert.equal(await page.locator('#fw-write').isDisabled(), true);
  // Task state and stop remain operational after view changes.
  await page.goto(new URL('/demo/fast', target).href); await ready();
  await page.locator('#goal').fill('打开 Wi-Fi 设置'); await page.locator('#run-task').click();
  await state('completed'); await page.waitForFunction(() => document.querySelector('#task-empty').hidden);
  assert.ok(await page.locator('#steps li').count() >= 1);
  await page.screenshot({path:resolve(out,'task-completed.png'),fullPage:true});
  await page.locator('#clear-task').click(); await state('idle'); await visible('#task-empty');
  await page.goto(new URL('/demo/slow', target).href); await ready();
  await page.locator('#goal').fill('打开 Wi-Fi 设置'); await page.locator('#run-task').click();
  await page.waitForFunction(() => !document.querySelector('#pause-task').disabled);
  await page.locator('#pause-task').click(); await state('paused');
  await page.locator('#resume-task').click();
  await page.waitForFunction(() => document.querySelector('#resume-task').disabled);
  await nav('settings').click(); await page.locator('#emergency-stop').click(); await state('stopped');
  await page.keyboard.press('Escape'); await visible('#message.success');
  await page.goto(new URL('/demo/fast', target).href); await ready();
  await page.locator('#clear-task').click(); await state('idle'); await visible('#task-empty');
  for (const viewport of [{width:1440,height:900},{width:1024,height:768},{width:390,height:844},{width:720,height:450}]) {
    await page.setViewportSize(viewport);
    for (const view of ['workspace','devices','settings']) {
      await nav(view).click();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
      assert.equal(overflow, false, `${viewport.width} ${view} overflows`);
      if (viewport.width === 390 && view === 'workspace') {
        const composer = await page.locator('.task-composer').boundingBox();
        const screen = await page.locator('.device-pane').boundingBox();
        assert.ok(composer.y < screen.y, 'narrow screen prioritizes task entry');
      }
      if (viewport.width === 390 && view === 'devices') {
        assert.ok((await page.locator('#device-select').boundingBox()).width > 290, 'device identity gets a full row');
      }
      await page.locator('footer').scrollIntoViewIfNeeded();
      const stop = await page.locator('#emergency-stop').boundingBox();
      assert.ok(stop.y >= 0 && stop.y + stop.height <= viewport.height, 'stop remains in viewport');
      await page.evaluate(() => scrollTo(0,0));
      await page.screenshot({path:resolve(out,`${view}-${viewport.width}.png`), fullPage:true});
    }
  }
  await page.setViewportSize({width:390,height:844});
  await nav('workspace').click();
  await page.route('**/api/frame.png', route => route.fulfill({status:503,contentType:'application/json',body:'{"detail":"DEMO screen unavailable"}'}));
  await visible('#screen-hint');
  assert.match(await page.locator('#screen-hint p').innerText(), /DEMO screen unavailable/);
  assert.equal(await page.locator('#screen-hint strong').innerText(), messages.zh.screenUnavailable);
  await page.screenshot({path:resolve(out,'screen-unavailable.png'),fullPage:true});
  await page.unroute('**/api/frame.png');
  await page.setViewportSize({width:1440,height:900});
  await nav('settings').click();
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, '200% CSS zoom overflow');
  assert.ok((await page.locator('#settings-panel').boundingBox()).width > 500, 'zoomed settings retain readable width');
  assert.ok((await page.locator('#settings-panel').boundingBox()).y < (await page.locator('.device-pane').boundingBox()).y, 'zoomed settings precede preview');
  await page.screenshot({path:resolve(out,'settings-css-zoom-200.png'),fullPage:true});
  assert.equal(await page.locator('#console-main').evaluate(el => getComputedStyle(el).animationName), 'none');
  assert.deepEqual(errors, [], 'page JavaScript errors');
  console.log('PASS: navigation/drafts, persisted settings, failed save, bilingual controls, firmware gates, task complete/pause/resume/stop, responsive layout, sticky stop, capture failure');
} finally { await browser.close(); }
