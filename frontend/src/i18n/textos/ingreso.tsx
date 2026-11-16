import type { ReactNode } from "react";
import { definir } from "../definir";

/** El texto de aceptación lleva enlaces: se componen en la pantalla y llegan aquí ya armados. */
type Enlaces = { terminos: (texto: string) => ReactNode; privacidad: (texto: string) => ReactNode };

export const ingreso = definir({
  es: {
    eyebrow: (concurso: string | null | undefined) => `Proyecto de concurso${concurso ? ` · ${concurso}` : ""}`,
    titulo: "Verificación de descansos médicos asistida por inteligencia artificial",
    lead: "HumanAIz digitaliza la recepción de certificados de descanso médico, realiza una lectura automática con IA y deja la decisión final en manos de Recursos Humanos.",
    acceder: "Acceder a la demostración",
    comoFunciona: "Cómo funciona",
    acepto: (e: Enlaces) => (
      <>
        Entiendo que es un proyecto de concurso sin uso real y acepto los {e.terminos("términos y condiciones")} y
        la {e.privacidad("política de privacidad")}.
      </>
    ),
    marcaCasilla: "Marca esta casilla para continuar.",
    cuentas: {
      colaborador: { titulo: "Entrar como colaborador", texto: "Registra un certificado y consulta su estado." },
      analista_rrhh: { titulo: "Entrar como analista de RRHH", texto: "Revisa solicitudes, pide lecturas y decide." },
    },
    entrando: "Entrando…",
    conDni: "Ingresar con DNI y contraseña",
    dni: "DNI",
    password: "Contraseña",
    ingresar: "Ingresar",
    errores: {
      dni: "El DNI tiene 8 dígitos.",
      password: "Escribe tu contraseña.",
      sinConfig: "No se pudo cargar la configuración. Recarga la página.",
      demasiados: (segundos: number) => `Demasiados intentos. Vuelve a probar en ${segundos} segundos.`,
      generico: "No se pudo iniciar sesión. Inténtalo de nuevo.",
    },
    notaDemo: (horas: number) =>
      `Cuentas de prueba compartidas: cada navegador solo ve lo que sube él mismo y todo se borra a las ${horas} horas.`,
    notaReal: "No hay registro abierto: las cuentas las crea el equipo del proyecto.",
    caracteristicasEtiqueta: "Qué hace HumanAIz",
    caracteristicas: [
      {
        titulo: "Registro digital del certificado",
        texto: "El colaborador sube una foto del certificado; no necesita transcribir datos.",
      },
      {
        titulo: "Lectura automática con IA",
        texto: "La IA extrae los datos y reglas transparentes los contrastan con la ficha del colaborador.",
      },
      {
        titulo: "Decisión final de Recursos Humanos",
        texto: "La IA sugiere; una persona confirma las fechas y aprueba o rechaza.",
      },
    ],
    vista: {
      etiqueta: "Vista de ejemplo del producto",
      alt: "Certificado médico de ejemplo, con datos ficticios y marca de agua de muestra",
      lectura: "Lectura con IA",
      comprobaciones: [
        "El DNI coincide con la ficha del colaborador",
        "El nombre coincide con la ficha",
        "Fechas coherentes · 3 días de descanso",
        "Figura el CMP del médico tratante",
      ],
      decision: "Decisión de RRHH",
      leyenda: "Ejemplo ficticio: certificado médico y resultado de su lectura automática.",
    },
  },
  en: {
    eyebrow: (concurso: string | null | undefined) => `Contest project${concurso ? ` · ${concurso}` : ""}`,
    titulo: "AI-assisted verification of sick leave certificates",
    lead: "HumanAIz digitizes the intake of sick leave medical certificates, runs an automatic AI reading and leaves the final decision in the hands of Human Resources.",
    acceder: "Access the demo",
    comoFunciona: "How it works",
    acepto: (e: Enlaces) => (
      <>
        I understand this is a contest project with no real-world use, and I accept the{" "}
        {e.terminos("terms and conditions")} and the {e.privacidad("privacy policy")}.
      </>
    ),
    marcaCasilla: "Check this box to continue.",
    cuentas: {
      colaborador: { titulo: "Sign in as an employee", texto: "Submit a certificate and track its status." },
      analista_rrhh: { titulo: "Sign in as an HR analyst", texto: "Review requests, request readings and decide." },
    },
    entrando: "Signing in…",
    conDni: "Sign in with ID number and password",
    dni: "ID number (DNI)",
    password: "Password",
    ingresar: "Sign in",
    errores: {
      dni: "The ID number (DNI) has 8 digits.",
      password: "Enter your password.",
      sinConfig: "The configuration couldn't be loaded. Reload the page.",
      demasiados: (segundos: number) => `Too many attempts. Try again in ${segundos} seconds.`,
      generico: "Couldn't sign in. Please try again.",
    },
    notaDemo: (horas: number) =>
      `Shared demo accounts: each browser only sees what it uploads, and everything is deleted after ${horas} hours.`,
    notaReal: "There's no open sign-up: accounts are created by the project team.",
    caracteristicasEtiqueta: "What HumanAIz does",
    caracteristicas: [
      {
        titulo: "Digital certificate intake",
        texto: "The employee uploads a photo of the certificate; no need to transcribe anything.",
      },
      {
        titulo: "Automatic AI reading",
        texto: "The AI extracts the details and transparent rules check them against the employee's record.",
      },
      {
        titulo: "Final decision by Human Resources",
        texto: "The AI suggests; a person confirms the dates and approves or rejects.",
      },
    ],
    vista: {
      etiqueta: "Sample product view",
      alt: "Sample medical certificate with fictitious data and a sample watermark",
      lectura: "AI reading",
      comprobaciones: [
        "The ID number matches the employee's record",
        "The name matches the record",
        "Consistent dates · 3 days of leave",
        "The treating doctor's CMP is shown",
      ],
      decision: "HR decision",
      leyenda: "Fictitious example: a medical certificate and the result of its automatic reading.",
    },
  },
});
