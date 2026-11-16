import { useEffect, useState } from "react";

/** Devuelve `valor` con retraso: evita una consulta por cada tecla en los filtros. */
export function useDebounce<T>(valor: T, ms = 350): T {
  const [retrasado, setRetrasado] = useState(valor);
  useEffect(() => {
    const id = window.setTimeout(() => setRetrasado(valor), ms);
    return () => window.clearTimeout(id);
  }, [valor, ms]);
  return retrasado;
}
