import { createContext, useContext } from "react";
import type { Usuario } from "@/lib/types";

export interface AuthContextValue {
  usuario: Usuario | null;
  /** true mientras se comprueba si ya existe una sesión al cargar la página. */
  cargando: boolean;
  esRRHH: boolean;
  iniciarSesion: (dni: string, password: string, terminosVersion: string) => Promise<void>;
  cerrarSesion: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return value;
}
