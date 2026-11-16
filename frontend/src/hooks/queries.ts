// Acceso a datos con react-query. Las páginas no llaman a la API directamente.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type FiltrosColaboradores, type FiltrosDescansos } from "@/lib/api";
import type { DecisionRequest, Descanso, PaginaDescansos } from "@/lib/types";

const DESCANSOS = "descansos";
// Mientras el servidor tenga un análisis en curso se vuelve a consultar: así
// el resultado aparece aunque lo haya lanzado otra persona u otra pestaña.
const SONDEO_ANALISIS_MS = 4000;

function sondeoSiHayAnalisis(datos: PaginaDescansos | undefined): number | false {
  return datos?.items.some((d) => d.analisis_en_curso) ? SONDEO_ANALISIS_MS : false;
}

export function useConfig() {
  return useQuery({ queryKey: ["config"], queryFn: api.config, staleTime: Infinity });
}

/** Nombre del concurso para usar dentro de una frase. */
export function useMisDescansos(filtros: FiltrosDescansos = {}) {
  return useQuery({
    queryKey: [DESCANSOS, "mios", filtros],
    queryFn: () => api.misDescansos(filtros),
    refetchInterval: (query) => sondeoSiHayAnalisis(query.state.data),
  });
}

export function useDescansos(filtros: FiltrosDescansos, opciones: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: [DESCANSOS, "todos", filtros],
    queryFn: () => api.descansos(filtros),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => sondeoSiHayAnalisis(query.state.data),
    enabled: opciones.enabled ?? true,
  });
}

export function useDescanso(id: string | undefined) {
  return useQuery({
    queryKey: [DESCANSOS, "detalle", id],
    queryFn: () => api.descanso(id ?? ""),
    enabled: Boolean(id),
    refetchInterval: (query) =>
      (query.state.data as Descanso | undefined)?.analisis_en_curso ? SONDEO_ANALISIS_MS : false,
  });
}

/** Tras cualquier cambio se refrescan todos los listados de descansos. */
export function useRefrescarDescansos() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: [DESCANSOS] });
}

export function useCrearDescanso() {
  const refrescar = useRefrescarDescansos();
  return useMutation({
    mutationFn: ({ archivo, sede }: { archivo: File; sede: string }) =>
      api.crearDescanso(archivo, sede),
    onSettled: refrescar,
  });
}

export function useEliminarDescanso() {
  const refrescar = useRefrescarDescansos();
  return useMutation({ mutationFn: (id: string) => api.eliminarDescanso(id), onSettled: refrescar });
}

export function useDecidir() {
  const refrescar = useRefrescarDescansos();
  return useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: DecisionRequest }) =>
      api.decidir(id, decision),
    onSettled: refrescar,
  });
}

export function useColaboradores(filtros: FiltrosColaboradores) {
  return useQuery({
    queryKey: ["colaboradores", "lista", filtros],
    queryFn: () => api.colaboradores(filtros),
    placeholderData: keepPreviousData,
  });
}

export function useFacetas() {
  return useQuery({
    queryKey: ["colaboradores", "facetas"],
    queryFn: api.facetas,
    staleTime: 5 * 60_000,
  });
}
