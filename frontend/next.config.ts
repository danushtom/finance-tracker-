import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,

  // Optional escape hatch: `next dev` and `next build` both write to
  // `.next` by default, so building while the dev server is running makes
  // the build fail during "Collecting page data" with a confusing
  // `PageNotFoundError`. Set NEXT_DIST_DIR to build into a separate
  // directory instead of stopping the dev server:
  //
  //     NEXT_DIST_DIR=.next-build npm run build
  //
  // Defaults to the normal `.next`, so nothing changes unless you opt in.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
