import { describe, expect, it } from "vitest";
import { escalar, motivoFormato, prepararImagen } from "./imagen";

const TIPOS = ["image/jpeg", "image/png", "image/webp"];
const LIMITES = { tipos: TIPOS, maxBytes: 5 * 1024 * 1024, minLado: 400, maxLado: 2400 };

describe("escalar", () => {
  it("reduce el lado mayor al máximo y conserva la proporción", () => {
    expect(escalar(4000, 3000, 2400)).toEqual({ ancho: 2400, alto: 1800 });
    expect(escalar(3000, 6000, 2400)).toEqual({ ancho: 1200, alto: 2400 });
  });

  it("nunca agranda una imagen pequeña", () => {
    expect(escalar(800, 600, 2400)).toEqual({ ancho: 800, alto: 600 });
  });
});

describe("motivoFormato", () => {
  const archivo = (nombre: string, tipo: string) => new File(["x"], nombre, { type: tipo });

  it("admite JPG, PNG y WebP", () => {
    expect(motivoFormato(archivo("a.jpg", "image/jpeg"), TIPOS)).toBeNull();
    expect(motivoFormato(archivo("a.png", "image/png"), TIPOS)).toBeNull();
    expect(motivoFormato(archivo("a.webp", "image/webp"), TIPOS)).toBeNull();
  });

  it("da motivos específicos para PDF y HEIC", () => {
    expect(motivoFormato(archivo("a.pdf", "application/pdf"), TIPOS)).toBe("pdf");
    expect(motivoFormato(archivo("IMG_1.HEIC", ""), TIPOS)).toBe("heic");
    expect(motivoFormato(archivo("a", "image/heif"), TIPOS)).toBe("heic");
  });

  it("rechaza cualquier otro tipo declarado", () => {
    expect(motivoFormato(archivo("a.gif", "image/gif"), TIPOS)).toBe("formato");
    expect(motivoFormato(archivo("a.svg", "image/svg+xml"), TIPOS)).toBe("formato");
    expect(motivoFormato(archivo("a.zip", "application/zip"), TIPOS)).toBe("formato");
  });

  it("si el sistema no informa el tipo, deja decidir al decodificador", () => {
    expect(motivoFormato(archivo("foto", ""), TIPOS)).toBeNull();
  });
});

describe("prepararImagen sin APIs de imagen (jsdom)", () => {
  it("envía tal cual lo que cabe y rechaza lo que pesa de más", async () => {
    const pequena = new File([new Uint8Array(1000)], "a.jpg", { type: "image/jpeg" });
    expect(await prepararImagen(pequena, LIMITES)).toEqual({ ok: true, archivo: pequena, reducida: false });
    const pesada = new File([new Uint8Array(2000)], "a.jpg", { type: "image/jpeg" });
    expect(await prepararImagen(pesada, { ...LIMITES, maxBytes: 1500 })).toEqual({ ok: false, motivo: "pesada" });
  });

  it("rechaza un PDF antes de intentar nada", async () => {
    const pdf = new File(["%PDF-1.7"], "c.pdf", { type: "application/pdf" });
    expect(await prepararImagen(pdf, LIMITES)).toEqual({ ok: false, motivo: "pdf" });
  });
});
