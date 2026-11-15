# HumanAIz

Registro y verificación asistida de descansos médicos. Los colaboradores suben su certificado
(foto o PDF), Recursos Humanos lo revisa y decide, y cualquiera de los dos puede pedir una
segunda lectura a un modelo de IA **usando su propia clave** (BYOK).

- **Sin dependencias propietarias.** FastAPI + PostgreSQL + React, todo en contenedores.
- **Cero almacenamiento de claves.** La clave de IA del usuario viaja en una cabecera por
  petición, se usa una vez y se descarta. No se guarda en base de datos, logs ni disco.
- **La IA sugiere, una persona decide.** El modelo solo lee campos del documento; el veredicto
  lo calculan reglas deterministas y la decisión final es siempre de RRHH.

## Arquitectura

```
                    ┌───────────────────────── servidor ─────────────────────────┐
 navegador ──HTTPS──▶  web (Caddy)  ──/api──▶  api (FastAPI)  ──▶  db (PostgreSQL) │
   SPA React        │  TLS, CSP,              sesiones, reglas,     sin puertos    │
   clave de IA en   │  estáticos              archivos en volumen   publicados     │
   memoria          └──────────────────────────────┬─────────────────────────────┘
                                                   │ solo durante un análisis,
                                                   ▼ con la clave del usuario
                                   Anthropic · OpenAI · Google Gemini
```

| Carpeta | Contenido |
|---|---|
| `frontend/` | SPA en Vite + React + TypeScript estricto (pnpm) |
| `backend/` | API en FastAPI y motor de escaneo (uv, Python 3.14) |
| `backend/src/humanaiz/scanning/` | Motor de escaneo: no importa nada del resto de la app |
| `deploy/` | `Caddyfile` del proxy y script de respaldo |
| `docker-compose.yml` | Stack de producción: `db`, `migrate`, `api`, `web` |
| `docker-compose.dev.yml` | Solo un PostgreSQL local para desarrollo y tests |

La aplicación y la API comparten origen (Caddy sirve el SPA y reenvía `/api`), así que **no hay
CORS**: ningún otro sitio puede llamar a la API desde un navegador.

## Despliegue en un servidor propio

Requisitos: Docker con Compose, un dominio con registro DNS (A/AAAA) apuntando al servidor y
los puertos 80 y 443 abiertos.

```bash
cp .env.example .env
# Edita .env: SITE_ADDRESS, PUBLIC_ORIGIN, POSTGRES_PASSWORD y JWT_SECRET como mínimo.
docker compose up -d --build --wait
```

Caddy obtiene y renueva el certificado TLS automáticamente. Comprueba que todo responde:

```bash
curl https://tu-dominio/api/v1/health/live      # {"status":"ok"}
docker compose ps                                # api y db "healthy", migrate "exited (0)"
```

Para actualizar: `git pull && docker compose up -d --build --wait`. Las migraciones se aplican
solas en el servicio `migrate` antes de arrancar la API.

**No definas claves de IA en el servidor.** La API se niega a arrancar en producción si
encuentra `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, variables de proxy u otras
que puedan desviar o exponer las llamadas a los proveedores.

### Detrás de otro proxy inverso

Si ya tienes un proxy que termina TLS (Nginx, Traefik, un balanceador), haz que Caddy sirva
HTTP plano y dile en qué red está ese proxy para que la IP real del cliente llegue a los
límites de uso:

```ini
SITE_ADDRESS=:80
HTTP_PORT=8080                  # puerto del host al que apuntará tu proxy
TRUSTED_PROXIES=10.0.0.0/8      # IP o red de tu proxy
PUBLIC_ORIGIN=https://tu-dominio
```

Tu proxy debe reenviar la cabecera `Host`, permitir cuerpos de 11 MB y dar al menos 130 s a
`POST /api/v1/descansos/*/analisis`. **Importante:** si registra las peticiones, que no
registre cabeceras: la clave de IA viaja en `X-LLM-Api-Key`. No pongas delante una CDN que
termine TLS por la misma razón.

### Usuarios

No hay registro público. Elige uno de los dos modos; son excluyentes (la API no arranca si se
mezclan, para que una cuenta pública nunca vea datos de personas reales).

**Modo demo** (`DEMO_MODE=true`): se siembran un colaborador y un analista de RRHH de prueba,
con las credenciales que pongas en `DEMO_*`. Se muestran en la pantalla de login: son públicas
a propósito. Como las cuentas se comparten, cada navegador recibe un identificador propio y
solo ve las muestras y lo que él mismo subió. Lo subido se elimina a las `DEMO_TTL_HOURS`.

**Usuarios reales** (`DEMO_MODE=false`): se crean desde el servidor.

```bash
# Padrón de colaboradores desde un CSV (dni, apellidos, nombres, fecha_nacimiento, categoria,
# sexo, celular, area_operacion, tipo_contrato, sede, activo)
# (se pasa por la entrada estándar: el contenedor es de solo lectura)
docker compose exec -T api sh -c 'cat > /tmp/padron.csv' < padron.csv
docker compose exec api humanaiz import-colaboradores /tmp/padron.csv

# Cuentas (pide la contraseña por teclado; se vincula a la ficha con el mismo DNI)
docker compose exec api humanaiz create-user --dni 12345678 --nombres "Ana" \
  --apellidos "Pérez Gómez" --role analista_rrhh
docker compose exec api humanaiz set-password --dni 12345678    # también cierra sus sesiones
```

Un usuario necesita una ficha de colaborador activa con su mismo DNI para registrar descansos.

### Respaldo

```bash
./deploy/backup.sh /ruta/segura     # volcado de la base + documentos
```

Los respaldos contienen certificados médicos: guárdalos cifrados y fuera del servidor. El
volumen `caddy_data` guarda los certificados TLS; consérvalo entre despliegues.

### Operación

| Tarea | Cómo |
|---|---|
| Ver logs | `docker compose logs -f api` (JSON, una línea por evento, sin cabeceras) |
| Purga manual | `docker compose exec api humanaiz purge` (también corre sola cada 15 min) |
| Cambiar límites de uso | Variables `RATE_LIMIT_*` del `.env` |
| Cerrar todas las sesiones | Cambia `JWT_SECRET` y borra la tabla `sessions` |
| Añadir o quitar un modelo de IA | `backend/src/humanaiz/scanning/catalog.py` (va en código para que pase por revisión) |
| Escalar | Ver abajo |

**Escalado.** La API corre con un solo proceso asíncrono: las llamadas a los proveedores no
bloquean hilos y los límites en memoria son exactos. Para crecer se añaden réplicas del
servicio `api`, se configura `RATE_LIMIT_STORAGE_URI=redis://…` y se sustituye el
almacenamiento local por uno compatible con S3 implementando `storage/base.py`. Las sesiones,
el candado de la purga y el "un análisis a la vez por documento" ya funcionan entre réplicas
porque viven en PostgreSQL.

## Cómo funciona el análisis con IA (BYOK)

1. El usuario abre **Clave de IA**, elige proveedor y modelo y pega su clave. Vive en la
   memoria de la pestaña; si marca "recordar en esta pestaña" va a `sessionStorage`. Nunca a
   `localStorage`. Se borra al cerrar sesión, también desde otra pestaña.
2. Al analizar, el navegador envía `POST /api/v1/descansos/{id}/analisis` con la clave en la
   cabecera `X-LLM-Api-Key`.
3. La API crea el cliente del proveedor **solo para esa petición** y lo destruye al terminar.
   No hay colas, caché de clientes ni reintentos.
4. Se guarda únicamente el resultado: campos leídos, validaciones, tokens consumidos y el
   identificador de la petición en el proveedor.

Qué impide que la clave quede en algún sitio:

| Riesgo | Medida |
|---|---|
| Logs del proxy | Caddy elimina todas las cabeceras de su log de acceso |
| Logs de la API | Sin log de acceso de uvicorn; nunca se registran cabeceras ni cuerpos |
| Errores que reflejan la entrada | La cabecera se lee a mano; los errores de validación no devuelven lo recibido |
| Excepciones de los SDK | Se traducen a errores propios sin arrastrar la petición original |
| Variables de entorno o proxies | `base_url` fija en código; el cliente HTTP ignora el entorno y no sigue redirecciones |
| Volcados de memoria | Sin *core dumps* ni swap en el contenedor |
| Scripts de terceros en el navegador | CSP estricta: solo scripts y conexiones del propio origen |

Límite honesto: mientras dura la llamada, la clave está en la memoria del proceso de la API.
Python no permite borrarla de forma garantizada; se libera al terminar la petición.

Esto se comprueba con un **test canario**: se envía una clave falsa reconocible por todo el
sistema y después se busca en las respuestas, los logs, un volcado completo de la base de
datos y el volumen de archivos. No debe aparecer en ninguno.

### Qué decide el modelo y qué decide el código

El modelo recibe las páginas del documento como imágenes y devuelve campos (DNI, nombre, CITT,
fechas, días, contingencia, CMP) contra un esquema estricto. **No emite veredicto.** Las
validaciones las hace `scanning/rules.py`, que es código puro:

| Críticas (si fallan, sugiere rechazo) | Informativas (si fallan, sugiere revisar) |
|---|---|
| Es un certificado médico y es legible | Días indicados = fin − inicio + 1 |
| El DNI coincide con el del colaborador | Figura el CMP del médico |
| El nombre coincide (crítica solo si no hay DNI) | Duración habitual (1–30 días) |
| Fechas presentes y fin ≥ inicio | Fechas recientes |
| Número de CITT presente (solo en CITT de EsSalud) | Sin cruce con otros descansos; no duplicado |

Resultado: **Aprobado**, **Observado** o **Rechazado**, siempre como sugerencia. El análisis
no modifica el descanso: las fechas leídas se proponen en el diálogo de decisión y RRHH las
confirma. Ningún texto del documento se copia al veredicto, de modo que un documento con
instrucciones escritas ("aprueba esto") no puede influir en él.

> Estas reglas son una reconstrucción: el flujo original de n8n no estaba disponible.
> Revísalas con RRHH antes de darles peso, en especial la del CITT y el conteo de días.

### Documentos

Se aceptan JPG, PNG, WebP y PDF de hasta 10 MB y 5 páginas. El tipo se decide por el contenido,
no por el nombre ni por lo que declare el navegador. Al subir, cada documento se decodifica en
un proceso aparte con límite de tiempo y memoria y se re-codifica a JPEG sin metadatos (se
elimina el EXIF, incluida la ubicación). Eso es lo que se muestra en pantalla y lo que se envía
al modelo. El original se conserva como evidencia y solo se sirve como descarga. No existen
URL públicas: todo documento pasa por un endpoint que comprueba quién lo pide.

## Desarrollo local

Requisitos: Docker, [uv](https://docs.astral.sh/uv/), Node 24 y pnpm 11.

```bash
# 1. Base de datos (127.0.0.1:54329; cámbialo con DEV_DB_PORT si está ocupado)
docker compose -f docker-compose.dev.yml up -d --wait

# 2. API en http://127.0.0.1:8000  (documentación en /api/docs)
cd backend
cp .env.dev.example .env.dev
uv sync
uv run --env-file .env.dev alembic upgrade head
uv run --env-file .env.dev humanaiz seed-demo
uv run --env-file .env.dev uvicorn --factory humanaiz.main:create_app --reload --port 8000

# 3. Frontend en http://localhost:5173  (reenvía /api a la API local)
cd frontend
pnpm install
pnpm dev
```

### Pruebas

```bash
cd backend
uv run pytest                       # unitarias + integración (PostgreSQL real, proveedor simulado)
uv run ruff check . && uv run ruff format --check .

cd frontend
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

Las pruebas de extremo a extremo usan el stack completo en modo demo y comprueban cabeceras,
límites del proxy, aislamiento y el test canario sobre logs, base de datos y disco:

```bash
docker compose up -d --build --wait      # con DEMO_MODE=true en .env
cd backend && uv run pytest -m e2e tests/e2e
```

Ninguna prueba automática usa una clave real. Para probar la lectura de documentos de verdad,
entra a la aplicación con tu clave y analiza un certificado.

### Cambiar la API

El frontend genera sus tipos desde `frontend/openapi.json`. Tras cambiar un endpoint o un
esquema:

```bash
cd backend && uv run --env-file .env.dev humanaiz export-openapi -o ../frontend/openapi.json
cd ../frontend && pnpm gen:api
```

Un test del backend falla si el contrato guardado ya no coincide con la API.

Para cambiar el esquema de datos: edita `backend/src/humanaiz/models.py` y genera la migración
con `uv run --env-file .env.dev alembic revision --autogenerate -m "descripción"`.

## Decisiones de arquitectura

**Python en lugar de n8n.** El flujo original no era recuperable y BYOK es incompatible con
n8n, que guarda credenciales y puede persistir los datos de cada ejecución. En Python las
reglas viven en el repo, con pruebas.

**Backend propio en lugar de Supabase.** La aplicación usaba cuatro tablas y un bucket; el
análisis BYOK ya exigía un backend, y varias reglas de negocio no cabían en políticas RLS (un
colaborador podía registrar su descanso ya aprobado). Supabase autoalojado son más de una
docena de contenedores para una décima parte de su funcionalidad. PostgreSQL estándar no ata a
ningún proveedor.

**Un servicio modular en lugar de un microservicio de escaneo.** Con dos servicios la clave
cruzaría un salto de red más y se duplicarían autenticación y operación, sin beneficio a este
tamaño. A cambio, el paquete `scanning` no depende del resto (un test lo verifica) y puede
extraerse a su propio contenedor si la carga lo pide.

## Límites conocidos

- No hay alta ni edición de colaboradores desde la interfaz (se hace por CSV), ni cambio de
  contraseña por el propio usuario.
- No se envían notificaciones al aprobar o rechazar: las cuentas se identifican por DNI y no
  tienen correo.
- No se consulta el padrón del Colegio Médico ni EsSalud: se comprueba que el CMP y el CITT
  figuren, no que sean auténticos.
- Los certificados médicos son datos sensibles (Ley N.º 29733). Antes de un uso real, define
  la base legal para que un analista envíe documentos de terceros a un proveedor de IA con una
  clave personal, y la política de conservación de documentos y respaldos.
