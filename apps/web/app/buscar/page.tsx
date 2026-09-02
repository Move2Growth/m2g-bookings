import type { Metadata } from 'next'
import Link from 'next/link'
import { Cabecera } from '@/componentes/cabecera'
import { Pie } from '@/componentes/pie'
import { buscarNegocios, ErrorDeApi, type ResultadoDeBusqueda } from '@/lib/api'

export const metadata: Metadata = {
  title: 'Buscar salones y barberías',
  description:
    'Busca por servicio o por zona en Ciudad de Panamá y mira las horas libres de cada salón.',
}

/**
 * El marketplace.
 *
 * El buscador va por formulario con método GET a propósito: cada búsqueda tiene su URL, se
 * comparte por WhatsApp y el rastreador la puede seguir. Un buscador que solo funciona con
 * JavaScript es un buscador que Google no usa, y de Google llega media clientela.
 */

type Props = { searchParams: Promise<{ texto?: string; zona?: string; categoria?: string }> }

const ZONAS = [
  ['Bella Vista', 'bella-vista'],
  ['El Cangrejo', 'el-cangrejo'],
  ['Obarrio', 'obarrio'],
  ['San Francisco', 'san-francisco'],
  ['Costa del Este', 'costa-del-este'],
  ['Juan Díaz', 'juan-diaz'],
]

const CATEGORIAS = [
  ['Barbería', 'barberia'],
  ['Peluquería', 'peluqueria'],
  ['Uñas', 'unas'],
  ['Pestañas y cejas', 'pestanas-cejas'],
  ['Spa y masajes', 'spa-masajes'],
  ['Estética', 'estetica'],
]

function enlaceCon(actual: Record<string, string | undefined>, clave: string, valor: string) {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(actual)) if (v && k !== clave) p.set(k, v)
  if (actual[clave] !== valor) p.set(clave, valor)
  const cadena = p.toString()
  return cadena ? `/buscar?${cadena}` : '/buscar'
}

export default async function Buscar({ searchParams }: Props) {
  const filtros = await searchParams
  const { texto, zona, categoria } = filtros

  let resultados: ResultadoDeBusqueda[] = []
  let fallo: string | null = null
  try {
    resultados = await buscarNegocios({ texto, zona, categoria })
  } catch (error) {
    // Si la API no responde, la página sale igual y lo dice. Una pantalla en blanco no informa
    // de nada, y una excepción sin capturar tumba el renderizado del servidor.
    fallo = error instanceof ErrorDeApi ? error.message : 'No pudimos cargar los salones.'
  }

  const hayFiltro = Boolean(texto || zona || categoria)

  return (
    <>
      <Cabecera />

      <main className="seccion">
        <div className="contenedor">
          <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>
            {zona
              ? `Salones en ${ZONAS.find(([, s]) => s === zona)?.[0] ?? zona}`
              : 'Salones y barberías en Ciudad de Panamá'}
          </h1>

          <form
            method="get"
            style={{
              display: 'flex',
              gap: 'var(--espacio-2)',
              marginTop: 'var(--espacio-4)',
              maxWidth: '34rem',
            }}
          >
            {zona && <input type="hidden" name="zona" value={zona} />}
            {categoria && <input type="hidden" name="categoria" value={categoria} />}
            <div className="campo" style={{ flex: 1, minWidth: 0 }}>
              <label htmlFor="texto" className="oculto-visualmente">
                Qué buscas
              </label>
              <input
                id="texto"
                className="entrada"
                type="search"
                name="texto"
                defaultValue={texto ?? ''}
                placeholder="Corte, balayage, uñas…"
              />
            </div>
            <button type="submit" className="boton boton--primario">
              Buscar
            </button>
          </form>

          <nav aria-label="Filtrar por zona" className="tira" style={{ marginTop: 'var(--espacio-4)' }}>
            {ZONAS.map(([nombre, slug]) => (
              <Link
                key={slug}
                href={enlaceCon(filtros, 'zona', slug)}
                className="ficha"
                aria-current={zona === slug ? 'true' : undefined}
              >
                {nombre}
              </Link>
            ))}
          </nav>

          <nav aria-label="Filtrar por servicio" className="tira" style={{ marginTop: 'var(--espacio-2)' }}>
            {CATEGORIAS.map(([nombre, slug]) => (
              <Link
                key={slug}
                href={enlaceCon(filtros, 'categoria', slug)}
                className="ficha"
                aria-current={categoria === slug ? 'true' : undefined}
              >
                {nombre}
              </Link>
            ))}
          </nav>

          <p className="tenue" style={{ marginTop: 'var(--espacio-5)' }} aria-live="polite">
            {fallo
              ? ''
              : `${resultados.length} ${resultados.length === 1 ? 'salón' : 'salones'}${
                  hayFiltro ? ' con esos filtros' : ' publicados'
                }`}
          </p>

          {fallo && (
            <p role="status" className="aviso aviso--error" style={{ marginTop: 'var(--espacio-4)' }}>
              {fallo} Comprueba que la API está levantada con <code>make arriba</code>.
            </p>
          )}

          {!fallo && resultados.length === 0 && (
            /* Un resultado vacío dice qué pasó y qué hacer, no «sin resultados» a secas. */
            <div className="panel" style={{ marginTop: 'var(--espacio-4)' }}>
              <p>
                {hayFiltro
                  ? 'No encontramos salones con eso.'
                  : 'Todavía no hay salones publicados por aquí.'}
              </p>
              <p className="apagado" style={{ marginTop: 'var(--espacio-2)' }}>
                {hayFiltro ? (
                  <>
                    Prueba otra palabra o <Link href="/buscar">quita los filtros</Link>.
                  </>
                ) : (
                  <>
                    Si tienes un salón, <Link href="/para-negocios">el tuyo puede ser el primero</Link>.
                  </>
                )}
              </p>
            </div>
          )}

          <ul className="resultados">
            {resultados.map((negocio) => (
              <li key={negocio.slug}>
                <Link href={`/${negocio.slug}`} className="resultado">
                  {negocio.patrocinado && (
                    /* Un patrocinado va etiquetado siempre y encima del nombre, donde se lee
                       antes de decidir. Es la regla MKT-4 y no admite matices. */
                    <span className="etiqueta">Patrocinado</span>
                  )}
                  <h2>{negocio.nombre}</h2>
                  <p className="apagado">
                    {[negocio.zona, negocio.direccion].filter(Boolean).join(' · ')}
                  </p>
                  {negocio.distancia_metros !== null && (
                    <p className="tenue cifras">
                      A {(negocio.distancia_metros / 1000).toFixed(1)} km
                    </p>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </main>

      <Pie />
    </>
  )
}
