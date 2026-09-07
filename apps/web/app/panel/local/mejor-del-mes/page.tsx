'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'
import { dinero, type CategoriaGlobal, type FilaDelMes } from '@/lib/dueno'

/**
 * Mejor del mes: **por importe o por número de servicios**, y filtrable por categoría.
 *
 * Se enseña **la lista entera**, no solo el primero. Enseñar únicamente al ganador y esconder que
 * el segundo se quedó a dos servicios convierte un dato en un concurso, y un concurso que nadie
 * pidió dentro de un equipo pequeño hace daño. Aquí sirve para repartir turnos y para saber qué
 * se vende, no para colgar un cartel.
 *
 * El mes se navega hacia atrás porque la pregunta que se hace de verdad no es «¿cómo va este
 * mes?» —eso está en Finanzas— sino «¿cómo acabó el pasado?».
 */

type Criterio = 'importe' | 'servicios'

/** El primer día del mes, `cuantos` meses hacia atrás. */
function mesRelativo(cuantos: number): Date {
  const hoy = new Date()
  return new Date(hoy.getFullYear(), hoy.getMonth() + cuantos, 1, 0, 0, 0, 0)
}

export default function MejorDelMes() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [mes, setMes] = useState(0)
  const [criterio, setCriterio] = useState<Criterio>('importe')
  const [categoria, setCategoria] = useState<string | null>(null)
  const [categorias, setCategorias] = useState<CategoriaGlobal[]>([])
  const [filas, setFilas] = useState<FilaDelMes[] | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  useEffect(() => {
    if (!sesion) return
    // Solo las categorías del salón tendrían sentido, pero la API de categorías es global y no
    // sabe de este negocio. Se enseñan todas: una categoría sin servicios devuelve la lista a
    // cero, y eso es una respuesta honesta, no un error.
    conSesion<CategoriaGlobal[]>('/api/v1/catalogo/categorias', { token: sesion.acceso })
      .then(setCategorias)
      .catch(() => setCategorias([]))
  }, [sesion])

  const cargar = useCallback(
    async (actual: Sesion, cuantosMeses: number, como: Criterio, slug: string | null) => {
      setCargando(true)
      setError(null)
      const desde = mesRelativo(cuantosMeses)
      const hasta = mesRelativo(cuantosMeses + 1)
      const parametros = new URLSearchParams({
        desde: desde.toISOString(),
        hasta: hasta.toISOString(),
        criterio: como,
      })
      if (slug) parametros.set('categoria', slug)
      try {
        setFilas(
          await conSesion<FilaDelMes[]>(`/api/v1/negocio/mejor-del-mes?${parametros}`, {
            token: actual.acceso,
          }),
        )
      } catch (fallo) {
        setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar el mes.')
      } finally {
        setCargando(false)
      }
    },
    [],
  )

  useEffect(() => {
    if (sesion) void cargar(sesion, mes, criterio, categoria)
  }, [sesion, mes, criterio, categoria, cargar])

  const nombreDelMes = new Intl.DateTimeFormat('es-PA', { month: 'long', year: 'numeric' })
  const conAlgo = (filas ?? []).filter((f) => f.servicios > 0)
  // El de arriba, para poder decir a cuánto está cada uno de él. La lista ya llega ordenada por
  // el criterio pedido: reordenarla aquí sería tener dos criterios, el del servidor y el mío.
  const tope = conAlgo.length
    ? criterio === 'importe'
      ? conAlgo[0].importe_centavos
      : conAlgo[0].servicios
    : 0

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Mejor del mes</h1>
      </div>

      <nav aria-label="Cambiar de mes" className="dias">
        <button
          type="button"
          onClick={() => setMes((m) => m - 1)}
          className="dias__flecha"
          aria-label="Mes anterior"
        >
          ←
        </button>
        <div>
          <strong className="primera-mayuscula">{nombreDelMes.format(mesRelativo(mes))}</strong>
          <span className="tenue" style={{ display: 'block' }}>
            {mes === 0 ? 'el mes en curso, todavía sin cerrar' : 'mes cerrado'}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setMes((m) => Math.min(0, m + 1))}
          className="dias__flecha"
          aria-label="Mes siguiente"
          disabled={mes >= 0}
        >
          →
        </button>
      </nav>

      <div className="tira" role="group" aria-label="Ordenar por">
        <button
          type="button"
          className="ficha ficha--modo"
          aria-pressed={criterio === 'importe'}
          onClick={() => setCriterio('importe')}
        >
          Quién facturó más
        </button>
        <button
          type="button"
          className="ficha ficha--modo"
          aria-pressed={criterio === 'servicios'}
          onClick={() => setCriterio('servicios')}
        >
          Quién hizo más servicios
        </button>
      </div>

      {categorias.length > 0 && (
        <div className="tira" role="group" aria-label="De qué categoría">
          <button
            type="button"
            className="ficha ficha--modo"
            aria-pressed={categoria === null}
            onClick={() => setCategoria(null)}
          >
            Todo
          </button>
          {categorias.map((c) => (
            <button
              key={c.slug}
              type="button"
              className="ficha ficha--modo"
              aria-pressed={categoria === c.slug}
              onClick={() => setCategoria(c.slug)}
            >
              {c.nombre}
            </button>
          ))}
        </div>
      )}

      {error && (
        <BloqueDeError
          mensaje={error}
          reintentar={sesion ? () => void cargar(sesion, mes, criterio, categoria) : undefined}
        />
      )}

      {cargando && !error && <Esqueleto filas={4} alto={72} etiqueta="Cargando el mes" />}

      {!cargando && !error && conAlgo.length === 0 && (
        <Vacio
          icono={Iconos.equipo}
          titulo="Este mes todavía no hay nada que contar"
          texto={
            categoria
              ? 'Nadie ha atendido citas de esa categoría en este mes. Prueba con «Todo» o con el mes anterior.'
              : 'Solo cuentan las citas marcadas como atendidas. En cuanto marques la primera, aquí aparece quién la hizo.'
          }
        />
      )}

      {!cargando && !error && conAlgo.length > 0 && (
        <>
          <ul className="filas escalona">
            {conAlgo.map((fila, posicion) => {
              const valor = criterio === 'importe' ? fila.importe_centavos : fila.servicios
              return (
                <li key={fila.profesional_id} className="fila">
                  <div className="fila__boton" style={{ cursor: 'default' }}>
                    <span className="fila__principal">
                      <span className="fila__nombre">
                        <span className="cifras tenue">{posicion + 1}. </span>
                        {fila.nombre}
                      </span>
                      <span className="fila__detalle">
                        {fila.servicios} {fila.servicios === 1 ? 'servicio' : 'servicios'} ·{' '}
                        {dinero(fila.importe_centavos)}
                      </span>
                      {/* La distancia con el primero, en texto. Dice de un vistazo si el de
                          arriba saca dos cuerpos o si van pegados, que es la diferencia entre un
                          dato y un titular. Va en palabras y no en una barra de color porque una
                          barra sin eje ni escala se lee mal y encima habría que rehacerla cuando
                          cambie la dirección visual. */}
                      {posicion > 0 && (
                        <span className="fila__detalle tenue">
                          {criterio === 'importe'
                            ? `${dinero(tope - valor)} por detrás`
                            : `${tope - valor} ${tope - valor === 1 ? 'servicio' : 'servicios'} por detrás`}
                        </span>
                      )}
                    </span>
                    <span className="fila__cifra cifras">
                      {criterio === 'importe'
                        ? dinero(fila.importe_centavos)
                        : `${fila.servicios} serv.`}
                    </span>
                  </div>
                </li>
              )
            })}
          </ul>

          <p className="tenue" style={{ marginTop: 'var(--espacio-4)' }}>
            Solo cuentan las citas <strong>atendidas</strong>, con el importe que se guardó en cada
            cita. Subirle hoy el precio a un servicio no cambia lo que se facturó el mes pasado.
          </p>
        </>
      )}
    </div>
  )
}
