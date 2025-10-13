import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite configuration tuned for:
 * - Production chunk splitting (explicit vendor groups)
 * - Deterministic hashing & long‑term caching
 * - Preview/server host binding for container / cloud
 * - Optional source map toggle via env (set BUILD_SOURCEMAP=true)
 *
 * Environment overrides:
 *  - VITE_API_URL consumed within code (see api.ts)
 *
 * Notes:
 * - We intentionally rely on Vite/esbuild default minifier (fast, no extra dep).
 * - BUILD_SOURCEMAP=true can be set locally (avoid enabling in prod unless debugging).
 */
export default defineConfig(() => {
  const enableSourceMap = process.env.BUILD_SOURCEMAP === "true";

  return {
    plugins: [react()],
    build: {
      outDir: "dist",
      sourcemap: enableSourceMap,
      target: "es2019",
      cssCodeSplit: true,
      // Removed custom terser config to avoid extra dependency; esbuild is sufficient here.
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
      host: true, // Allows access from LAN / containers (not used by Vercel build output)
      port: 5173
    },
    preview: {
      host: true,
      port: 4173
    }
  };
});
