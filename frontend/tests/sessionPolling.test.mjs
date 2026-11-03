import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
const source = readFileSync(new URL('../src/hooks/useSessionPolling.ts', import.meta.url), 'utf8').replace(/\r\n/g, '\n')
  .split('import { deriveCanonicalStageAccess }')[0]
  .replace(/^import .*;\n/gm, '')
  .replace('export function useSessionPolling', 'function useSessionPolling');
const code = `const useEffect = (effect, deps) => { globalThis.cleanup = globalThis.pollEffect ? globalThis.pollEffect(effect, deps) : effect(); };
const useRef = value => globalThis.pollRef ? globalThis.pollRef(value) : ({ current: value });
const SESSION_POLL_INTERVAL_MS = 5000;
const getSession = (...args) => globalThis.pollSession(...args);
${source}
export { useSessionPolling };`;
const { useSessionPolling } = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(code)).toString('base64'));

test('401 stops further polling; ApiRequestError uses status, not response.status', async () => {
  let timer, calls = 0;
  globalThis.window = { setInterval: fn => { timer = fn; return 1; }, clearInterval() {} };
  globalThis.pollSession = async () => { calls++; throw { status: 401 }; };
  useSessionPolling('old-session', () => assert.fail('must not update'), () => {});
  await new Promise(setImmediate);
  await timer();
  await timer();
  assert.equal(calls, 1);
  globalThis.cleanup();
});

test('changing callbacks keeps the polling timer and uses the latest not-found handler', async () => {
  let cursor = 0, previousDeps, effectCleanup, timers = 0, latestCalls = 0, rejectRequest;
  const refs = [];
  globalThis.pollRef = value => {
    const index = cursor++;
    return refs[index] ??= { current: value };
  };
  globalThis.pollEffect = (effect, deps) => {
    if (!previousDeps || deps.some((value, index) => value !== previousDeps[index])) {
      effectCleanup?.();
      previousDeps = deps;
      effectCleanup = effect();
    }
    return effectCleanup;
  };
  globalThis.window = { setInterval() { timers++; return timers; }, clearInterval() {} };
  globalThis.pollSession = () => new Promise((_, reject) => { rejectRequest = reject; });
  try {
    useSessionPolling('session', () => {}, () => assert.fail('stale callback'));
    cursor = 0;
    useSessionPolling('session', () => {}, () => { latestCalls++; });
    assert.equal(timers, 1);
    rejectRequest({ status: 404 });
    await new Promise(setImmediate);
    assert.equal(latestCalls, 1);
  } finally {
    effectCleanup?.();
    delete globalThis.pollRef;
    delete globalThis.pollEffect;
  }
});
