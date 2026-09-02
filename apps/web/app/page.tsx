import Image from 'next/image'
import Link from 'next/link'
import { Cabecera } from '@/componentes/cabecera'
import { Pie } from '@/componentes/pie'

/**
 * La portada.
 *
 * Se renderiza en servidor (ADR-0011): media clientela llega buscando «barbería en San
 * Francisco», y una página que llega vacía y se rellena con JavaScript no la indexa nadie.
 *
 * El buscador va en formulario con método GET a propósito. Así cada búsqueda tiene su URL, se
 * comparte por WhatsApp y el rastreador la puede seguir. Un buscador que solo funciona con
 * JavaScript es un buscador que Google no usa.
 */

// Solo dos categorías llevan foto, y son fotos de verdad. Poner una imagen genérica de banco
// en las ocho es peor que no ponerla: se nota que no es el salón de nadie. Las demás son celdas
// tipográficas, que además pesan cero en una red de 3G.
const CATEGORIAS = [
  { nombre: 'Barbería', slug: 'barberia', foto: null },
  { nombre: 'Peluquería', slug: 'peluqueria', foto: null },
  { nombre: 'Uñas', slug: 'unas', foto: '/fotos/unas.webp' },
  { nombre: 'Pestañas y cejas', slug: 'pestanas-cejas', foto: null },
  { nombre: 'Maquillaje', slug: 'maquillaje', foto: null },
  { nombre: 'Depilación', slug: 'depilacion', foto: null },
  { nombre: 'Spa y masajes', slug: 'spa-masajes', foto: '/fotos/spa.webp' },
  { nombre: 'Estética', slug: 'estetica', foto: null },
]

const ZONAS = [
  ['Bella Vista', 'bella-vista'],
  ['El Cangrejo', 'el-cangrejo'],
  ['Obarrio', 'obarrio'],
  ['San Francisco', 'san-francisco'],
  ['Costa del Este', 'costa-del-este'],
  ['Juan Díaz', 'juan-diaz'],
]

const PASOS = [
  {
    titulo: 'Busca lo que necesitas',
    texto: 'Un corte, un balayage o el salón por su nombre. Filtra por tu zona y mira quién está cerca.',
  },
  {
    titulo: 'Mira las horas que quedan',
    texto: 'Las de verdad. Si aparece libre, está libre: se calcula contra la agenda del salón en ese momento.',
  },
  {
    titulo: 'Reserva con tu teléfono',
    texto: 'Te llega un código por WhatsApp y listo. Sin contraseña y sin esperar a que alguien te conteste.',
  },
]

const PREGUNTAS = [
  {
    p: '¿Cuánto cuesta reservar?',
    r: 'Nada. Reservar es gratis para quien reserva, y la agenda es gratis para el salón. Pagas tu servicio en el salón, como siempre.',
  },
  {
    p: '¿Puedo cancelar?',
    r: 'Sí, desde «Mis citas» hasta dos horas antes. Pasado ese plazo lo arreglas hablando con el salón, que es quien se queda con el hueco vacío.',
  },
  {
    p: '¿Por qué me piden el teléfono?',
    r: 'Porque el salón necesita saber que la cita es real. Verificamos el número con un código y nada más: no hay contraseña ni registro aparte.',
  },
  {
    p: 'Tengo un salón, ¿qué me cuesta?',
    r: 'Cero. Sin tarjeta para registrarte, sin mensualidad y sin comisión por cita. Ganamos cuando un salón quiere más visibilidad y compra un destacado, que va siempre marcado.',
  },
]

export default function Portada() {
  return (
    <>
      <Cabecera />

      <main>
        {/* Hero. Reparto asimétrico: la mitad izquierda decide, la derecha da contexto. */}
        <section className="seccion" style={{ paddingTop: 'var(--espacio-6)' }}>
          <div className="contenedor hero">
            <div>
              <h1>Reserva en salones y barberías de Panamá</h1>
              <p
                className="apagado medida"
                style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-mayor)' }}
              >
                Encuentra un sitio cerca, mira las horas libres de verdad y reserva. Sin llamar y
                sin esperar respuesta.
              </p>

              <form
                method="get"
                action="/buscar"
                style={{
                  display: 'flex',
                  gap: 'var(--espacio-2)',
                  marginTop: 'var(--espacio-5)',
                  maxWidth: '30rem',
                }}
              >
                {/* `minWidth: 0` no es cosmético: sin él el ancho intrínseco del campo impide
                    que encoja y la fila se sale de los 390 px. */}
                <label className="campo" style={{ flex: 1, minWidth: 0 }}>
                  <span className="oculto-visualmente">Qué buscas</span>
                  <input
                    className="entrada"
                    type="search"
                    name="texto"
                    placeholder="Corte, balayage, uñas…"
                  />
                </label>
                <button type="submit" className="boton boton--primario">
                  Buscar
                </button>
              </form>

              <p style={{ marginTop: 'var(--espacio-4)' }}>
                <Link href="/para-negocios">Tengo un salón y quiero mi agenda</Link>
              </p>
            </div>

            <div className="hero__foto">
              <Image
                src="/fotos/unas.webp"
                alt="Manos de una manicurista aplicando esmalte a una clienta"
                width={1000}
                height={1000}
                priority
                sizes="(min-width: 900px) 40vw, 100vw"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>
          </div>
        </section>

        {/* Categorías. Rejilla con celdas de distinto peso: cuatro llevan foto y cuatro no, y
            eso ya da ritmo sin inventarse decoración. */}
        <section className="seccion seccion--arena">
          <div className="contenedor">
            <h2>Qué te vas a hacer hoy</h2>
            <ul className="categorias" style={{ marginTop: 'var(--espacio-5)' }}>
              {CATEGORIAS.map((c) => (
                <li key={c.slug} className={c.foto ? 'categoria categoria--foto' : 'categoria'}>
                  <Link href={`/buscar?categoria=${c.slug}`}>
                    {c.foto && (
                      <Image
                        src={c.foto}
                        alt=""
                        width={1000}
                        height={1000}
                        sizes="(min-width: 768px) 25vw, 50vw"
                      />
                    )}
                    <span>{c.nombre}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* La diferencia del producto, enseñada con el producto: una rejilla de horas real. */}
        <section className="seccion">
          <div className="contenedor hero" style={{ alignItems: 'center' }}>
            <div>
              <p className="etiqueta">Lo que nos separa del WhatsApp</p>
              <h2 style={{ marginTop: 'var(--espacio-2)' }}>Horas que existen, no solicitudes</h2>
              <p className="apagado medida" style={{ marginTop: 'var(--espacio-4)' }}>
                Cada hora que ves sale de cruzar el horario del salón con el de tu profesional y
                restarle lo que ya está ocupado. Si aparece, es tuya al confirmar. Y si alguien
                se adelanta por segundos, te lo decimos en el momento en vez de al día siguiente.
              </p>
            </div>

            <div className="panel" aria-hidden="true">
              <p className="tenue">Jueves 3 de septiembre</p>
              <p style={{ fontWeight: 'var(--tipografia-pesos-medio)', marginTop: 'var(--espacio-1)' }}>
                Corte + barba, 45 min
              </p>
              <div className="horas" style={{ marginTop: 'var(--espacio-4)' }}>
                {['09:00', '09:15', '10:45', '11:00', '11:15', '14:00'].map((h) => (
                  <span key={h} className="hora">
                    {h}
                  </span>
                ))}
              </div>
              <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
                De 09:30 a 10:30 hay una cita. A la una almuerza el barbero.
              </p>
            </div>
          </div>
        </section>

        {/* Cómo funciona. Ritmo vertical numerado, no tres tarjetas iguales en fila. */}
        <section className="seccion seccion--arena">
          <div className="contenedor">
            <h2>Reservar lleva un minuto</h2>
            <ol className="pasos">
              {PASOS.map((paso, i) => (
                <li key={paso.titulo}>
                  <span className="pasos__numero cifras">{i + 1}</span>
                  <div>
                    <h3>{paso.titulo}</h3>
                    <p className="apagado" style={{ marginTop: 'var(--espacio-2)' }}>
                      {paso.texto}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* El único bloque de color de la página, y es para el otro público. Se usa una vez. */}
        <section className="seccion seccion--holgada seccion--tinta">
          <div className="contenedor" style={{ maxWidth: '46rem' }}>
            <h2>Tu agenda, gratis</h2>
            <p style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-mayor)' }}>
              Sin tarjeta para registrarte, sin mensualidad y sin comisión por cita. Tardas menos
              de diez minutos en dejarlo funcionando desde el teléfono.
            </p>
            <ul
              className="lista-filete"
              style={{ marginTop: 'var(--espacio-5)', borderTop: '1px solid rgba(255,255,255,.18)' }}
            >
              {[
                ['Se acabó apuntar citas en el WhatsApp', 'La agenda de todo tu equipo en una pantalla.'],
                ['No hay dobles citas', 'Dos clientas no pueden quedarse con la misma hora aunque confirmen a la vez.'],
                ['Cada quien ve lo suyo', 'Tu barbero ve su agenda. La caja y la configuración son tuyas.'],
              ].map(([titulo, texto]) => (
                <li
                  key={titulo}
                  style={{
                    padding: 'var(--espacio-4) 0',
                    borderBottom: '1px solid rgba(255,255,255,.18)',
                  }}
                >
                  <strong>{titulo}</strong>
                  <span style={{ display: 'block', opacity: 0.78, marginTop: '2px' }}>{texto}</span>
                </li>
              ))}
            </ul>
            <p style={{ marginTop: 'var(--espacio-6)' }}>
              <Link href="/para-negocios" className="boton boton--primario">
                Crear mi salón
              </Link>
            </p>
          </div>
        </section>

        {/* Índice de zonas: enlaces internos de verdad, que es lo que indexa Google. */}
        <section className="seccion">
          <div className="contenedor">
            <h2>Busca por tu zona</h2>
            <ul className="tira" style={{ marginTop: 'var(--espacio-4)' }}>
              {ZONAS.map(([nombre, slug]) => (
                <li key={slug}>
                  <Link href={`/buscar?zona=${slug}`} className="ficha">
                    {nombre}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Preguntas con `details`: acordeón nativo, accesible y sin una línea de JavaScript. */}
        <section className="seccion seccion--arena">
          <div className="contenedor" style={{ maxWidth: '46rem' }}>
            <h2>Preguntas</h2>
            <div style={{ marginTop: 'var(--espacio-5)' }}>
              {PREGUNTAS.map(({ p, r }) => (
                <details key={p} className="pregunta">
                  <summary>{p}</summary>
                  <p className="apagado">{r}</p>
                </details>
              ))}
            </div>
          </div>
        </section>
      </main>

      <Pie />
    </>
  )
}
