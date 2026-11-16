import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { KeyRound, LogOut } from "lucide-react";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n/context";
import { useLlm } from "@/llm/context";
import { cn } from "@/lib/utils";
import { AvisoConcurso } from "./AvisoConcurso";
import { Logo } from "./Logo";
import { PieDePagina } from "./PieDePagina";
import { SelectorIdioma } from "./SelectorIdioma";

const enlace = ({ isActive }: { isActive: boolean }) =>
  cn(
    "whitespace-nowrap rounded-md px-2.5 py-1.5 text-sm transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring",
    isActive ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground",
  );

export function SaltarAlContenido() {
  const { t } = useI18n();
  return (
    <a
      href="#contenido"
      className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:shadow"
    >
      {t.shell.saltar}
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
  const { t } = useI18n();
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
            aria-label={t.shell.navPrincipal}
            className="order-last -mx-1 flex w-full gap-1 overflow-x-auto sm:order-none sm:mx-0 sm:w-auto"
          >
            <NavLink to="/" end className={enlace}>
              {t.shell.nav.inicio}
            </NavLink>
            <NavLink to="/descansos" className={marcar("mis-descansos")}>
              {t.shell.nav.misDescansos}
            </NavLink>
            {esRRHH && (
              <>
                <NavLink to="/rrhh/descansos" className={marcar("solicitudes")}>
                  {t.shell.nav.solicitudes}
                </NavLink>
                <NavLink to="/rrhh/colaboradores" className={enlace}>
                  {t.shell.nav.colaboradores}
                </NavLink>
              </>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <SelectorIdioma className="mr-1" />
            <Button variant="ghost" size="sm" className="gap-2" onClick={abrir}>
              <KeyRound className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">{t.shell.claveIA}</span>
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  credencial ? "bg-emerald-600" : "bg-muted-foreground/40",
                )}
                aria-hidden
              />
              <span className="sr-only">{credencial ? t.shell.claveConfigurada : t.shell.claveSinConfigurar}</span>
            </Button>
            {usuario && (
              <div className="hidden px-2 text-right leading-tight lg:block">
                <p className="text-sm">{usuario.nombres.split(" ")[0]}</p>
                <p className="text-xs text-muted-foreground">{t.comun.rol[usuario.role]}</p>
              </div>
            )}
            <Button variant="ghost" size="sm" className="gap-2" onClick={salir}>
              <LogOut className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">{t.shell.salir}</span>
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
