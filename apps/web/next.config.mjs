/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@ngti/contracts"],
  // NOTE: the managed deploy (Path 3, Vercel) builds Next.js natively and does
  // NOT need `output: "standalone"`. The web Dockerfile (Path 2, single-VM
  // compose) DOES need it — add `output: "standalone"` here when building that
  // image. It's intentionally left off by default because the standalone step
  // creates symlinks that fail on Windows (`EPERM`) without Developer Mode, and
  // would break local `pnpm build`. The Linux Docker build handles it fine.
};

export default nextConfig;
