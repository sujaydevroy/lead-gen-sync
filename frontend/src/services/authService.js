// Authentication service backed by the API's cookie sessions (/api/v1/auth/*).
// The httpOnly cookies are the source of truth; the profile cached in browser storage is only
// used to paint the header instantly while the session is being confirmed.
import { api, markSignedIn } from '@/lib/apiClient';

const SESSION_KEY = 'dcp.session';

const storages = () => {
  if (typeof window === 'undefined') return [];
  const list = [];
  try { list.push(window.sessionStorage); } catch { /* unavailable */ }
  try { list.push(window.localStorage); } catch { /* unavailable */ }
  return list;
};

function readJson(storage, key) {
  try {
    const raw = storage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function clearStoredSession() {
  storages().forEach((s) => {
    try { s.removeItem(SESSION_KEY); } catch { /* ignore */ }
  });
}

function persistSession(session, remember) {
  const [sessionStore, localStore] = storages();
  clearStoredSession();
  try {
    (remember ? localStore : sessionStore)?.setItem(SESSION_KEY, JSON.stringify({ ...session, remember }));
  } catch {
    /* storage full / blocked — the cookies are still authoritative */
  }
}

function rememberedFlag() {
  const local = storages()[1];
  return Boolean(local && readJson(local, SESSION_KEY));
}

const authService = {
  /** @returns {Promise<import('@/types/user').Session>} */
  async login({ email, password, remember }) {
    const session = await api.post('/auth/login', { email, password, remember: Boolean(remember) });
    markSignedIn();
    persistSession(session, remember);
    return session;
  },

  async logout() {
    try {
      await api.post('/auth/logout');
    } finally {
      clearStoredSession();
    }
  },

  /** Cached profile for instant first paint (validated afterwards by getSession). */
  getStoredSession() {
    for (const storage of storages()) {
      const session = readJson(storage, SESSION_KEY);
      if (session?.user && (!session.expiresAt || new Date(session.expiresAt).getTime() > Date.now())) return session;
    }
    return null;
  },

  /** Confirms the session with the server (refreshing it if needed). Returns null when signed out. */
  async getSession() {
    const session = await api.get('/auth/session');
    if (!session?.user) {
      clearStoredSession();
      return null;
    }
    persistSession(session, rememberedFlag());
    return session;
  },

  clearStoredSession,

  async requestPasswordReset(email) {
    await api.post('/auth/forgot-password', { email });
    return { email };
  },

  async resetPassword(token, newPassword) {
    return api.post('/auth/reset-password', { token, newPassword });
  },

  /** PATCH /users/me — returns the updated user. */
  async updateProfile(_user, values) {
    const user = await api.patch('/users/me', values);
    const stored = authService.getStoredSession();
    if (stored) persistSession({ ...stored, user }, stored.remember);
    return user;
  },

  /** POST /users/me/password — change your own password (e.g. a temporary one set by an administrator). */
  changePassword(currentPassword, newPassword) {
    return api.post('/users/me/password', { currentPassword, newPassword });
  },
};

export default authService;
