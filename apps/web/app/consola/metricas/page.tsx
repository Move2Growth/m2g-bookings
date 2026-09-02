'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { conConsola, leerSesionDeConsola, type SesionDeConsola } from '@/lib/consola'

/**
 * Las métricas de la plataforma.
 *
 * Cuatro cifras y tres series, y ninguna que no se pueda explicar en una frase. Un panel con
 * veinte gráficas no se mira: se mira una vez el día que se monta.
 *
 * Las series se dibujan con divs y no con una librería de gráficas. Una librería de gráficas
 * son cientos de kilobytes para pintar treinta barras, y esta pantalla también se abre desde un
 * teléfono.
 */

type Punto = { dia: string; valor: number }

type Metricas = {
  negocios_totales: number
  negocios_publicados: number
  negocios_suspendidos: number
  reservas_por_dia: Punto[]
  impresiones_por_dia: Punto[]
  clics_por_dia: Punto[]
  reportes_abiertos: number
}

export default function MetricasDeConsola() {
  const [sesion, setSesion] = useState<SesionDeConsola | null>(null)
  const [datos, setDatos] = useState<Metricas | null>(null)
  const [dias, setDias] = useState(30)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesionDeConsola()), [])

  const cargar = useCallback(async (actual: SesionDeConsola, cuantos: number) => {
    setError(null)
    try {
      setDatos(
        await conConsola<Metricas>(`/api/v1/consola/metricas?dias=${cuantos}`, {
          token: actual.acceso,
        }),
      )
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar las métricas.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion, dias)
  }, [sesion, dias, cargar])

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Métricas</h1>
        <div className="tira">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              type="button"
              className="ficha ficha--modo"
              aria-pressed={dias === d}
              onClick={() => setDias(d)}
            >
              {d} días
            </button>
          ))}
        </div>
      </div>

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion, dias) : undefined} />
      )}

      {datos === null && !error && <Esqueleto filas={4} alto={96} etiqueta="Cargando las métricas" />}

      {datos && (
        <>
          <div className="cifras-clave">
            <Cifra titulo="Negocios publicados" valor={datos.negocios_publicados} />
            <Cifra titulo="Dados de alta" valor={datos.negocios_totales} />
            <Cifra titulo="Suspendidos" valor={datos.negocios_suspendidos} />
            <Cifra titulo="Reportes sin resolver" valor={datos.reportes_abiertos} />
          </div>

          <Serie titulo="Reservas por día" puntos={datos.reservas_por_dia} />
          <Serie titulo="Veces que se enseñó una ficha" puntos={datos.impresiones_por_dia} />
          <Serie titulo="Clics en una ficha" puntos={datos.clics_por_dia} />

          <p className="tenue" style={{ marginTop: 'var(--espacio-5)', fontSize: 'var(--tipografia-tamano-menor)' }}>
            Las impresiones y los clics salen ya contados por día, no de recorrer eventos: la
            serie de un año se pinta igual de rápido que la de una semana.
          </p>
        </>
      )}
    </div>
  )
}

function Cifra({ titulo, valor }: { titulo: string; valor: number }) {
  return (
    <div className="cifra-clave">
      <span className="cifra-clave__valor cifra-grande">{valor}</span>
      <span className="cifra-clave__titulo">{titulo}</span>
    </div>
  )
}

function Serie({ titulo, puntos }: { titulo: string; puntos: Punto[] }) {
  const maximo = Math.max(1, ...puntos.map((p) => p.valor))
  const total = puntos.reduce((suma, p) => suma + p.valor, 0)
  const fecha = new Intl.DateTimeFormat('es-PA', { day: 'numeric', month: 'short' })

  return (
    <section className="bloque-panel">
      <div className="cabeza-seccion" style={{ marginBlock: 0 }}>
        <h2 className="etiqueta">{titulo}</h2>
        <span className="cifras tenue">{total} en total</span>
      </div>

      {total === 0 ? (
        <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
          Todavía no hay nada que contar en este periodo.
        </p>
      ) : (
        <ol className="serie" aria-label={titulo}>
          {puntos.map((p) => (
            <li key={p.dia} className="serie__barra" title={`${fecha.format(new Date(`${p.dia}T12:00:00`))}: ${p.valor}`}>
              <span style={{ height: `${Math.round((p.valor / maximo) * 100)}%` }} />
              <span className="oculto-visualmente">
                {fecha.format(new Date(`${p.dia}T12:00:00`))}: {p.valor}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
