import type { Tono } from "./textos";

// Los colores de estado se reservan para lo que significan.
export const TONO_PUNTO: Record<Tono, string> = {
  neutro: "bg-muted-foreground/60",
  ok: "bg-emerald-600",
  aviso: "bg-amber-500",
  error: "bg-red-600",
};

export const TONO_TEXTO: Record<Tono, string> = {
  neutro: "text-muted-foreground",
  ok: "text-emerald-700",
  aviso: "text-amber-700",
  error: "text-red-700",
};

export const TONO_FONDO: Record<Tono, string> = {
  neutro: "bg-muted/60",
  ok: "bg-emerald-50",
  aviso: "bg-amber-50",
  error: "bg-red-50",
};
