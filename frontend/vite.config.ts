import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// IDMAS 前端开发服务器：/api 代理到 FastAPI 后端（默认 8000）
const apiBase =
  (typeof process !== "undefined" && process.env && process.env.IDMAS_API_BASE) ||
  "http://localhost:8080";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: apiBase, changeOrigin: true },
    },
  },
});
