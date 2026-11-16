import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { KeyRound, LogOut } from "lucide-react";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { useLlm } from "@/llm/context";
import { ROL } from "@/lib/textos";
import { cn } from "@/lib/utils";
import { AvisoConcurso } from "./AvisoConcurso";
import { Logo } from "./Logo";
import { PieDePagina } from "./PieDePagina";

const enlace = ({ isActive }: { isActive: boolean }) =>
  cn(
    "whitespace-nowrap rounded-md px-2.5 py-1.5 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    isActive ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
  );

export function SaltarAlContenido() {
  return (
    <a
      href="#contenido"
      className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:shadow"
    >
      Saltar al contenido
    </a>
  );
}

type Seccion = "mis-descansos" | "solicitudes";

interface Props {
  children: ReactNode;
  /**
   * Fuerza qué entrada del menú se marca. El detalle de un descanso vive en
   * /descansos/:id para todos, pero si RRHH lo abrió desde Solicitudes debe
   * seguir marcada Solicitudes.
   */
  seccion?: Seccion;
}

/** Estructura de las pantallas con sesión iniciada. */
export function AppShell({ children, seccion }: Props) {
  const marcar = (propia: Seccion) => ({ isActive }: { isActive: boolean }) =>
    enlace({ isActive: seccion ? seccion === propia : isActive });
  const { usuario, esRRHH, cerrarSesion } = useAuth();
  const { credencial, abrir } = useLlm();
  const navigate = useNavigate();

  const salir = async () => {
    await cerrarSesion();
    navigate("/ingresar", { replace: true });
  };

  return (
    <div className="flex min-h-screen flex-col">
      <SaltarAlContenido />
      <AvisoConcurso />
      <header className="border-b">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Logo />
          <nav
            aria-label="Principal"
            className="order-last -mx-1 flex w-full gap-1 overflow-x-auto sm:order-none sm:mx-0 sm:w-auto"
          >
            <NavLink to="/" end className={enlace}>
              Inicio
            </NavLink>
            <NavLink to="/descansos" className={marcar("mis-descansos")}>
              Mis descansos
            </NavLink>
            {esRRHH && (
              <>
                <NavLink to="/rrhh/descansos" className={marcar("solicitudes")}>
                  Solicitudes
                </NavLink>
                <NavLink to="/rrhh/colaboradores" className={enlace}>
                  Colaboradores
                </NavLink>
              </>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <Button variant="ghost" size="sm" className="gap-2" onClick={abrir}>
              <KeyRound className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">Clave de IA</span>
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  credencial ? "bg-emerald-600" : "bg-muted-foreground/40",
                )}
                aria-hidden
              />
              <span className="sr-only">{credencial ? "(configurada)" : "(sin configurar)"}</span>
            </Button>
            {usuario && (
              <div className="hidden px-2 text-right leading-tight lg:block">
                <p className="text-sm">{usuario.nombres.split(" ")[0]}</p>
                <p className="text-xs text-muted-foreground">{ROL[usuario.role]}</p>
              </div>
            )}
            <Button variant="ghost" size="sm" className="gap-2" onClick={salir}>
              <LogOut className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">Salir</span>
            </Button>
          </div>
        </div>
      </header>
      <main id="contenido" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:py-10">
        {children}
      </main>
      <PieDePagina />
    </div>
  );
}
