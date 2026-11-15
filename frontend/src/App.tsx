import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { ProtectedRoute } from "@/auth/ProtectedRoute";
import { Toaster } from "@/components/ui/toaster";
import { ApiError } from "@/lib/api";
import { LlmKeyProvider } from "@/llm/LlmKeyProvider";
import Auth from "@/pages/Auth";
import Descansos from "@/pages/Descansos";
import Index from "@/pages/Index";
import NotFound from "@/pages/NotFound";
import RRHHColaboradores from "@/pages/RRHHColaboradores";
import RRHHDescansos from "@/pages/RRHHDescansos";

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

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <LlmKeyProvider>
            <Routes>
              <Route path="/auth" element={<Auth />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <Index />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/descansos"
                element={
                  <ProtectedRoute>
                    <Descansos />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/rrhh/descansos"
                element={
                  <ProtectedRoute role="analista_rrhh">
                    <RRHHDescansos />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/rrhh/colaboradores"
                element={
                  <ProtectedRoute role="analista_rrhh">
                    <RRHHColaboradores />
                  </ProtectedRoute>
                }
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
