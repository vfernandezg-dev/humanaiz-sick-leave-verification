import { definir } from "../definir";

// Marco común de los textos legales. El cuerpo de cada documento vive en su
// propia página (una versión por idioma), porque es prosa larga con enlaces.
export const legal = definir({
  es: {
    etiqueta: "Proyecto de concurso · Sin uso real",
    version: (version: string) => `Versión vigente: ${version}`,
    enPocasPalabras: "En pocas palabras",
    // Vacío en español: es la versión de referencia.
    avisoTraduccion: "",
    contactoSin: "usa el canal de contacto que indiquen las bases del concurso",
    unConcurso: "un concurso",
    terminos: { titulo: "Términos y condiciones" },
    privacidad: { titulo: "Política de privacidad" },
  },
  en: {
    etiqueta: "Contest project · Not for real use",
    version: (version: string) => `Current version: ${version}`,
    enPocasPalabras: "In a nutshell",
    avisoTraduccion:
      "This English translation is provided for convenience only. If there is any discrepancy, the Spanish version prevails.",
    contactoSin: "use the contact channel indicated in the contest rules",
    unConcurso: "a contest",
    terminos: { titulo: "Terms and conditions" },
    privacidad: { titulo: "Privacy policy" },
  },
});
