# HumanAIz

Plataforma de registro y verificación asistida de descansos médicos.

> Refactor en curso hacia un stack propio (FastAPI + PostgreSQL + Docker). La guía
> completa de arquitectura y despliegue se añade al cerrar la migración.

## Estructura

| Carpeta | Contenido |
|---|---|
| `frontend/` | SPA en Vite + React + TypeScript (pnpm) |
| `backend/` | API en FastAPI y motor de escaneo (uv) |
| `deploy/` | Configuración del proxy inverso |

## Desarrollo del frontend

```bash
cd frontend
pnpm install
pnpm dev        # http://localhost:8080
```
