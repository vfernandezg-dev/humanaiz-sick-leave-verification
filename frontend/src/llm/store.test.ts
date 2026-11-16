import { beforeEach, describe, expect, it, vi } from "vitest";
import { llmStore } from "./store";

const CREDENCIAL = {
  proveedor: "anthropic",
  modelo: "claude-opus-5-5",
  clave: "sk-ant-clave-de-prueba-0123456789",
  recordar: false,
};

beforeEach(() => {
  llmStore.olvidar();
  sessionStorage.clear();
  localStorage.clear();
});

describe("clave de IA en el navegador", () => {
  it("por defecto vive solo en memoria", () => {
    llmStore.guardar(CREDENCIAL);
    expect(llmStore.get()?.clave).toBe(CREDENCIAL.clave);
    expect(sessionStorage.length).toBe(0);
    expect(localStorage.length).toBe(0);
  });

  it("con 'recordar' va a sessionStorage y nunca a localStorage", () => {
    llmStore.guardar({ ...CREDENCIAL, recordar: true });
    expect(sessionStorage.getItem("humanaiz.llm")).toContain(CREDENCIAL.clave);
    expect(localStorage.length).toBe(0);
  });

  it("desmarcar 'recordar' la quita de sessionStorage", () => {
    llmStore.guardar({ ...CREDENCIAL, recordar: true });
    llmStore.guardar({ ...CREDENCIAL, recordar: false });
    expect(sessionStorage.length).toBe(0);
    expect(llmStore.get()?.clave).toBe(CREDENCIAL.clave);
  });

  it("olvidar la borra de memoria y de sessionStorage, y avisa a quien escucha", () => {
    const suscriptor = vi.fn();
    const cancelar = llmStore.subscribe(suscriptor);
    llmStore.guardar({ ...CREDENCIAL, recordar: true });
    llmStore.olvidar();
    expect(llmStore.get()).toBeNull();
    expect(sessionStorage.length).toBe(0);
    expect(suscriptor).toHaveBeenCalledTimes(2);
    cancelar();
    llmStore.guardar(CREDENCIAL);
    expect(suscriptor).toHaveBeenCalledTimes(2);
  });

  it("recorta espacios al pegar la clave", () => {
    llmStore.guardar({ ...CREDENCIAL, clave: `  ${CREDENCIAL.clave}\n` });
    expect(llmStore.get()?.clave).toBe(CREDENCIAL.clave);
  });

  it("al cargar recupera lo guardado en la pestaña e ignora contenido dañado", async () => {
    sessionStorage.setItem("humanaiz.llm", JSON.stringify({ ...CREDENCIAL, recordar: true }));
    vi.resetModules();
    const recargado = await import("./store");
    expect(recargado.llmStore.get()).toEqual({ ...CREDENCIAL, recordar: true });

    sessionStorage.setItem("humanaiz.llm", "{no es json");
    vi.resetModules();
    expect((await import("./store")).llmStore.get()).toBeNull();

    sessionStorage.setItem("humanaiz.llm", JSON.stringify({ proveedor: "x" }));
    vi.resetModules();
    expect((await import("./store")).llmStore.get()).toBeNull();
  });
});
