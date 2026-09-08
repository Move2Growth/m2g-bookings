import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { Calendario } from '@/componentes/calendario'
import { AccionesDeSalon } from '@/componentes/acciones-salon'
import { Cabecera } from '@/componentes/cabecera'
import { FotoDeSalon } from '@/componentes/foto'
import { Rotulo } from '@/componentes/rotulo'
import { PestanasClienteSiHaySesion } from '@/componentes/pestanas-cliente'
import { Pie } from '@/componentes/pie'
import {
  duracion,
  precio,
  verDisponibilidad,
  verPerfil,
  verResenas,
  type Perfil,
  type ResenasDelPerfil,
  type Slot,
} from '@/lib/api'

/**
 * El perfil público de un salón y sus horas libres.
 *
 * Es **la** página que tiene que indexar Google (MKT-7): de aquí llega la mitad del negocio.
 * Por eso se renderiza en servidor con sus metadatos y sus datos estructurados, y por eso el
 * contenido está en el HTML y no detrás de una llamada del navegador.
 *
 * El orden de la página es el orden de la decisión, no el del organigrama del salón: **qué
 * hacen y cuánto cuesta**, luego **cuándo puedo**, y solo después quién trabaja allí y qué
 * dicen las clientas. Quien ya sabe a qué viene reserva sin bajar; quien está comparando sigue
 * leyendo.
 */

type Props = {
  params: Promise<{ slug: string }>
  searchParams: Promise<{ servicio?: string; dia?: string }>
}

async function cargar(slug: string): Promise<Perfil | null> {
  try {
    return await verPerfil(slug)
  } catch {
    return null
  }
}

async function cargarResenas(slug: string): Promise<ResenasDelPerfil | null> {
  try {
    return await verResenas(slug)
  } catch {
    // Que fallen las reseñas no puede tumbar la ficha: es la página desde la que se reserva.
    return null
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const perfil = await cargar(slug)
  if (!perfil) return { title: 'Salón no encontrado' }

  return {
    title: perfil.nombre,
    description: `Reserva en ${perfil.nombre}${perfil.direccion ? `, ${perfil.direccion}` : ''}. Servicios, precios y horas libres.`,
    alternates: { canonical: `/${perfil.slug}` },
    openGraph: {
      title: perfil.nombre,
      description: `Mira las horas libres de ${perfil.nombre} y reserva sin llamar.`,
      images: perfil.fotos?.[0] ? [perfil.fotos[0]] : undefined,
    },
  }
}

/** Los días que se ofrecen de un vistazo. Siete y adelante: nadie reserva a cuarenta días. */
function proximosDias(desde: Date, cuantos = 7): Date[] {
  return Array.from({ length: cuantos }, (_, indice) => {
    const dia = new Date(desde)
    dia.setDate(dia.getDate() + indice)
    dia.setHours(0, 0, 0, 0)
    return dia
  })
}

function iso(dia: Date): string {
  return dia.toISOString().slice(0, 10)
}

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

/**
 * Agrupa los tramos por día.
 *
 * Un salón que cierra a mediodía manda dos tramos del mismo día, y sin agrupar se pinta
 * «Martes» dos veces seguidas, que se lee como un fallo. Además dos filas con la misma clave
 * hacen que React se queje con razón.
 */
function porDia(tramos: { dia: number; abre: string; cierra: string }[]) {
  const agrupados = new Map<number, string[]>()
  for (const t of [...tramos].sort((a, b) => a.dia - b.dia || a.abre.localeCompare(b.abre))) {
    const franjas = agrupados.get(t.dia) ?? []
    franjas.push(`${t.abre.slice(0, 5)} a ${t.cierra.slice(0, 5)}`)
    agrupados.set(t.dia, franjas)
  }
  return [...agrupados.entries()]
}

/** Mañana, tarde y noche: una rejilla de veinte horas seguidas no se lee. */
function franjas(slots: Slot[], zona: string): [string, Slot[]][] {
  const hora24 = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', hour12: false, timeZone: zona })
  const cajones: Record<string, Slot[]> = { Mañana: [], Tarde: [], Noche: [] }
  for (const slot of slots) {
    const h = Number(hora24.format(new Date(slot.inicio)))
    cajones[h < 12 ? 'Mañana' : h < 18 ? 'Tarde' : 'Noche'].push(slot)
  }
  return (Object.entries(cajones) as [string, Slot[]][]).filter(([, lista]) => lista.length > 0)
}

export default async function PaginaDeNegocio({ params, searchParams }: Props) {
  const { slug } = await params
  const { servicio: servicioPedido, dia: diaPedido } = await searchParams

  const [perfil, resenas] = await Promise.all([cargar(slug), cargarResenas(slug)])
  if (!perfil) notFound()

  const servicio =
    perfil.servicios.find((s) => s.id === servicioPedido) ?? perfil.servicios[0] ?? null

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
  //: Qué días del mes visible tienen algún hueco, para apagar los llenos en el calendario.
  let diasConHueco = new Set<string>()
  if (servicio) {
    try {
      const hoy = new Date()
      const desdeMes = new Date(Math.max(new Date(dia.getFullYear(), dia.getMonth(), 1).getTime(), hoy.getTime()))
      const hastaMes = new Date(dia.getFullYear(), dia.getMonth() + 1, 1)
      const mes = await verDisponibilidad(slug, [servicio.id], desdeMes, hastaMes)
      const enZona = new Intl.DateTimeFormat('en-CA', {
        timeZone: mes.zona,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      })
      diasConHueco = new Set(mes.slots.map((s) => enZona.format(new Date(s.inicio))))
    } catch {
      diasConHueco = new Set()
    }
    try {
      const disponibilidad = await verDisponibilidad(slug, [servicio.id], dia, finDelDia)
      slots = disponibilidad.slots
      zona = disponibilidad.zona
    } catch {
      slots = []
    }
  }

  const hora = new Intl.DateTimeFormat('es-PA', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: zona,
  })
  const diaCorto = new Intl.DateTimeFormat('es-PA', { weekday: 'short', day: 'numeric' })
  const fotos = perfil.fotos ?? []
  const nota = perfil.rating ?? resenas?.resumen.media ?? null
  const cuantasResenas = perfil.numero_reviews ?? resenas?.resumen.total ?? 0

  return (
    <>
      <Cabecera />
      <main>
        {/* Datos estructurados para Google: sin esto el perfil se indexa como texto suelto y
            no como un negocio con dirección, nota y servicios (MKT-7). */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'HealthAndBeautyBusiness',
              name: perfil.nombre,
              address: perfil.direccion ?? undefined,
              image: fotos,
              aggregateRating:
                nota && cuantasResenas > 0
                  ? { '@type': 'AggregateRating', ratingValue: nota, reviewCount: cuantasResenas }
                  : undefined,
              makesOffer: perfil.servicios.map((s) => ({
                '@type': 'Offer',
                itemOffered: { '@type': 'Service', name: s.nombre },
                price: s.precio_centavos !== null ? (s.precio_centavos / 100).toFixed(2) : undefined,
                priceCurrency: 'USD',
              })),
            }),
          }}
        />

        {/* Galería. Con una sola foto ocupa el ancho; con varias se desliza. Sin ninguna, un
            bloque de color con la inicial: una foto de banco engaña sobre cómo es el sitio. */}
        {fotos.length > 0 ? (
          <div className={fotos.length === 1 ? 'galeria galeria--una' : 'galeria'}>
            {fotos.slice(0, 6).map((foto, i) => (
              <FotoDeSalon
                key={foto}
                src={foto}
                ancho={1200}
                alto={800}
                sizes="(min-width: 900px) 60vw, 90vw"
                prioridad={i === 0}
              />
            ))}
          </div>
        ) : (
          /* Sin foto no hay hueco tapado: hay rótulo. El nombre entero hace de imagen y la
             trama dice el oficio, que es lo que el brandbook llama «rótulo pintado de un
             local» y hasta ahora no existía en ninguna pantalla. */
          <Rotulo nombre={perfil.nombre} categoria={perfil.categorias?.[0]} talla="cartel" />
        )}

        <div className="contenedor">
          <p style={{ marginTop: 'var(--espacio-4)' }}>
            <Link href="/buscar">← Todos los salones</Link>
          </p>

          <div className="identidad">
            <div>
              <h1>{perfil.nombre}</h1>
              <p className="identidad__meta">
                {nota !== null && cuantasResenas > 0 && (
                  <span className="cifras">
                    <span aria-hidden="true">★</span> {nota.toFixed(1)}
                    <span className="tenue"> ({cuantasResenas})</span>
                    <span className="oculto-visualmente">
                      de nota sobre 5, con {cuantasResenas} reseñas
                    </span>
                  </span>
                )}
                {perfil.zona && <span>{perfil.zona}</span>}
                {perfil.direccion && <span className="apagado">{perfil.direccion}</span>}
              </p>
            </div>
            <AccionesDeSalon
              negocioId={perfil.id}
              slug={perfil.slug}
              nombre={perfil.nombre}
              tieneWhatsapp={perfil.tiene_whatsapp}
            />
          </div>

          {/* El cartel del salón: lo escribe el dueño desde su portal y la API solo lo manda
              mientras está vigente. Va **antes** de la descripción porque es lo que caduca: una
              promoción de esta semana importa más que el texto de siempre. Si no hay ninguno
              encendido, aquí no queda ningún hueco. */}
          {perfil.anuncio && (
            <p className="aviso aviso--exito" style={{ marginTop: 'var(--espacio-4)' }}>
              {perfil.anuncio.texto}
            </p>
          )}

          {perfil.descripcion && <p className="medida identidad__texto">{perfil.descripcion}</p>}

          {perfil.atributos && perfil.atributos.length > 0 && (
            <ul className="atributos">
              {perfil.atributos.map((a) => (
                <li key={a.slug}>{a.nombre}</li>
              ))}
            </ul>
          )}

          <section className="bloque-panel">
            <h2>Servicios</h2>
            <ul className="lista-servicios">
              {perfil.servicios.map((s) => {
                const elegido = servicio?.id === s.id
                return (
                  <li key={s.id}>
                    <Link
                      href={`/${perfil.slug}?servicio=${s.id}&dia=${iso(dia)}#horas`}
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
          </section>

          {/* **Un salón sin nadie en el equipo no tiene horas ningún día, y decirle a quien mira
              «prueba otro día» es mandarlo a recorrer una semana entera para nada.** Pasa de
              verdad: publicar exige un servicio, horario, ubicación y una foto (D11), no un
              profesional, y el alta invita a saltarse el paso de las personas —«si trabajas
              sola, salta este paso»—. Ese salón se publica y el calendario sale vacío los siete
              días. Aquí se dice lo que hay y se ofrece la única salida que existe: escribirle. */}
          {servicio && perfil.equipo.length === 0 ? (
            <section className="bloque-horas" id="horas">
              <h2>Horas libres para {servicio.nombre}</h2>
              <p className="aviso aviso--info">
                Este salón todavía no tiene a nadie en el equipo, así que no puede dar horas por
                aquí.{' '}
                {perfil.tiene_whatsapp
                  ? 'Escríbele por WhatsApp con el botón de arriba y pídele la cita.'
                  : 'Todavía está montando su agenda; vuelve en unos días.'}
              </p>
            </section>
          ) : servicio && (
            <section className="bloque-horas" id="horas">
              <h2>Horas libres para {servicio.nombre}</h2>

              <nav aria-label="Días cercanos" className="tira" style={{ margin: 'var(--espacio-4) 0 var(--espacio-2)' }}>
                {dias.slice(0, 3).map((candidato) => {
                  const activo = iso(candidato) === iso(dia)
                  return (
                    <Link
                      key={iso(candidato)}
                      href={`/${perfil.slug}?servicio=${servicio.id}&dia=${iso(candidato)}#horas`}
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
                enlaceBase={`/${perfil.slug}?servicio=${servicio.id}&dia=`}
              />

              {slots.length === 0 ? (
                /* Un día sin huecos no es un error ni una pantalla vacía: dice qué pasa y qué
                   hacer ahora, que es la regla de los estados vacíos del design system. */
                <p className="aviso aviso--info">
                  No quedan horas para {servicio.nombre} este día. Prueba otro día de la fila de
                  arriba: un servicio de {duracion(servicio.duracion_minutos)} necesita un hueco
                  seguido.
                </p>
              ) : (
                franjas(slots, zona).map(([franja, deLaFranja]) => (
                  <div className="franja-horas" key={franja}>
                    <p className="franja-horas__rotulo">{franja}</p>
                    <ul className="rejilla-horas" style={{ marginTop: 0 }}>
                  {deLaFranja.map((slot) => {
                    const destino = new URLSearchParams({
                      negocio: perfil.slug,
                      servicio: servicio.id,
                      profesional: slot.profesional_id ?? '',
                      inicio: slot.inicio,
                      nombre: servicio.nombre,
                      zona,
                    })
                    return (
                      <li key={slot.inicio}>
                        {/* El hueco es un enlace y no un botón: tiene su propia URL, se puede
                            abrir en otra pestaña y sobrevive a que se recargue la página. Y
                            tocarlo no aparta nada: se compite por él al confirmar. */}
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

              <p className="tenue" style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-menor)' }}>
                Toca una hora para reservarla. Mirarla no la aparta: se confirma en la pantalla
                siguiente.
              </p>
            </section>
          )}

          {perfil.equipo.length > 0 && (
            /* El equipo deja de ser una lista de nombres y pasa a ser la puerta al perfil de
               cada persona (encargo §3): quien quiere elegir con quién se atiende empieza aquí.
               Se enlaza por slug, y por identificador cuando la ficha todavía no tiene: un nulo
               en una columna no puede dejar a nadie sin página. */
            <section className="bloque-panel">
              <h2>Quién te atiende</h2>
              <ul className="equipo">
                {perfil.equipo.map((p) => (
                  <li key={p.id}>
                    <Link href={`/${perfil.slug}/${p.slug ?? p.id}`} className="equipo__persona">
                      <span className="equipo__inicial" aria-hidden="true">
                        {p.nombre.trim().charAt(0)}
                      </span>
                      <span>
                        {p.nombre}
                        {p.titular && (
                          <span
                            className="tenue"
                            style={{ display: 'block', fontSize: 'var(--tipografia-tamano-menor)' }}
                          >
                            {p.titular}
                          </span>
                        )}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="bloque-panel bloque-panel--arena">
            <h2>Lo que dicen las clientas</h2>
            {!resenas || resenas.resumen.total === 0 ? (
              <p className="apagado medida" style={{ marginTop: 'var(--espacio-3)' }}>
                Todavía no hay reseñas. Solo puede dejar una quien haya venido de verdad: se
                pide después de la cita y no antes.
              </p>
            ) : (
              <>
                <div className="resumen-notas">
                  <span className="resumen-notas__media cifra-grande">
                    {resenas.resumen.media?.toFixed(1)}
                  </span>
                  <div className="resumen-notas__reparto">
                    {[5, 4, 3, 2, 1].map((n) => {
                      const cuantas = resenas.resumen.reparto?.[String(n)] ?? 0
                      const parte = resenas.resumen.total ? (cuantas / resenas.resumen.total) * 100 : 0
                      return (
                        <div key={n} className="resumen-notas__fila">
                          <span className="cifras">{n}</span>
                          <span className="resumen-notas__barra">
                            <span style={{ width: `${parte}%` }} />
                          </span>
                          <span className="cifras tenue">{cuantas}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>

                <ul className="resenas">
                  {resenas.resenas.slice(0, 8).map((r) => (
                    <li key={r.id} className="resena">
                      <p className="resena__cabeza">
                        <span className="cifras" aria-label={`${r.nota} de 5`}>
                          {'★'.repeat(r.nota)}
                          <span className="tenue">{'★'.repeat(5 - r.nota)}</span>
                        </span>
                        <span className="resena__autor">{r.autor}</span>
                        {r.profesional && <span className="tenue">con {r.profesional}</span>}
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
              </>
            )}
          </section>

          {perfil.horario && perfil.horario.length > 0 && (
            <section className="bloque-panel">
              <h2>Cuándo abre</h2>
              <ul className="filas" style={{ marginTop: 'var(--espacio-3)' }}>
                {porDia(perfil.horario).map(([dia, franjas]) => (
                  <li key={dia} className="fila">
                    <div className="fila__boton" style={{ cursor: 'default', minHeight: 48 }}>
                      <span className="fila__nombre">{DIAS[dia]}</span>
                      <span className="fila__cifra cifras">{franjas.join(' y ')}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </main>
      <Pie />
      <PestanasClienteSiHaySesion />
    </>
  )
}
