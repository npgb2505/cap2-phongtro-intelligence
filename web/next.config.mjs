/** @type {import('next').NextConfig} */
const isGithubPages = process.env.GITHUB_PAGES === "true";

const nextConfig = {
  typedRoutes: true,
  output: isGithubPages ? "export" : undefined,
  basePath: isGithubPages ? "/cap2-phongtro-intelligence" : undefined,
  assetPrefix: isGithubPages ? "/cap2-phongtro-intelligence/" : undefined,
  images: {
    unoptimized: true
  }
};

export default nextConfig;
