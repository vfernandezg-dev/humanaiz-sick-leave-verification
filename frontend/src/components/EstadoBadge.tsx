import { Badge } from "@/components/ui/badge";
import type { EstadoDescanso } from "@/lib/types";

export function EstadoBadge({ estado }: { estado: EstadoDescanso }) {
  if (estado === "Aprobado") return <Badge className="bg-success hover:bg-success">Aprobado</Badge>;
  if (estado === "Rechazado") return <Badge variant="destructive">Rechazado</Badge>;
  return <Badge variant="secondary">Pendiente</Badge>;
}
