export const PES_LOGO =
  "https://images.fillout.com/orgid-407996/flowpublicid-anon-zite/widgetid-default/fB5cj8wcBy1vvWnee5A8fk/pasted-image-1782896422944.png";

export const CIE_LOGO =
  "https://images.fillout.com/orgid-407996/flowpublicid-anon-zite/widgetid-default/uEbUMzTUa6gp95qonQK3nf/pasted-image-1782896478033.png";

/** Base URL per docs/api-spec.md §1 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** Session polling interval per docs/backend-arch.md §2.3 */
export const SESSION_POLL_INTERVAL_MS = 5000;

/** Use mock flow responses when backend is unavailable (dev only) */
export const USE_MOCK_FLOWS = import.meta.env.VITE_USE_MOCK_FLOWS !== "false";

export const SESSION_FIELD_MIN = 50;
export const SESSION_FIELD_MAX = 5000;
export const DFV_CONTEXT_MIN = 100;
export const DFV_CONTEXT_MAX = 3000;
export const COMMENT_MIN = 10;
export const COMMENT_MAX = 2000;
