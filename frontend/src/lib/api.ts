// Cliente de la API. Todas las rutas son relativas (/api/v1): la aplicación y
// la API comparten origen, así que no hay CORS ni URLs configurables.
//
// El token de acceso vive solo en memoria de esta pestaña. La sesión real es
// una cookie HttpOnly que el navegador envía a /auth/refresh; JavaScript no
// puede leerla.
import type {
  Analisis,
  AnalisisRequest,
  ConfigPublica,
  DecisionRequest,
  Descanso,
  EstadoDescanso,
  Facetas,
  ModelosDisponibles,
  PaginaColaboradores,
  PaginaDescansos,
  Sesion,
  Usuario,
} from "./types";
import { mensajeDeError } from "@/i18n/context";

const BASE = "/api/v1";
export const LLM_KEY_HEADER = "X-LLM-Api-Key";
// Mayor que el plazo del servidor (100 s) y el del proxy (120 s): así el
// usuario recibe siempre el error explicado por la API y no un corte local.
const ANALISIS_TIMEOUT_MS = 130_000;

export interface DetalleError {
  campo: string;
  mensaje: string;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly detalles: DetalleError[] = [],
    readonly retryAfter?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** La petición pudo haberse completado en el servidor aunque aquí falló. */
  get resultadoIncierto(): boolean {
    return this.status === 0 || this.status === 502 || this.status === 504;
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  const retryAfter = Number(res.headers.get("Retry-After")) || undefined;
  try {
    const body: unknown = await res.json();
    const error = (body as { error?: Record<string, unknown> } | null)?.error;
    if (error && typeof error.code === "string" && typeof error.message === "string") {
      const detalles = Array.isArray(error.detalles) ? (error.detalles as DetalleError[]) : [];
      const mensaje = mensajeDeError(error.code, error.message, res.status);
      return new ApiError(res.status, error.code, mensaje, detalles, retryAfter);
    }
  } catch {
    // Respuesta sin JSON: la generó el proxy, no la API.
  }
  return new ApiError(res.status, "error", mensajeDeError("error", null, res.status), [], retryAfter);
}

let accessToken: string | null = null;
let refreshEnCurso: Promise<Sesion | null> | null = null;
let alPerderSesion: (() => void) | null = null;

/** Lo registra el proveedor de sesión para reaccionar cuando la cookie ya no vale. */
export function setAlPerderSesion(callback: (() => void) | null): void {
  alPerderSesion = callback;
}

export function clearAccessToken(): void {
  accessToken = null;
}

async function fetchSeguro(input: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(input, { credentials: "same-origin", cache: "no-store", ...init });
  } catch (error) {
    const code =
      error instanceof DOMException && error.name === "TimeoutError"
        ? "tiempo_agotado"
        : error instanceof DOMException && error.name === "AbortError"
          ? "cancelada"
          : "sin_conexion";
    throw new ApiError(0, code, mensajeDeError(code, null));
  }
}

/**
 * Renueva el token de acceso con la cookie de sesión. Devuelve null si no hay
 * sesión válida. Si varias peticiones lo piden a la vez, comparten una sola
 * llamada.
 */
export function refreshSession(): Promise<Sesion | null> {
  refreshEnCurso ??= (async () => {
    const res = await fetchSeguro(`${BASE}/auth/refresh`, { method: "POST" });
    if (res.ok) {
      const sesion = (await res.json()) as Sesion;
      accessToken = sesion.access_token;
      return sesion;
    }
    if (res.status === 401 || res.status === 403) {
      accessToken = null;
      return null;
    }
    throw await toApiError(res);
  })().finally(() => {
    refreshEnCurso = null;
  });
  return refreshEnCurso;
}

interface Opciones {
  method?: string;
  json?: unknown;
  body?: FormData;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

async function send(path: string, opciones: Opciones = {}, reintentar = true): Promise<Response> {
  const headers = new Headers(opciones.headers);
  if (opciones.json !== undefined) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const res = await fetchSeguro(`${BASE}${path}`, {
    method: opciones.method ?? "GET",
    headers,
    body: opciones.json !== undefined ? JSON.stringify(opciones.json) : opciones.body,
    signal: opciones.signal,
  });
  if (res.ok) return res;

  const error = await toApiError(res);
  // 401 es siempre de la sesión propia: los problemas con la clave de IA
  // llegan como 400/402/429, nunca como 401.
  if (res.status === 401 && reintentar) {
    const sesion = await refreshSession().catch(() => null);
    if (sesion) return send(path, opciones, false);
    alPerderSesion?.();
  }
  throw error;
}

async function json<T>(path: string, opciones?: Opciones): Promise<T> {
  return (await (await send(path, opciones)).json()) as T;
}

function query(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [clave, valor] of Object.entries(params)) {
    if (valor !== undefined && valor !== null && valor !== "") search.set(clave, String(valor));
  }
  const texto = search.toString();
  return texto ? `?${texto}` : "";
}

export type VarianteEjemplo = "valido" | "observado" | "otra-persona" | "citt";

export interface FiltrosDescansos {
  estado?: EstadoDescanso;
  dni?: string;
  sede?: string;
  limit?: number;
  offset?: number;
}

export interface FiltrosColaboradores {
  q?: string;
  categoria?: string;
  area_operacion?: string;
  tipo_contrato?: string;
  sexo?: string;
  activo?: boolean;
  limit?: number;
  offset?: number;
}

export const api = {
  config: () => json<ConfigPublica>("/config"),

  /** Inicia sesión aceptando la versión vigente de los términos (se registra en el servidor). */
  async login(dni: string, password: string, terminosVersion: string): Promise<Sesion> {
    // Sin reintento con refresh: un 401 aquí significa credenciales incorrectas.
    const cuerpo = { dni, password, acepta_terminos: true, terminos_version: terminosVersion };
    const sesion = (await (
      await send("/auth/login", { method: "POST", json: cuerpo }, false)
    ).json()) as Sesion;
    accessToken = sesion.access_token;
    return sesion;
  },

  async logout(): Promise<void> {
    try {
      await send("/auth/logout", { method: "POST" }, false);
    } finally {
      accessToken = null;
    }
  },

  me: () => json<Usuario>("/auth/me"),

  misDescansos: (filtros: FiltrosDescansos = {}) =>
    json<PaginaDescansos>(`/me/descansos${query({ ...filtros })}`),

  descansos: (filtros: FiltrosDescansos = {}) =>
    json<PaginaDescansos>(`/descansos${query({ ...filtros })}`),

  descanso: (id: string) => json<Descanso>(`/descansos/${id}`),

  crearDescanso(archivo: File, sede: string): Promise<Descanso> {
    const form = new FormData();
    form.set("archivo", archivo);
    if (sede.trim()) form.set("sede", sede.trim());
    return json<Descanso>("/descansos", { method: "POST", body: form });
  },

  async eliminarDescanso(id: string): Promise<void> {
    await send(`/descansos/${id}`, { method: "DELETE" });
  },

  decidir: (id: string, decision: DecisionRequest) =>
    json<Descanso>(`/descansos/${id}/decision`, { method: "POST", json: decision }),

  /**
   * Analiza el documento con la clave de IA del usuario. La clave viaja solo
   * en la cabecera de esta petición; el servidor la usa una vez y la descarta.
   */
  analizar: (id: string, peticion: AnalisisRequest, clave: string) =>
    json<Analisis>(`/descansos/${id}/analisis`, {
      method: "POST",
      json: peticion,
      headers: { [LLM_KEY_HEADER]: clave },
      signal: AbortSignal.timeout(ANALISIS_TIMEOUT_MS),
    }),

  historialAnalisis: (id: string) => json<Analisis[]>(`/descansos/${id}/analisis`),

  /**
   * Comprueba la clave y lista los modelos que ofrece. Como en el análisis, la
   * clave viaja solo en la cabecera de esta petición y no se guarda.
   */
  modelosDisponibles: (proveedor: string, clave: string) =>
    json<ModelosDisponibles>("/llm/modelos", {
      method: "POST",
      json: { proveedor },
      headers: { [LLM_KEY_HEADER]: clave },
    }),

  /** Certificado ficticio con los datos del propio usuario (solo en modo demo). */
  certificadoEjemplo: async (variante: VarianteEjemplo): Promise<Blob> =>
    (await send(`/demo/certificados/${variante}`)).blob(),

  /** Página del documento re-codificada por el servidor (JPEG sin metadatos). */
  pagina: async (id: string, numero: number, signal?: AbortSignal): Promise<Blob> =>
    (await send(`/descansos/${id}/paginas/${numero}`, { signal })).blob(),

  /** La imagen guardada (re-codificada por el servidor). */
  imagen: async (id: string): Promise<Blob> => (await send(`/descansos/${id}/archivo`)).blob(),

  colaboradores: (filtros: FiltrosColaboradores = {}) =>
    json<PaginaColaboradores>(`/colaboradores${query({ ...filtros })}`),

  facetas: () => json<Facetas>("/colaboradores/facetas"),
};


