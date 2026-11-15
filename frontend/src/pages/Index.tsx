import type { ComponentType } from "react";
import { Link } from "react-router-dom";
import { ClipboardCheck, FileText, KeyRound, Users } from "lucide-react";
import { useAuth } from "@/auth/context";
import { Layout } from "@/components/Layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useLlm } from "@/llm/context";

interface Acceso {
  to: string;
  titulo: string;
  descripcion: string;
  Icono: ComponentType<{ className?: string }>;
}

const DE_TODOS: Acceso[] = [
  {
    to: "/descansos",
    titulo: "Mis descansos",
    descripcion: "Registra un certificado médico y consulta el estado de tus descansos.",
    Icono: FileText,
  },
];

const DE_RRHH: Acceso[] = [
  {
    to: "/rrhh/descansos",
    titulo: "Gestión de descansos",
    descripcion: "Revisa, analiza y aprueba o rechaza las solicitudes.",
    Icono: ClipboardCheck,
  },
  {
    to: "/rrhh/colaboradores",
    titulo: "Colaboradores",
    descripcion: "Consulta el padrón de colaboradores.",
    Icono: Users,
  },
];

export default function Index() {
  const { usuario, esRRHH } = useAuth();
  const { credencial, abrir } = useLlm();
  const accesos = esRRHH ? [...DE_TODOS, ...DE_RRHH] : DE_TODOS;

  return (
    <Layout>
      <div>
        <h1 className="text-3xl font-bold">Hola, {usuario?.nombres}</h1>
        <p className="mt-2 text-muted-foreground">
          {esRRHH
            ? "Panel de Recursos Humanos para la verificación de descansos médicos."
            : "Registra tus certificados de descanso médico y sigue su revisión."}
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {accesos.map(({ to, titulo, descripcion, Icono }) => (
          <Link key={to} to={to} className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <Card className="h-full transition-shadow hover:shadow-lg">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-primary/10 p-2">
                    <Icono className="h-6 w-6 text-primary" />
                  </div>
                  <CardTitle>{titulo}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription>{descripcion}</CardDescription>
              </CardContent>
            </Card>
          </Link>
        ))}

        <button
          type="button"
          onClick={abrir}
          className="rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Card className="h-full transition-shadow hover:shadow-lg">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-primary/10 p-2">
                  <KeyRound className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Clave de IA</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                {credencial
                  ? "Tu clave está lista en este navegador. Puedes cambiarla u olvidarla."
                  : "Configura tu propia clave para analizar documentos. No se guarda en el servidor."}
              </CardDescription>
            </CardContent>
          </Card>
        </button>
      </div>
    </Layout>
  );
}
