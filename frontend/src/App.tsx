import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { ProtectedRoute } from "@/auth/ProtectedRoute";
import { Toaster } from "@/components/ui/toaster";
import { ApiError } from "@/lib/api";
import { LlmKeyProvider } from "@/llm/LlmKeyProvider";
import Colaboradores from "@/pages/Colaboradores";
import ComoFunciona from "@/pages/ComoFunciona";
import DescansoDetalle from "@/pages/DescansoDetalle";
import Ingresar from "@/pages/Ingresar";
import Inicio from "@/pages/Inicio";
import Privacidad from "@/pages/legal/Privacidad";
import Terminos from "@/pages/legal/Terminos";
import MisDescansos from "@/pages/MisDescansos";
import NotFound from "@/pages/NotFound";
import NuevoDescanso from "@/pages/NuevoDescanso";
import Solicitudes from "@/pages/Solicitudes";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      refetchOnWindowFocus: true,
      // Solo se reintenta lo que puede arreglarse solo: red o servidor caído.
      // Un 4xx (sin permiso, no existe, validación) no cambia por repetirlo.
      retry: (intentos, error) =>
        intentos < 2 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
    },
    mutations: { retry: false },
  },
});

/** Al cambiar de pantalla se vuelve arriba, como en una web tradicional. */
function ScrollArriba() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

const conSesion = (pagina: React.ReactNode, role?: "analista_rrhh") => (
  <ProtectedRoute role={role}>{pagina}</ProtectedRoute>
);

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ScrollArriba />
        <AuthProvider>
          <LlmKeyProvider>
            <Routes>
              {/* Públicas */}
              <Route path="/ingresar" element={<Ingresar />} />
              <Route path="/auth" element={<Navigate to="/ingresar" replace />} />
              <Route path="/como-funciona" element={<ComoFunciona />} />
              <Route path="/terminos" element={<Terminos />} />
              <Route path="/privacidad" element={<Privacidad />} />

              {/* Con sesión */}
              <Route path="/" element={conSesion(<Inicio />)} />
              <Route path="/descansos" element={conSesion(<MisDescansos />)} />
              <Route path="/descansos/nuevo" element={conSesion(<NuevoDescanso />)} />
              <Route path="/descansos/:id" element={conSesion(<DescansoDetalle />)} />
              <Route path="/rrhh/descansos" element={conSesion(<Solicitudes />, "analista_rrhh")} />
              <Route
                path="/rrhh/colaboradores"
                element={conSesion(<Colaboradores />, "analista_rrhh")}
              />

              <Route path="*" element={<NotFound />} />
            </Routes>
            <Toaster />
          </LlmKeyProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
