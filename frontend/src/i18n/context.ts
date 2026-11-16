import { createContext, useContext } from "react";
import { idiomaActual, type Idioma } from "./definir";
import { clave } from "./textos/clave";
import { comoFunciona } from "./textos/comoFunciona";
import { comun } from "./textos/comun";
import { detalle } from "./textos/detalle";
import { errores } from "./textos/errores";
import { ingreso } from "./textos/ingreso";
import { inicio } from "./textos/inicio";
import { legal } from "./textos/legal";
import { registro } from "./textos/registro";
import { rrhh } from "./textos/rrhh";
import { shell } from "./textos/shell";

const SECCIONES = {
  clave,
  comoFunciona,
  comun,
  detalle,
  errores,
  ingreso,
  inicio,
  legal,
  registro,
  rrhh,
  shell,
};

type Secciones = typeof SECCIONES;
export type Textos = { [S in keyof Secciones]: Secciones[S]["es"] };

const cache: Partial<Record<Idioma, Textos>> = {};

export function textosDe(idioma: Idioma): Textos {
  cache[idioma] ??= Object.fromEntries(
    Object.entries(SECCIONES).map(([nombre, seccion]) => [nombre, seccion[idioma]]),
  ) as Textos;
  return cache[idioma];
}

/** Para código fuera de React (cliente de la API, utilidades). */
export function textosActuales(): Textos {
  return textosDe(idiomaActual());
}

/**
 * Mensaje de error para mostrar. En español se usa el del servidor, que puede
 * ser más concreto (p. ej. distingue un PDF de una foto HEIC); en inglés, el del
 * diccionario, porque el servidor responde en español.
 */
export function mensajeDeError(code: string, mensajeServidor: string | null, status = 0): string {
  const { errores: e } = textosActuales();
  const porCodigo = (e.porCodigo as Record<string, string | undefined>)[code];
  const porEstado = (e.porEstado as Record<number, string | undefined>)[status];
  if (idiomaActual() === "es" && mensajeServidor) return mensajeServidor;
  return porCodigo ?? porEstado ?? mensajeServidor ?? e.generico;
}

export interface ContextoIdioma {
  idioma: Idioma;
  cambiarIdioma: (idioma: Idioma) => void;
  t: Textos;
}

export const IdiomaContext = createContext<ContextoIdioma | null>(null);

export function useI18n(): ContextoIdioma {
  const contexto = useContext(IdiomaContext);
  if (!contexto) throw new Error("useI18n debe usarse dentro de <IdiomaProvider>");
  return contexto;
}
