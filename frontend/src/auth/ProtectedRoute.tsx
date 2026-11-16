import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useI18n } from "@/i18n/context";
import type { Role } from "@/lib/types";
import { useAuth } from "./context";

interface Props {
  children: ReactNode;
  /** Si se indica, solo ese rol puede entrar. */
  role?: Role;
}

/**
 * Guarda de ruta. Es solo comodidad de navegación: quien decide qué puede ver
 * o hacer cada usuario es siempre la API.
 */
export function ProtectedRoute({ children, role }: Props) {
  const { usuario, cargando, salidaVoluntaria } = useAuth();
  const location = useLocation();
  const { t } = useI18n();

  if (cargando) {
    return (
      <div className="flex min-h-screen items-center justify-center" role="status">
        <p className="text-sm text-muted-foreground">{t.shell.cargandoSesion}</p>
      </div>
    );
  }
  if (!usuario) {
    // Tras un "Salir" no se recuerda la pantalla; si la sesión caducó, sí:
    // al volver a entrar se continúa donde se estaba.
    return <Navigate to="/ingresar" replace state={salidaVoluntaria ? null : { desde: location.pathname }} />;
  }
  if (role && usuario.role !== role) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
