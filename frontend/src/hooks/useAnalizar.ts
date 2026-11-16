import { useCallback, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { LECTURA_IA } from "@/lib/textos";
import type { Analisis, Descanso } from "@/lib/types";
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

function avisoListo(analisis: Pick<Analisis, "estado_documento">) {
  const lectura = LECTURA_IA[analisis.estado_documento];
  return { title: `Lectura con IA: ${lectura.etiqueta.toLowerCase()}`, description: lectura.descripcion };
}

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
          title: "Configura tu clave de IA",
          description: "La lectura con IA es opcional y usa tu propia clave.",
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
        toast(avisoListo(analisis));
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
            toast(avisoListo(ultimo));
            return true;
          }
        }
        if (apiError.code === "analisis_en_curso") {
          toast({
            title: "Lectura en curso",
            description: "Este documento ya se está leyendo con IA. El resultado aparecerá aquí.",
          });
          return false;
        }
        toast({
          title: "No se pudo completar la lectura",
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
