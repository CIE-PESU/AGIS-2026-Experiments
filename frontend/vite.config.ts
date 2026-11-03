import path from "path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, import.meta.dirname, "VITE_");
  return {
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
          target: env.VITE_BACKEND_URL || "http://127.0.0.1:8008",
          changeOrigin: true
        }
      }
    }
  };
});
