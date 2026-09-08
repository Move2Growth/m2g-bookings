import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { Cabecera } from '@/componentes/cabecera'
import { FotoDeSalon } from '@/componentes/foto'
import { PestanasClienteSiHaySesion } from '@/componentes/pestanas-cliente'
import { Pie } from '@/componentes/pie'
import { Redes } from '@/componentes/redes'
import { Rotulo } from '@/componentes/rotulo'
import { Calendario } from '@/componentes/calendario'
import {
  duracion,
  precio,
  verDisponibilidadDeProfesional,
  verPerfilDeProfesional,
  type PerfilDeProfesional,
  type Slot,
} from '@/lib/api'

/**
 * El perfil público de una persona (encargo 2026-09-07 §3).
 *
 * El encargo dice que **la clienta elige primero con quién se quiere atender**, y esta es la
 * pantalla donde eso pasa. No es una ficha de equipo dentro del salón: es una página propia,
 * con su URL, sus metadatos y su calendario, porque quien busca a Kevin busca a Kevin y no a
 * la barbería en la que trabaja hoy.
 *
 * **Es también el camino de reserva inverso entero**: persona → uno de *sus* servicios → hora.
 * Se resuelve en dos pantallas (esta y confirmar), no en tres, porque servicio y hora caben en
 * la misma vista: al tocar un servicio se recarga con sus horas debajo y sin salir de aquí.
 * El camino de siempre —negocio → servicio → profesional— sigue en `/[slug]` sin tocar.
 *
 * Renderizado en servidor por lo mismo que el perfil del salón: el contenido tiene que estar en
 * el HTML antes de ejecutar JavaScript, que es lo que ve el rastreador.
 */

type Props = {
  params: Promise<{ slug: string; profesional: string }>
  searchParams: Promise<{ servicio?: string; dia?: string }>
}

async function cargar(slug: string, quien: string): Promise<PerfilDeProfesional | null> {
  try {
    return await verPerfilDeProfesional(slug, quien)
  } catch {
    return null
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug, profesional } = await params
  const perfil = await cargar(slug, profesional)
  if (!perfil) return { title: 'Esa persona no está aquí' }

  const donde = perfil.negocio ? ` en ${perfil.negocio}` : ''
  return {
    title: `${perfil.nombre}${donde}`,
    description:
      perfil.titular ??
      `Reserva con ${perfil.nombre}${donde}. Mira sus servicios, sus trabajos y sus horas libres.`,
    alternates: { canonical: `/${slug}/${perfil.slug ?? perfil.id}` },
    openGraph: {
      title: `${perfil.nombre}${donde}`,
      description: perfil.titular ?? `Mira las horas libres de ${perfil.nombre} y reserva sin llamar.`,
      images: perfil.foto ? [perfil.foto] : undefined,
    },
  }
}

/** Siete días y adelante: nadie reserva a cuarenta días. Igual que en la ficha del salón. */
function proximosDias(desde: Date, cuantos = 7): Date[] {
  return Array.from({ length: cuantos }, (_, indice) => {
    const dia = new Date(desde)
    dia.setDate(dia.getDate() + indice)
    dia.setHours(0, 0, 0, 0)
    return dia
  })
}

/**
 * Parte las horas libres en mañana, tarde y noche. Se corta a las 12 y a las 18 porque es como
 * se habla, no por ninguna razón técnica; las franjas vacías no se pintan.
 */
function franjas(slots: Slot[], zona: string): [string, Slot[]][] {
  const hora24 = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', hour12: false, timeZone: zona })
  const cajones: Record<string, Slot[]> = { Mañana: [], Tarde: [], Noche: [] }
  for (const slot of slots) {
    const h = Number(hora24.format(new Date(slot.inicio)))
    cajones[h < 12 ? 'Mañana' : h < 18 ? 'Tarde' : 'Noche'].push(slot)
  }
  return (Object.entries(cajones) as [string, Slot[]][]).filter(([, lista]) => lista.length > 0)
}

function iso(dia: Date): string {
  return dia.toISOString().slice(0, 10)
}

export default async function PaginaDeProfesional({ params, searchParams }: Props) {
  const { slug, profesional: quien } = await params
  const { servicio: servicioPedido, dia: diaPedido } = await searchParams

  const perfil = await cargar(slug, quien)
  if (!perfil) notFound()

  const aqui = `/${slug}/${perfil.slug ?? perfil.id}`
  const servicio =
    perfil.catalogo.find((s) => s.id === servicioPedido) ?? perfil.catalogo[0] ?? null

  //: **Hoy es hoy en el salón, y una sola vez.** Se calculaba de dos maneras: la tira de días y
  //: las horas salían de `new Date()` —que en el servidor es UTC—, y el calendario lo hacía otra
  //: vez en el navegador. De siete de la tarde en adelante en Panamá eso son **dos días
  //: distintos**: la tira ofrecía mañana como si fuera hoy, el calendario marcaba hoy, y React
  //: avisaba de que el HTML servido y el hidratado no coincidían. Ahora sale de aquí, ya
  //: partido en año, mes y día con la zona del salón, y de aquí lo toma todo.
  const hoyIso = new Intl.DateTimeFormat('en-CA', {
    timeZone: perfil.zona_horaria,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
  const dia = new Date(`${diaPedido ?? hoyIso}T00:00:00`)
  const dias = proximosDias(new Date(`${hoyIso}T00:00:00`))
  const finDelDia = new Date(dia)
  finDelDia.setDate(finDelDia.getDate() + 1)

  let slots: Slot[] = []
  let zona = perfil.zona_horaria
  let falloDeHoras = false
  //: Días del mes visible que tienen al menos un hueco. Es lo que permite apagar en el
  //  calendario los días llenos en vez de dejar que se pulsen para no enseñar nada.
  let diasConHueco = new Set<string>()
  if (servicio) {
    try {
      const libre = await verDisponibilidadDeProfesional(perfil.id, [servicio.id], dia, finDelDia)
      slots = libre.slots
      zona = libre.zona
    } catch {
      // Que se caiga el motor no puede tumbar el perfil entero: se dice y se ofrece recargar.
      falloDeHoras = true
    }

    // Una segunda consulta, del mes entero, solo para pintar el calendario. Va con caché de un
    // minuto: aquí no se reserva, se decide qué día abrir, y una hora de más o de menos en esta
    // rejilla no engaña a nadie. La del día sigue sin caché.
    try {
      const hoy = new Date()
      const desdeMes = new Date(Math.max(new Date(dia.getFullYear(), dia.getMonth(), 1).getTime(), hoy.getTime()))
      const hastaMes = new Date(dia.getFullYear(), dia.getMonth() + 1, 1)
      const mes = await verDisponibilidadDeProfesional(perfil.id, [servicio.id], desdeMes, hastaMes, 60)
      diasConHueco = new Set(
        mes.slots.map((s) =>
          new Intl.DateTimeFormat('en-CA', {
            timeZone: mes.zona,
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
          }).format(new Date(s.inicio)),
        ),
      )
    } catch {
      // Sin el mes, el calendario deja pulsar cualquier día futuro: es peor que apagarlos, pero
      // mucho mejor que no poder elegir fecha.
      diasConHueco = new Set()
    }
  }

  const hora = new Intl.DateTimeFormat('es-PA', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: zona,
  })
  const diaCorto = new Intl.DateTimeFormat('es-PA', { weekday: 'short', day: 'numeric' })
  const conServicio = perfil.trabajos.filter((t) => t.servicio)
  const sinServicio = perfil.trabajos.filter((t) => !t.servicio)

  return (
    <>
      <Cabecera />
      <main>
        {/* Datos estructurados: una persona que trabaja en un negocio, no un negocio. Sin esto
            Google indexa el nombre como texto suelto y no como quien presta el servicio. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'Person',
              name: perfil.nombre,
              jobTitle: perfil.titular ?? undefined,
              description: perfil.descripcion ?? undefined,
              image: perfil.foto ?? undefined,
              worksFor: perfil.negocio
                ? { '@type': 'HealthAndBeautyBusiness', name: perfil.negocio }
                : undefined,
              sameAs: [
                perfil.redes.instagram_url,
                perfil.redes.facebook_url,
                perfil.redes.x_url,
              ].filter(Boolean),
              aggregateRating:
                perfil.nota && perfil.numero_resenas > 0
                  ? {
                      '@type': 'AggregateRating',
                      ratingValue: perfil.nota,
                      reviewCount: perfil.numero_resenas,
                    }
                  : undefined,
            }),
          }}
        />

        {perfil.foto ? (
          <div className="galeria galeria--una">
            <FotoDeSalon
              src={perfil.foto}
              ancho={1200}
              alto={800}
              sizes="(min-width: 900px) 60vw, 90vw"
              prioridad
            />
          </div>
        ) : (
          <Rotulo nombre={perfil.nombre} categoria={undefined} talla="cartel" />
        )}

        <div className="contenedor">
          <p style={{ marginTop: 'var(--espacio-4)' }}>
            <Link href={`/${slug}`}>← {perfil.negocio ?? 'Volver al salón'}</Link>
          </p>

          <div className="identidad">
            <div>
              <h1>{perfil.nombre}</h1>
              {perfil.titular && <p className="identidad__texto medida">{perfil.titular}</p>}
              <p className="identidad__meta">
                {perfil.nota !== null && perfil.numero_resenas > 0 && (
                  <span className="cifras">
                    <span aria-hidden="true">★</span> {perfil.nota.toFixed(1)}
                    <span className="tenue"> ({perfil.numero_resenas})</span>
                    <span className="oculto-visualmente">
                      de nota sobre 5, con {perfil.numero_resenas} reseñas
                    </span>
                  </span>
                )}
                {perfil.negocio_slug && (
                  <span>
                    <Link href={`/${perfil.negocio_slug}`}>{perfil.negocio}</Link>
                  </span>
                )}
                {perfil.direccion && <span className="apagado">{perfil.direccion}</span>}
              </p>
            </div>
          </div>

          {/* Los tres números del encargo: años, cuánta gente ha atendido y cuántas citas. Van
              juntos y en cifras, porque es lo que decide a quien está comparando dos personas.
              Solo se pinta lo que existe: un «0 clientes» no da confianza, la quita. */}
          {(perfil.anos_de_experiencia || perfil.clientes_atendidos > 0) && (
            <div className="datos vistazo" style={{ marginTop: 'var(--espacio-4)' }}>
              {perfil.anos_de_experiencia ? (
                <div>
                  <b className="cifras">{perfil.anos_de_experiencia}</b>
                  <small>{perfil.anos_de_experiencia === 1 ? 'año de oficio' : 'años de oficio'}</small>
                </div>
              ) : null}
              {perfil.clientes_atendidos > 0 && (
                <div>
                  <b className="cifras">{perfil.clientes_atendidos}</b>
                  <small>
                    {perfil.clientes_atendidos === 1 ? 'persona atendida' : 'personas atendidas'}
                  </small>
                </div>
              )}
              {perfil.citas_atendidas > 0 && (
                <div>
                  <b className="cifras">{perfil.citas_atendidas}</b>
                  <small>{perfil.citas_atendidas === 1 ? 'cita hecha' : 'citas hechas'}</small>
                </div>
              )}
            </div>
          )}

          {perfil.descripcion && (
            <p className="medida identidad__texto" style={{ marginTop: 'var(--espacio-4)' }}>
              {perfil.descripcion}
            </p>
          )}

          <Redes redes={perfil.redes} de={perfil.nombre} />

          {/* Sus servicios: los que hace esta persona, no los del salón entero. Es la mitad de
              lo que el encargo pide, y la que evita que alguien reserve un balayage con quien
              solo hace barbas. */}
          <section className="bloque-panel">
            <h2>Qué hace {perfil.nombre.split(' ')[0]}</h2>
            {perfil.catalogo.length === 0 ? (
              <p className="apagado medida" style={{ marginTop: 'var(--espacio-3)' }}>
                Todavía no tiene servicios asignados en {perfil.negocio ?? 'este salón'}. Los
                asigna quien administra el salón desde su panel de equipo.
              </p>
            ) : (
              <ul className="lista-servicios">
                {perfil.catalogo.map((s) => {
                  const elegido = servicio?.id === s.id
                  return (
                    <li key={s.id}>
                      <Link
                        href={`${aqui}?servicio=${s.id}&dia=${iso(dia)}#horas`}
                        aria-current={elegido ? 'true' : undefined}
                        className={elegido ? 'servicio servicio--elegido' : 'servicio'}
                      >
                        <span>
                          <strong style={{ fontWeight: 'var(--tipografia-pesos-medio)' }}>
                            {s.nombre}
                          </strong>
                          <span className="cifras servicio__duracion">
                            {duracion(s.duracion_minutos)}
                          </span>
                        </span>
                        <span className="cifras" style={{ whiteSpace: 'nowrap' }}>
                          {s.tipo_de_precio === 'desde' ? 'desde ' : ''}
                          {precio(s.precio_centavos)}
                        </span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>

          {servicio && (
            <section className="bloque-horas" id="horas">
              <h2>
                Horas de {perfil.nombre.split(' ')[0]} para {servicio.nombre}
              </h2>

              {/* Atajos para lo que se pide el 80 % de las veces, y debajo el calendario
                  de siempre para todo lo demás. */}
              <nav aria-label="Días cercanos" className="tira" style={{ margin: 'var(--espacio-4) 0 var(--espacio-2)' }}>
                {dias.slice(0, 3).map((candidato) => {
                  const activo = iso(candidato) === iso(dia)
                  return (
                    <Link
                      key={iso(candidato)}
                      href={`${aqui}?servicio=${servicio.id}&dia=${iso(candidato)}#horas`}
                      aria-current={activo ? 'date' : undefined}
                      className="ficha cifras"
                    >
                      {diaCorto.format(candidato)}
                    </Link>
                  )
                })}
              </nav>

              <Calendario
                diaElegidoIso={diaPedido ?? hoyIso}
                diasConHueco={diasConHueco}
                hoyIso={hoyIso}
                enlaceBase={`${aqui}?servicio=${servicio.id}&dia=`}
              />

              {falloDeHoras ? (
                <p role="alert" className="aviso aviso--error">
                  No pudimos consultar sus horas ahora mismo.{' '}
                  <Link href={`${aqui}?servicio=${servicio.id}&dia=${iso(dia)}#horas`} style={{ color: 'inherit' }}>
                    Volver a intentarlo
                  </Link>
                  .
                </p>
              ) : slots.length === 0 ? (
                <p className="aviso aviso--info">
                  {perfil.nombre.split(' ')[0]} no tiene horas libres este día para{' '}
                  {servicio.nombre}. Prueba otro día de la fila de arriba, o{' '}
                  <Link href={`/${slug}`}>mira quién más lo hace en {perfil.negocio}</Link>.
                </p>
              ) : (
                // Agrupadas por franja: una rejilla de veinte horas seguidas no se lee, y
                // «por la tarde» es como pide la hora todo el mundo.
                franjas(slots, zona).map(([franja, deLaFranja]) => (
                  <div className="franja-horas" key={franja}>
                    <p className="franja-horas__rotulo">{franja}</p>
                    <ul className="rejilla-horas" style={{ marginTop: 0 }}>
                      {deLaFranja.map((slot) => {
                        const destino = new URLSearchParams({
                          negocio: slug,
                          servicio: servicio.id,
                          // La persona va explícita: aquí no vale «cualquiera», que es justo lo
                          // que distingue este camino del de siempre.
                          profesional: perfil.id,
                          inicio: slot.inicio,
                          nombre: `${servicio.nombre} con ${perfil.nombre}`,
                          zona,
                        })
                        return (
                          <li key={slot.inicio}>
                            <Link href={`/reservar?${destino}`} className="hora">
                              {hora.format(new Date(slot.inicio))}
                            </Link>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                ))
              )}

              <p
                className="tenue"
                style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-menor)' }}
              >
                Estas horas son las de {perfil.nombre}, no las del salón. Tocar una no la aparta:
                se confirma en la pantalla siguiente.
              </p>
            </section>
          )}

          {/* Sus trabajos. Los que están atados a un servicio se dicen con el servicio delante:
              eso es exactamente lo que el encargo pide, «que se vea quién hizo qué». */}
          {perfil.trabajos.length > 0 && (
            <section className="bloque-panel">
              <h2>Sus trabajos</h2>
              <ul className="fotos" style={{ marginTop: 'var(--espacio-4)' }}>
                {[...conServicio, ...sinServicio].map((t) => (
                  <li key={t.id} className="foto">
                    <FotoDeSalon
                      src={t.url}
                      alt={t.descripcion ?? (t.servicio ? `${t.servicio}, por ${perfil.nombre}` : '')}
                      ancho={296}
                      alto={208}
                      sizes="148px"
                    />
                    {t.servicio && <span className="etiqueta">{t.servicio}</span>}
                    {t.descripcion && (
                      <span className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
                        {t.descripcion}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="bloque-panel bloque-panel--arena">
            <h2>Lo que dicen de {perfil.nombre.split(' ')[0]}</h2>
            {perfil.resenas.length === 0 ? (
              <p className="apagado medida" style={{ marginTop: 'var(--espacio-3)' }}>
                Todavía no hay reseñas suyas. Solo puede dejar una quien haya venido de verdad:
                se pide después de la cita y no antes.
              </p>
            ) : (
              <ul className="resenas">
                {perfil.resenas.map((r) => (
                  <li key={r.id} className="resena">
                    <p className="resena__cabeza">
                      <span className="cifras" aria-label={`${r.nota} de 5`}>
                        {'★'.repeat(r.nota)}
                        <span className="tenue">{'★'.repeat(5 - r.nota)}</span>
                      </span>
                      <span className="resena__autor">{r.autor}</span>
                    </p>
                    {r.texto && <p className="resena__texto medida">{r.texto}</p>}
                    {r.respuesta && (
                      <p className="resena__respuesta medida">
                        <strong>Respuesta del salón:</strong> {r.respuesta.texto}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </main>
      <Pie />
      <PestanasClienteSiHaySesion />
    </>
  )
}
