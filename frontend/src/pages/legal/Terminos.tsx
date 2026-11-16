import { Link } from "react-router-dom";
import { useConfig } from "@/hooks/queries";
import { useI18n } from "@/i18n/context";
import { Clausula, Contacto, DocumentoLegal } from "./DocumentoLegal";

// Si cambias este texto de forma sustancial, sube TERMINOS_VERSION en
// backend/src/humanaiz/legal.py: se pedirá aceptarlo de nuevo al ingresar.
// La versión en español es la de referencia; la inglesa es una traducción y
// debe mantenerse con las mismas cláusulas y numeración.

interface Datos {
  concurso: string;
  horas: number;
  maxMb: number;
}

export default function Terminos() {
  const { data } = useConfig();
  const { t, idioma } = useI18n();
  const datos: Datos = {
    concurso: data?.proyecto.concurso ?? t.legal.unConcurso,
    horas: data?.demo.retencion_horas ?? 24,
    maxMb: Math.floor((data?.carga.max_bytes ?? 5 * 1024 * 1024) / (1024 * 1024)),
  };
  return idioma === "en" ? <TerminosEn {...datos} /> : <TerminosEs {...datos} />;
}

function TerminosEs({ concurso, horas, maxMb }: Datos) {
  const { t } = useI18n();
  return (
    <DocumentoLegal
      titulo={t.legal.terminos.titulo}
      resumen={
        <p>
          HumanAIz es un prototipo hecho para un concurso. No es un servicio real: todo lo que ves es
          ficticio y nada de lo que hagas aquí tiene efecto médico, legal ni laboral. No subas datos
          ni documentos reales. Si usas la lectura con IA, lo haces con tu propia clave y bajo tu
          responsabilidad.
        </p>
      }
    >
      <Clausula numero={1} titulo="Qué es HumanAIz">
        <p>
          HumanAIz es un prototipo desarrollado para participar en {concurso}. Su único propósito es
          demostrar una idea: registrar certificados de descanso médico y revisarlos con ayuda de
          inteligencia artificial, dejando la decisión a una persona.
        </p>
        <p>
          No es un producto comercial ni un servicio en funcionamiento. No está vinculado a ningún
          empleador, centro de salud, EsSalud ni al Colegio Médico del Perú, y no los representa. Las
          personas, cuentas, documentos y resultados que aparecen en la demostración son ficticios.
        </p>
      </Clausula>

      <Clausula numero={2} titulo="Aceptación">
        <p>
          Al marcar la casilla de aceptación e ingresar, declaras que leíste estos términos y la{" "}
          <Link to="/privacidad" className="text-primary underline underline-offset-2">
            política de privacidad
          </Link>{" "}
          y que los aceptas. Si no estás de acuerdo, no uses la demostración. Cada inicio de sesión
          registra la versión de los términos que aceptaste.
        </p>
      </Clausula>

      <Clausula numero={3} titulo="Sin validez real">
        <p>
          Nada de lo que ocurre en HumanAIz —registros, lecturas con IA, aprobaciones o rechazos—
          tiene validez médica, legal, laboral ni administrativa. No sirve para justificar ausencias
          ni para tomar decisiones sobre personas reales.
        </p>
        <p>HumanAIz no es un dispositivo médico y no ofrece consejo médico.</p>
      </Clausula>

      <Clausula numero={4} titulo="Qué puedes subir">
        <p>
          Solo imágenes JPG, PNG o WebP, de hasta {maxMb} MB, de certificados ficticios o de prueba,
          como los ejemplos que genera la propia demostración. Cualquier otro formato (PDF, documentos,
          comprimidos, vídeos, etc.) se rechaza.
        </p>
        <p>
          Cada imagen se vuelve a generar en el servidor a partir de sus píxeles y se guarda solo esa
          copia, sin metadatos (como la ubicación de una foto). El archivo tal como lo subiste se
          descarta, junto con cualquier cosa que llevara escondida.
        </p>
      </Clausula>

      <Clausula numero={5} titulo="Contenido y usos prohibidos">
        <p>No está permitido:</p>
        <ul>
          <li>
            Subir documentos reales, en especial certificados médicos o cualquier documento con datos
            de salud o de identidad de una persona real, incluida tú.
          </li>
          <li>
            Subir contenido ilegal, en particular cualquier material de abuso o explotación sexual de
            menores, así como contenido sexual, violento, que incite al odio o a la discriminación,
            o que acose o difame a alguien.
          </li>
          <li>
            Subir imágenes de terceros sin su consentimiento o que infrinjan derechos de autor, de
            marca o de imagen.
          </li>
          <li>
            Usar la demostración para fabricar, probar o perfeccionar documentos falsos o
            adulterados, o para cualquier otro fraude.
          </li>
          <li>
            Subir archivos preparados para atacar el servicio (código malicioso, archivos
            manipulados o diseñados para agotar sus recursos) o intentar acceder a lo que suben
            otros visitantes.
          </li>
          <li>
            Eludir los límites de uso —por ejemplo, con VPN, proxies, varios navegadores o scripts—,
            usar la demostración de forma automatizada o con fines comerciales, o probar su
            seguridad sin autorización del equipo.
          </li>
        </ul>
      </Clausula>

      <Clausula numero={6} titulo="Qué pasa si se incumplen estas reglas">
        <ul>
          <li>El equipo puede eliminar ese contenido de inmediato y sin aviso, y bloquear el acceso.</li>
          <li>
            Si el contenido pudiera constituir un delito, podemos ponerlo en conocimiento de las
            autoridades competentes, conservar la información necesaria (como el registro de accesos)
            y colaborar con ellas conforme a la ley.
          </li>
          <li>Eres el único responsable de lo que subes y de sus consecuencias.</li>
        </ul>
        <p>
          Si detectas un uso indebido de la demostración, <Contacto con="avísanos escribiendo a " />.
        </p>
      </Clausula>

      <Clausula numero={7} titulo="Cuentas de prueba">
        <p>
          Las cuentas de prueba son públicas y compartidas. Cada navegador solo ve lo que sube él
          mismo, pero no debes contar con confidencialidad: cualquier persona puede usar las mismas
          credenciales.
        </p>
        <p>
          Lo que subes se elimina automáticamente a las {horas} horas, y la sesión de prueba caduca
          antes. No se hacen copias de seguridad de ese contenido.
        </p>
      </Clausula>

      <Clausula numero={8} titulo="Lectura con IA y tu clave">
        <ul>
          <li>
            La lectura con IA es opcional y funciona con una clave de API de un proveedor externo
            (por ejemplo Anthropic, OpenAI, Google u OpenRouter) que aportas tú.
          </li>
          <li>
            Cuando pides una lectura, las imágenes del documento se envían a ese proveedor, que las
            trata según sus propias condiciones y política de privacidad. Cumplirlas es tu
            responsabilidad.
          </li>
          <li>
            El consumo se cobra a tu cuenta del proveedor. Te recomendamos usar una clave con límite
            de gasto y revocarla cuando termines de probar.
          </li>
          <li>No guardamos tu clave: el detalle está en la política de privacidad.</li>
          <li>
            La IA puede equivocarse. Su resultado es una sugerencia; la decisión siempre la toma una
            persona.
          </li>
        </ul>
      </Clausula>

      <Clausula numero={9} titulo="Disponibilidad y ausencia de garantías">
        <p>
          La demostración se ofrece tal cual, sin garantías de ningún tipo: ni de disponibilidad, ni
          de exactitud, ni de que sirva para un fin concreto. Puede interrumpirse, cambiar o retirarse
          en cualquier momento y sin aviso, por ejemplo al terminar el concurso.
        </p>
      </Clausula>

      <Clausula numero={10} titulo="Responsabilidad">
        <p>
          En la medida en que la ley lo permita, el equipo del proyecto no responde por daños
          derivados del uso de la demostración, de decisiones tomadas a partir de ella, del contenido
          que subas ni de los cargos de tu proveedor de IA. Eres responsable del contenido que subes y
          del uso que haces de tu clave.
        </p>
      </Clausula>

      <Clausula numero={11} titulo="Propiedad intelectual">
        <p>
          El código, el diseño y los textos de HumanAIz pertenecen a sus autores. Las marcas de
          terceros que se mencionan, como las de los proveedores de IA, pertenecen a sus titulares.
        </p>
        <p>
          Conservas los derechos sobre lo que subes y nos autorizas a tratarlo solo para que la
          demostración funcione, durante el plazo indicado.
        </p>
      </Clausula>

      <Clausula numero={12} titulo="Cambios">
        <p>
          Podemos actualizar estos términos. La versión vigente figura al inicio de esta página; si
          cambia, se te pedirá aceptarla de nuevo al ingresar.
        </p>
      </Clausula>

      <Clausula numero={13} titulo="Ley aplicable">
        <p>Estos términos se rigen por las leyes de la República del Perú.</p>
      </Clausula>

      <Clausula numero={14} titulo="Contacto">
        <p>
          Para cualquier consulta sobre estos términos, <Contacto con="escribe a " />.
        </p>
      </Clausula>
    </DocumentoLegal>
  );
}

function TerminosEn({ concurso, horas, maxMb }: Datos) {
  const { t } = useI18n();
  return (
    <DocumentoLegal
      titulo={t.legal.terminos.titulo}
      resumen={
        <p>
          HumanAIz is a prototype built for a contest. It is not a real service: everything you see is
          fictitious, and nothing you do here has any medical, legal or employment effect. Don't
          upload real data or documents. If you use the AI reading, you do so with your own key and
          at your own risk.
        </p>
      }
    >
      <Clausula numero={1} titulo="What HumanAIz is">
        <p>
          HumanAIz is a prototype developed to take part in {concurso}. Its only purpose is to
          demonstrate an idea: submitting sick leave medical certificates and reviewing them with the
          help of artificial intelligence, while leaving the decision to a person.
        </p>
        <p>
          It is not a commercial product or an operating service. It is not affiliated with, and does
          not represent, any employer, healthcare facility, EsSalud or the Colegio Médico del Perú
          (Peruvian Medical Association). The people, accounts, documents and results shown in the
          demo are fictitious.
        </p>
      </Clausula>

      <Clausula numero={2} titulo="Acceptance">
        <p>
          By ticking the acceptance box and signing in, you confirm that you have read these terms and
          the{" "}
          <Link to="/privacidad" className="text-primary underline underline-offset-2">
            privacy policy
          </Link>{" "}
          and that you accept them. If you don't agree, don't use the demo. Each sign-in records the
          version of the terms you accepted.
        </p>
      </Clausula>

      <Clausula numero={3} titulo="No real validity">
        <p>
          Nothing that happens in HumanAIz—submissions, AI readings, approvals or rejections—has any
          medical, legal, employment or administrative validity. It cannot be used to justify
          absences or to make decisions about real people.
        </p>
        <p>HumanAIz is not a medical device and does not provide medical advice.</p>
      </Clausula>

      <Clausula numero={4} titulo="What you can upload">
        <p>
          Only JPG, PNG or WebP images of up to {maxMb} MB, of fictitious or test medical
          certificates, such as the samples generated by the demo itself. Any other format (PDFs,
          documents, archives, videos, etc.) is rejected.
        </p>
        <p>
          Each image is regenerated on the server from its pixels, and only that copy is stored,
          without metadata (such as a photo's location). The file as you uploaded it is discarded,
          along with anything hidden inside it.
        </p>
      </Clausula>

      <Clausula numero={5} titulo="Prohibited content and uses">
        <p>You may not:</p>
        <ul>
          <li>
            Upload real documents, especially medical certificates or any document containing health
            or identity data of a real person, including yourself.
          </li>
          <li>
            Upload illegal content, in particular any child sexual abuse or exploitation material, as
            well as sexual or violent content, content that incites hatred or discrimination, or
            content that harasses or defames anyone.
          </li>
          <li>
            Upload images of third parties without their consent, or images that infringe copyright,
            trademark or image rights.
          </li>
          <li>
            Use the demo to create, test or improve forged or altered documents, or for any other
            kind of fraud.
          </li>
          <li>
            Upload files designed to attack the service (malicious code, tampered files or files
            designed to exhaust its resources), or try to access what other visitors upload.
          </li>
          <li>
            Circumvent the usage limits—for example, with VPNs, proxies, multiple browsers or
            scripts—, use the demo in an automated way or for commercial purposes, or test its
            security without the team's authorization.
          </li>
        </ul>
      </Clausula>

      <Clausula numero={6} titulo="What happens if these rules are broken">
        <ul>
          <li>The team may remove that content immediately and without notice, and block access.</li>
          <li>
            If the content could constitute a crime, we may report it to the competent authorities,
            keep the necessary information (such as the access log) and cooperate with them in
            accordance with the law.
          </li>
          <li>You are solely responsible for what you upload and its consequences.</li>
        </ul>
        <p>
          If you notice any misuse of the demo, <Contacto con="let us know at " />.
        </p>
      </Clausula>

      <Clausula numero={7} titulo="Demo accounts">
        <p>
          The demo accounts are public and shared. Each browser only sees what it uploads itself, but
          you should not expect confidentiality: anyone can use the same credentials.
        </p>
        <p>
          What you upload is automatically deleted after {horas} hours, and the demo session expires
          sooner. No backups of that content are made.
        </p>
      </Clausula>

      <Clausula numero={8} titulo="AI reading and your key">
        <ul>
          <li>
            The AI reading is optional and works with an API key from an external provider (for
            example Anthropic, OpenAI, Google or OpenRouter) that you provide.
          </li>
          <li>
            When you request a reading, the document images are sent to that provider, which
            processes them under its own terms and privacy policy. Complying with them is your
            responsibility.
          </li>
          <li>
            Usage is charged to your account with the provider. We recommend using a key with a
            spending limit and revoking it when you finish testing.
          </li>
          <li>We don't store your key: the details are in the privacy policy.</li>
          <li>
            AI can make mistakes. Its result is a suggestion; the decision is always made by a
            person.
          </li>
        </ul>
      </Clausula>

      <Clausula numero={9} titulo="Availability and no warranties">
        <p>
          The demo is provided as is, without warranties of any kind: of availability, of accuracy or
          of fitness for a particular purpose. It may be interrupted, changed or withdrawn at any time
          and without notice, for example when the contest ends.
        </p>
      </Clausula>

      <Clausula numero={10} titulo="Liability">
        <p>
          To the extent permitted by law, the project team is not liable for damages arising from the
          use of the demo, from decisions made based on it, from the content you upload or from
          charges by your AI provider. You are responsible for the content you upload and for how you
          use your key.
        </p>
      </Clausula>

      <Clausula numero={11} titulo="Intellectual property">
        <p>
          The code, design and texts of HumanAIz belong to their authors. Third-party trademarks
          mentioned, such as those of the AI providers, belong to their respective owners.
        </p>
        <p>
          You keep the rights to what you upload and authorize us to process it only to make the demo
          work, for the period stated.
        </p>
      </Clausula>

      <Clausula numero={12} titulo="Changes">
        <p>
          We may update these terms. The current version is shown at the top of this page; if it
          changes, you'll be asked to accept it again when you sign in.
        </p>
      </Clausula>

      <Clausula numero={13} titulo="Governing law">
        <p>These terms are governed by the laws of the Republic of Peru.</p>
      </Clausula>

      <Clausula numero={14} titulo="Contact">
        <p>
          For any questions about these terms, <Contacto con="write to " />.
        </p>
      </Clausula>
    </DocumentoLegal>
  );
}
