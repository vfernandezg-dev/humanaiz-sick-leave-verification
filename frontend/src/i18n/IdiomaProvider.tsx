import { useCallback, useLayoutEffect, useMemo, useState, type ReactNode } from "react";
import { IdiomaContext, textosDe, type ContextoIdioma } from "./context";
import { esIdioma, fijarIdiomaActual, IDIOMAS, type Idioma } from "./definir";

// Preferencia de interfaz, no un dato personal: se guarda en localStorage para
// recordarla entre visitas (ver la política de privacidad).
const CLAVE_ALMACEN = "hz_idioma";

function guardado(): Idioma | null {
  try {
    const valor = window.localStorage.getItem(CLAVE_ALMACEN);
    return esIdioma(valor) ? valor : null;
  } catch {
    return null;
  }
}

/** Preferencia guardada, si no el primer idioma del navegador que tengamos; si no, inglés. */
function idiomaInicial(): Idioma {
  const elegido = guardado();
  if (elegido) return elegido;
  const preferidos = navigator.languages?.length ? navigator.languages : [navigator.language];
  for (const etiqueta of preferidos) {
    const base = etiqueta?.slice(0, 2).toLowerCase();
    if (esIdioma(base)) return base;
  }
  return IDIOMAS[1];
}

export function IdiomaProvider({ children }: { children: ReactNode }) {
  const [idioma, setIdioma] = useState<Idioma>(() => {
    const inicial = idiomaInicial();
    // Antes del primer render: fechas y errores ya salen en este idioma.
    fijarIdiomaActual(inicial);
    return inicial;
  });

  const cambiarIdioma = useCallback((nuevo: Idioma) => {
    fijarIdiomaActual(nuevo);
    try {
      window.localStorage.setItem(CLAVE_ALMACEN, nuevo);
    } catch {
      // Sin almacenamiento (modo privado estricto): vale para esta visita.
    }
    setIdioma(nuevo);
  }, []);

  const t = textosDe(idioma);

  useLayoutEffect(() => {
    document.documentElement.lang = idioma;
    document.title = t.comun.tituloDocumento;
  }, [idioma, t]);

  const valor = useMemo<ContextoIdioma>(() => ({ idioma, cambiarIdioma, t }), [idioma, cambiarIdioma, t]);
  return <IdiomaContext.Provider value={valor}>{children}</IdiomaContext.Provider>;
}
