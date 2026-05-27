import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  // Do NOT add output: "standalone" — Vercel handles its own output format.

  compress: true,               // gzip at the Next.js layer (CDN edge caches compressed)
  poweredByHeader: false,       // remove X-Powered-By header (minor security + size)

  experimental: {
    optimizePackageImports: [
      "lucide-react",           // tree-shake icons — only bundle what's imported
      "recharts",
    ],
  },
}

export default nextConfig
