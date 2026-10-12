import test from 'node:test';
import assert from 'node:assert/strict';
import { screenPoint } from '../android_agent/static/geometry.js';

test('portrait side letterboxing is not clickable', () => {
  const rect = { left:10, top:20, width:400, height:400 };
  assert.equal(screenPoint(20,220,rect,100,200),null);
  assert.deepEqual(screenPoint(210,220,rect,100,200),{ x:500,y:500 });
});
test('landscape top letterboxing is not clickable', () => {
  const rect = { left:0, top:0, width:400, height:400 };
  assert.equal(screenPoint(200,20,rect,200,100),null);
  assert.deepEqual(screenPoint(0,100,rect,200,100),{ x:0,y:0 });
});
test('missing image cannot send input', () => {
  assert.equal(screenPoint(1,1,{ left:0,top:0,width:10,height:10 },0,0),null);
});
