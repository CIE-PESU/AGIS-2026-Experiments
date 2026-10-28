import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src")
    }
  },
  server: {
    port: 5176,
    strictPort: true,
    proxy: {
      "/api/v1": {
        target: process.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8004",
        changeOrigin: true
      }
    }
  }
});
