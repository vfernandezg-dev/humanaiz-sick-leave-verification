import { Link } from "react-router-dom";
import { useConfig } from "@/hooks/queries";
import { useI18n } from "@/i18n/context";
import { enlaceContacto } from "@/lib/contacto";
import { NOMBRE_APP } from "@/lib/textos";

const enlace = "rounded hover:text-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring";

export function PieDePagina() {
  const { data } = useConfig();
  const { t } = useI18n();
  const concurso = data?.proyecto.concurso;
  const contacto = enlaceContacto(data?.proyecto.contacto);

  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-6 text-xs text-muted-foreground sm:flex-row sm:items-start sm:justify-between">
        <p className="max-w-xl leading-5">
          {t.shell.pie.texto(NOMBRE_APP, concurso)}
        </p>
        <nav aria-label={t.shell.pie.navegacion} className="flex flex-wrap gap-x-4 gap-y-1">
          <Link to="/como-funciona" className={enlace}>
            {t.shell.pie.comoFunciona}
          </Link>
          <Link to="/terminos" className={enlace}>
            {t.shell.pie.terminos}
          </Link>
          <Link to="/privacidad" className={enlace}>
            {t.shell.pie.privacidad}
          </Link>
          {contacto && (
            <a href={contacto} className={enlace} rel="noopener noreferrer">
              {t.shell.pie.contacto}
            </a>
          )}
        </nav>
      </div>
    </footer>
  );
}
