import { afterEach, describe, expect, it } from "vitest";
import { formatoFecha } from "@/lib/fechas";
import { periodo } from "@/lib/textos";
import { mensajeDeError, textosDe } from "./context";
import { fijarIdiomaActual, IDIOMAS } from "./definir";

afterEach(() => fijarIdiomaActual("es"));

/** Recorre el diccionario y devuelve la ruta de cada texto vacío. */
function vacios(valor: unknown, ruta = ""): string[] {
  if (typeof valor === "string") return valor.trim() === "" ? [ruta] : [];
  if (Array.isArray(valor)) return valor.flatMap((v, i) => vacios(v, `${ruta}[${i}]`));
  if (valor && typeof valor === "object") {
    return Object.entries(valor).flatMap(([k, v]) => vacios(v, ruta ? `${ruta}.${k}` : k));
  }
  return [];
}

// Textos que pueden quedar vacíos a propósito: comprobaciones que no tienen el
// estado "no evaluada" y el aviso de traducción, que en español no aplica.
const VACIOS_PERMITIDOS = /(\.reglas\.[a-z_]+\.no_evaluada|^legal\.avisoTraduccion)$/;

describe("diccionarios", () => {
  it.each(IDIOMAS)("en %s no hay textos vacíos sin querer", (idioma) => {
    const faltan = vacios(textosDe(idioma)).filter((ruta) => !VACIOS_PERMITIDOS.test(ruta));
    expect(faltan).toEqual([]);
  });

  it("las dos versiones tienen las mismas claves (además de lo que exige el tipo)", () => {
    const claves = (valor: unknown, ruta = ""): string[] =>
      valor && typeof valor === "object" && !Array.isArray(valor)
        ? Object.entries(valor).flatMap(([k, v]) => [`${ruta}${k}`, ...claves(v, `${ruta}${k}.`)])
        : [];
    expect(claves(textosDe("en")).sort()).toEqual(claves(textosDe("es")).sort());
  });
});

describe("mensajeDeError", () => {
  it("en español respeta el mensaje del servidor, que puede ser más concreto", () => {
    expect(mensajeDeError("tipo_no_soportado", "Los PDF no se admiten.", 415)).toBe("Los PDF no se admiten.");
  });

  it("en inglés traduce por código y, si no lo conoce, usa el del servidor", () => {
    fijarIdiomaActual("en");
    expect(mensajeDeError("tipo_no_soportado", "Los PDF no se admiten.", 415)).toMatch(/^Unsupported format/);
    expect(mensajeDeError("codigo_nuevo", "Mensaje del servidor", 400)).toBe("Mensaje del servidor");
    expect(mensajeDeError("error", null, 413)).toBe("The image exceeds the maximum allowed size.");
    expect(mensajeDeError("error", null, 418)).toBe(textosDe("en").errores.generico);
  });

  it("los errores que genera el propio cliente también se traducen", () => {
    expect(mensajeDeError("sin_conexion", null)).toMatch(/No se pudo conectar/);
    fijarIdiomaActual("en");
    expect(mensajeDeError("sin_conexion", null)).toMatch(/Could not reach the server/);
  });
});

describe("formato según el idioma", () => {
  it("en inglés las fechas llevan el mes en letras y los días en inglés", () => {
    fijarIdiomaActual("en");
    expect(formatoFecha("2026-11-10")).toBe("Nov 10, 2026");
    expect(periodo({ fecha_inicio: "2026-11-10", fecha_fin: "2026-11-10" })).toBe(
      "Nov 10, 2026 – Nov 10, 2026 · 1 day",
    );
  });

  it("en español se mantiene el formato peruano", () => {
    expect(formatoFecha("2026-11-10")).toBe("10/11/2026");
  });
});

describe("puesto en el concurso", () => {
  it("usa los ordinales de cada idioma", () => {
    const es = textosDe("es");
    const en = textosDe("en");
    expect([1, 2, 3, 4].map(es.comun.puesto)).toEqual(["1.er puesto", "2.º puesto", "3.er puesto", "4.º puesto"]);
    expect([1, 2, 3, 4, 11, 21].map(en.comun.puesto)).toEqual([
      "1st place",
      "2nd place",
      "3rd place",
      "4th place",
      "11th place",
      "21st place",
    ]);
  });

  it("destaca al proyecto ganador en la portada y en el pie", () => {
    const es = textosDe("es");
    const en = textosDe("en");
    expect(es.ingreso.eyebrow("Hackathon X", 1)).toBe("Proyecto ganador · 1.er puesto · Hackathon X");
    expect(en.ingreso.eyebrow("Hackathon X", 1)).toBe("Winning project · 1st place · Hackathon X");
    expect(es.ingreso.eyebrow("Hackathon X", 2)).toBe("2.º puesto · Hackathon X");
    expect(es.ingreso.eyebrow("Hackathon X", null)).toBe("Proyecto de concurso · Hackathon X");
    expect(es.shell.pie.texto("HumanAIz", "Hackathon X", 1)).toMatch(/^HumanAIz es un prototipo que obtuvo el 1\.er puesto en Hackathon X\./);
    expect(en.shell.pie.texto("HumanAIz", "Hackathon X", 1)).toMatch(/^HumanAIz is a prototype that won 1st place at Hackathon X\./);
  });
});
