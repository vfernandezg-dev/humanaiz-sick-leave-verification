import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n/context";
import { SaltarAlContenido } from "./AppShell";
import { AvisoConcurso } from "./AvisoConcurso";
import { Logo } from "./Logo";
import { PieDePagina } from "./PieDePagina";
import { SelectorIdioma } from "./SelectorIdioma";

interface Props {
  children: ReactNode;
  /** En la propia pantalla de ingreso no tiene sentido el botón "Ingresar". */
  sinAcceso?: boolean;
}

/** Estructura de las pantallas públicas: ingreso, cómo funciona y textos legales. */
export function PublicShell({ children, sinAcceso }: Props) {
  const { usuario } = useAuth();
  const { t } = useI18n();

  return (
    <div className="flex min-h-screen flex-col">
      <SaltarAlContenido />
      <AvisoConcurso />
      <header className="border-b">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <Logo />
          <div className="flex items-center gap-2">
            <SelectorIdioma />
            {!sinAcceso && (
              <Button asChild variant="ghost" size="sm">
                <Link to={usuario ? "/" : "/ingresar"}>{usuario ? t.shell.irALaApp : t.shell.ingresar}</Link>
              </Button>
            )}
          </div>
        </div>
      </header>
      <main id="contenido" className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:py-12">
        {children}
      </main>
      <PieDePagina />
    </div>
  );
}
