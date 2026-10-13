import test from 'node:test';
import assert from 'node:assert/strict';
import { boardStatusKey } from '../android_agent/static/board-status.js';
import { messages } from '../android_agent/static/i18n.js';

const state = { link:true, authenticated:true, keyboard_subscribed:true, mouse_subscribed:true, auth_error:null };
function status(ble_state = state, extra = {}) {
  return { mode:'ble', calibrated:false, board:{ connected:true, hid_ready:false, ble_state }, ...extra };
}
test('readiness hints follow link, authentication and each real subscription', () => {
  for (const [value, key] of [
    [null, 'boardPairNeeded'], [{ ...state, link:false }, 'boardPairNeeded'],
    [{ ...state, authenticated:false, auth_error:5 }, 'boardAuthNeeded'],
    [{ ...state, keyboard_subscribed:false }, 'boardReportsNeeded'],
    [{ ...state, mouse_subscribed:false }, 'boardReportsNeeded'],
    [state, 'boardNotReady'],
  ]) {
    assert.equal(boardStatusKey(status(value)), key);
    for (const language of ['zh','en']) assert.ok(messages[language][key]);
  }
});
test('serial failure, USB and calibration keep their existing precedence', () => {
  assert.equal(boardStatusKey(status(state, { board:null })), 'boardInactive');
  assert.equal(boardStatusKey(status(state, { board:{ connected:false, ble_state:state } })), 'boardDisconnected');
  assert.equal(boardStatusKey(status(state, { mode:'usb' })), 'usbHostNeeded');
  const ready = { connected:true, hid_ready:true, ble_state:null };
  assert.equal(boardStatusKey(status(null, { board:ready })), 'boardCalibrateNeeded');
  assert.equal(boardStatusKey(status(null, { board:ready, calibrated:true })), 'boardReady');
});
