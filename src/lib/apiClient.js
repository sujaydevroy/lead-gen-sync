// HTTP client for the backend API (FastAPI, /api/v1). Requests go to the same origin and are
// forwarded to the API by the rewrite in next.config.mjs, so auth cookies stay first-party.
//
// - Sends cookies, plus the X-CSRF-Token header (double-submit) on state-changing requests.
// - On 401 it refreshes the session once (POST /auth/refresh) and retries; if that fails it
//   emits an "auth:expired" event so the app can send the user back to the login page.
// - Errors are thrown as ApiError with the server's {"message"} and the HTTP status.

export const API_BASE = '/api/v1';
const CSRF_COOKIE = 'dcp_csrf';
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);
const NO_REFRESH_PATHS = ['/auth/login', '/auth/refresh', '/auth/logout', '/auth/session', '/auth/token'];

export class ApiError extends Error {
  constructor(message, status = 500, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

// Developer options (Settings → Developer options) to exercise loading / error states.
const devOptions = { simulateErrors: false, extraLatencyMs: 0 };

export function configureDevNetwork(partial) {
  Object.assign(devOptions, partial);
}

const authListeners = new Set();
/** Subscribe to "session expired" events. Returns an unsubscribe function. */
export function onAuthExpired(listener) {
  authListeners.add(listener);
  return () => authListeners.delete(listener);
}

// Incremented on every sign-in, so a 401 from a request that started before the latest sign-in
// (e.g. with a stale cached session) can't sign the user out again.
let authEpoch = 0;
export function markSignedIn() {
  authEpoch += 1;
}

function readCookie(name) {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.split('; ').find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

/** Build a query string; arrays become repeated parameters (?countries=India&countries=Japan). */
export function toQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else search.append(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : '';
}

let refreshing = null;
function refreshSession() {
  // Concurrent 401s share one refresh request.
  refreshing ??= fetch(`${API_BASE}/auth/refresh`, { method: 'POST', credentials: 'same-origin' })
    .then((response) => response.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * @param {string} path      path below /api/v1, e.g. "/dealers"
 * @param {{ method?: string, query?: object, json?: any, formData?: FormData, signal?: AbortSignal }} [options]
 */
export async function apiRequest(path, { method = 'GET', query, json, formData, signal } = {}, retried = false) {
  const epoch = authEpoch;
  if (devOptions.extraLatencyMs) await wait(devOptions.extraLatencyMs);
  if (devOptions.simulateErrors && !path.startsWith('/auth/')) {
    throw new ApiError('Simulated network error (Settings → Developer options).', 503);
  }

  const headers = { Accept: 'application/json' };
  if (!SAFE_METHODS.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers['X-CSRF-Token'] = csrf;
  }
  let body;
  if (formData) body = formData;
  else if (json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}${toQuery(query)}`, { method, headers, body, credentials: 'same-origin', signal });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError('Cannot reach the server. Check that the API is running and try again.', 0);
  }

  if (response.status === 401 && !retried && !NO_REFRESH_PATHS.includes(path)) {
    if (await refreshSession()) return apiRequest(path, { method, query, json, formData, signal }, true);
    if (epoch === authEpoch) authListeners.forEach((listener) => listener());
  }

  if (response.status === 204) return null;
  const isJson = (response.headers.get('content-type') || '').includes('application/json');
  const data = isJson ? await response.json().catch(() => null) : null;
  if (!response.ok) {
    const fallback = response.status >= 500 ? 'The server could not complete the request.' : 'Request failed.';
    throw new ApiError(data?.message || fallback, response.status, data?.errors);
  }
  return data;
}

export const api = {
  get: (path, query, options) => apiRequest(path, { ...options, query }),
  post: (path, json, options) => apiRequest(path, { ...options, method: 'POST', json }),
  put: (path, json, options) => apiRequest(path, { ...options, method: 'PUT', json }),
  patch: (path, json, options) => apiRequest(path, { ...options, method: 'PATCH', json }),
  delete: (path, options) => apiRequest(path, { ...options, method: 'DELETE' }),
  upload: (path, formData, options) => apiRequest(path, { ...options, method: 'POST', formData }),
};
