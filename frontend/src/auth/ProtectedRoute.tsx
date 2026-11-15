import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
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
  const { usuario, cargando } = useAuth();
  const location = useLocation();

  if (cargando) {
    return (
      <div className="flex min-h-screen items-center justify-center" role="status">
        <p className="text-muted-foreground">Cargando…</p>
      </div>
    );
  }
  if (!usuario) {
    return <Navigate to="/auth" replace state={{ desde: location.pathname }} />;
  }
  if (role && usuario.role !== role) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
