import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
const source = readFileSync(new URL('../src/utils/sessionStatus.ts', import.meta.url), 'utf8').replace(/^import type .*;\n/gm, '');
const { deriveCanonicalStageAccess: derive } = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64'));

test('PMF stage preserves earlier results and Quickstart access across retries', () => {
  for (const [status, pmf] of Object.entries({completed: 'available', pmf_waiting: 'in_progress', pmf_running: 'in_progress', pmf_failed: 'failed', pmf_completed: 'completed'})) {
    const access = derive({status, dfv: {output: {final_decision: {status: 'GO'}}}});
    assert.equal(access.pmf, pmf);
    assert.equal(access.tipsc, 'completed');
    assert.equal(access.dfv, 'GO');
    assert.equal(access.discovery, 'completed');
    assert.equal(access.quickstart, 'completed');
  }
});

test('PMF stays locked until Discovery finishes; DFV retains its readiness gate', () => {
  for (const status of ['created', 'tipsc_completed', 'dfv_completed', 'discovery_running', 'discovery_failed']) {
    assert.equal(derive({status}).pmf, 'locked');
  }
  assert.equal(derive({status: 'tipsc_completed', tipsc: {ready_for_dfv: false}}).dfv, 'locked');
  assert.equal(derive({status: 'tipsc_completed', tipsc: {ready_for_dfv: true}}).dfv, 'available');
});
