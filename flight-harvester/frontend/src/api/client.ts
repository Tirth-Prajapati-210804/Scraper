import axios from "axios";

// In Docker, VITE_API_BASE_URL is "" so axios uses relative URLs (proxied by nginx).
// In local dev it is "http://localhost:8000" (set in frontend/.env).
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "token";

function readToken(): string | null {
  return sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = readToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (
      err.response?.status === 401 &&
      window.location.pathname !== "/login"
    ) {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      window.location.href = "/login";
    }
    return Promise.reject(err);
  },
);

/** Extract a human-readable message from an axios error response. */
export function getErrorMessage(err: unknown, fallback = "Something went wrong"): string {
  if (err && typeof err === "object" && "response" in err) {
    const detail = (err as { response?: { data?: { detail?: string } } })
      .response?.data?.detail;
    if (detail) return detail;
  }
  return fallback;
}
