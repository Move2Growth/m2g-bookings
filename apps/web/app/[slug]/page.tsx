import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import {
  duracion,
  precio,
  verDisponibilidad,
  verPerfil,
  type Perfil,
  type Slot,
} from '@/lib/api'

/**
 * El perfil público de un negocio y sus horas libres.
 *
 * Es **la** página que tiene que indexar Google (MKT-7): de aquí llega la mitad del negocio.
 * Por eso se renderiza en servidor con sus metadatos y sus datos estructurados, y por eso el
 * contenido está en el HTML y no detrás de una llamada del navegador.
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

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const perfil = await cargar(slug)
  if (!perfil) return { title: 'Negocio no encontrado' }

  return {
    title: perfil.nombre,
    description: `Reserva en ${perfil.nombre}${perfil.direccion ? `, ${perfil.direccion}` : ''}. Servicios, precios y horas libres.`,
    alternates: { canonical: `/${perfil.slug}` },
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

export default async function PaginaDeNegocio({ params, searchParams }: Props) {
  const { slug } = await params
  const { servicio: servicioPedido, dia: diaPedido } = await searchParams

  const perfil = await cargar(slug)
  if (!perfil) notFound()

  const servicio =
    perfil.servicios.find((s) => s.id === servicioPedido) ?? perfil.servicios[0] ?? null

  const dias = proximosDias(new Date())
  const dia = diaPedido ? new Date(`${diaPedido}T00:00:00`) : dias[0]
  const finDelDia = new Date(dia)
  finDelDia.setDate(finDelDia.getDate() + 1)

  let slots: Slot[] = []
  let zona = perfil.zona_horaria
  if (servicio) {
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

  return (
    <main className="contenido">
      {/* Datos estructurados para Google: sin esto el perfil se indexa como texto suelto y
          no como un negocio con dirección y servicios (MKT-7). */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'HealthAndBeautyBusiness',
            name: perfil.nombre,
            address: perfil.direccion ?? undefined,
            makesOffer: perfil.servicios.map((s) => ({
              '@type': 'Offer',
              itemOffered: { '@type': 'Service', name: s.nombre },
              price: s.precio_centavos !== null ? (s.precio_centavos / 100).toFixed(2) : undefined,
              priceCurrency: 'USD',
            })),
          }),
        }}
      />

      <p style={{ marginBottom: 'var(--espacio-4)' }}>
        <Link href="/">← Todos los negocios</Link>
      </p>

      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-1)' }}>{perfil.nombre}</h1>
      {perfil.direccion && (
        <p style={{ color: 'var(--color-texto-suave)', marginTop: 'var(--espacio-2)' }}>
          {perfil.direccion}
        </p>
      )}

      <section style={{ marginTop: 'var(--espacio-6)' }}>
        <h2 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Servicios</h2>
        <ul
          style={{
            listStyle: 'none',
            padding: 0,
            margin: 'var(--espacio-4) 0 0',
            display: 'grid',
            gap: 'var(--espacio-2)',
          }}
        >
          {perfil.servicios.map((s) => {
            const elegido = servicio?.id === s.id
            return (
              <li key={s.id}>
                <Link
                  href={`/${perfil.slug}?servicio=${s.id}&dia=${iso(dia)}`}
                  aria-current={elegido ? 'true' : undefined}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 'var(--espacio-3)',
                    alignItems: 'baseline',
                    minHeight: 'var(--espacio-toque-minimo)',
                    padding: 'var(--espacio-3) var(--espacio-4)',
                    background: elegido ? 'var(--color-acento-suave)' : 'var(--color-superficie)',
                    border: `1px solid ${elegido ? 'var(--color-acento)' : 'var(--color-borde)'}`,
                    borderRadius: 'var(--radio-grande)',
                    textDecoration: 'none',
                    color: 'inherit',
                  }}
                >
                  <span>
                    <strong style={{ fontWeight: 'var(--tipografia-pesos-medio)' }}>
                      {s.nombre}
                    </strong>
                    <span
                      className="cifras"
                      style={{
                        display: 'block',
                        color: 'var(--color-texto-suave)',
                        fontSize: 'var(--tipografia-tamano-menor)',
                      }}
                    >
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

      {servicio && (
        <section style={{ marginTop: 'var(--espacio-6)' }}>
          <h2 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>
            Horas libres para {servicio.nombre}
          </h2>

          <nav
            aria-label="Elegir día"
            style={{
              display: 'flex',
              gap: 'var(--espacio-2)',
              overflowX: 'auto',
              margin: 'var(--espacio-4) 0',
              paddingBottom: 'var(--espacio-2)',
            }}
          >
            {dias.map((candidato) => {
              const activo = iso(candidato) === iso(dia)
              return (
                <Link
                  key={iso(candidato)}
                  href={`/${perfil.slug}?servicio=${servicio.id}&dia=${iso(candidato)}`}
                  aria-current={activo ? 'date' : undefined}
                  className="cifras"
                  style={{
                    flex: '0 0 auto',
                    minWidth: '4.5rem',
                    minHeight: 'var(--espacio-toque-minimo)',
                    display: 'grid',
                    placeItems: 'center',
                    padding: 'var(--espacio-2)',
                    borderRadius: 'var(--radio-normal)',
                    border: `1px solid ${activo ? 'var(--color-acento)' : 'var(--color-borde)'}`,
                    background: activo ? 'var(--color-acento)' : 'var(--color-superficie)',
                    color: activo ? 'var(--color-acento-texto)' : 'inherit',
                    textDecoration: 'none',
                  }}
                >
                  {diaCorto.format(candidato)}
                </Link>
              )
            })}
          </nav>

          {slots.length === 0 ? (
            /* Un día sin huecos no es un error ni una pantalla vacía: dice qué pasa y qué
               hacer ahora, que es la regla de los estados vacíos del design system. */
            <p
              style={{
                background: 'var(--color-superficie)',
                border: '1px solid var(--color-borde)',
                borderRadius: 'var(--radio-grande)',
                padding: 'var(--espacio-4)',
                color: 'var(--color-texto-suave)',
              }}
            >
              No quedan horas para {servicio.nombre} este día. Prueba otro día de la fila de
              arriba: un servicio de {duracion(servicio.duracion_minutos)} necesita un hueco
              seguido.
            </p>
          ) : (
            <ul
              style={{
                listStyle: 'none',
                margin: 0,
                padding: 0,
                display: 'grid',
                gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
                gap: 'var(--espacio-2)',
              }}
            >
              {slots.map((slot) => {
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
                        tocarlo **no aparta nada**: se compite por él al confirmar. */}
                    <Link
                      href={`/reservar?${destino}`}
                      className="cifras"
                      style={{
                        display: 'grid',
                        placeItems: 'center',
                        minHeight: 'var(--espacio-toque-minimo)',
                        padding: 'var(--espacio-2)',
                        background: 'var(--color-superficie)',
                        border: '1px solid var(--color-borde-fuerte)',
                        borderRadius: 'var(--radio-normal)',
                        textDecoration: 'none',
                        color: 'inherit',
                      }}
                    >
                      {hora.format(new Date(slot.inicio))}
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}

          <p
            style={{
              marginTop: 'var(--espacio-4)',
              color: 'var(--color-texto-tenue)',
              fontSize: 'var(--tipografia-tamano-menor)',
            }}
          >
            Toca una hora para reservarla. Mirarla no la aparta: se confirma en la pantalla
            siguiente.
          </p>
        </section>
      )}
    </main>
  )
}
