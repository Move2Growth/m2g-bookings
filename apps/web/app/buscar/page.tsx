import type { Metadata } from 'next'
import Link from 'next/link'
import { Suspense } from 'react'
import { Buscador } from '@/componentes/buscador'
import { Cabecera } from '@/componentes/cabecera'
import { Vacio } from '@/componentes/estados'
import { ListaSalones } from '@/componentes/lista-salones'
import { Iconos } from '@/componentes/pestanas'
import { PestanasClienteSiHaySesion } from '@/componentes/pestanas-cliente'
import { Pie } from '@/componentes/pie'
import { buscarNegocios, ErrorDeApi, type ResultadoDeBusqueda } from '@/lib/api'
import { nombreDeZona } from '@/lib/taxonomia'

/**
 * El marketplace.
 *
 * Se resuelve en el servidor y con la búsqueda en la URL, a propósito: cada combinación de
 * filtros tiene su propia dirección, se comparte por WhatsApp y la puede seguir un rastreador.
 * Un buscador que solo funciona con JavaScript es un buscador que Google no usa, y de Google
 * llega media clientela.
 */

type Filtros = {
  texto?: string
  zona?: string
  categoria?: string
  precio_min?: string
  precio_max?: string
  rating_min?: string
  disponibilidad?: string
  dia?: string
  abierto_ahora?: string
  orden?: string
}

type Props = { searchParams: Promise<Filtros> }

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const { zona, categoria } = await searchParams
  const nombreZona = nombreDeZona(zona)
  // El título de una página de zona es lo que se lee en Google, así que dice el sitio con su
  // nombre propio y no «resultados de búsqueda».
  const titulo = nombreZona
    ? `Salones y barberías en ${nombreZona}`
    : categoria
      ? 'Salones por servicio en Ciudad de Panamá'
      : 'Buscar salones y barberías en Ciudad de Panamá'
  return {
    title: titulo,
    description: nombreZona
      ? `Mira las horas libres de los salones de ${nombreZona} y reserva sin llamar.`
      : 'Busca por servicio o por zona en Ciudad de Panamá y mira las horas libres de cada salón.',
  }
}

export default async function Buscar({ searchParams }: Props) {
  const filtros = await searchParams

  let resultados: ResultadoDeBusqueda[] = []
  let fallo: string | null = null
  try {
    resultados = await buscarNegocios(filtros)
  } catch (error) {
    // Si la API no responde, la página sale igual y lo dice. Una pantalla en blanco no informa
    // de nada, y una excepción sin capturar tumba el renderizado del servidor.
    fallo = error instanceof ErrorDeApi ? error.message : 'No pudimos cargar los salones.'
  }

  const hayFiltro = Boolean(
    filtros.texto ||
      filtros.zona ||
      filtros.categoria ||
      filtros.precio_max ||
      filtros.rating_min ||
      filtros.disponibilidad ||
      filtros.abierto_ahora,
  )
  const nombreZona = nombreDeZona(filtros.zona)

  return (
    <>
      <Cabecera />

      <main className="seccion">
        <div className="contenedor">
          <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>
            {nombreZona ? `Salones en ${nombreZona}` : 'Salones y barberías en Ciudad de Panamá'}
          </h1>

          <Suspense fallback={<div style={{ height: 132 }} />}>
            <Buscador />
          </Suspense>

          <p className="tenue buscador__cuantos" aria-live="polite">
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
            <div style={{ marginTop: 'var(--espacio-4)' }}>
              <Vacio
                icono={Iconos.buscar}
                titulo={
                  hayFiltro
                    ? 'No encontramos salones con eso'
                    : 'Todavía no hay salones publicados por aquí'
                }
                texto={
                  hayFiltro ? (
                    <>
                      Prueba otra palabra, quita algún filtro o{' '}
                      <Link href="/buscar">empieza de cero</Link>.
                    </>
                  ) : (
                    <>
                      Si tienes un salón,{' '}
                      <Link href="/para-negocios">el tuyo puede ser el primero</Link>.
                    </>
                  )
                }
              />
            </div>
          )}

          {resultados.length > 0 && <ListaSalones salones={resultados} />}
        </div>
      </main>

      <Pie />
      <PestanasClienteSiHaySesion />
    </>
  )
}
