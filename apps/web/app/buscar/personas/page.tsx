import type { Metadata } from 'next'
import Link from 'next/link'
import { Cabecera } from '@/componentes/cabecera'
import { Vacio } from '@/componentes/estados'
import { FichaProfesional } from '@/componentes/ficha-profesional'
import { ModoDeBusqueda } from '@/componentes/modo-busqueda'
import { Iconos } from '@/componentes/pestanas'
import { PestanasClienteSiHaySesion } from '@/componentes/pestanas-cliente'
import { Pie } from '@/componentes/pie'
import { buscarProfesionales, conProximaHora, ErrorDeApi, type ProfesionalEnLista } from '@/lib/api'
import { nombreDeCategoria, nombreDeZona } from '@/lib/taxonomia'

/**
 * Buscar personas, no locales (encargo 2026-09-07 §3 y §5).
 *
 * **Convive con `/buscar`, no la sustituye.** Son dos URL y dos listas: quien busca «barbería en
 * San Francisco» quiere locales, y quien busca «Kevin» quiere a Kevin. Un solo buscador con un
 * conmutador escondido acaba enseñando siempre lo que no se pidió.
 *
 * Igual que la de salones: se resuelve en el servidor, la búsqueda vive en la URL y por eso se
 * comparte, se guarda en marcadores y la sigue un rastreador.
 */

type Filtros = { texto?: string; servicio?: string; zona?: string; negocio?: string; orden?: string }
type Props = { searchParams: Promise<Filtros> }

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const { zona, servicio } = await searchParams
  const nombreZona = nombreDeZona(zona)
  const oficio = nombreDeCategoria(servicio)
  const titulo = oficio
    ? `Quién hace ${oficio.toLowerCase()}${nombreZona ? ` en ${nombreZona}` : ' en Ciudad de Panamá'}`
    : nombreZona
      ? `Profesionales de belleza en ${nombreZona}`
      : 'Elige con quién te atiendes en Ciudad de Panamá'
  return {
    title: titulo,
    description:
      'Busca a la persona, no al local: mira su oficio, sus años, su nota y sus horas libres, y reserva con ella.',
  }
}

export default async function BuscarPersonas({ searchParams }: Props) {
  const filtros = await searchParams

  let personas: ProfesionalEnLista[] = []
  let fallo: string | null = null
  try {
    // La próxima hora libre no viene en la lista: se sonda persona a persona. Si el motor
    // tarda o falla, la fila sale igual y dice «ver horas» en vez de desaparecer.
    personas = await conProximaHora(await buscarProfesionales(filtros))
  } catch (error) {
    fallo = error instanceof ErrorDeApi ? error.message : 'No pudimos cargar a las personas.'
  }

  const hayFiltro = Boolean(filtros.texto || filtros.zona || filtros.servicio || filtros.negocio)

  return (
    <>
      <Cabecera />

      <main>
        <div className="cabecera-buscar">
          <div className="contenedor">
            <h1>Elige con quién te atiendes</h1>

            {/* Un formulario normal, sin JavaScript: envía por GET a esta misma URL y por eso
                funciona con el navegador desnudo, que es lo que ve el rastreador y lo que
                queda cuando el paquete todavía no ha bajado en 3G. */}
            <form className="buscador__fila" action="/buscar/personas" method="get">
              <label htmlFor="q" className="oculto-visualmente">
                A quién buscas
              </label>
              <input
                id="q"
                name="texto"
                type="search"
                className="entrada"
                defaultValue={filtros.texto ?? ''}
                placeholder="Un nombre, o «barbero», «colorista»…"
              />
              <button type="submit" className="boton boton--primario">
                Buscar
              </button>
            </form>

            <div style={{ marginTop: 'var(--espacio-3)' }}>
              <ModoDeBusqueda modo="personas" consulta={filtros.texto} />
            </div>
          </div>
        </div>

        <div className="contenedor seccion seccion--arena-suelta">
          <p className="tenue buscador__cuantos" aria-live="polite">
            {fallo
              ? ''
              : `${personas.length} ${personas.length === 1 ? 'persona' : 'personas'}${
                  hayFiltro ? ' con esa búsqueda' : ' atendiendo en Ciudad de Panamá'
                }`}
          </p>

          {fallo && (
            <p role="status" className="aviso aviso--error" style={{ marginTop: 'var(--espacio-4)' }}>
              {fallo} Comprueba que la API está levantada con <code>make arriba</code>.
            </p>
          )}

          {!fallo && personas.length === 0 && (
            <div style={{ marginTop: 'var(--espacio-4)' }}>
              <Vacio
                icono={Iconos.persona}
                titulo={
                  hayFiltro
                    ? 'No encontramos a nadie con eso'
                    : 'Todavía no hay nadie publicado por aquí'
                }
                texto={
                  hayFiltro ? (
                    <>
                      Prueba otro nombre, o{' '}
                      <Link href="/buscar/personas">mira a todo el mundo</Link>. También puedes{' '}
                      <Link href="/buscar">buscar por local</Link>.
                    </>
                  ) : (
                    <>
                      Mientras tanto, <Link href="/buscar">busca por local</Link>.
                    </>
                  )
                }
              />
            </div>
          )}

          {personas.length > 0 && (
            <ul className="resultados escalona">
              {personas.map((p, i) => (
                <FichaProfesional key={p.id} persona={p} indice={i} />
              ))}
            </ul>
          )}
        </div>
      </main>

      <Pie />
      <PestanasClienteSiHaySesion />
    </>
  )
}
