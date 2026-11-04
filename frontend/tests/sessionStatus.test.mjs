import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
const source = readFileSync(new URL('../src/utils/sessionStatus.ts', import.meta.url), 'utf8').replace(/\r\n/g, '\n').replace(/^import type .*;\n/gm, '');
const { deriveCanonicalStageAccess: derive, hasCompletedStage } = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64'));

test('PMF stage preserves earlier results and Quickstart access across retries', () => {
  for (const [status, pmf] of Object.entries({completed: 'available', pmf_waiting: 'in_progress', pmf_running: 'in_progress', pmf_failed: 'failed', pmf_completed: 'completed'})) {
    const access = derive({status, dfv: {output: {final_decision: {status: 'GO'}}}, discovery: {status: 'done', output: {report: {}}}});
    assert.equal(access.pmf, pmf);
    assert.equal(access.tipsc, 'completed');
    assert.equal(access.dfv, 'GO');
    assert.equal(access.discovery, 'completed');
    assert.equal(access.quickstart, 'available');
  }
});

test('PMF stays locked until Discovery finishes; DFV retains its readiness gate', () => {
  for (const status of ['created', 'tipsc_completed', 'dfv_completed', 'discovery_running', 'discovery_failed']) {
    assert.equal(derive({status}).pmf, 'locked');
  }
  assert.equal(derive({status: 'tipsc_completed', tipsc: {ready_for_dfv: false}}).dfv, 'locked');
  assert.equal(derive({status: 'tipsc_completed', tipsc: {ready_for_dfv: true}}).dfv, 'available');
});


test('Quickstart stays independent of persisted pipeline progress', () => {
  for (const status of ['tipsc_completed', 'dfv_completed', 'completed', 'pmf_completed']) {
    assert.equal(derive({status}).quickstart, 'available');
  }
});

test('Discovery requires an explicit GO; PMF requires a completed saved Discovery report', () => {
  for (const decision of [undefined, 'NO-GO', 'UNKNOWN']) {
    assert.equal(derive({status: 'dfv_completed', dfv: {output: {decision}}}).discovery, 'locked');
  }
  assert.equal(derive({status: 'dfv_completed', dfv: {output: {decision: 'GO'}}}).discovery, 'available');
  for (const discovery of [undefined, {status: 'running'}, {status: 'done', output: null}]) {
    assert.equal(derive({status: 'completed', discovery}).pmf, 'locked');
  }
  assert.equal(derive({status: 'completed', discovery: {status: 'done', output: {report: 'plan'}}}).pmf, 'available');
});

test('Completion statistics describe finished evaluations, independently of favorable results', () => {
  assert.equal(hasCompletedStage({status: 'tipsc_completed', tipsc: {ready_for_dfv: false}}, 'tipsc'), true);
  assert.equal(hasCompletedStage({status: 'tipsc_running'}, 'tipsc'), false);
  assert.equal(hasCompletedStage({status: 'dfv_running', dfv: 'running'}, 'dfv'), false);
  assert.equal(hasCompletedStage({status: 'dfv_failed'}, 'dfv'), false);
  for (const decision of ['GO', 'NO-GO']) {
    assert.equal(hasCompletedStage({status: 'dfv_completed', dfv: decision}, 'dfv'), true);
  }
});
