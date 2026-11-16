# Imagen única (web + API) para plataformas que ejecutan un solo contenedor, como
# Vercel. docker compose usa en cambio backend/Dockerfile y frontend/Dockerfile,
# con Caddy delante; aquí la API sirve también la web (STATIC_DIR) con las mismas
# cabeceras de seguridad, y las imágenes se guardan en la base (no hay disco
# persistente).
ARG PYTHON_VERSION=3.14

# ---------- build del SPA ----------
FROM node:26-slim AS web
RUN npm install --global pnpm@11.28.12
WORKDIR /web
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# ---------- dependencias y paquete de la API ----------
FROM python:${PYTHON_VERSION}-slim AS api
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --frozen --no-dev --no-editable

# ---------- imagen final ----------
FROM python:${PYTHON_VERSION}-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:${PATH}" \
    STATIC_DIR=/app/static \
    STORAGE_BACKEND=database \
    PORT=8000 \
    # La plataforma reescribe X-Forwarded-For con la IP real del cliente y el
    # contenedor solo es accesible a través de ella. Detrás de otro proxy,
    # restringe este valor a su IP.
    FORWARDED_ALLOW_IPS=*

RUN groupadd --gid 10001 app \
 && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=api /app/.venv /app/.venv
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY --from=web /web/dist ./static

USER 10001:10001
EXPOSE 8000

# Antes de servir: migraciones y siembra de la demo, con un candado por si
# arrancan varias instancias a la vez. Un solo worker por instancia.
CMD ["sh", "-c", "humanaiz prepare && exec uvicorn --factory humanaiz.main:create_app --host 0.0.0.0 --port \"$PORT\" --workers 1 --proxy-headers --no-access-log --no-server-header --timeout-graceful-shutdown 130"]
