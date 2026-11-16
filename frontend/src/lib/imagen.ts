/**
 * Preparación de la imagen del certificado antes de subirla.
 *
 * El servidor guarda cada imagen con un lado máximo (2400 px) y la re-codifica
 * de todos modos, así que enviar una foto de 12 o 48 megapíxeles solo gasta
 * datos móviles y CPU del servidor. Aquí se reduce a ese lado máximo antes de
 * subirla. No es una medida de seguridad: el servidor vuelve a validarlo todo.
 */

export interface LimitesImagen {
  tipos: readonly string[];
  maxBytes: number;
  minLado: number;
  maxLado: number;
}

export type MotivoRechazo = "formato" | "heic" | "pdf" | "pesada" | "pequena" | "ilegible";

export type Preparacion =
  | { ok: true; archivo: File; reducida: boolean }
  | { ok: false; motivo: MotivoRechazo };

const CALIDAD_JPEG = 0.9;

/** Tamaño final manteniendo la proporción, sin agrandar nunca. */
export function escalar(ancho: number, alto: number, maxLado: number): { ancho: number; alto: number } {
  const factor = Math.min(1, maxLado / Math.max(ancho, alto));
  return { ancho: Math.max(1, Math.round(ancho * factor)), alto: Math.max(1, Math.round(alto * factor)) };
}

/** Clasifica por tipo y extensión los formatos que no se admiten, para dar un mensaje útil. */
export function motivoFormato(archivo: File, tipos: readonly string[]): MotivoRechazo | null {
  const nombre = archivo.name.toLowerCase();
  if (archivo.type === "application/pdf" || nombre.endsWith(".pdf")) return "pdf";
  if (/hei[cf]/.test(archivo.type) || /\.hei[cf]$/.test(nombre)) return "heic";
  // Algunos sistemas no informan el tipo: en ese caso decide el decodificador.
  if (archivo.type && !tipos.includes(archivo.type)) return "formato";
  return null;
}

async function decodificar(archivo: File): Promise<ImageBitmap | null> {
  try {
    // "from-image" aplica la rotación EXIF de las fotos de móvil.
    return await createImageBitmap(archivo, { imageOrientation: "from-image" });
  } catch {
    return null;
  }
}

function aJpeg(imagen: ImageBitmap, ancho: number, alto: number): Promise<Blob | null> {
  const lienzo = document.createElement("canvas");
  lienzo.width = ancho;
  lienzo.height = alto;
  const contexto = lienzo.getContext("2d");
  if (!contexto) return Promise.resolve(null);
  // Fondo blanco: un PNG con transparencia saldría negro en JPEG.
  contexto.fillStyle = "#ffffff";
  contexto.fillRect(0, 0, ancho, alto);
  contexto.imageSmoothingQuality = "high";
  contexto.drawImage(imagen, 0, 0, ancho, alto);
  return new Promise((resolver) => lienzo.toBlob(resolver, "image/jpeg", CALIDAD_JPEG));
}

export async function prepararImagen(archivo: File, limites: LimitesImagen): Promise<Preparacion> {
  const motivo = motivoFormato(archivo, limites.tipos);
  if (motivo) return { ok: false, motivo };

  // Sin APIs de imagen (navegadores muy antiguos): se envía tal cual si cabe.
  if (typeof createImageBitmap === "undefined") {
    return archivo.size <= limites.maxBytes
      ? { ok: true, archivo, reducida: false }
      : { ok: false, motivo: "pesada" };
  }

  const imagen = await decodificar(archivo);
  if (!imagen) return { ok: false, motivo: "ilegible" };
  try {
    if (Math.min(imagen.width, imagen.height) < limites.minLado) return { ok: false, motivo: "pequena" };
    if (Math.max(imagen.width, imagen.height) <= limites.maxLado && archivo.size <= limites.maxBytes) {
      return { ok: true, archivo, reducida: false };
    }
    const { ancho, alto } = escalar(imagen.width, imagen.height, limites.maxLado);
    const blob = await aJpeg(imagen, ancho, alto);
    if (!blob || blob.size > limites.maxBytes) {
      return archivo.size <= limites.maxBytes
        ? { ok: true, archivo, reducida: false }
        : { ok: false, motivo: "pesada" };
    }
    const base = archivo.name.replace(/\.[^.]+$/, "") || "certificado";
    return { ok: true, archivo: new File([blob], `${base}.jpg`, { type: "image/jpeg" }), reducida: true };
  } finally {
    imagen.close();
  }
}
