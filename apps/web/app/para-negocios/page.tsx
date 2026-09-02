import type { Metadata } from 'next'
import Image from 'next/image'
import Link from 'next/link'
import { Cabecera } from '@/componentes/cabecera'
import { Pie } from '@/componentes/pie'

export const metadata: Metadata = {
  title: 'Tu agenda, gratis',
  description:
    'Agenda, equipo, ficha pública y recordatorios para tu salón. Sin tarjeta, sin mensualidad y sin comisión por cita. Operativo en menos de diez minutos.',
}

/**
 * La landing del salón.
 *
 * Aquí no se vende «gestión»: se desmonta un escepticismo concreto. La dueña de un salón ha
 * visto muchos «gratis» con letra pequeña, así que la página tiene que decir dónde está el
 * dinero antes de que lo pregunte. Si no, no se registra.
 */

const LO_QUE_RESUELVE = [
  {
    titulo: 'Se acabó apuntar citas en el WhatsApp',
    texto:
      'La agenda de todo tu equipo en una pantalla, desde tu teléfono. Ves el día, mueves una cita y apuntas a quien entró por la puerta sin soltar la tijera.',
  },
  {
    titulo: 'No hay dobles citas',
    texto:
      'Dos clientas no pueden quedarse con la misma hora aunque confirmen a la vez. No lo evita un aviso: lo impide la base de datos.',
  },
  {
    titulo: 'Cada quien ve lo suyo',
    texto:
      'Tu profesional ve su agenda y sus clientas. La caja, los precios y la configuración son tuyos y solo tuyos.',
  },
  {
    titulo: 'Tus clientas te encuentran',
    texto:
      'Tu ficha sale en las búsquedas de tu zona con tus servicios, tus precios y tus horas libres. Y tienes una dirección corta para tu bio de Instagram.',
  },
]

const PLAN = [
  ['Agenda, equipo, ficha pública y recordatorios', 'Incluido'],
  ['Comisión por cada reserva que entra', 'Ninguna'],
  ['Tarjeta de crédito para registrarte', 'No hace falta'],
  ['Profesionales que puedes dar de alta', 'Sin tope'],
  ['Citas al mes', 'Sin tope'],
]

export default function ParaNegocios() {
  return (
    <>
      <Cabecera />

      <main>
        <section className="seccion">
          <div className="contenedor hero" style={{ alignItems: 'center' }}>
            <div>
              <h1>Tu agenda, gratis</h1>
              <p
                className="apagado medida"
                style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-mayor)' }}
              >
                Sin comisión por reserva. Ni ahora, ni cuando tengas la agenda llena. Tardas
                menos de diez minutos en dejarlo funcionando desde el teléfono.
              </p>
              <p style={{ marginTop: 'var(--espacio-5)', display: 'flex', gap: 'var(--espacio-3)', flexWrap: 'wrap' }}>
                <Link href="/entrar" className="boton boton--primario">
                  Crear mi salón
                </Link>
                <Link href="/buscar" className="boton boton--secundario">
                  Ver cómo se ve mi ficha
                </Link>
              </p>
            </div>
            <div className="hero__foto">
              <Image
                src="/fotos/spa.webp"
                alt="Manos de una terapeuta trabajando la espalda de una clienta"
                width={1000}
                height={1000}
                priority
                sizes="(min-width: 900px) 45vw, 100vw"
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            </div>
          </div>
        </section>

        {/* Dónde está el dinero, dicho antes de que lo pregunten. Es la sección que decide si
            alguien se registra o cierra la pestaña. */}
        <section className="seccion seccion--arena filo">
          <div className="contenedor">
            <h2>Dónde está el truco</h2>
            <p className="apagado medida" style={{ marginTop: 'var(--espacio-4)' }}>
              En ningún sitio, y por eso conviene explicarlo. Bukeo gana cuando un salón quiere
              más clientas y compra aparecer primero en su categoría y su zona durante unos días.
              Es opcional, va siempre marcado como patrocinado, nunca esconde a los salones que
              no pagan y no toca la nota de nadie. Si nunca compras visibilidad, nunca pagas nada.
            </p>
            <p className="tenue medida" style={{ marginTop: 'var(--espacio-3)' }}>
              El precio de esa visibilidad depende de la zona y de los días, y lo verás antes de
              comprarla. Todavía no está a la venta: primero tiene que haber clientas buscando.
            </p>

            <table className="tabla-plan">
              <caption className="oculto-visualmente">Qué incluye el plan gratuito</caption>
              <tbody>
                {PLAN.map(([que, valor]) => (
                  <tr key={que}>
                    <th scope="row">{que}</th>
                    <td className="cifras">{valor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="seccion filo">
          <div className="contenedor">
            <h2>Qué te quita de encima</h2>
            <div className="rejilla rejilla--2" style={{ marginTop: 'var(--espacio-5)' }}>
              {LO_QUE_RESUELVE.map(({ titulo, texto }) => (
                <div key={titulo} style={{ borderTop: '2px solid var(--color-tinta)', paddingTop: 'var(--espacio-3)' }}>
                  <h3>{titulo}</h3>
                  <p className="apagado" style={{ marginTop: 'var(--espacio-2)' }}>
                    {texto}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="seccion seccion--holgada seccion--tinta filo">
          <div className="contenedor">
            <h2>Lo que hace falta para publicar</h2>
            <p className="medida" style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-mayor)' }}>
              Un servicio, tu horario, dónde estás y una foto. Nada más. Mientras tanto tu salón
              existe en borrador y no lo ve nadie.
            </p>
            <p style={{ marginTop: 'var(--espacio-6)' }}>
              <Link href="/entrar" className="boton boton--primario">
                Empezar ahora
              </Link>
            </p>
          </div>
        </section>
      </main>

      <Pie />
    </>
  )
}
