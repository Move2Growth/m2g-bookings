import Link from 'next/link';

import { NOMBRE_COMERCIAL } from '@/lib/marca';

export const metadata = {
  title: 'Términos de uso',
  description: `Las reglas de ${NOMBRE_COMERCIAL} para quien reserva y para el salón que publica su agenda.`,
};

/**
 * Los términos de uso.
 *
 * Lo que de verdad importa que quede escrito es **quién presta el servicio**: lo presta el salón,
 * no la plataforma. Sin eso, cualquier problema con un corte acaba reclamándosele a quien solo
 * puso la agenda.
 */
export default function Terminos() {
  return (
    <div className="contenido" data-superficie="calle">
      <article className="seccion pila aparece">
        <span className="etiqueta">Legal</span>
        <h1 className="rotulo rotulo--grande">Las reglas, en corto</h1>

        <h2 className="rotulo rotulo--medio">Qué es esto</h2>
        <p className="parrafo">
          {NOMBRE_COMERCIAL} conecta a quien busca un servicio de belleza o bienestar con el salón
          que lo hace. <strong>El servicio lo presta el salón, no nosotros.</strong> El precio, la
          calidad y el cumplimiento de la cita son cosa suya.
        </p>

        <h2 className="rotulo rotulo--medio">Reservar</h2>
        <p className="parrafo">
          Reservar es gratis y no se paga aquí: se paga en el salón, como siempre. Puedes cancelar
          por tu cuenta hasta el plazo que ponga cada salón; pasado ese plazo, se habla con ellos.
          Faltar sin avisar queda anotado, y un salón puede dejar de aceptarte reservas si se
          repite.
        </p>

        <h2 className="rotulo rotulo--medio">Opinar</h2>
        <p className="parrafo">
          Solo puede opinar quien fue de verdad, y solo de la cita a la que fue. Una opinión puede
          retirarse si se reporta y la revisamos. El salón puede responderte una vez.
        </p>

        <h2 className="rotulo rotulo--medio">Si tienes un salón</h2>
        <p className="parrafo">
          La agenda es gratis. Lo que se cobra —cuando se cobre— es salir arriba, y se dirá con
          esas palabras. Publicar tu salón es decir que los datos son tuyos y ciertos. Podemos
          suspender un salón que incumpla, y cuando lo hagamos te diremos por qué.
        </p>

        <h2 className="rotulo rotulo--medio">Lo que no se puede</h2>
        <p className="parrafo">
          Suplantar a un salón o a una persona, copiar la base de salones, o usar esto para algo
          que sea ilegal en Panamá.
        </p>

        <p className="menor tenue">
          Este texto es un borrador de producto y no ha pasado por un abogado.
        </p>

        <p className="parrafo">
          <Link href="/legal/privacidad">Qué hacemos con tus datos</Link> ·{' '}
          <Link href="/">Volver a la portada</Link>
        </p>
      </article>
    </div>
  );
}
