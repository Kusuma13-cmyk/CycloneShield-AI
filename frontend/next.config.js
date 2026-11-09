/** @type {import('next').NextConfig} */
const nextConfig = {
  // Output to static export not used — we keep SSR for API proxy support
  reactStrictMode: true,
  env: {
    // The API base URL — in Vercel production this is the same origin.
    // In local dev, point to a local Python dev server or use Next.js rewrites.
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || "",
  },
  async rewrites() {
    // In local dev, proxy /api/* to the local Python server running on port 8000.
    // In Vercel production, /api/* is handled natively by the Python serverless fns.
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/api/:path*",
          destination: `http://localhost:8000/api/:path*`,
        },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
