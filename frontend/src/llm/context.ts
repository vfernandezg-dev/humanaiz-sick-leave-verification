import { createContext, useContext } from "react";
import type { CredencialLlm } from "./store";

export interface LlmContextValue {
  credencial: CredencialLlm | null;
  /** Abre el diálogo de configuración de la clave de IA. */
  abrir: () => void;
}

export const LlmContext = createContext<LlmContextValue | null>(null);

export function useLlm(): LlmContextValue {
  const value = useContext(LlmContext);
  if (!value) throw new Error("useLlm debe usarse dentro de <LlmKeyProvider>");
  return value;
}
