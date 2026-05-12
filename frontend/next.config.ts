import path from "node:path";

import type { NextConfig } from "next";

const IMMUTABLE_STATIC_CACHE = "public, max-age=31536000, immutable";
const PWA_ASSET_CACHE = "public, max-age=3600, stale-while-revalidate=86400";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.join(__dirname, ".."),
  typedRoutes: true,
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [{ key: "Cache-Control", value: IMMUTABLE_STATIC_CACHE }],
      },
      {
        source: "/icons/:path*",
        headers: [{ key: "Cache-Control", value: IMMUTABLE_STATIC_CACHE }],
      },
      {
        source: "/:asset(logo.svg|favicon.ico|offline.html|sw.js)",
        headers: [{ key: "Cache-Control", value: PWA_ASSET_CACHE }],
      },
      {
        source: "/driver-portal/:path*",
        headers: [{ key: "Cache-Control", value: "no-store, private" }],
      },
      {
        source: "/portal/:path*",
        headers: [{ key: "Cache-Control", value: "no-store, private" }],
      },
      {
        source: "/dashboard/:path*",
        headers: [{ key: "Cache-Control", value: "no-store, private" }],
      },
    ];
  },
};

export default nextConfig;
