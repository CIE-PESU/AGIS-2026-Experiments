import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
const source = readFileSync(new URL('../src/hooks/useSessionPolling.ts', import.meta.url), 'utf8')
  .split('import { deriveCanonicalStageAccess }')[0]
  .replace(/^import .*;\n/gm, '')
  .replace('export function useSessionPolling', 'function useSessionPolling');
const code = `const useEffect = effect => { globalThis.cleanup = effect(); };
const useRef = value => ({ current: value });
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
