import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src")
    }
  },
  server: {
    port: 5167,
    strictPort: true,
    proxy: {
      "/api/v1": {
        target: process.env.VITE_BACKEND_URL ?? "http://localhost:8008",
        changeOrigin: true
      }
    }
  }
});
