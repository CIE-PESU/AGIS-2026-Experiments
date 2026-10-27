# Frontend Architecture & Development Guide

> **Frontend** is a React 19 + TypeScript + Vite SPA with Tailwind CSS, React Router v7, and Radix UI primitives.

---

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | React | 19.x |
| Build Tool | Vite | 8.x |
| Language | TypeScript | 7.x |
| Styling | Tailwind CSS | 3.4 |
| UI Primitives | Radix UI | 1.x |
| Routing | React Router | 7.x |
| State | React Context + Hooks |
| Notifications | Sonner |
| Markdown | React Markdown |

---

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── shared/          # Reusable components (Logos, MentorChat, DetailedProgressView, etc.)
│   │   └── ui/              # Radix-based UI primitives (Button, Card, Input, etc.)
│   ├── context/             # React Context providers
│   │   ├── AuthContext.tsx  # Auth state, login/logout, session management
18:   │   └── ThemeContext.tsx # Light/dark theme toggle + persistence
│   ├── hooks/               # Custom React hooks
│   │   ├── useSessionPolling.ts
│   │   └── useSessionStream.ts
│   ├── pages/               # Route-level page components
│   │   ├── LandingPage.tsx
19:   │   ├── Login.tsx
20:   │   ├── QuickstartFlow.tsx
21:   │   ├── WorkspaceLayout.tsx
22:   │   ├── StudentWorkspace.tsx
23:   │   ├── TIPSCFlow.tsx
24:   │   ├── DFVFlow.tsx
25:   │   ├── DiscoveryFlow.tsx
26:   │   ├── MentorDashboard.tsx
27:   │   ├── AdminDashboard.tsx
28:   │   └── MentorMagicLinkHandler.tsx
│   ├── services/            # API clients
│   │   ├── apiClient.ts     # Base fetch wrapper with auth + refresh
│   │   └── authSessions.ts  # Session/auth API calls
│   ├── utils/               # Utilities
│   │   ├── response.ts      # Success/error response helpers
19:   │   └── utils.ts       # cn() className helper, etc.
│   ├── types/               # TypeScript types
│   │   └── api.ts
│   ├── constants.ts         # API base URL, config constants
│   ├── App.tsx              # Root component + routing
19:   ├── main.tsx           # Entry point (ThemeProvider + AuthProvider)
19:   └── index.css          # Tailwind + CSS variables + dark mode
├── dist/                    # Production build output
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
└── postcss.config.js
```

---

## Key Concepts

### Theme System (Dark/Light Mode)

**Implementation**: `src/context/ThemeContext.tsx`

- **CSS Variables**: Defined in `src/index.css` under `:root` (light) and `.dark` (dark)
- **Provider**: `ThemeProvider` wraps the entire app in `main.tsx`
- **Toggle**: `ThemeToggle` component in `src/components/ui/theme-toggle.tsx`
- **Persistence**: `localStorage` key `theme` + `prefers-color-scheme` fallback
- **Dark Mode**: True black (`#000000` / `hsl(0 0% 0%)`)

**CSS Variables** (subset):

```css
:root {
  --background: 0 0% 99%;
  --foreground: 248 27% 20%;
  --primary: 248 27% 31%;
  --muted: 220 20% 96%;
  --card: 0 0% 100%;
  --border: 220 20% 90%;
}

.dark {
  --background: 0 0% 0%;        /* TRUE BLACK */
  --foreground: 0 0% 100%;
  --muted: 0 0% 8%;
  --card: 0 0% 3%;
  --border: 0 0% 15%;
}
```

**Usage**: Use semantic Tailwind classes (`bg-background`, `text-foreground`, `bg-card`, `border-border`) instead of hardcoded colors.

---

### Authentication Context

**Implementation**: `src/context/AuthContext.tsx`

**State**:
```typescript
interface AuthContextValue {
  user: AppUser | null;           // Current user
  sessionId: string | null;       // Active session ID
  serverStatus: SessionStatus;    // Current session status
  pendingQuestion: string | null; // TIPSC follow-up question
  session: SessionState;          // { tipsc, dfv, discovery, quickstart }
  results: SessionResults;        // { tips, dfv, discovery }
  formData: FormDataMap;          // Form persistence
  timeline: TimelineEvent[];      // Activity log
  sessionDoc: SessionDocument;    // Full session document
  
  // Actions
  login(srn, password): Promise<Role>;
  loginWithWorkspace(workspaceId, name, role): void;
  logout(): Promise<void>;
  setSessionFromServer(doc): void;
  unlockNext(stage): void;
  saveResults(stage, data): void;
  setFormData(data): void;
  setSessionId(id): void;
  archiveSession(): void;
  addEvent(label): void;
}
```

**Persistence**: User + session ID in `localStorage` (keys: `appUser`, `appSessionId`)

---

### API Client

**Implementation**: `src/services/apiClient.ts`

**Features**:
- Automatic JWT attachment (`Authorization: Bearer <access_token>`)
- Automatic token refresh on 401 (`/api/v1/auth/refresh`)
- Idempotency key support for mutations
- Standardized error handling (`ApiRequestError`)

**Base URL**: `VITE_API_BASE_URL` or `/api/v1` (proxied via Vite)

---

### Routing

**Configuration**: `src/App.tsx`

```tsx
<Routes>
  <Route path="/" element={<LandingPage />} />
  <Route path="/login" element={<Login />} />
  <Route path="/workspace/:token" element={<MentorMagicLinkHandler />} />
  <Route path="/workspace" element={<WorkspaceLayout />}>
    <Route index element={<StudentWorkspace />} />
    <Route path="tipsc" element={<TIPSCFlow />} />
    <Route path="dfv" element={<DFVFlow />} />
    <Route path="discovery" element={<DiscoveryFlow />} />
    <Route path="jtbd" element={<Navigate to="/workspace/discovery" replace />} />
  </Route>
  <Route path="/quickstart" element={<QuickstartFlow />} />
  <Route path="/mentor" element={<MentorDashboard />} />
  <Route path="/admin" element={<AdminDashboard />} />
  <Route path="*" element={<Navigate to="/" replace />} />
</Routes>
```

---

## Page Components

### 1. LandingPage (`/`)
- Public marketing page
- Pipeline visualization (ArcDiagram)
- Quickstart CTA → `/login?redirect=/quickstart`
- Dark mode: Navy gradient background

### 2. Login (`/login`)
- SRN + password form
- Role detection (student/mentor/admin)
- Redirects to role home or `?redirect=` param

### 3. QuickstartFlow (`/quickstart`)
- 7-question form (textarea/input)
- In-process CrewAI evaluation (Ethics + TIPSC + DFV)
- Results: 10 parameters with GREEN/YELLOW/RED + advice
- **Back button**: Links to `/` (Home)

### 4. WorkspaceLayout + StudentWorkspace (`/workspace`)
- Layout with header (logo, breadcrumbs, user avatar, ThemeToggle, chat, logout)
- Progress bar (TIPSC → DFV → Discovery)
- Module cards with status badges
- Team progress monitor table
- Timeline + MentorChat sidebar

### 5. Flow Pages
| Page | Route | Purpose |
|------|-------|---------|
| `TIPSCFlow` | `/workspace/tipsc` | 5-tab wizard (Pre-eval → Validation → Regulatory → Ethics → TIPSC) |
| `DFVFlow` | `/workspace/dfv` | 3-context form → DFV results (GO/NO-GO) |
| `DiscoveryFlow` | `/workspace/discovery` | 6-field JTBD form → structured discovery plan |

### 6. MentorDashboard (`/mentor`)
- Team selector tabs
- Student progress table (TIPSC/DFV/JTBD status)
- Detail dialog with session timeline
- Mentor comment system (Dialog + MentorChat)

### 7. AdminDashboard (`/admin`)
- User management
- Team management
- Session audit logs
- Metrics dashboard

---

## State Management Patterns

### Form Persistence
- **Context**: `formData` in `AuthContext` (persisted in `localStorage` via `useEffect`)
- **Sync**: `setFormData()` called on every input change
- **Namespacing**: `discovery_problem`, `dfv_desirability_context`, etc.

### Session Polling
- **Hook**: `useSessionPolling.ts` (5s interval)
- **Scope**: Global in `WorkspaceLayout` + per-flow pages
- **Updates**: `serverStatus`, `pendingQuestion`, `session`, `results`

### Server-Sent Events (SSE)
- **Hook**: `useSessionStream.ts`
- **Endpoint**: `GET /api/v1/sessions/{id}/stream`
- **Use case**: Real-time status updates during agent runs

---

## UI Components

### Radix UI Primitives (`src/components/ui/`)
| Component | Description |
|-----------|-------------|
| `Button` | Variants: default, secondary, outline, ghost, destructive, accent |
| `Card` | Card, CardHeader, CardTitle, CardContent, CardFooter |
| `Input` | Styled input with consistent focus states |
| `Textarea` | Multi-line input |
| `Button` (AlertDialog) | Confirmation dialogs |
| `Tabs` | Tab navigation |
| `Select` | Dropdown select |
| `Tooltip` | Hover tooltips |

### Shared Components (`src/components/shared/`)
| Component | Purpose |
|-----------|---------|
| `Logos` | PES + CIE logos with invert prop |
| `MentorChat` | Sidebar chat for mentor comments |
| `DetailedProgressView` | Modal with full session detail |
| `StatusBadge` | Status chips (available/locked/in_progress/completed/failed) |
| `TrafficDot` | GREEN/YELLOW/RED indicator dots |
| `Timeline` | Vertical activity timeline |

---

## Development Workflow

### Commands
```bash
# Development
cd frontend && npm run dev        # Vite dev server (port 5173)

# Production build
cd frontend && npm run build      # tsc + vite build → dist/

# Type checking
cd frontend && npx tsc --noEmit

# Preview production build
cd frontend && npm run preview
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `/api/v1` | API base URL (proxied via Vite) |
| `VITE_USE_MOCK_FLOWS` | `false` | Set `true` to use mock flows |

---

## Vite Configuration

**File**: `vite.config.ts`

```typescript
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    proxy: {
      "/api/v1": {
        target: process.env.VITE_BACKEND_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

**Key features**:
- Path alias `@` → `./src`
- API proxy to backend (avoids CORS in dev)
- HMR enabled

---

## TypeScript Configuration

**Files**: `tsconfig.json`, `tsconfig.node.json`

- **Target**: ES2022
- **Module**: ESNext
- **Strict**: true
- **JSX**: react-jsx
- **ModuleResolution**: bundler
- **BaseUrl**: `.` with `@/*` → `src/*`

---

## Testing

### Unit Tests
```bash
# Backend
cd .. && PYTHONPATH=. .venv/bin/python -m pytest tests/backend/unit/ -q

# Frontend (TypeScript only - no test runner configured)
npx tsc --noEmit
```

### E2E Tests
Not yet configured. Consider Playwright or Cypress.

---

## Accessibility

- **Semantic HTML**: `<main>`, `<header>`, `<nav>`, `<section>`, `<footer>`
- **ARIA**: Labels, roles, live regions on dynamic content
- **Focus**: Visible focus rings (`focus-visible:ring-2`)
- **Skip Links**: "Skip to main content" on all layouts
- **Color Contrast**: WCAG AA compliant in both themes
- **Reduced Motion**: Respects `prefers-reduced-motion`

---

## Performance

| Metric | Target |
|--------|--------|
| Initial JS | < 600 KB gzipped |
| First Contentful Paint | < 1.5s |
| Time to Interactive | < 3s |
| Bundle Analysis | `npm run build` → `dist/` |

**Code Splitting**: Not yet implemented (single chunk ~600KB). Consider:
- `React.lazy()` for route components
- `manualChunks` in Vite config for vendor splitting

---

## Deployment

### Build
```bash
cd frontend && npm run build
# Output: dist/
```

### Static Hosting (Vercel, Netlify, Cloudflare Pages)
- Build command: `npm run build`
- Output directory: `dist`
- SPA fallback: `index.html` for all routes

### Docker
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `ModuleNotFoundError` | Run `npm install` in `frontend/` |
| CORS errors in dev | Check Vite proxy config (`vite.config.ts`) |
| Hydration mismatch | Check for SSR/client mismatches (random IDs, dates) |
| Theme not persisting | Check `localStorage` for `theme` key |
| Auth redirect loop | Check `AuthContext` login/logout logic |
| Build fails on types | Run `npx tsc --noEmit` to isolate |

---

## File Map (Quick Reference)

| Feature | Files |
|---------|-------|
| Theme | `src/context/ThemeContext.tsx`, `src/components/ui/theme-toggle.tsx`, `src/index.css` |
| Auth | `src/context/AuthContext.tsx`, `src/services/apiClient.ts`, `src/services/authSessions.ts` |
| Routing | `src/App.tsx` |
| Landing | `src/pages/LandingPage.tsx` |
| Auth Pages | `src/pages/Login.tsx`, `src/pages/MentorMagicLinkHandler.tsx` |
| Workspace | `src/pages/WorkspaceLayout.tsx`, `src/pages/StudentWorkspace.tsx` |
| Flows | `src/pages/QuickstartFlow.tsx`, `src/pages/TIPSCFlow.tsx`, `src/pages/DFVFlow.tsx`, `src/pages/DiscoveryFlow.tsx` |
| Dashboards | `src/pages/MentorDashboard.tsx`, `src/pages/AdminDashboard.tsx` |
| API | `src/services/apiClient.ts`, `src/services/authSessions.ts` |
| Hooks | `src/hooks/useSessionPolling.ts`, `src/hooks/useSessionStream.ts` |
| UI | `src/components/ui/`, `src/components/shared/` |
| Styles | `src/index.css`, `tailwind.config.ts` |
| Config | `vite.config.ts`, `tsconfig.json`, `tailwind.config.ts` |