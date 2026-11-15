import { useCallback, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { LlmContext, type LlmContextValue } from "./context";
import { LlmKeyDialog } from "./LlmKeyDialog";
import { llmStore } from "./store";

export function LlmKeyProvider({ children }: { children: ReactNode }) {
  const credencial = useSyncExternalStore(llmStore.subscribe, llmStore.get);
  const [abierto, setAbierto] = useState(false);
  const abrir = useCallback(() => setAbierto(true), []);

  const value = useMemo<LlmContextValue>(() => ({ credencial, abrir }), [credencial, abrir]);

  return (
    <LlmContext.Provider value={value}>
      {children}
      <LlmKeyDialog abierto={abierto} onCambio={setAbierto} />
    </LlmContext.Provider>
  );
}
