import { NextResponse } from 'next/server';

// Cookies set by the API at sign-in. dcp_access (15 min) and dcp_csrf (lives as long as the
// refresh session) are sent with page requests; the refresh cookie is scoped to /api/v1/auth.
// Their presence is only a hint for routing — the API validates every request, and the client
// AuthGuard sends the user to /login if the session turns out to be invalid.
const SIGNED_IN_HINT_COOKIES = ['dcp_access', 'dcp_csrf'];

const PROTECTED_PREFIXES = [
  '/dashboard',
  '/dealers',
  '/communications',
  '/sales',
  '/forecast',
  '/company',
  '/profile',
  '/settings',
  '/users',
  '/admin',
];

export function proxy(request) {
  const { pathname, search } = request.nextUrl;
  const maybeSignedIn = SIGNED_IN_HINT_COOKIES.some((name) => request.cookies.has(name));

  const isProtected = PROTECTED_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (isProtected && !maybeSignedIn) {
    const url = new URL('/login', request.url);
    url.searchParams.set('next', `${pathname}${search}`);
    return NextResponse.redirect(url);
  }
  if (pathname === '/') {
    return NextResponse.redirect(new URL(maybeSignedIn ? '/dealers' : '/login', request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|samples|favicon.ico).*)'],
};
