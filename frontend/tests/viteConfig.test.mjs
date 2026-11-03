import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { loadConfigFromFile } from 'vite';

test('manual Vite startup honors frontend env files and launcher overrides', async () => {
  // Keep the copied config under frontend so its imports resolve the installed plugins.
  const directory = mkdtempSync(fileURLToPath(new URL('./.vite-config-', import.meta.url)));
  const previous = process.env.VITE_BACKEND_URL;
  const configFile = path.join(directory, 'vite.config.ts');
  const readTarget = async () => {
    const result = await loadConfigFromFile({ command: 'serve', mode: 'development' }, configFile);
    assert.ok(result);
    return result.config.server.proxy['/api/v1'].target;
  };
  try {
    writeFileSync(configFile, readFileSync(new URL('../vite.config.ts', import.meta.url)));
    delete process.env.VITE_BACKEND_URL;
    assert.equal(await readTarget(), 'http://127.0.0.1:8008');
    writeFileSync(path.join(directory, '.env'), 'VITE_BACKEND_URL=http://127.0.0.1:18008\n');
    assert.equal(await readTarget(), 'http://127.0.0.1:18008');
    writeFileSync(path.join(directory, '.env.development'), 'VITE_BACKEND_URL=http://127.0.0.1:28008\n');
    assert.equal(await readTarget(), 'http://127.0.0.1:28008');
    process.env.VITE_BACKEND_URL = 'http://127.0.0.1:8008';
    assert.equal(await readTarget(), 'http://127.0.0.1:8008');
  } finally {
    if (previous === undefined) delete process.env.VITE_BACKEND_URL;
    else process.env.VITE_BACKEND_URL = previous;
    rmSync(directory, { recursive: true, force: true });
  }
});
