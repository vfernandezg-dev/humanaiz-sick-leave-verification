import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, clearAccessToken, refreshSession, setAlPerderSesion } from "./api";

const CLAVE = "sk-ant-clave-de-prueba-0123456789";
const USUARIO = { id: "u1", dni: "12345678", nombres: "Ana", apellidos: "Pérez", role: "colaborador" };

function respuesta(status: number, cuerpo?: unknown, cabeceras: Record<string, string> = {}): Response {
  return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), {
    status,
    headers: { "Content-Type": "application/json", ...cabeceras },
  });
}

const sesion = (token: string) =>
  respuesta(200, { access_token: token, token_type: "bearer", expires_in: 900, usuario: USUARIO });

const sobre = (code: string, message = "mensaje") => ({ error: { code, message } });

interface Llamada {
  url: string;
  method: string;
  headers: Headers;
  body: BodyInit | null | undefined;
}

/** Sustituye `fetch` por una cola de respuestas y registra cada petición. */
function simularFetch(respuestas: (Response | (() => Response | Promise<Response>))[]): Llamada[] {
  const llamadas: Llamada[] = [];
  const cola = [...respuestas];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit = {}) => {
      llamadas.push({
        url,
        method: init.method ?? "GET",
        headers: new Headers(init.headers),
        body: init.body,
      });
      const siguiente = cola.shift();
      if (!siguiente) throw new Error(`fetch inesperado a ${url}`);
      return typeof siguiente === "function" ? siguiente() : siguiente;
    }),
  );
  return llamadas;
}

beforeEach(() => {
  clearAccessToken();
  setAlPerderSesion(null);
  vi.unstubAllGlobals();
});

describe("sesión", () => {
  it("ante un 401 renueva el token y repite la petición una sola vez", async () => {
    const llamadas = simularFetch([
      respuesta(401, sobre("token_expirado")),
      sesion("token-nuevo"),
      respuesta(200, USUARIO),
    ]);
    await expect(api.me()).resolves.toMatchObject({ dni: "12345678" });
    expect(llamadas.map((l) => l.url)).toEqual([
      "/api/v1/auth/me",
      "/api/v1/auth/refresh",
      "/api/v1/auth/me",
    ]);
    expect(llamadas[0]?.headers.has("Authorization")).toBe(false);
    expect(llamadas[2]?.headers.get("Authorization")).toBe("Bearer token-nuevo");
  });

  it("si la cookie ya no vale, avisa de la pérdida de sesión y propaga el error", async () => {
    const alPerder = vi.fn();
    setAlPerderSesion(alPerder);
    simularFetch([respuesta(401, sobre("token_expirado")), respuesta(401, sobre("sesion_invalida"))]);
    await expect(api.me()).rejects.toMatchObject({ status: 401, code: "token_expirado" });
    expect(alPerder).toHaveBeenCalledOnce();
  });

  it("no entra en bucle si el reintento vuelve a dar 401", async () => {
    const llamadas = simularFetch([
      respuesta(401, sobre("token_expirado")),
      sesion("t"),
      respuesta(401, sobre("no_autenticado")),
    ]);
    await expect(api.me()).rejects.toBeInstanceOf(ApiError);
    expect(llamadas).toHaveLength(3);
  });

  it("varias renovaciones simultáneas comparten una sola llamada", async () => {
    let liberar: (r: Response) => void = () => undefined;
    const pendiente = new Promise<Response>((resolve) => {
      liberar = resolve;
    });
    const llamadas = simularFetch([() => pendiente]);
    const a = refreshSession();
    const b = refreshSession();
    liberar(sesion("compartido"));
    expect(await a).toEqual(await b);
    expect(llamadas).toHaveLength(1);
  });

  it("un 401 al iniciar sesión es credenciales incorrectas, sin intento de renovación", async () => {
    const llamadas = simularFetch([
      respuesta(401, sobre("credenciales_invalidas", "DNI o contraseña incorrectos.")),
    ]);
    await expect(api.login("12345678", "mala")).rejects.toMatchObject({
      code: "credenciales_invalidas",
      message: "DNI o contraseña incorrectos.",
    });
    expect(llamadas).toHaveLength(1);
  });

  it("refreshSession devuelve null sin sesión y lanza ante un fallo del servidor", async () => {
    simularFetch([respuesta(401, sobre("sesion_invalida"))]);
    await expect(refreshSession()).resolves.toBeNull();
    simularFetch([respuesta(503)]);
    await expect(refreshSession()).rejects.toMatchObject({ status: 503 });
  });
});

describe("clave de IA", () => {
  it("viaja solo en la cabecera del análisis: ni en la URL ni en el cuerpo", async () => {
    const llamadas = simularFetch([respuesta(201, { id: "a1", estado_documento: "Aprobado" })]);
    await api.analizar("d1", { proveedor: "anthropic", modelo: "claude-opus-5-5" }, CLAVE);
    const [llamada] = llamadas;
    expect(llamada?.url).toBe("/api/v1/descansos/d1/analisis");
    expect(llamada?.headers.get("X-LLM-Api-Key")).toBe(CLAVE);
    expect(llamada?.url).not.toContain(CLAVE);
    expect(String(llamada?.body)).not.toContain(CLAVE);
    expect(JSON.parse(String(llamada?.body))).toEqual({
      proveedor: "anthropic",
      modelo: "claude-opus-5-5",
    });
  });

  it("no se envía en ninguna otra petición", async () => {
    const llamadas = simularFetch([
      respuesta(200, { items: [], total: 0, limit: 50, offset: 0 }),
      respuesta(200, { id: "d1" }),
    ]);
    await api.misDescansos();
    await api.descanso("d1");
    for (const llamada of llamadas) expect(llamada.headers.has("X-LLM-Api-Key")).toBe(false);
  });

  it("un rechazo de la clave llega como 400 y no cierra la sesión", async () => {
    const alPerder = vi.fn();
    setAlPerderSesion(alPerder);
    const llamadas = simularFetch([respuesta(400, sobre("llm_clave_invalida", "Clave rechazada."))]);
    await expect(api.analizar("d1", { proveedor: "openai" }, CLAVE)).rejects.toMatchObject({
      status: 400,
      code: "llm_clave_invalida",
    });
    expect(llamadas).toHaveLength(1);
    expect(alPerder).not.toHaveBeenCalled();
  });
});

describe("errores", () => {
  it("lee el sobre de error con detalles y Retry-After", async () => {
    simularFetch([
      respuesta(
        429,
        { error: { code: "rate_limit", message: "Espera.", detalles: [{ campo: "x", mensaje: "y" }] } },
        { "Retry-After": "17" },
      ),
    ]);
    const error = await api.misDescansos().catch((e: unknown) => e);
    expect(error).toMatchObject({ status: 429, code: "rate_limit", message: "Espera.", retryAfter: 17 });
    expect((error as ApiError).detalles).toEqual([{ campo: "x", mensaje: "y" }]);
  });

  it("da un mensaje útil cuando responde el proxy sin sobre JSON", async () => {
    simularFetch([new Response("<html>413</html>", { status: 413 })]);
    await expect(api.crearDescanso(new File(["x"], "c.jpg"), "Lima")).rejects.toMatchObject({
      status: 413,
      message: "El archivo supera el tamaño máximo permitido.",
    });
    simularFetch([new Response("Bad Gateway", { status: 502 })]);
    const error = (await api.descanso("d1").catch((e: unknown) => e)) as ApiError;
    expect(error.resultadoIncierto).toBe(true);
  });

  it("traduce un fallo de red a un error propio", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    const error = (await api.config().catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("sin_conexion");
    expect(error.resultadoIncierto).toBe(true);
  });
});

describe("peticiones", () => {
  it("omite los filtros vacíos y codifica los demás", async () => {
    const llamadas = simularFetch([respuesta(200, { items: [], total: 0, limit: 20, offset: 0 })]);
    await api.descansos({ estado: undefined, dni: "", sede: "Lima Centro & más", limit: 20, offset: 0 });
    expect(llamadas[0]?.url).toBe("/api/v1/descansos?sede=Lima+Centro+%26+m%C3%A1s&limit=20&offset=0");
  });

  it("sube el certificado como multipart sin fijar Content-Type a mano", async () => {
    const llamadas = simularFetch([respuesta(201, { id: "d1" })]);
    await api.crearDescanso(new File(["contenido"], "cert.pdf", { type: "application/pdf" }), " Lima ");
    const form = llamadas[0]?.body as FormData;
    expect(form.get("sede")).toBe("Lima");
    expect((form.get("archivo") as File).name).toBe("cert.pdf");
    // El navegador añade el boundary: si se fija a mano, el servidor no puede leerlo.
    expect(llamadas[0]?.headers.has("Content-Type")).toBe(false);
  });
});
