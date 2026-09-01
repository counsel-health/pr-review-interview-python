/** @type {import('next').NextConfig} */
const nextConfig = {
  /**
   * The REST API lives in the Django backend, not in Next. Proxying
   * /api/:path* keeps the browser-side client (src/utils/api.ts) calling
   * relative URLs, so it needs no knowledge of where the backend runs and
   * requests stay same-origin (no CORS preflight).
   */
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
