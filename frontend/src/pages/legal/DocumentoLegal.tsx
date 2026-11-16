import type { ReactNode } from "react";
import { PublicShell } from "@/components/shell/PublicShell";
import { useConfig } from "@/hooks/queries";
import { enlaceContacto } from "@/lib/contacto";

interface Props {
  titulo: string;
  resumen: ReactNode;
  children: ReactNode;
}

export function DocumentoLegal({ titulo, resumen, children }: Props) {
  const { data } = useConfig();
  const version = data?.proyecto.version_terminos;

  return (
    <PublicShell>
      <article className="mx-auto max-w-2xl">
        <header className="mb-10 space-y-4 border-b pb-8">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Proyecto de concurso · Sin uso real
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">{titulo}</h1>
          {version && <p className="text-sm text-muted-foreground">Versión vigente: {version}</p>}
          <div className="rounded-lg bg-amber-50 p-4 text-sm leading-6 text-amber-950">
            <p className="mb-1 font-semibold">En pocas palabras</p>
            {resumen}
          </div>
        </header>
        <div className="space-y-10">{children}</div>
      </article>
    </PublicShell>
  );
}

export function Clausula({ numero, titulo, children }: { numero: number; titulo: string; children: ReactNode }) {
  return (
    <section className="space-y-3" aria-labelledby={`clausula-${numero}`}>
      <h2 id={`clausula-${numero}`} className="text-lg font-semibold">
        {numero}. {titulo}
      </h2>
      <div className="space-y-3 text-sm leading-7 text-foreground/80 [&_li]:pl-1 [&_ul]:list-disc [&_ul]:space-y-1.5 [&_ul]:pl-5">
        {children}
      </div>
    </section>
  );
}

interface ContactoProps {
  /** Texto que precede al contacto cuando está configurado, p. ej. "escribe a ". */
  con: string;
  /** Frase completa cuando no hay contacto configurado. */
  sin?: string;
}

/** Contacto del equipo o, si no está configurado, el canal que indiquen las bases del concurso. */
export function Contacto({
  con,
  sin = "usa el canal de contacto que indiquen las bases del concurso",
}: ContactoProps) {
  const { data } = useConfig();
  const contacto = data?.proyecto.contacto;
  if (!contacto) return <>{sin}</>;
  const enlace = enlaceContacto(contacto);
  return (
    <>
      {con}
      {enlace ? (
        <a href={enlace} className="font-medium text-primary underline underline-offset-2" rel="noopener noreferrer">
          {contacto}
        </a>
      ) : (
        <span className="font-medium">{contacto}</span>
      )}
    </>
  );
}
