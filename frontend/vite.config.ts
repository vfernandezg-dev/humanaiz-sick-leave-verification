import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// El SPA llama siempre a rutas relativas (/api/v1). En desarrollo Vite las
// reenvía a la API local, así desarrollo y producción son same-origin y no
// hace falta CORS.
export default defineConfig({
  server: {
    port: 8080,
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  build: {
    // Sin mapas de código en producción y con la CSP estricta no hay scripts en línea.
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"],
    restoreMocks: true,
  },
});
