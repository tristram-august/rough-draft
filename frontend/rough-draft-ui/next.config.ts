import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "static.www.nfl.com",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
