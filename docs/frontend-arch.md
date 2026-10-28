# Frontend architecture

React 19, TypeScript, Vite 8, React Router 7, Tailwind 3, and Radix UI form the SPA. Exact tested versions are in `frontend/package-lock.json`. Use Node 22.13+; CI uses Node 24. See [setup](workflow_and_running_guide.md).

`App.tsx` lazily loads route pages with a shared loading boundary. `AuthContext` owns the current identity, session, mapped results, and logout/reset behavior. `ThemeContext` persists light/dark preferences. Role guards route students, mentors, admins, and isolated mentor-workspace users to their supported pages.

All authenticated requests use `services/apiClient.ts`, including admin actions, comments, and streaming. It uses `VITE_API_BASE_URL` or same-origin `/api/v1`, serializes JSON, attaches tokens, coalesces token refreshes, retries once after a 401, and clears authentication when refresh is rejected. Admin failures are surfaced instead of being converted into empty lists. Comments intentionally use raw responses because that API returns arrays/objects rather than the standard data envelope.

`utils/sessionStatus.ts` maps the `SessionStatus` union exhaustively, including Ethics processing. The backend owns unlock decisions; the frontend renders them. TIPSC's `ready_for_dfv` gates DFV, and a DFV NO-GO locks Discovery. `mapSessionResults.ts` accepts the backend's `IMPORTANT` score and the legacy agent `I` alias.

Polling uses the shared client and stops on authentication failure. SSE uses authenticated fetch, handles normal stream closure and errors with bounded reconnect delay, and aborts/cancels timers on unmount. Tokens are not sent in query strings. LocalStorage retains tokens and display identity; authorization is always enforced on the backend.

Vite proxies `/api/v1` to `VITE_BACKEND_URL` in development. Configure `VITE_API_BASE_URL` at build time or a reverse proxy for production. Never rely on the development proxy in production. Generated `dist/` output and local environment files are excluded from source control.

Run `npm test`, `npm run build`, and `npm audit` from `frontend/`. Real-browser authentication journeys run through the Python Playwright integration suite with an isolated MongoDB/Kafka stack. Mock agent outputs keep automated tests deterministic and free of paid model calls.

Brand images are bundled in `frontend/public/branding/`, preserving the original assets while removing dependence on external image hosts.
