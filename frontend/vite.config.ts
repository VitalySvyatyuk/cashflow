import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// В Docker бэкенд доступен как http://backend:8000, локально — localhost:8000.
const backend = process.env.BACKEND_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Host не меняем: Django сверяет его с Origin (CSRF) и ALLOWED_HOSTS.
    proxy: {
      "/api": { target: backend },
      "/admin": { target: backend },
      "/static": { target: backend },
      "/ws": { target: backend, ws: true },
    },
  },
});
