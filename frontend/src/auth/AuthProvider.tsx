import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, clearAccessToken, refreshSession, setAlPerderSesion } from "@/lib/api";
import type { Usuario } from "@/lib/types";
import { llmStore } from "@/llm/store";
import { AuthContext, type AuthContextValue } from "./context";

// Canal entre pestañas: cerrar sesión en una la cierra en todas, y con ello se
// borra también la clave de IA que cada una tuviera en memoria.
const CANAL = "humanaiz-sesion";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);
  const queryClient = useQueryClient();
  const canal = useRef<BroadcastChannel | null>(null);

  const limpiarEstadoLocal = useCallback(() => {
    clearAccessToken();
    llmStore.olvidar();
    setUsuario(null);
    // Nada de lo consultado por el usuario anterior debe quedar en memoria.
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    let vigente = true;
    refreshSession()
      .then((sesion) => {
        if (vigente && sesion) setUsuario(sesion.usuario);
      })
      .catch(() => {
        // Sin conexión o servidor caído: se muestra el inicio de sesión.
      })
      .finally(() => {
        if (vigente) setCargando(false);
      });
    return () => {
      vigente = false;
    };
  }, []);

  useEffect(() => {
    setAlPerderSesion(limpiarEstadoLocal);
    if (typeof BroadcastChannel !== "undefined") {
      const bc = new BroadcastChannel(CANAL);
      bc.onmessage = (evento: MessageEvent<unknown>) => {
        if (evento.data === "logout") limpiarEstadoLocal();
      };
      canal.current = bc;
    }
    return () => {
      setAlPerderSesion(null);
      canal.current?.close();
      canal.current = null;
    };
  }, [limpiarEstadoLocal]);

  const iniciarSesion = useCallback(
    async (dni: string, password: string, terminosVersion: string) => {
      const sesion = await api.login(dni, password, terminosVersion);
      // Otra persona pudo usar antes esta pestaña: se parte de cero.
      llmStore.olvidar();
      queryClient.clear();
      setUsuario(sesion.usuario);
    },
    [queryClient],
  );

  const cerrarSesion = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      limpiarEstadoLocal();
      canal.current?.postMessage("logout");
    }
  }, [limpiarEstadoLocal]);

  const value = useMemo<AuthContextValue>(
    () => ({
      usuario,
      cargando,
      esRRHH: usuario?.role === "analista_rrhh",
      iniciarSesion,
      cerrarSesion,
    }),
    [usuario, cargando, iniciarSesion, cerrarSesion],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
