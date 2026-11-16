import { definir } from "../definir";

// Página pública "Cómo funciona".
export const comoFunciona = definir({
  es: {
    prototipo: (concurso: string) => `Prototipo presentado a ${concurso}`,
    unConcurso: "un concurso",
    titulo: "Cómo funciona HumanAIz",
    intro:
      "Revisar certificados de descanso médico a mano lleva tiempo: comprobar que el DNI y el nombre coinciden, que las fechas tengan sentido, que figure el médico… HumanAIz propone que una IA haga la primera lectura, que reglas transparentes señalen lo que no cuadra y que una persona decida.",
    recorrido: "El recorrido",
    pasos: [
      {
        titulo: "1. El colaborador sube su certificado",
        texto: "Una foto o captura (JPG, PNG o WebP). No escribe fechas ni datos: solo indica su sede.",
      },
      {
        titulo: "2. La IA lo lee (opcional)",
        texto:
          "Cualquiera de los dos puede pedirlo con su propia clave. La IA transcribe los datos y el sistema los compara con la ficha del colaborador.",
      },
      {
        titulo: "3. RRHH decide",
        texto:
          "Revisa el documento y la lectura, confirma las fechas y aprueba o rechaza. Siempre decide una persona.",
      },
    ],
    iaLee: "La IA lee; una persona decide",
    iaSoloTranscribe: (
      <>
        La IA solo <strong className="text-foreground">transcribe</strong> lo que ve en el
        documento: DNI, nombre, fechas, días, número de CITT, CMP del médico y contingencia. No
        emite un veredicto. Después, unas reglas fijas comprueban:
      </>
    ),
    comprobaciones: [
      "Que sea un certificado médico y se pueda leer.",
      "Que el DNI y el nombre coincidan con la ficha del colaborador.",
      "Que las fechas de inicio y fin existan y tengan sentido.",
      "Si es un CITT de EsSalud, que tenga número.",
      "Que los días indicados cuadren con las fechas y figure el CMP del médico.",
      "Que la duración sea habitual, que no se cruce con otro descanso aprobado y que no se haya presentado antes.",
    ],
    tresSugerencias: "El resultado se resume en una de tres sugerencias:",
    esUnaAyuda:
      "Es una ayuda, no una decisión: la lectura no cambia el estado de la solicitud y puede equivocarse. Además, ningún texto del documento pasa al resultado, así que un certificado con instrucciones escritas («apruébame») no puede influir en él.",
    tuClave: "Tu propia clave de IA",
    tuClaveTexto:
      "La lectura usa una clave de API tuya de un proveedor como Anthropic, OpenAI, Google u OpenRouter. Así no dependemos de una cuenta central y el consumo queda bajo tu control. La clave viaja cifrada en cada lectura, se usa una vez y se descarta: no la guardamos en ningún sitio. En tu navegador se borra al cerrar sesión.",
    noEs: "Lo que esta demo no es",
    noEsLista: (horas: number) => [
      "No es un servicio real ni tiene validez médica, legal o laboral.",
      "No está conectada a EsSalud ni al Colegio Médico: comprueba que el CITT y el CMP figuren, no que sean auténticos.",
      "No es para datos reales: las personas son ficticias y debes subir solo documentos de prueba.",
      `No guarda nada por mucho tiempo: lo que subes se borra a las ${horas} horas.`,
    ],
    irALaApp: "Ir a la aplicación",
    probarDemo: "Probar la demo",
    terminos: "Términos",
    privacidad: "Privacidad",
  },
  en: {
    prototipo: (concurso: string) => `Prototype submitted to ${concurso}`,
    unConcurso: "a contest",
    titulo: "How HumanAIz works",
    intro:
      "Reviewing sick-leave certificates by hand takes time: checking that the ID number and name match, that the dates make sense, that the doctor is listed… HumanAIz proposes that an AI does the first reading, that transparent rules flag what doesn't add up, and that a person makes the decision.",
    recorrido: "The flow",
    pasos: [
      {
        titulo: "1. The employee uploads their certificate",
        texto: "A photo or screenshot (JPG, PNG or WebP). No dates or details to type in: they just enter their location.",
      },
      {
        titulo: "2. The AI reads it (optional)",
        texto:
          "Either of them can request it with their own key. The AI transcribes the details and the system compares them with the employee's record.",
      },
      {
        titulo: "3. HR decides",
        texto:
          "They review the document and the reading, confirm the dates, and approve or reject. A person always decides.",
      },
    ],
    iaLee: "The AI reads; a person decides",
    iaSoloTranscribe: (
      <>
        The AI only <strong className="text-foreground">transcribes</strong> what it sees in the
        document: ID number, name, dates, days, CITT number, the doctor&apos;s CMP and the type of
        condition. It doesn&apos;t give a verdict. Then a fixed set of rules checks:
      </>
    ),
    comprobaciones: [
      "That it's a medical certificate and it's readable.",
      "That the ID number and name match the employee's record.",
      "That the start and end dates are there and make sense.",
      "If it's an EsSalud CITT, that it has a number.",
      "That the number of days matches the dates and the doctor's CMP is listed.",
      "That the length is typical, that it doesn't overlap another approved sick leave, and that it hasn't been submitted before.",
    ],
    tresSugerencias: "The result is summed up as one of three suggestions:",
    esUnaAyuda:
      "It's an aid, not a decision: the reading doesn't change the request's status, and it can be wrong. Also, no text from the document makes it into the result, so a certificate with written instructions (“approve me”) can't influence it.",
    tuClave: "Your own AI key",
    tuClaveTexto:
      "The reading uses your own API key from a provider such as Anthropic, OpenAI, Google or OpenRouter. That way there's no central account and usage stays under your control. The key travels encrypted with each reading, is used once and discarded: we don't store it anywhere. In your browser, it's deleted when you sign out.",
    noEs: "What this demo is not",
    noEsLista: (horas: number) => [
      "It's not a real service and has no medical, legal or employment validity.",
      "It's not connected to EsSalud or the Peruvian Medical Association: it checks that the CITT and CMP are present, not that they're authentic.",
      "It's not for real data: the people are fictitious and you should only upload test documents.",
      `It doesn't keep anything for long: what you upload is deleted after ${horas} hours.`,
    ],
    irALaApp: "Go to the app",
    probarDemo: "Try the demo",
    terminos: "Terms",
    privacidad: "Privacy",
  },
});
