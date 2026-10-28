import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';

const source = readFileSync(new URL('../src/utils/quickstartState.ts', import.meta.url), 'utf8')
  .replace(/^import type .*;\n/gm, '');
const { loadQuickstartState, saveQuickstartState, clearQuickstartState } = await import(
  'data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64')
);

test('quickstart draft and result survive reload and stay scoped to the user', () => {
  const values = new Map();
  globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
  };
  const saved = { answers: { problem: 'Campus queues' }, result: { parameters: [], green_count: 0 }, activeGroup: 'dfv' };
  saveQuickstartState('student-a', saved);
  assert.deepEqual(loadQuickstartState('student-a'), saved);
  assert.deepEqual(loadQuickstartState('student-b'), { answers: {}, result: null, activeGroup: 'ethics' });
  clearQuickstartState('student-a');
  assert.deepEqual(loadQuickstartState('student-a'), { answers: {}, result: null, activeGroup: 'ethics' });
  assert.equal(values.size, 0);
});

test('invalid or old saved state falls back to an editable form', () => {
  globalThis.localStorage = {
    getItem: () => '{broken',
    setItem: () => {},
  };
  assert.deepEqual(loadQuickstartState('student-a'), { answers: {}, result: null, activeGroup: 'ethics' });
});
