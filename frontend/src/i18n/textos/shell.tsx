import { definir } from "../definir";
import { comun } from "./comun";

export const shell = definir({
  es: {
    saltar: "Saltar al contenido",
    demo: "Demo",
    navPrincipal: "Principal",
    nav: {
      inicio: "Inicio",
      misDescansos: "Mis descansos",
      solicitudes: "Solicitudes",
      colaboradores: "Colaboradores",
    },
    claveIA: "Clave de IA",
    claveConfigurada: "(configurada)",
    claveSinConfigurar: "(sin configurar)",
    salir: "Salir",
    ingresar: "Ingresar",
    irALaApp: "Ir a la aplicación",
    idioma: "Idioma",
    aviso: {
      titulo: (concurso: string | null | undefined) =>
        `Proyecto de concurso${concurso ? ` · ${concurso}` : ""}.`,
      texto: "Es una demostración sin uso real: no subas datos ni documentos verdaderos.",
      verTerminos: "Ver términos",
    },
    pie: {
      texto: (app: string, concurso: string | null | undefined, puesto: number | null | undefined) =>
        `${app} es un prototipo ${puesto ? `que obtuvo el ${comun.es.puesto(puesto)} en` : "presentado a"} ${concurso ?? "un concurso"}. No es un servicio real ni tiene validez médica, legal o laboral.`,
      navegacion: "Información del proyecto",
      comoFunciona: "Cómo funciona",
      terminos: "Términos",
      privacidad: "Privacidad",
      contacto: "Contacto",
    },
    noEncontrada: {
      titulo: "Esta página no existe",
      descripcion: "Puede que el enlace esté mal escrito o que el contenido ya no exista.",
      volver: "Volver al inicio",
    },
    cargandoSesion: "Comprobando tu sesión…",
  },
  en: {
    saltar: "Skip to content",
    demo: "Demo",
    navPrincipal: "Main",
    nav: {
      inicio: "Home",
      misDescansos: "My sick leaves",
      solicitudes: "Requests",
      colaboradores: "Employees",
    },
    claveIA: "AI key",
    claveConfigurada: "(set up)",
    claveSinConfigurar: "(not set up)",
    salir: "Sign out",
    ingresar: "Sign in",
    irALaApp: "Go to the app",
    idioma: "Language",
    aviso: {
      titulo: (concurso: string | null | undefined) =>
        `Contest project${concurso ? ` · ${concurso}` : ""}.`,
      texto: "This is a demo with no real-world use: don't upload real data or documents.",
      verTerminos: "See terms",
    },
    pie: {
      texto: (app: string, concurso: string | null | undefined, puesto: number | null | undefined) =>
        `${app} is a prototype ${puesto ? `that won ${comun.en.puesto(puesto)} at` : "submitted to"} ${concurso ?? "a contest"}. It is not a real service and has no medical, legal or employment validity.`,
      navegacion: "Project information",
      comoFunciona: "How it works",
      terminos: "Terms",
      privacidad: "Privacy",
      contacto: "Contact",
    },
    noEncontrada: {
      titulo: "This page doesn't exist",
      descripcion: "The link may be mistyped, or the content may no longer exist.",
      volver: "Back to home",
    },
    cargandoSesion: "Checking your session…",
  },
});
