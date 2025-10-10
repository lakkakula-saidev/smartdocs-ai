import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Generate a build/session id at dev server (process) start.
// Each restart of `npm run dev` yields a new id, so persisted dev data
// keyed with this id can be isolated per run and effectively "reset".
const buildId = Date.now().toString(36);

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    __BUILD_ID__: JSON.stringify(buildId)
  }
});
