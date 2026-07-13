# Frontend Architecture Documentation

## Overview

This frontend application is a React-based web platform for the AGIS (Agentic AI Entrepreneurship System) project. It provides a role-based interface for students, mentors, and admins to manage entrepreneurship evaluation workflows including TIPSC assessment, DFV analysis, and Customer Discovery.

## Tech Stack

### Core Framework
- **React 18.3.1** - UI framework with hooks and concurrent features
- **TypeScript 5.7.2** - Type-safe development with strict mode enabled
- **Vite 6.0.3** - Build tool and dev server with HMR

### Routing & State
- **React Router DOM 6.28.0** - Client-side routing with nested routes
- **React Context API** - Global state management (AuthContext)

### UI & Styling
- **TailwindCSS 3.4.16** - Utility-first CSS framework
- **Radix UI** - Accessible component primitives
  - @radix-ui/react-dialog
  - @radix-ui/react-alert-dialog
  - @radix-ui/react-slot
- **Lucide React 0.468.0** - Icon library
- **Sonner 1.7.1** - Toast notifications
- **class-variance-authority** - Component variant management
- **clsx & tailwind-merge** - Conditional class utilities

### Development Tools
- **PostCSS & Autoprefixer** - CSS processing
- **ESLint & Prettier** - Code quality (configured via project standards)

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # Base UI components (Button, Card, Input, etc.)
│   │   └── shared/          # Shared business components (StatusBadge, Timeline, etc.)
│   ├── context/
│   │   └── AuthContext.tsx  # Global authentication & session state
│   ├── data/
│   │   └── mockData.ts      # Mock responses for development
│   ├── hooks/
│   │   └── useSessionPolling.ts  # Session status polling hook
│   ├── lib/
│   │   └── utils.ts         # Utility functions (cn for class merging)
│   ├── pages/
│   │   ├── LandingPage.tsx  # Public landing page
│   │   ├── Login.tsx        # Authentication page
│   │   ├── WorkspaceLayout.tsx  # Student workspace layout wrapper
│   │   ├── StudentWorkspace.tsx # Student dashboard
│   │   ├── TIPSCFlow.tsx    # TIPSC evaluation flow
│   │   ├── DFVFlow.tsx      # DFV analysis flow
│   │   ├── DiscoveryFlow.tsx # Customer discovery flow
│   │   ├── MentorDashboard.tsx # Mentor interface
│   │   └── AdminDashboard.tsx  # Admin interface
│   ├── services/
│   │   ├── apiClient.ts     # HTTP client with auth & error handling
│   │   ├── authSessions.ts  # Auth & session API calls
│   │   └── api.ts           # Mock API functions (dev mode)
│   ├── types/
│   │   └── api.ts           # TypeScript types aligned with backend API
│   ├── utils/
│   │   ├── adminData.ts     # Local storage utilities for admin/mentor data
│   │   └── exportMarkdown.ts # Report generation utilities
│   ├── App.tsx              # Root component with routing
│   ├── main.tsx             # Application entry point
│   ├── constants.ts         # App-wide constants
│   └── index.css            # Global styles & Tailwind directives
├── index.html               # HTML template
├── package.json             # Dependencies & scripts
├── vite.config.ts           # Vite configuration with proxy
├── tailwind.config.ts       # Tailwind configuration
└── tsconfig.json            # TypeScript configuration
```

## Architecture Patterns

### 1. Component Architecture

**Component Hierarchy:**
```
App (Router + AuthProvider)
├── LandingPage (Public)
├── Login (Public)
├── WorkspaceLayout (Protected - Student)
│   └── StudentWorkspace
│   ├── TIPSCFlow
│   ├── DFVFlow
│   └── DiscoveryFlow
├── MentorDashboard (Protected - Mentor)
└── AdminDashboard (Protected - Admin)
```

**Component Organization:**
- **UI Components** (`components/ui/`): Reusable, stateless components following Radix UI patterns
- **Shared Components** (`components/shared/`): Business-specific reusable components
- **Page Components** (`pages/`): Route-level components with business logic

### 2. State Management

**Global State (AuthContext):**
```typescript
interface AuthContextValue {
  user: AppUser | null;           // Current authenticated user
  sessionId: string | null;        // Active session ID
  serverStatus: SessionStatus;    // Backend session status
  session: SessionState;          // Stage access (tipsc, dfv, discovery)
  results: SessionResults;        // Flow results storage
  formData: FormDataMap;          // Form input data
  timeline: TimelineEvent[];       // Activity timeline
  login(): Promise<Role>;         // Authentication
  logout(): Promise<void>;        // Logout
  setSessionFromServer(): void;   // Sync with backend
  unlockNext(): void;             // Progress to next stage
  saveResults(): void;            // Store flow results
  archiveSession(): void;          // Archive current session
}
```

**Local State:**
- Component-level state using React hooks (useState, useEffect, useMemo)
- Custom hooks for complex logic (useSessionPolling)

### 3. Data Flow

**Authentication Flow:**
```
User Login → apiClient.login() → Backend API
                ↓
         Store JWT tokens (localStorage)
                ↓
         Set user in AuthContext
                ↓
         Route to role-specific dashboard
```

**Session Flow:**
```
Create Session → Backend creates session document
                    ↓
              Poll session status (useSessionPolling)
                    ↓
              Update UI based on status
                    ↓
              Trigger flows (TIPSC → DFV → Discovery)
                    ↓
              Store results in AuthContext
                    ↓
              Archive session when complete
```

**API Request Flow:**
```
Component → Service Function → apiClient.apiRequest()
                                    ↓
                            Add auth headers
                                    ↓
                            Make fetch request
                                    ↓
                            401 error? → Refresh token → Retry
                                    ↓
                            Parse response or throw error
                                    ↓
                            Return data to component
```

## Routing Structure

### Route Definitions (App.tsx)

```typescript
/                          → LandingPage (public)
/login                     → Login (public)
/workspace                 → StudentWorkspace (student)
/workspace/tipsc           → TIPSCFlow (student)
/workspace/dfv             → DFVFlow (student)
/workspace/discovery       → DiscoveryFlow (student)
/workspace/jtbd            → Redirect to /workspace/discovery
/mentor                    → MentorDashboard (mentor)
/admin                     → AdminDashboard (admin)
*                          → Redirect to /
```

### Route Protection
- `WorkspaceLayout` checks for authenticated student role
- `RequireRole` component (shared) for role-based access
- AuthContext provides user state for route guards

## API Integration

### API Client (services/apiClient.ts)

**Features:**
- Centralized HTTP client using fetch API
- Automatic JWT token injection via Authorization header
- Token refresh on 401 responses
- Error parsing with custom ApiRequestError
- Idempotency key support for safe retries
- Type-safe request/response handling

**Key Functions:**
```typescript
apiRequest<T>(path, options): Promise<T>
  - method: GET | POST | DELETE
  - body: request payload
  - auth: boolean (include auth headers)
  - idempotencyKey: string (for idempotent requests)
```

### Service Layer (services/authSessions.ts)

**Authentication:**
- `login(srn, password)` - User authentication
- `logout(refreshToken)` - Session termination
- `getCurrentUser()` - Fetch current user details

**Session Management:**
- `createSession(payload)` - Create new evaluation session
- `getSession(sessionId)` - Fetch session document
- `archiveSession(sessionId)` - Archive session
- `triggerTipsc(sessionId)` - Start TIPSC flow
- `triggerDfv(sessionId, payload)` - Start DFV flow
- `triggerDiscovery(sessionId)` - Start Discovery flow

**Mentor Features:**
- `getSessionComments(sessionId)` - Fetch mentor comments
- `getMentorSessions(params)` - Fetch sessions for review

### Mock API (services/api.ts)

**Purpose:** Provides mock responses when backend is unavailable (development mode)

**Functions:**
- `checkCompliance()` - Mock compliance check
- `getInitialTIPSCScores()` - Mock TIPSC initial scores
- `submitFollowUp(round, answer)` - Mock follow-up responses
- `runDFVAnalysis()` - Mock DFV analysis
- `generateJTBD()` - Mock JTBD generation

### Backend Integration

**Proxy Configuration (vite.config.ts):**
```typescript
proxy: {
  "/api/v1": {
    target: process.env.VITE_BACKEND_URL ?? "http://localhost:8000",
    changeOrigin: true
  }
}
```

**Environment Variables:**
- `VITE_API_BASE_URL` - Backend API base URL (default: /api/v1)
- `VITE_USE_MOCK_FLOWS` - Enable mock data (default: true for dev)
- `VITE_BACKEND_URL` - Backend server URL for proxy

## Type System

### Core Types (types/api.ts)

**Role Types:**
```typescript
type Role = "student" | "mentor" | "admin";
```

**Session Status:**
```typescript
type SessionStatus =
  | "created"
  | "queued"
  | "tipsc_running"
  | "tipsc_completed"
  | "tipsc_failed"
  | "dfv_waiting"
  | "dfv_running"
  | "dfv_completed"
  | "dfv_failed"
  | "discovery_waiting"
  | "discovery_running"
  | "discovery_failed"
  | "completed"
  | "archived";
```

**API Response Types:**
```typescript
type ApiSuccess<T> = {
  data: T;
  meta?: ApiMeta;
};

type ApiError = {
  code: string;
  message: string;
  field?: string | null;
  request_id: string;
  timestamp: string;
};
```

**Session Types:**
```typescript
type SessionDocument = {
  session_id: string;
  team_id: string;
  student_id: string;
  problem_statement: string;
  idea: string;
  status: SessionStatus;
  tipsc: Record<string, unknown> | null;
  dfv: Record<string, unknown> | null;
  discovery: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};
```

### Flow Result Types (data/mockData.ts)

**TIPSC Result:**
```typescript
type TIPSCResult = {
  scores: Record<"timely" | "importance" | "profitable" | "solvable", TIPSCScore>;
  readyForDFV: boolean;
  explanation: string;
  followUps?: { question: string; answer: string }[];
};
```

**DFV Result:**
```typescript
type DFVResult = {
  decision: "GO" | "NO-GO";
  executiveSummary: string;
  dimensions: Record<"desirability" | "feasibility" | "viability", {
    status: Traffic;
    summary: string;
    details: string[];
  }>;
  recommendations: string[];
};
```

**JTBD Result:**
```typescript
type JTBDResult = {
  title: string;
  objectives: Objective[];
  assumptions: Assumption[];
  interviewGuide: InterviewSection[];
  executionGuide: ExecutionGuide;
  recordingTemplate: RecordingTemplate;
  evidenceChecklist: string[];
  finalSummary: FinalSummary;
};
```

## Key Workflows

### 1. Student Workflow

**Step 1: Login**
1. User enters SRN and password on Login page
2. `AuthContext.login()` calls `authSessions.login()`
3. Backend validates credentials and returns JWT tokens
4. Tokens stored in localStorage
5. User redirected to StudentWorkspace

**Step 2: Create Session**
1. User fills problem statement and idea form
2. `createSession()` called via authSessions
3. Backend creates session document with status "created"
4. Session ID stored in AuthContext
5. Session polling begins via `useSessionPolling`

**Step 3: TIPSC Evaluation**
1. User navigates to /workspace/tipsc
2. Pre-evaluation questions collected
3. `triggerTipsc()` called to start backend flow
4. Session status updates to "tipsc_running"
5. Polling detects completion → "tipsc_completed"
6. Results stored in AuthContext
7. DFV stage unlocked

**Step 4: DFV Analysis**
1. User navigates to /workspace/dfv (unlocked after TIPSC)
2. User provides DFV context (desirability, feasibility, viability)
3. `triggerDfv()` called with context payload
4. Session status updates to "dfv_running"
5. Polling detects completion → "dfv_completed"
6. Results stored in AuthContext
7. Discovery stage unlocked

**Step 5: Customer Discovery**
1. User navigates to /workspace/discovery (unlocked after DFV)
2. `triggerDiscovery()` called
3. Session status updates to "discovery_running"
4. Polling detects completion → "completed"
5. JTBD results stored in AuthContext
6. Full workflow complete

**Step 6: Archive & Export**
1. User clicks "Archive Session"
2. Report generated via `exportMarkdown()`
3. `archiveSession()` called on backend
4. Session status set to "archived"
5. Local state reset
6. User can start new session

### 2. Mentor Workflow

**Dashboard Access:**
1. Mentor logs in with mentor credentials
2. Redirected to MentorDashboard
3. Fetches assigned sessions via `getMentorSessions()`

**Session Review:**
1. View list of student sessions with filters (team_id, status, pagination)
2. Click session to view details
3. Add comments via `getSessionComments()` and comment UI
4. Monitor progress through TIPSC → DFV → Discovery stages

### 3. Admin Workflow

**Dashboard Access:**
1. Admin logs in with admin credentials
2. Redirected to AdminDashboard
3. Full system visibility and management

**Student Management:**
1. View all registered students
2. Manage team assignments
3. Monitor overall progress

## Session Polling

### Implementation (hooks/useSessionPolling.ts)

**Purpose:** Continuously poll backend for session status updates during flow execution

**Configuration:**
- Interval: 5000ms (SESSION_POLL_INTERVAL_MS)
- Auto-starts when sessionId exists
- Stops when component unmounts or sessionId clears

**Status Mapping:**
```typescript
deriveStageAccess(status): SessionState {
  // Maps backend status to UI stage states
  // tipsc: "available" | "in_progress" | "completed" | "locked"
  // dfv: "available" | "in_progress" | "completed" | "locked"
  // discovery: "available" | "in_progress" | "completed" | "locked"
}
```

**Usage:**
```typescript
useSessionPolling(sessionId, setSessionFromServer, enabled);
```

## Authentication & Authorization

### Token Management

**Storage:** localStorage
- `agis_access_token` - JWT access token
- `agis_refresh_token` - JWT refresh token

**Token Refresh Flow:**
1. API request returns 401
2. `refreshAccessToken()` called automatically
3. Refresh token sent to /auth/refresh
4. New access token received and stored
5. Original request retried with new token
6. If refresh fails, tokens cleared and user logged out

### Role-Based Access Control

**Role Inference (Dev Mode):**
```typescript
inferMockRole(srn): Role {
  if (srn.includes("admin")) return "admin";
  if (srn.includes("mentor") || srn.includes("@")) return "mentor";
  return "student";
}
```

**Route Protection:**
- WorkspaceLayout: Requires student role
- MentorDashboard: Requires mentor role
- AdminDashboard: Requires admin role

## Development Mode Features

### Mock Data Fallback

When backend is unavailable:
- Login falls back to mock authentication
- Role inferred from SRN
- Flow responses use mock data from `data/mockData.ts`
- Session state managed locally
- Admin/mentor data stored in localStorage

### Local Storage Utilities (utils/adminData.ts)

**Student Management:**
- `registerStudentTeam(srn, teamName)` - Register student to team
- `getStudents()` - Retrieve all students
- `initializeStorage()` - Setup default data

**Comment System:**
- `getComments(srn)` - Get student comments
- `addComment(srn, comment)` - Add new comment

## UI Components

### Base UI Components (components/ui/)

**Radix UI Wrappers:**
- `button.tsx` - Button with variants
- `card.tsx` - Card container
- `input.tsx` - Text input
- `textarea.tsx` - Multi-line input
- `dialog.tsx` - Modal dialog
- `alert-dialog.tsx` - Confirmation dialog
- `tabs.tsx` - Tab navigation

**Styling Pattern:**
```typescript
const { variant, size, ...props } = props;
const className = cn(baseClasses, variantClasses[variant], sizeClasses[size], props.className);
```

### Shared Components (components/shared/)

**Business Components:**
- `StatusBadge.tsx` - Stage status indicator with traffic light colors
- `Timeline.tsx` - Activity timeline display
- `MentorChat.tsx` - Mentor comment interface
- `DetailedProgressView.tsx` - Detailed progress modal
- `Logos.tsx` - PES and CIE logos
- `RequireRole.tsx` - Role-based component rendering

## Utility Functions

### Class Merging (lib/utils.ts)
```typescript
cn(...inputs) - Merge Tailwind classes with conflict resolution
```

### Export Utilities (utils/exportMarkdown.ts)
```typescript
generateMarkdown(results, formData) - Generate markdown report
downloadMarkdown(content, filename) - Trigger file download
```

## Configuration Files

### Vite Configuration (vite.config.ts)
- React plugin for JSX transformation
- Path alias: `@` → `./src`
- Proxy for /api/v1 routes to backend
- Development server on 0.0.0.0

### TypeScript Configuration (tsconfig.json)
- Target: ES2020
- Strict mode enabled
- Path resolution with @ alias
- JSX: react-jsx

### Tailwind Configuration (tailwind.config.ts)
- Custom color scheme (primary, secondary, accent)
- Animation utilities
- Content paths for component scanning

## Environment Variables

### Required Variables
```bash
VITE_API_BASE_URL=/api/v1              # Backend API base path
VITE_BACKEND_URL=http://localhost:8000 # Backend server URL
VITE_USE_MOCK_FLOWS=true               # Enable mock data (dev)
```

### Setup
Create `.env` file in frontend root:
```bash
VITE_API_BASE_URL=/api/v1
VITE_BACKEND_URL=http://localhost:8000
VITE_USE_MOCK_FLOWS=true
```

## Build & Deployment

### Development
```bash
npm install          # Install dependencies
npm run dev          # Start dev server (http://localhost:5173)
```

### Production Build
```bash
npm run build        # Build for production (dist/ directory)
npm run preview      # Preview production build
```

### Build Output
- `dist/index.html` - Entry HTML
- `dist/assets/` - Bundled JS/CSS assets
- Optimized and minified for production

## Integration with Backend

### API Contract

**Base URL:** `/api/v1` (proxied to backend)

**Authentication Endpoints:**
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user

**Session Endpoints:**
- `POST /sessions` - Create session
- `GET /sessions/{id}` - Get session details
- `DELETE /sessions/{id}` - Archive session
- `POST /sessions/{id}/trigger/tipsc` - Trigger TIPSC
- `POST /sessions/{id}/trigger/dfv` - Trigger DFV
- `POST /sessions/{id}/trigger/discovery` - Trigger Discovery

**Mentor Endpoints:**
- `GET /sessions/{id}/comments` - Get session comments
- `GET /mentor/sessions` - Get mentor sessions (with query params)

### Request/Response Format

**Request Headers:**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {access_token}",
  "Idempotency-Key": "{optional_key}"
}
```

**Success Response:**
```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO-8601"
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "field": "field_name (optional)",
    "request_id": "uuid",
    "timestamp": "ISO-8601"
  }
}
```

## Troubleshooting

### Common Issues

**CORS Errors:**
- Ensure Vite proxy is configured correctly
- Check backend allows requests from frontend origin

**Authentication Failures:**
- Verify tokens are stored in localStorage
- Check token refresh logic in apiClient
- Ensure backend refresh endpoint is accessible

**Session Polling Issues:**
- Check SESSION_POLL_INTERVAL_MS in constants
- Verify sessionId is set in AuthContext
- Check network tab for failed polling requests

**Mock Data Not Loading:**
- Set VITE_USE_MOCK_FLOWS=true in .env
- Check mockData.ts exports are correct
- Verify api.ts functions are being called

## Best Practices

### Component Development
- Use TypeScript for all components
- Follow functional component pattern with hooks
- Extract reusable logic into custom hooks
- Use Radix UI primitives for accessibility
- Apply consistent styling with Tailwind

### State Management
- Keep component state local when possible
- Use AuthContext for global auth/session state
- Avoid prop drilling - use context or custom hooks
- Keep API calls in service layer

### API Integration
- Always use apiClient for HTTP requests
- Handle errors with try-catch blocks
- Show user feedback via toast notifications
- Use proper TypeScript types for responses

### Code Organization
- Group related components in directories
- Use barrel exports (index.ts) for cleaner imports
- Keep utility functions in utils/ directory
- Separate business logic from UI components

## Future Enhancements

### Potential Improvements
- Add React Query for data fetching and caching
- Implement error boundary for better error handling
- Add loading skeletons for better UX
- Implement comprehensive testing (Jest, React Testing Library)
- Add storybook for component documentation
- Implement internationalization (i18n)
- Add analytics tracking
- Implement offline support with service workers

### Scalability Considerations
- Code splitting for route-based lazy loading
- Virtual scrolling for long lists
- Image optimization and lazy loading
- Bundle size optimization
- Performance monitoring

## Conclusion

This frontend architecture provides a solid foundation for the AGIS platform with clear separation of concerns, type safety, and scalability. The component-based architecture, centralized state management, and well-defined API integration patterns make it easy to maintain and extend. The mock data fallback ensures development can continue even without backend availability, while the production-ready API client ensures seamless backend integration when deployed.
