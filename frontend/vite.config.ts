import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const PROXIED_PREFIXES = [
  "/auth",
  "/health",
  "/projects",
  "/uploads",
  "/ocr",
  "/pages",
  "/segments",
  "/glossary",
  "/entities",
  "/conflicts",
  "/translation-jobs",
  "/ocr-export",
  "/exports",
  "/admin",
  "/history",
  "/morphology",
] as const;

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(
      PROXIED_PREFIXES.map((p) => [
        p,
        { target: BACKEND, changeOrigin: true, secure: false },
      ]),
    ),
  },
});
