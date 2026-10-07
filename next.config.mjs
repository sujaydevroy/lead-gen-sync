// Where the FastAPI backend runs. Browser calls go to this app's own origin (/api/v1/...) and are
// forwarded here, so the API's httpOnly auth cookies are first-party and no CORS is needed.
// Rewrites are resolved at build time: set API_ORIGIN before `next build` as well as `next dev`.
const API_ORIGIN = (process.env.API_ORIGIN || 'http://localhost:8000').replace(/\/$/, '');

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: '/api/v1/:path*', destination: `${API_ORIGIN}/api/v1/:path*` }];
  },
};

export default nextConfig;
