import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  devIndicators: false,
  output: 'standalone',
  eslint: {
    ignoreDuringBuilds: true, // Désactiver ESLint pendant le build
  },
};

export default nextConfig;
