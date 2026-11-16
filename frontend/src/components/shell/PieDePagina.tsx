import { Link } from "react-router-dom";
import { useConfig } from "@/hooks/queries";
import { enlaceContacto } from "@/lib/contacto";
import { NOMBRE_APP } from "@/lib/textos";

const enlace = "rounded hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function PieDePagina() {
  const { data } = useConfig();
  const concurso = data?.proyecto.concurso;
  const contacto = enlaceContacto(data?.proyecto.contacto);

  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-6 text-xs text-muted-foreground sm:flex-row sm:items-start sm:justify-between">
        <p className="max-w-xl leading-5">
          {NOMBRE_APP} es un prototipo presentado a {concurso ?? "un concurso"}. No es un servicio
          real ni tiene validez médica, legal o laboral.
        </p>
        <nav aria-label="Información del proyecto" className="flex flex-wrap gap-x-4 gap-y-1">
          <Link to="/como-funciona" className={enlace}>
            Cómo funciona
          </Link>
          <Link to="/terminos" className={enlace}>
            Términos
          </Link>
          <Link to="/privacidad" className={enlace}>
            Privacidad
          </Link>
          {contacto && (
            <a href={contacto} className={enlace} rel="noopener noreferrer">
              Contacto
            </a>
          )}
        </nav>
      </div>
    </footer>
  );
}
