import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The browser always calls relative /api URLs — the dev server proxies them to
// the FastAPI backend so no backend origin or secret ever reaches the client.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Accept any Host header so proxied sandbox previews work (the app only
    // serves static assets + /api proxy; tighten in production deploys).
    allowedHosts: true,
    proxy: {
      "/api": {
        target: process.env.API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
