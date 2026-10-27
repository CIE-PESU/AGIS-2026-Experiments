import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { stripTypeScriptTypes } from 'node:module';
const source = readFileSync(new URL('../src/services/apiClient.ts', import.meta.url), 'utf8')
  .replace('import { API_BASE_URL } from "@/constants";', 'const API_BASE_URL = "/api/v1";');
const client = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64'));
let calls;
beforeEach(() => {
  const data = new Map();
  globalThis.localStorage = { getItem: k => data.get(k) ?? null, setItem: (k,v) => data.set(k,v), removeItem: k => data.delete(k) };
  globalThis.window = new EventTarget();
  calls = [];
});
const ok = data => new Response(JSON.stringify({ data }), { status: 200 });

test('missing credentials never send a protected request', async () => {
  globalThis.fetch = async (...args) => { calls.push(args); return ok({}); };
  let cleared = false;
  window.addEventListener('agis:auth-cleared', () => { cleared = true; });
  await assert.rejects(client.apiRequest('/sessions/old'), { status: 401 });
  assert.equal(calls.length, 0);
  assert.equal(cleared, true);
});

test('refresh-only session authenticates before requesting session data', async () => {
  localStorage.setItem('agis_refresh_token', 'refresh');
  globalThis.fetch = async (url, options) => {
    calls.push([url, options.headers.Authorization]);
    return url.endsWith('/auth/refresh') ? ok({access_token:'new',refresh_token:'next'}) : ok({});
  };
  await client.apiRequest('/sessions/new');
  assert.deepEqual(calls, [['/api/v1/auth/refresh', undefined], ['/api/v1/sessions/new', 'Bearer new']]);
});

test('rejected refresh stops before session data is requested', async () => {
  localStorage.setItem('agis_refresh_token', 'expired');
  globalThis.fetch = async url => { calls.push(url); return new Response('{}',{status:401}); };
  await assert.rejects(client.apiRequest('/sessions/old'), { status: 401 });
  assert.deepEqual(calls, ['/api/v1/auth/refresh']);
});

test('retry uses a refreshed Authorization header', async () => {
  client.setTokens('expired','refresh');
  globalThis.fetch = async (url,options) => {
    calls.push([url,options.headers.Authorization]);
    if (url.endsWith('/auth/refresh')) return ok({access_token:'new',refresh_token:'next'});
    return options.headers.Authorization === 'Bearer expired' ? new Response('{}',{status:401}) : ok({});
  };
  await client.apiRequest('/sessions/new');
  assert.equal(calls.at(-1)[1], 'Bearer new');
});

test('public login works without a token', async () => {
  globalThis.fetch = async url => { calls.push(url); return ok({}); };
  await client.apiRequest('/auth/login',{auth:false,method:'POST'});
  assert.deepEqual(calls,['/api/v1/auth/login']);
});
