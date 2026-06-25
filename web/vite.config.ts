import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

/** 开发服所有响应统一加安全/缓存头（避免 Issues 面板误报） */
function devSecurityHeaders(): Plugin {
  return {
    name: "dev-security-headers",
    configureServer(server) {
      server.middlewares.use((_req, res, next) => {
        res.setHeader("X-Content-Type-Options", "nosniff");
        res.setHeader("Cache-Control", "no-store");
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), devSecurityHeaders()],
  appType: "spa",
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    headers: {
      "X-Content-Type-Options": "nosniff",
      "Cache-Control": "no-store",
    },
    proxy: {
      "/api": "http://127.0.0.1:8765",
      "/ws": { target: "ws://127.0.0.1:8765", ws: true },
      "/screenshots": "http://127.0.0.1:8765",
      "/health": "http://127.0.0.1:8765",
    },
  },
});
