import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { ClipboardCheck, FileText, Home, Info, KeyRound, LogOut, Users } from "lucide-react";
import { useAuth } from "@/auth/context";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useConfig } from "@/hooks/queries";
import { useLlm } from "@/llm/context";
import { cn } from "@/lib/utils";

const enlace = ({ isActive }: { isActive: boolean }) =>
  cn(
    "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-muted",
  );

export function Layout({ children }: { children: ReactNode }) {
  const { usuario, esRRHH, cerrarSesion } = useAuth();
  const { credencial, abrir } = useLlm();
  const { data: config } = useConfig();
  const navigate = useNavigate();

  const salir = async () => {
    await cerrarSesion();
    navigate("/auth", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="flex flex-wrap items-center gap-4">
            <span className="text-2xl font-bold text-primary">HumanAIz</span>
            <nav className="flex flex-wrap gap-1" aria-label="Principal">
              <NavLink to="/" end className={enlace}>
                <Home className="h-4 w-4" aria-hidden />
                Inicio
              </NavLink>
              <NavLink to="/descansos" className={enlace}>
                <FileText className="h-4 w-4" aria-hidden />
                Mis descansos
              </NavLink>
              {esRRHH && (
                <>
                  <NavLink to="/rrhh/descansos" className={enlace}>
                    <ClipboardCheck className="h-4 w-4" aria-hidden />
                    Gestión de descansos
                  </NavLink>
                  <NavLink to="/rrhh/colaboradores" className={enlace}>
                    <Users className="h-4 w-4" aria-hidden />
                    Colaboradores
                  </NavLink>
                </>
              )}
            </nav>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" className="gap-2" onClick={abrir}>
              <KeyRound className="h-4 w-4" aria-hidden />
              Clave de IA
              <span
                className={cn(
                  "h-2 w-2 rounded-full",
                  credencial ? "bg-success" : "bg-muted-foreground/40",
                )}
                aria-hidden
              />
              <span className="sr-only">{credencial ? "configurada" : "sin configurar"}</span>
            </Button>
            {usuario && (
              <span className="hidden text-sm text-muted-foreground md:inline">
                {usuario.nombres} {usuario.apellidos}
              </span>
            )}
            <Button variant="outline" size="sm" className="gap-2" onClick={salir}>
              <LogOut className="h-4 w-4" aria-hidden />
              Cerrar sesión
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto space-y-6 px-4 py-8">
        {usuario?.is_demo && config?.demo.aviso && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>{config.demo.aviso}</AlertDescription>
          </Alert>
        )}
        {children}
      </main>
    </div>
  );
}
