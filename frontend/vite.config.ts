import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

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
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
