# Frontend development

See [frontend architecture](frontend-arch.md) for the module map and [setup](workflow_and_running_guide.md) for complete platform commands.

```bash
npm ci --prefix frontend
npm run dev --prefix frontend
npm test --prefix frontend
npm run build --prefix frontend
npm audit --prefix frontend
```

Use Node 22.13+ and commit `package-lock.json` whenever dependencies change. Use `apiRequest` for data envelopes, `apiRequest(..., {raw: true})` for raw comment responses, and `apiFetch` for streams or existing response-oriented callers. Do not introduce page-local fetch/refresh implementations. Handle request failures in the visible UI.

Add new backend states to `SessionStatus` and its exhaustive stage mapping together. Treat backend authorization and unlock decisions as authoritative. Keep pages lazy-loaded, use accessible labels, and verify student, mentor, admin, and magic-link routes with Playwright before changing shared authentication.
