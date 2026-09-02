'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { conConsola, leerSesionDeConsola, type SesionDeConsola } from '@/lib/consola'

/**
 * Los pesos del ranking del marketplace.
 *
 * Es la pantalla con más consecuencias del producto: cambiar un número de aquí reordena quién
 * sale primero en toda Ciudad de Panamá. Por eso cada peso lleva escrito **qué hace y en qué
 * dirección**, y por eso se guarda todo junto con un botón explícito y no campo a campo.
 *
 * Ningún número del ranking vive en el código (ADR-0009): están en la base de datos y esta es
 * la pantalla que los toca. Guardar crea una versión nueva, no pisa la anterior.
 */

type Pesos = {
  version: number
  vigente_desde: string
  distancia: number
  rating: number
  reservas_recientes: number
  tasa_completado: number
  completitud: number
  actividad: number
  boost_nuevo: number
  radio_km: number
  decaimiento_km: number
  dias_recientes: number
  techo_reservas: number
  dias_actividad: number
  dias_boost: number
  bayes_m: number
  bayes_c: number
  patrocinados_por_pagina: number
  tamano_pagina: number
  notas: string | null
}

/** Los siete pesos que suman la puntuación, con lo que significa subir cada uno. */
const PESOS: [keyof Pesos, string, string][] = [
  ['distancia', 'Cerca de quien busca', 'Sube y los salones del barrio ganan a los buenos de lejos.'],
  ['rating', 'Nota de las clientas', 'Sube y manda la opinión por encima de la distancia.'],
  ['reservas_recientes', 'Se reserva mucho ahora', 'Sube y lo que está de moda se refuerza solo.'],
  ['tasa_completado', 'Atiende lo que acepta', 'Sube y penaliza a quien cancela o no aparece.'],
  ['completitud', 'Ficha completa', 'Sube y premia a quien puso fotos, precios y horario.'],
  ['actividad', 'Sigue vivo', 'Sube y hunde a los salones que llevan meses sin tocar nada.'],
  ['boost_nuevo', 'Empujón a los nuevos', 'Sube y un salón recién publicado tiene su oportunidad.'],
]

export default function Ranking() {
  const [sesion, setSesion] = useState<SesionDeConsola | null>(null)
  const [pesos, setPesos] = useState<Pesos | null>(null)
  const [borrador, setBorrador] = useState<Partial<Pesos>>({})
  const [notas, setNotas] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [guardado, setGuardado] = useState(false)

  useEffect(() => setSesion(leerSesionDeConsola()), [])

  const cargar = useCallback(async (actual: SesionDeConsola) => {
    setError(null)
    try {
      const datos = await conConsola<Pesos>('/api/v1/consola/ranking', { token: actual.acceso })
      setPesos(datos)
      setBorrador({})
      setNotas('')
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar los pesos.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  const hayCambios = Object.keys(borrador).length > 0

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Ranking</h1>
        {pesos && (
          <span className="tenue cifras">
            versión {pesos.version} · desde{' '}
            {new Intl.DateTimeFormat('es-PA', { day: 'numeric', month: 'short', year: 'numeric' }).format(
              new Date(pesos.vigente_desde),
            )}
          </span>
        )}
      </div>

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      )}

      {pesos === null && !error && <Esqueleto filas={7} alto={72} etiqueta="Cargando los pesos" />}

      {pesos && (
        <>
          <p className="aviso aviso--info">
            Esto reordena el marketplace entero. Guardar no pisa los pesos de ahora: crea una
            versión nueva, así que se puede volver atrás.
          </p>

          <section className="bloque-panel">
            <h2 className="etiqueta">Qué pesa en el orden</h2>
            <div className="formulario" style={{ marginTop: 'var(--espacio-4)' }}>
              {PESOS.map(([clave, titulo, explicacion]) => {
                const valor = (borrador[clave] ?? pesos[clave]) as number
                return (
                  <div key={clave} className="peso">
                    <label className="peso__etiqueta" htmlFor={`peso-${clave}`}>
                      {titulo}
                      <span className="cifras peso__valor">{valor.toFixed(2)}</span>
                    </label>
                    <input
                      id={`peso-${clave}`}
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={valor}
                      onChange={(e) =>
                        setBorrador((previo) => ({ ...previo, [clave]: Number(e.target.value) }))
                      }
                    />
                    <p className="peso__explicacion">{explicacion}</p>
                  </div>
                )
              })}
            </div>
          </section>

          <section className="bloque-panel">
            <h2 className="etiqueta">Patrocinados y página</h2>
            <div className="pareja" style={{ marginTop: 'var(--espacio-4)' }}>
              <label className="campo">
                <span>Patrocinados por página</span>
                <select
                  className="entrada"
                  value={(borrador.patrocinados_por_pagina ?? pesos.patrocinados_por_pagina) as number}
                  onChange={(e) =>
                    setBorrador((p) => ({ ...p, patrocinados_por_pagina: Number(e.target.value) }))
                  }
                >
                  {[0, 1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <label className="campo">
                <span>Resultados por página</span>
                <select
                  className="entrada"
                  value={(borrador.tamano_pagina ?? pesos.tamano_pagina) as number}
                  onChange={(e) => setBorrador((p) => ({ ...p, tamano_pagina: Number(e.target.value) }))}
                >
                  {[10, 15, 20, 25, 30].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="tenue" style={{ marginTop: 'var(--espacio-3)', fontSize: 'var(--tipografia-tamano-menor)' }}>
              Los patrocinados se intercalan entre los orgánicos, nunca en su lugar, y van
              siempre etiquetados. Eso no es un ajuste: es una regla del producto.
            </p>
          </section>

          <section className="bloque-panel">
            <h2 className="etiqueta">Nota de la ponderación bayesiana</h2>
            <div className="pareja" style={{ marginTop: 'var(--espacio-4)' }}>
              <label className="campo">
                <span>Media sembrada</span>
                <input
                  className="entrada cifras"
                  type="number"
                  min={0}
                  max={5}
                  step={0.1}
                  value={(borrador.bayes_m ?? pesos.bayes_m) as number}
                  onChange={(e) => setBorrador((p) => ({ ...p, bayes_m: Number(e.target.value) }))}
                />
              </label>
              <label className="campo">
                <span>Reseñas de confianza</span>
                <input
                  className="entrada cifras"
                  type="number"
                  min={0}
                  max={1000}
                  value={(borrador.bayes_c ?? pesos.bayes_c) as number}
                  onChange={(e) => setBorrador((p) => ({ ...p, bayes_c: Number(e.target.value) }))}
                />
              </label>
            </div>
            <p className="tenue" style={{ marginTop: 'var(--espacio-3)', fontSize: 'var(--tipografia-tamano-menor)' }}>
              Es lo que evita que un salón con una sola reseña de cinco estrellas se ponga por
              delante de otro con doscientas y un 4,7.
            </p>
          </section>

          <section className="bloque-panel">
            <label className="campo">
              <span>Por qué cambias esto</span>
              <input
                className="entrada"
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                placeholder="Queda con la versión. Dentro de un año es lo único que lo explica."
                maxLength={500}
              />
            </label>

            <div className="acciones" style={{ marginTop: 'var(--espacio-4)' }}>
              <button
                type="button"
                className="boton boton--cierra"
                disabled={!hayCambios || guardando}
                onClick={async () => {
                  if (!sesion) return
                  setGuardando(true)
                  setGuardado(false)
                  setError(null)
                  try {
                    await conConsola('/api/v1/consola/ranking', {
                      metodo: 'PUT',
                      token: sesion.acceso,
                      cuerpo: { ...borrador, notas: notas.trim() || null },
                    })
                    setGuardado(true)
                    void cargar(sesion)
                  } catch (fallo) {
                    setError(fallo instanceof Error ? fallo.message : 'No se pudo guardar.')
                  } finally {
                    setGuardando(false)
                  }
                }}
              >
                {guardando ? 'Guardando…' : 'Guardar versión nueva'}
              </button>
              {hayCambios && (
                <button type="button" className="boton boton--llano" onClick={() => setBorrador({})}>
                  Descartar cambios
                </button>
              )}
              {guardado && (
                <p role="status" className="aviso aviso--exito">
                  Guardado. Ya es la versión vigente.
                </p>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
