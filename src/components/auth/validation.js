export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Only allow same-site relative redirects after login. */
export function safeRedirect(target, fallback = '/dealers') {
  if (!target || typeof target !== 'string') return fallback;
  if (!target.startsWith('/') || target.startsWith('//') || target.startsWith('/login')) return fallback;
  return target;
}
