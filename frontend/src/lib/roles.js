// Role names (same as dcp.roles on the API) and what each role can open.

export const SYSTEM_ADMIN = 'System Administrator';
export const COMPANY_ADMIN = 'Company Administrator';

export const isSystemAdmin = (user) => user?.role === SYSTEM_ADMIN;
export const isCompanyAdmin = (user) => user?.role === COMPANY_ADMIN;

/** Pages a system administrator uses; the tenant pages (dealers, sales, ...) have no data for them. */
export const SYSTEM_ADMIN_PATHS = ['/admin', '/profile', '/settings'];

/** Where a user lands after signing in or opening a page their role doesn't use. */
export function homePathFor(user) {
  return isSystemAdmin(user) ? '/admin/companies' : '/dealers';
}

/** Whether the signed-in user may open this path (the API enforces the same rules). */
export function canOpenPath(user, pathname) {
  const under = (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`);
  if (isSystemAdmin(user)) return SYSTEM_ADMIN_PATHS.some(under);
  if (under('/admin')) return false;
  if (under('/users')) return isCompanyAdmin(user);
  return true;
}
