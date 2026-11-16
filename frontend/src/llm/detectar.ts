import type { ProveedorLlm } from "@/lib/types";

/**
 * Reconoce el proveedor por el prefijo de la clave (p. ej. "sk-ant-" es
 * Anthropic y "sk-or-" es OpenRouter). Gana el prefijo más largo, porque
 * "sk-" (OpenAI) también es el comienzo de las otras dos.
 * Solo se ejecuta en el navegador: la clave no sale de aquí para esto.
 */
export function detectarProveedor(
  clave: string,
  proveedores: readonly ProveedorLlm[],
): ProveedorLlm | null {
  const limpia = clave.trim();
  if (!limpia) return null;
  let mejor: { proveedor: ProveedorLlm; largo: number } | null = null;
  for (const proveedor of proveedores) {
    for (const prefijo of proveedor.prefijos_clave) {
      if (limpia.startsWith(prefijo) && (!mejor || prefijo.length > mejor.largo)) {
        mejor = { proveedor, largo: prefijo.length };
      }
    }
  }
  return mejor?.proveedor ?? null;
}
