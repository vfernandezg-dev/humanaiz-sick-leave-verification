import { useCallback, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Descanso } from "@/lib/types";
import { useLlm } from "@/llm/context";
import { useRefrescarDescansos } from "./queries";
import { useToast } from "./use-toast";

const ERRORES_DE_CLAVE = new Set([
  "llm_clave_faltante",
  "llm_clave_invalida",
  "llm_sin_acceso_modelo",
  "llm_sin_saldo",
  "llm_proveedor_no_soportado",
  "llm_modelo_no_permitido",
]);

const SUGERENCIA: Record<string, string> = {
  Aprobado: "El documento supera las validaciones automáticas.",
  Observado: "Hay puntos que conviene revisar a mano.",
  Rechazado: "Se detectaron problemas en el documento.",
};

/**
 * Lanza el análisis con IA de un descanso usando la clave del usuario.
 * Devuelve true si el análisis quedó registrado.
 */
export function useAnalizar() {
  const { credencial, abrir } = useLlm();
  const { toast } = useToast();
  const refrescar = useRefrescarDescansos();
  const [enCurso, setEnCurso] = useState<ReadonlySet<string>>(new Set());

  const analizar = useCallback(
    async (descanso: Pick<Descanso, "id">): Promise<boolean> => {
      if (!credencial) {
        toast({
          title: "Falta tu clave de IA",
          description: "Configúrala para poder analizar documentos.",
        });
        abrir();
        return false;
      }
      const inicio = Date.now();
      setEnCurso((ids) => new Set(ids).add(descanso.id));
      try {
        const analisis = await api.analizar(
          descanso.id,
          { proveedor: credencial.proveedor, modelo: credencial.modelo },
          credencial.clave,
        );
        toast({
          title: `Análisis listo: ${analisis.estado_documento.toLowerCase()}`,
          description: SUGERENCIA[analisis.estado_documento],
        });
        return true;
      } catch (error) {
        const apiError =
          error instanceof ApiError
            ? error
            : new ApiError(0, "error", "No se pudo completar el análisis.");

        // Si se cortó la conexión o respondió el proxy, el servidor pudo
        // terminar igual: el análisis ya está pagado y se guarda siempre.
        if (apiError.resultadoIncierto) {
          const actual = await api.descanso(descanso.id).catch(() => null);
          const ultimo = actual?.ultimo_analisis;
          if (ultimo && new Date(ultimo.created_at).getTime() >= inicio - 5000) {
            toast({
              title: `Análisis listo: ${ultimo.estado_documento.toLowerCase()}`,
              description: SUGERENCIA[ultimo.estado_documento],
            });
            return true;
          }
        }
        if (apiError.code === "analisis_en_curso") {
          toast({
            title: "Análisis en curso",
            description: "Este documento ya se está analizando. El resultado aparecerá aquí.",
          });
          return false;
        }
        toast({
          title: "No se pudo analizar",
          description: apiError.message,
          variant: "destructive",
        });
        if (ERRORES_DE_CLAVE.has(apiError.code)) abrir();
        return false;
      } finally {
        setEnCurso((ids) => {
          const siguiente = new Set(ids);
          siguiente.delete(descanso.id);
          return siguiente;
        });
        await refrescar();
      }
    },
    [credencial, abrir, toast, refrescar],
  );

  return { analizar, analizando: (id: string) => enCurso.has(id) };
}
