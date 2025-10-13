import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

/**
 * GitHub Pages project deployment note:
 * Vite injects import.meta.env.BASE_URL matching the configured `base` in vite.config.ts.
 * For project pages (e.g. /smartdocs-ai/) we set BrowserRouter basename to this value
 * so route matching works when the app is served from a sub-path.
 */
const basename = import.meta.env.BASE_URL || "/";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <App />
    </BrowserRouter>
  </StrictMode>
);
