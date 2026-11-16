import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ClipboardCheck, FileUp, ShieldCheck, Sparkles, KeyRound } from "lucide-react";
import { useAuth } from "@/auth/context";
import { Indicador } from "@/components/Indicador";
import { PublicShell } from "@/components/shell/PublicShell";
import { Button } from "@/components/ui/button";
import { useConfig } from "@/hooks/queries";
import { useI18n } from "@/i18n/context";
import { TONO_LECTURA } from "@/lib/textos";
import type { EstadoDocumento } from "@/lib/types";

function Bloque({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold tracking-tight">{titulo}</h2>
      <div className="space-y-3 text-sm leading-7 text-foreground/80">{children}</div>
    </section>
  );
}

const ICONOS_PASOS = [FileUp, Sparkles, ClipboardCheck];
const LECTURAS = Object.keys(TONO_LECTURA) as EstadoDocumento[];

export default function ComoFunciona() {
  const { usuario } = useAuth();
  const { data } = useConfig();
  const { t } = useI18n();
  const tc = t.comoFunciona;
  const concurso = data?.proyecto.concurso ?? tc.unConcurso;
  const horas = data?.demo.retencion_horas ?? 24;

  return (
    <PublicShell>
      <article className="mx-auto max-w-2xl space-y-14">
        <header className="space-y-4">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {tc.prototipo(concurso)}
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">{tc.titulo}</h1>
          <p className="text-base leading-7 text-muted-foreground">{tc.intro}</p>
        </header>

        <Bloque titulo={tc.recorrido}>
          <ol className="space-y-5">
            {tc.pasos.map(({ titulo, texto }, indice) => {
              const Icono = ICONOS_PASOS[indice] ?? FileUp;
              return (
                <li key={titulo} className="flex gap-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
                    <Icono className="h-5 w-5" aria-hidden />
                  </span>
                  <div>
                    <p className="font-medium text-foreground">{titulo}</p>
                    <p>{texto}</p>
                  </div>
                </li>
              );
            })}
          </ol>
        </Bloque>

        <Bloque titulo={tc.iaLee}>
          <p>{tc.iaSoloTranscribe}</p>
          <ul className="list-disc space-y-1.5 pl-5">
            {tc.comprobaciones.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          <p>{tc.tresSugerencias}</p>
          <dl className="space-y-3 rounded-lg border p-4">
            {LECTURAS.map((clave) => (
              <div key={clave} className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
                <dt className="sm:w-40">
                  <Indicador tono={TONO_LECTURA[clave]}>{t.comun.lectura[clave].etiqueta}</Indicador>
                </dt>
                <dd>{t.comun.lectura[clave].descripcion}</dd>
              </div>
            ))}
          </dl>
          <p>{tc.esUnaAyuda}</p>
        </Bloque>

        <Bloque titulo={tc.tuClave}>
          <div className="flex gap-4 rounded-lg bg-muted/60 p-4">
            <KeyRound className="mt-1 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden />
            <p>{tc.tuClaveTexto}</p>
          </div>
        </Bloque>

        <Bloque titulo={tc.noEs}>
          <ul className="space-y-2">
            {tc.noEsLista(horas).map((texto) => (
              <li key={texto} className="flex gap-3">
                <ShieldCheck className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                <span>{texto}</span>
              </li>
            ))}
          </ul>
        </Bloque>

        <footer className="flex flex-wrap items-center gap-3 border-t pt-8">
          <Button asChild>
            <Link to={usuario ? "/" : "/ingresar"}>{usuario ? tc.irALaApp : tc.probarDemo}</Link>
          </Button>
          <Button asChild variant="ghost">
            <Link to="/terminos">{tc.terminos}</Link>
          </Button>
          <Button asChild variant="ghost">
            <Link to="/privacidad">{tc.privacidad}</Link>
          </Button>
        </footer>
      </article>
    </PublicShell>
  );
}
