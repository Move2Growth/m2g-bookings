import Link from 'next/link'
import { NOMBRE } from '@/lib/marca'
import { buscarNegocios, ErrorDeApi, type ResultadoDeBusqueda } from '@/lib/api'

/**
 * La portada del marketplace: buscar y encontrar.
 *
 * Se renderiza **en servidor** (ADR-0011): la mitad de la clientela llega buscando «barbería
 * en San Francisco», y una página que llega vacía y se rellena con JavaScript no la indexa
 * nadie. La búsqueda va por formulario y método GET a propósito — así cada búsqueda tiene su
 * propia URL, se puede compartir por WhatsApp y el rastreador la puede seguir.
 */

type Props = { searchParams: Promise<{ q?: string; zona?: string }> }

const ZONAS = [
  { slug: 'bella-vista', nombre: 'Bella Vista' },
  { slug: 'el-cangrejo', nombre: 'El Cangrejo' },
  { slug: 'obarrio', nombre: 'Obarrio' },
  { slug: 'costa-del-este', nombre: 'Costa del Este' },
  { slug: 'san-francisco', nombre: 'San Francisco' },
]

export default async function Portada({ searchParams }: Props) {
  const { q, zona } = await searchParams

  let resultados: ResultadoDeBusqueda[] = []
  let fallo: string | null = null
  try {
    resultados = await buscarNegocios({ texto: q, zona })
  } catch (error) {
    // Si la API no responde, la página **sale igual** y lo dice. Una pantalla en blanco no
    // informa de nada, y una excepción sin capturar tumba el renderizado del servidor.
    fallo = error instanceof ErrorDeApi ? error.message : 'No pudimos cargar los negocios.'
  }

  return (
    <main className="contenido">
      <header style={{ marginBottom: 'var(--espacio-5)' }}>
        <p
          style={{
            color: 'var(--color-acento)',
            fontWeight: 'var(--tipografia-pesos-medio)',
            marginBottom: 'var(--espacio-2)',
          }}
        >
          {NOMBRE}
        </p>
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-1)' }}>
          Reserva en salones y barberías de Panamá
        </h1>
        <p style={{ color: 'var(--color-texto-suave)', marginTop: 'var(--espacio-3)' }}>
          Sin llamar y sin esperar respuesta por WhatsApp. Eliges servicio, profesional y hora.
        </p>
      </header>

      <form
        method="get"
        style={{ display: 'flex', gap: 'var(--espacio-2)', marginBottom: 'var(--espacio-4)' }}
      >
        <label style={{ flex: 1 }}>
          <span className="oculto-visualmente">Qué buscas</span>
          <input
            type="search"
            name="q"
            defaultValue={q ?? ''}
            placeholder="Corte, balayage, barbería…"
            style={{
              width: '100%',
              minHeight: 'var(--espacio-toque-minimo)',
              padding: 'var(--espacio-3)',
              fontSize: 'var(--tipografia-tamano-cuerpo)',
              fontFamily: 'inherit',
              border: '1px solid var(--color-borde-fuerte)',
              borderRadius: 'var(--radio-normal)',
              background: 'var(--color-superficie)',
              color: 'var(--color-texto)',
            }}
          />
        </label>
        <button
          type="submit"
          style={{
            minHeight: 'var(--espacio-toque-minimo)',
            padding: '0 var(--espacio-4)',
            border: 'none',
            borderRadius: 'var(--radio-normal)',
            background: 'var(--color-acento)',
            color: 'var(--color-acento-texto)',
            fontFamily: 'inherit',
            fontWeight: 'var(--tipografia-pesos-medio)',
            cursor: 'pointer',
          }}
        >
          Buscar
        </button>
      </form>

      <nav
        aria-label="Buscar por zona"
        style={{
          display: 'flex',
          gap: 'var(--espacio-2)',
          overflowX: 'auto',
          paddingBottom: 'var(--espacio-2)',
          marginBottom: 'var(--espacio-4)',
        }}
      >
        {ZONAS.map((z) => {
          const activa = zona === z.slug
          return (
            <Link
              key={z.slug}
              href={activa ? '/' : `/?zona=${z.slug}`}
              aria-current={activa ? 'true' : undefined}
              style={{
                flex: '0 0 auto',
                minHeight: 'var(--espacio-toque-minimo)',
                display: 'grid',
                placeItems: 'center',
                padding: '0 var(--espacio-3)',
                borderRadius: 'var(--radio-pildora)',
                border: `1px solid ${activa ? 'var(--color-acento)' : 'var(--color-borde)'}`,
                background: activa ? 'var(--color-acento)' : 'var(--color-superficie)',
                color: activa ? 'var(--color-acento-texto)' : 'inherit',
                textDecoration: 'none',
                fontSize: 'var(--tipografia-tamano-menor)',
                whiteSpace: 'nowrap',
              }}
            >
              {z.nombre}
            </Link>
          )
        })}
      </nav>

      {fallo && (
        <p
          role="status"
          style={{
            background: 'var(--color-peligro-suave)',
            color: 'var(--color-peligro)',
            padding: 'var(--espacio-4)',
            borderRadius: 'var(--radio-grande)',
          }}
        >
          {fallo} Comprueba que la API está levantada con <code>make arriba</code>.
        </p>
      )}

      {!fallo && resultados.length === 0 && (
        /* Un resultado vacío dice qué pasó y qué hacer, no «sin resultados» a secas. */
        <p
          style={{
            background: 'var(--color-superficie)',
            border: '1px solid var(--color-borde)',
            borderRadius: 'var(--radio-grande)',
            padding: 'var(--espacio-4)',
            color: 'var(--color-texto-suave)',
          }}
        >
          {q || zona
            ? 'No encontramos negocios con eso. Prueba con otra palabra o quita el filtro de zona.'
            : 'Todavía no hay negocios publicados. Carga los datos de ejemplo con make semilla.'}
        </p>
      )}

      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--espacio-3)' }}>
        {resultados.map((negocio) => (
          <li key={negocio.slug}>
            <Link
              href={`/${negocio.slug}`}
              style={{
                display: 'block',
                background: 'var(--color-superficie)',
                border: '1px solid var(--color-borde)',
                borderRadius: 'var(--radio-grande)',
                padding: 'var(--espacio-4)',
                textDecoration: 'none',
                color: 'inherit',
                minHeight: 'var(--espacio-toque-minimo)',
              }}
            >
              {negocio.patrocinado && (
                /* Un patrocinado va etiquetado **siempre** y por encima del nombre, donde se
                   lee antes de decidir. Es la regla MKT-4 y no admite matices. */
                <span
                  style={{
                    display: 'inline-block',
                    marginBottom: 'var(--espacio-1)',
                    fontSize: 'var(--tipografia-tamano-micro)',
                    color: 'var(--color-texto-suave)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                  }}
                >
                  Patrocinado
                </span>
              )}
              <h2 style={{ fontSize: 'var(--tipografia-tamano-mayor)' }}>{negocio.nombre}</h2>
              <p
                style={{
                  color: 'var(--color-texto-suave)',
                  fontSize: 'var(--tipografia-tamano-menor)',
                  marginTop: 'var(--espacio-1)',
                }}
              >
                {[negocio.zona, negocio.direccion].filter(Boolean).join(' · ')}
              </p>
              {negocio.distancia_metros !== null && (
                <p
                  className="cifras"
                  style={{
                    marginTop: 'var(--espacio-2)',
                    fontSize: 'var(--tipografia-tamano-menor)',
                  }}
                >
                  A {(negocio.distancia_metros / 1000).toFixed(1)} km
                </p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  )
}
