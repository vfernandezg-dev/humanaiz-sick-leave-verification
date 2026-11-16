/**
 * Internacionalización sin dependencias y con tipos estrictos.
 *
 * Cada sección de la interfaz define sus textos en un archivo con las dos
 * versiones juntas. El español es la referencia: `definir` infiere la forma a
 * partir de `es` y exige que `en` tenga exactamente las mismas claves y las
 * mismas firmas. Si falta una traducción, no compila.
 *
 * Los textos con datos son funciones (`(n: number) => string`), así que los
 * parámetros también se comprueban. Los que llevan enlaces o negritas pueden
 * devolver JSX.
 */

export const IDIOMAS = ["es", "en"] as const;
export type Idioma = (typeof IDIOMAS)[number];

export const NOMBRE_IDIOMA: Record<Idioma, string> = { es: "Español", en: "English" };

/** Locale de `Intl` para fechas y números. */
export const LOCALE: Record<Idioma, string> = { es: "es-PE", en: "en-US" };

export function definir<T>(textos: { es: T; en: NoInfer<T> }): { es: T; en: T } {
  return textos;
}

// El idioma activo también se necesita fuera de React (mensajes de error del
// cliente de la API, formato de fechas). Lo fija el proveedor de idioma antes
// de renderizar, así que en cada render ya es el correcto.
let actual: Idioma = "es";

export function idiomaActual(): Idioma {
  return actual;
}

export function fijarIdiomaActual(idioma: Idioma): void {
  actual = idioma;
}

export function esIdioma(valor: unknown): valor is Idioma {
  return typeof valor === "string" && (IDIOMAS as readonly string[]).includes(valor);
}
