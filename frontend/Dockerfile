# syntax=docker/dockerfile:1
# Contexto de build: la raíz del repo (necesita frontend/ y deploy/Caddyfile).

# ---------- build del SPA ----------
FROM node:24-slim AS build
RUN npm install --global pnpm@11.1.2
WORKDIR /app
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile
COPY frontend/ ./
# El SPA llama a rutas relativas (/api/v1): no hay configuración en tiempo de build.
RUN pnpm build

# ---------- proxy inverso + estáticos ----------
FROM caddy:2-alpine AS runtime
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
