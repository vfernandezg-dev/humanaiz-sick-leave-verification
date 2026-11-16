import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ClipboardCheck, FileUp, KeyRound, ShieldCheck, Sparkles } from "lucide-react";
import { useAuth } from "@/auth/context";
import { Indicador } from "@/components/Indicador";
import { PublicShell } from "@/components/shell/PublicShell";
import { Button } from "@/components/ui/button";
import { useConfig } from "@/hooks/queries";
import { LECTURA_IA } from "@/lib/textos";
import type { EstadoDocumento } from "@/lib/types";

function Bloque({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold tracking-tight">{titulo}</h2>
      <div className="space-y-3 text-sm leading-7 text-foreground/80">{children}</div>
    </section>
  );
}

const PASOS = [
  {
    Icono: FileUp,
    titulo: "1. El colaborador sube su certificado",
    texto: "Una foto o un PDF. No escribe fechas ni datos: solo indica su sede.",
  },
  {
    Icono: Sparkles,
    titulo: "2. La IA lo lee (opcional)",
    texto:
      "Cualquiera de los dos puede pedirlo con su propia clave. La IA transcribe los datos y el sistema los compara con la ficha del colaborador.",
  },
  {
    Icono: ClipboardCheck,
    titulo: "3. RRHH decide",
    texto: "Revisa el documento y la lectura, confirma las fechas y aprueba o rechaza. Siempre decide una persona.",
  },
];

const COMPROBACIONES = [
  "Que sea un certificado médico y se pueda leer.",
  "Que el DNI y el nombre coincidan con la ficha del colaborador.",
  "Que las fechas de inicio y fin existan y tengan sentido.",
  "Si es un CITT de EsSalud, que tenga número.",
  "Que los días indicados cuadren con las fechas y figure el CMP del médico.",
  "Que la duración sea habitual, que no se cruce con otro descanso aprobado y que no se haya presentado antes.",
];

export default function ComoFunciona() {
  const { usuario } = useAuth();
  const { data } = useConfig();
  const concurso = data?.proyecto.concurso ?? "un concurso";
  const horas = data?.demo.retencion_horas ?? 24;

  return (
    <PublicShell>
      <article className="mx-auto max-w-2xl space-y-14">
        <header className="space-y-4">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Prototipo presentado a {concurso}
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">Cómo funciona HumanAIz</h1>
          <p className="text-base leading-7 text-muted-foreground">
            Revisar certificados de descanso médico a mano lleva tiempo: comprobar que el DNI y el
            nombre coinciden, que las fechas tengan sentido, que figure el médico… HumanAIz propone
            que una IA haga la primera lectura, que reglas transparentes señalen lo que no cuadra y
            que una persona decida.
          </p>
        </header>

        <Bloque titulo="El recorrido">
          <ol className="space-y-5">
            {PASOS.map(({ Icono, titulo, texto }) => (
              <li key={titulo} className="flex gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
                  <Icono className="h-5 w-5" aria-hidden />
                </span>
                <div>
                  <p className="font-medium text-foreground">{titulo}</p>
                  <p>{texto}</p>
                </div>
              </li>
            ))}
          </ol>
        </Bloque>

        <Bloque titulo="La IA lee; una persona decide">
          <p>
            La IA solo <strong className="text-foreground">transcribe</strong> lo que ve en el
            documento: DNI, nombre, fechas, días, número de CITT, CMP del médico y contingencia. No
            emite un veredicto. Después, unas reglas fijas comprueban:
          </p>
          <ul className="list-disc space-y-1.5 pl-5">
            {COMPROBACIONES.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
          <p>El resultado se resume en una de tres sugerencias:</p>
          <dl className="space-y-3 rounded-lg border p-4">
            {(Object.keys(LECTURA_IA) as EstadoDocumento[]).map((clave) => (
              <div key={clave} className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
                <dt className="sm:w-40">
                  <Indicador tono={LECTURA_IA[clave].tono}>{LECTURA_IA[clave].etiqueta}</Indicador>
                </dt>
                <dd>{LECTURA_IA[clave].descripcion}</dd>
              </div>
            ))}
          </dl>
          <p>
            Es una ayuda, no una decisión: la lectura no cambia el estado de la solicitud y puede
            equivocarse. Además, ningún texto del documento pasa al resultado, así que un certificado
            con instrucciones escritas («apruébame») no puede influir en él.
          </p>
        </Bloque>

        <Bloque titulo="Tu propia clave de IA">
          <div className="flex gap-4 rounded-lg bg-muted/60 p-4">
            <KeyRound className="mt-1 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden />
            <p>
              La lectura usa una clave de API tuya de Anthropic, OpenAI o Google. Así no dependemos
              de una cuenta central y el consumo queda bajo tu control. La clave viaja cifrada en cada
              lectura, se usa una vez y se descarta: no la guardamos en ningún sitio. En tu navegador
              se borra al cerrar sesión.
            </p>
          </div>
        </Bloque>

        <Bloque titulo="Lo que esta demo no es">
          <ul className="space-y-2">
            {[
              "No es un servicio real ni tiene validez médica, legal o laboral.",
              "No está conectada a EsSalud ni al Colegio Médico: comprueba que el CITT y el CMP figuren, no que sean auténticos.",
              "No es para datos reales: las personas son ficticias y debes subir solo documentos de prueba.",
              `No guarda nada por mucho tiempo: lo que subes se borra a las ${horas} horas.`,
            ].map((texto) => (
              <li key={texto} className="flex gap-3">
                <ShieldCheck className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                <span>{texto}</span>
              </li>
            ))}
          </ul>
        </Bloque>

        <footer className="flex flex-wrap items-center gap-3 border-t pt-8">
          <Button asChild>
            <Link to={usuario ? "/" : "/ingresar"}>{usuario ? "Ir a la aplicación" : "Probar la demo"}</Link>
          </Button>
          <Button asChild variant="ghost">
            <Link to="/terminos">Términos</Link>
          </Button>
          <Button asChild variant="ghost">
            <Link to="/privacidad">Privacidad</Link>
          </Button>
        </footer>
      </article>
    </PublicShell>
  );
}
