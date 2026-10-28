export const PES_LOGO =
  "/branding/pes.png";

export const PES_LOGO_WHITE =
  "/branding/pes-white.png"

  export const CIE_LOGO =
  "/branding/cie.png";

/** Base URL per docs/api-spec.md §1 — automatically uses current LAN hostname if accessing over network */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** Session polling interval per docs/backend-arch.md §2.3 */
export const SESSION_POLL_INTERVAL_MS = 5000;

// Defaults to real API. Set VITE_USE_MOCK_FLOWS=true in .env.local to re-enable mocks.
export const USE_MOCK_FLOWS = import.meta.env.VITE_USE_MOCK_FLOWS === "true";

export const SESSION_FIELD_MIN = 50;
export const SESSION_FIELD_MAX = 5000;
export const DFV_CONTEXT_MIN = 100;
export const DFV_CONTEXT_MAX = 3000;
export const COMMENT_MIN = 10;
export const COMMENT_MAX = 2000;
