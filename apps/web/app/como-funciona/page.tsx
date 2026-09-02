import type { Metadata } from 'next'
import Link from 'next/link'
import { Cabecera } from '@/componentes/cabecera'
import { Pie } from '@/componentes/pie'

export const metadata: Metadata = {
  title: 'Cómo funciona Bukeo',
  description:
    'Cómo se reserva en Bukeo, cómo funciona para un salón, qué cuesta y qué pasa con tu teléfono. Explicado sin letra pequeña.',
}

/**
 * La página que explica el producto.
 *
 * No es un folleto: es la página a la que llega quien duda. Por eso el orden va del gesto
 * concreto —cómo se reserva— a lo que da miedo —qué cuesta, qué pasa con mi número, qué pasa si
 * no puedo ir—, y no al revés. Un explicativo que empieza por la visión de la empresa no lo
 * lee nadie.
 */

const PASOS_CLIENTA = [
  {
    titulo: 'Busca por lo que necesitas, no por el nombre del sitio',
    texto:
      'Un corte, un balayage, las uñas. O tu zona: Bella Vista, El Cangrejo, Costa del Este. Salen los salones que hacen eso, con su precio más barato a la vista para que puedas descartar sin entrar.',
  },
  {
    titulo: 'Mira las horas que quedan de verdad',
    texto:
      'Lo que ves libre está libre. Cada hora sale de cruzar el horario del salón con el de tu profesional y restarle lo que ya está ocupado, en ese momento. No es una solicitud que alguien contesta mañana.',
  },
  {
    titulo: 'Reserva con tu teléfono, sin contraseña',
    texto:
      'Te llega un código por WhatsApp y ya está. Sin registro, sin contraseña que recordar y sin tarjeta: en Bukeo no se paga la cita, se paga en el salón como siempre.',
  },
  {
    titulo: 'Te avisamos, y si no puedes ir lo cambias tú',
    texto:
      'Te llega la confirmación y un recordatorio el día antes. Y si te surge algo, cancelas desde tus citas sin tener que escribirle a nadie ni esperar respuesta.',
  },
]

const PASOS_SALON = [
  {
    titulo: 'Das de alta tu salón en menos de diez minutos',
    texto:
      'Un servicio, tu horario, dónde estás y una foto. Con eso ya se puede reservar. Mientras tanto tu salón existe en borrador y no lo ve nadie.',
  },
  {
    titulo: 'Tu agenda deja de estar en el WhatsApp',
    texto:
      'El día entero de todo tu equipo en una pantalla, desde el teléfono. Mueves una cita, apuntas a quien entró por la puerta y ves quién viene después sin soltar la tijera.',
  },
  {
    titulo: 'No hay dobles citas, y no porque avisemos',
    texto:
      'Dos clientas no pueden quedarse con la misma hora aunque confirmen a la vez. No lo evita un aviso en pantalla: lo impide la base de datos, que es la única forma de que no pase nunca.',
  },
  {
    titulo: 'Y tus clientas te encuentran',
    texto:
      'Tu ficha sale en las búsquedas de tu zona con tus servicios, tus precios y tus horas libres. Y tienes una dirección corta para poner en tu bio de Instagram.',
  },
]

const PREGUNTAS = [
  {
    p: '¿Cuánto cuesta para el salón?',
    r: 'Nada. Sin tarjeta para registrarte, sin mensualidad y sin comisión por cada reserva que entra. Ni ahora, ni cuando tengas la agenda llena.',
  },
  {
    p: 'Entonces, ¿de qué vive Bukeo?',
    r: 'De que un salón quiera más clientas y compre aparecer primero en su categoría y su zona durante unos días. Es opcional, va siempre marcado como patrocinado, nunca esconde a los salones que no pagan y no toca la nota de nadie. Si nunca compras visibilidad, nunca pagas nada.',
  },
  {
    p: '¿Qué pasa con mi número de teléfono?',
    r: 'Se usa para mandarte el código de acceso, la confirmación y el recordatorio. No aparece en ninguna ficha pública ni se le entrega a nadie: cuando escribes a un salón desde aquí, el enlace se resuelve en nuestro servidor y el número no viaja por la web.',
  },
  {
    p: '¿Puedo cancelar?',
    r: 'Sí, desde tus citas, hasta el plazo que ponga cada salón. Pasado ese plazo el botón desaparece y te decimos por qué: ahí toca escribirle al salón, que son ellos quienes se quedan con el hueco vacío.',
  },
  {
    p: '¿Y si el salón no usa Bukeo todavía?',
    r: 'Puedes decírselo. Darse de alta es gratis y no tienen que instalar nada ni cambiar cómo trabajan: la agenda se abre desde el mismo teléfono que ya usan.',
  },
  {
    p: '¿Se paga la cita por aquí?',
    r: 'No. Se paga en el salón, como siempre. Bukeo no pide datos de tarjeta a nadie para reservar.',
  },
]

export default function ComoFunciona() {
  return (
    <>
      <Cabecera />

      <main>
        <section className="seccion seccion--holgada">
          <div className="contenedor">
            <p className="etiqueta">Cómo funciona</p>
            <h1 style={{ marginTop: 'var(--espacio-3)', maxWidth: '18ch' }}>
              Reservar sin llamar y sin esperar respuesta
            </h1>
            <p className="medida" style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-mayor)' }}>
              Bukeo es dos cosas a la vez: la agenda de un salón, que es gratis, y el sitio donde
              sus clientas lo encuentran. Aquí está entero, sin letra pequeña.
            </p>
          </div>
        </section>

        <section className="seccion seccion--azul filo">
          <div className="contenedor">
            <p className="etiqueta">Si vienes a reservar</p>
            <h2 style={{ marginTop: 'var(--espacio-3)' }}>Cuatro pasos y ninguno es un formulario</h2>
            <ol className="pasos escalona" style={{ marginTop: 'var(--espacio-6)' }}>
              {PASOS_CLIENTA.map((p, i) => (
                <li key={p.titulo}>
                  <span className="pasos__numero cifra-grande">{i + 1}</span>
                  <div>
                    <h3>{p.titulo}</h3>
                    <p style={{ marginTop: 'var(--espacio-2)', opacity: 0.92 }}>{p.texto}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p style={{ marginTop: 'var(--espacio-6)' }}>
              <Link href="/buscar" className="boton boton--primario">
                Buscar un salón
              </Link>
            </p>
          </div>
        </section>

        <section className="seccion seccion--holgada filo">
          <div className="contenedor">
            <p className="etiqueta">Si tienes un salón</p>
            <h2 style={{ marginTop: 'var(--espacio-3)' }}>Tu agenda, gratis</h2>
            <ol className="pasos escalona" style={{ marginTop: 'var(--espacio-6)' }}>
              {PASOS_SALON.map((p, i) => (
                <li key={p.titulo}>
                  <span className="pasos__numero cifra-grande">{i + 1}</span>
                  <div>
                    <h3>{p.titulo}</h3>
                    <p className="apagado" style={{ marginTop: 'var(--espacio-2)' }}>
                      {p.texto}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
            <p style={{ marginTop: 'var(--espacio-6)' }}>
              <Link href="/para-negocios" className="boton boton--primario">
                Crear mi salón
              </Link>
            </p>
          </div>
        </section>

        <section className="seccion seccion--arena filo">
          <div className="contenedor">
            <h2>Lo que suele preocupar</h2>
            <div style={{ marginTop: 'var(--espacio-5)' }}>
              {PREGUNTAS.map(({ p, r }) => (
                <details key={p} className="pregunta">
                  <summary>{p}</summary>
                  <p className="apagado medida">{r}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="seccion seccion--holgada seccion--tinta filo">
          <div className="contenedor">
            <h2>¿Empezamos?</h2>
            <p className="medida" style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-mayor)' }}>
              Si buscas hora, busca por tu zona. Si tienes un salón, en diez minutos lo tienes
              funcionando desde el teléfono.
            </p>
            <div className="acciones" style={{ marginTop: 'var(--espacio-6)' }}>
              <Link href="/buscar" className="boton boton--primario">
                Buscar un salón
              </Link>
              <Link href="/para-negocios" className="boton boton--secundario boton--sobre-oscuro">
                Tengo un salón
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Pie />
    </>
  )
}
