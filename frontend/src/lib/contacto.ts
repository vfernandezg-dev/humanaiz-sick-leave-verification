/**
 * Enlace seguro para el contacto del proyecto (viene de la configuración del
 * servidor). Solo se aceptan correos y URLs http(s): nunca `javascript:`.
 */
export function enlaceContacto(contacto: string | null | undefined): string | null {
  const valor = contacto?.trim();
  if (!valor) return null;
  if (/^https?:\/\/[^\s]+$/i.test(valor)) return valor;
  if (/^[^\s@/:]+@[^\s@/:]+\.[^\s@/:]+$/.test(valor)) return `mailto:${valor}`;
  return null;
}
