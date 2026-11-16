import { Link } from "react-router-dom";
import { useConcurso, useConfig } from "@/hooks/queries";
import { Clausula, Contacto, DocumentoLegal } from "./DocumentoLegal";

// Si cambias este texto de forma sustancial, sube TERMINOS_VERSION en
// backend/src/humanaiz/legal.py: se pedirá aceptarlo de nuevo al ingresar.
export default function Terminos() {
  const { data } = useConfig();
  const concurso = useConcurso();
  const horas = data?.demo.retencion_horas ?? 24;

  return (
    <DocumentoLegal
      titulo="Términos y condiciones"
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

      <Clausula numero={4} titulo="Uso permitido">
        <p>Puedes explorar la demostración con las cuentas de prueba y documentos ficticios. No está permitido:</p>
        <ul>
          <li>
            Subir documentos reales, en especial certificados médicos o cualquier documento con datos
            de salud o de identidad de una persona real, incluida tú.
          </li>
          <li>Subir contenido ilegal, ofensivo o que infrinja derechos de terceros.</li>
          <li>
            Intentar acceder a lo que suben otros visitantes, eludir los límites de uso o atacar,
            sobrecargar o probar la seguridad del sistema sin autorización del equipo.
          </li>
          <li>Usar la demostración de forma automatizada o con fines comerciales.</li>
        </ul>
        <p>El equipo puede bloquear el acceso o borrar el contenido que incumpla estas reglas.</p>
      </Clausula>

      <Clausula numero={5} titulo="Cuentas de prueba">
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

      <Clausula numero={6} titulo="Lectura con IA y tu clave">
        <ul>
          <li>
            La lectura con IA es opcional y funciona con una clave de API de un proveedor externo
            (Anthropic, OpenAI o Google) que aportas tú.
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

      <Clausula numero={7} titulo="Disponibilidad y ausencia de garantías">
        <p>
          La demostración se ofrece tal cual, sin garantías de ningún tipo: ni de disponibilidad, ni
          de exactitud, ni de que sirva para un fin concreto. Puede interrumpirse, cambiar o retirarse
          en cualquier momento y sin aviso, por ejemplo al terminar el concurso.
        </p>
      </Clausula>

      <Clausula numero={8} titulo="Responsabilidad">
        <p>
          En la medida en que la ley lo permita, el equipo del proyecto no responde por daños
          derivados del uso de la demostración, de decisiones tomadas a partir de ella, del contenido
          que subas ni de los cargos de tu proveedor de IA. Eres responsable del contenido que subes y
          del uso que haces de tu clave.
        </p>
      </Clausula>

      <Clausula numero={9} titulo="Propiedad intelectual">
        <p>
          El código, el diseño y los textos de HumanAIz pertenecen a sus autores. Las marcas de
          terceros que se mencionan, como las de los proveedores de IA, pertenecen a sus titulares.
        </p>
        <p>
          Conservas los derechos sobre lo que subes y nos autorizas a tratarlo solo para que la
          demostración funcione, durante el plazo indicado.
        </p>
      </Clausula>

      <Clausula numero={10} titulo="Cambios">
        <p>
          Podemos actualizar estos términos. La versión vigente figura al inicio de esta página; si
          cambia, se te pedirá aceptarla de nuevo al ingresar.
        </p>
      </Clausula>

      <Clausula numero={11} titulo="Ley aplicable">
        <p>Estos términos se rigen por las leyes de la República del Perú.</p>
      </Clausula>

      <Clausula numero={12} titulo="Contacto">
        <p>
          Para cualquier consulta sobre estos términos, <Contacto con="escribe a " />.
        </p>
      </Clausula>
    </DocumentoLegal>
  );
}
