import { definir } from "../definir";

export const inicio = definir({
  es: {
    inicio: {
      tituloSinUsuario: "Inicio",
      descripcionRRHH: "Revisa las solicitudes del equipo o gestiona tus propios descansos médicos.",
      descripcionColaborador: "Registra tus certificados de descanso médico y consulta su revisión.",
      pendientes: (n: number) => `${n} ${n === 1 ? "solicitud pendiente" : "solicitudes pendientes"}`,
      solicitudesEquipo: "Solicitudes del equipo",
      esperanDecision: "Certificados que esperan tu decisión.",
      revisar: "Revisar solicitudes",
      misDescansos: "Mis descansos",
      registrar: "Registrar descanso",
      cifras: { Pendiente: "Pendientes", Aprobado: "Aprobados", Rechazado: "Rechazados" },
      vacio: "Aún no registras descansos",
      sinFicha:
        "Tu cuenta no está vinculada a una ficha de colaborador, así que no puedes registrar descansos.",
      primerCertificado: "Sube tu primer certificado: solo necesitas una foto o una captura.",
      verTodos: (n: number) => `Ver los ${n} descansos`,
      claveIA: (configurada: boolean) => `Clave de IA ${configurada ? "· configurada" : "· opcional"}`,
      claveLista: "Lista en este navegador. Puedes cambiarla u olvidarla.",
      claveOpcional: "Configúrala si quieres que la IA lea los certificados. No la guardamos.",
      comoFunciona: "Cómo funciona",
      comoFuncionaDetalle: "Qué hace la IA, qué decide RRHH y qué pasa con tus datos. Dos minutos de lectura.",
    },
    mis: {
      titulo: "Mis descansos",
      descripcion:
        "Tus certificados registrados. Abre uno para ver el documento, la lectura con IA y la decisión de RRHH.",
      registrar: "Registrar descanso",
      sinFicha:
        "Tu cuenta no está vinculada a una ficha de colaborador, así que no puedes registrar descansos.",
      error: "No se pudieron cargar tus descansos. Recarga la página.",
      vacio: "Aún no registras descansos",
      vacioDetalle:
        "Sube una foto o captura de tu certificado. Recuerda: es una demo, usa solo documentos de prueba.",
    },
    lista: {
      fechasPorConfirmar: "Fechas por confirmar",
      dni: (dni: string) => `DNI ${dni}`,
      registrado: (fecha: string) => `Registrado el ${fecha}`,
      ejemplo: "Ejemplo",
      leyendo: "Leyendo con IA…",
      ia: (etiqueta: string) => `IA: ${etiqueta.toLowerCase()}`,
    },
  },
  en: {
    inicio: {
      tituloSinUsuario: "Home",
      descripcionRRHH: "Review your team's requests or manage your own sick leaves.",
      descripcionColaborador: "Submit your sick leave medical certificates and follow their review.",
      pendientes: (n: number) => `${n} pending ${n === 1 ? "request" : "requests"}`,
      solicitudesEquipo: "Team requests",
      esperanDecision: "Certificates waiting for your decision.",
      revisar: "Review requests",
      misDescansos: "My sick leaves",
      registrar: "Submit sick leave",
      cifras: { Pendiente: "Pending", Aprobado: "Approved", Rechazado: "Rejected" },
      vacio: "You haven't submitted any sick leave yet",
      sinFicha: "Your account isn't linked to an employee record, so you can't submit sick leaves.",
      primerCertificado: "Upload your first certificate: all you need is a photo or a screenshot.",
      verTodos: (n: number) => `See all ${n} sick leaves`,
      claveIA: (configurada: boolean) => `AI key ${configurada ? "· set up" : "· optional"}`,
      claveLista: "Ready in this browser. You can change it or forget it.",
      claveOpcional: "Set it up if you want the AI to read the certificates. We don't store it.",
      comoFunciona: "How it works",
      comoFuncionaDetalle: "What the AI does, what HR decides and what happens to your data. A two-minute read.",
    },
    mis: {
      titulo: "My sick leaves",
      descripcion:
        "Your submitted certificates. Open one to see the document, the AI reading and HR's decision.",
      registrar: "Submit sick leave",
      sinFicha: "Your account isn't linked to an employee record, so you can't submit sick leaves.",
      error: "Your sick leaves couldn't be loaded. Reload the page.",
      vacio: "You haven't submitted any sick leave yet",
      vacioDetalle:
        "Upload a photo or screenshot of your certificate. Remember: this is a demo, use test documents only.",
    },
    lista: {
      fechasPorConfirmar: "Dates to be confirmed",
      dni: (dni: string) => `ID ${dni}`,
      registrado: (fecha: string) => `Submitted ${fecha}`,
      ejemplo: "Sample",
      leyendo: "AI reading…",
      ia: (etiqueta: string) => `AI: ${etiqueta.toLowerCase()}`,
    },
  },
});
