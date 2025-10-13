import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite configuration tuned for:
 * - Production chunk splitting (explicit vendor groups)
 * - Deterministic hashing & long‑term caching
 * - Preview/server host binding for container / cloud
 * - Optional source map toggle via env (set BUILD_SOURCEMAP=true)
 * - GitHub Pages support via dynamic base path
 *
 * Environment overrides:
 *  - VITE_API_URL consumed within code (see api.ts)
 *
 * Notes:
 * - We intentionally rely on Vite/esbuild default minifier (fast, no extra dep).
 * - BUILD_SOURCEMAP=true can be set locally (avoid enabling in prod unless debugging).
 * - For GitHub Pages project sites the app is served under /<repo-name>/.
 *   We derive that automatically, but you can override with GITHUB_PAGES_BASE.
 */
export default defineConfig(() => {
  const enableSourceMap = process.env.BUILD_SOURCEMAP === "true";

  // Derive base path for GitHub Pages project site if not explicitly provided.
  // If deploying to a user/organization root (username.github.io) keep '/'.
  const derivedRepoSegment =
    process.env.GITHUB_REPOSITORY?.split("/")?.[1] || "";
  const defaultPagesBase =
    process.env.GITHUB_PAGES_PROJECT === "true" && derivedRepoSegment
      ? `/${derivedRepoSegment}/`
      : "/";
  const base =
    process.env.GITHUB_PAGES_BASE && process.env.GITHUB_PAGES_BASE.length
      ? process.env.GITHUB_PAGES_BASE
      : defaultPagesBase;

  return {
    base,
    plugins: [react()],
    build: {
      outDir: "dist",
      sourcemap: enableSourceMap,
      target: "es2019",
      cssCodeSplit: true,
      rollupOptions: {
        output: {
          manualChunks: {
            react: ["react", "react-dom"],
            router: ["react-router-dom"],
            markdown: ["react-markdown", "remark-gfm"],
            http: ["axios"]
          },
          chunkFileNames: "assets/[name]-[hash].js",
          entryFileNames: "assets/[name]-[hash].js",
          assetFileNames: "assets/[name]-[hash][extname]"
        }
      }
    },
    server: {
      host: true, // Allows access from LAN / containers (not used by Pages build output)
      port: 5173
    },
    preview: {
      host: true,
      port: 4173
    }
  };
});
