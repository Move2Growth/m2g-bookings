'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { Hoja } from '@/componentes/hoja'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * El horario del salón y las reglas de la agenda.
 *
 * Tres cosas distintas en una pantalla porque las tres responden a la misma pregunta —«cuándo
 * se puede reservar»— y separarlas obliga a ir y volver para entender por qué un hueco no
 * aparece:
 *
 * 1. **El horario semanal**: cuándo abre el salón. Es el techo de todo lo demás.
 * 2. **Las reglas**: con cuánta antelación, cada cuántos minutos, hasta cuándo se cancela.
 * 3. **Los cierres**: vacaciones, un día que no se abre, los feriados de Panamá.
 *
 * El horario del salón no es el de cada profesional: este manda como límite y el de cada
 * persona se recorta dentro. Se dice en pantalla porque si no, se configura dos veces y no
 * cuadra ninguna.
 */

type Tramo = { dia: number; abre: string; cierra: string }

type Ajustes = {
  granularidad_minutos: number
  antelacion_minima_minutos: number
  antelacion_maxima_dias: number
  auto_confirmar: boolean
  ventana_cancelacion_horas: number
  ventana_resena_dias: number
  bloquear_tras_ausencias: number | null
  permitir_cualquier_profesional: boolean
  resumen_diario: boolean
}

type Ausencia = {
  id: string
  profesional_id: string
  profesional: string
  desde: string
  hasta: string
  motivo: string | null
  activa: boolean
}

type Feriado = { fecha: string; nombre: string; ya_cerrado: boolean }

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

export default function Horario() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [horario, setHorario] = useState<Tramo[] | null>(null)
  const [ajustes, setAjustes] = useState<Ajustes | null>(null)
  const [ausencias, setAusencias] = useState<Ausencia[]>([])
  const [feriados, setFeriados] = useState<Feriado[]>([])
  const [error, setError] = useState<string | null>(null)
  const [guardado, setGuardado] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [nuevaAusencia, setNuevaAusencia] = useState(false)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      const [h, a, aus, fer] = await Promise.all([
        conSesion<Tramo[]>('/api/v1/negocio/horario', { token: actual.acceso }),
        conSesion<Ajustes>('/api/v1/negocio/ajustes', { token: actual.acceso }),
        conSesion<Ausencia[]>('/api/v1/negocio/ausencias', { token: actual.acceso }),
        conSesion<Feriado[]>('/api/v1/negocio/feriados', { token: actual.acceso }),
      ])
      setHorario(h)
      setAjustes(a)
      setAusencias(aus)
      setFeriados(fer)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar tu horario.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  function alternarDia(dia: number) {
    setHorario((previo) => {
      const actual = previo ?? []
      if (actual.some((t) => t.dia === dia)) return actual.filter((t) => t.dia !== dia)
      return [...actual, { dia, abre: '09:00', cierra: '18:00' }].sort((a, b) => a.dia - b.dia)
    })
  }

  async function guardarHorario() {
    if (!sesion || !horario) return
    setGuardando(true)
    setGuardado(false)
    setError(null)
    try {
      await conSesion('/api/v1/negocio/horario', {
        metodo: 'PUT',
        token: sesion.acceso,
        cuerpo: { horario },
      })
      setGuardado(true)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo guardar el horario.')
    } finally {
      setGuardando(false)
    }
  }

  async function cambiarAjuste(cambio: Partial<Ajustes>) {
    if (!sesion || !ajustes) return
    setAjustes({ ...ajustes, ...cambio })
    try {
      await conSesion('/api/v1/negocio/ajustes', {
        metodo: 'PATCH',
        token: sesion.acceso,
        cuerpo: cambio,
      })
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo guardar el ajuste.')
      void cargar(sesion)
    }
  }

  if (error && !horario) {
    return (
      <div className="contenedor" style={{ paddingTop: 'var(--espacio-5)' }}>
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      </div>
    )
  }

  return (
    <div className="contenedor">
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)', marginBlock: 'var(--espacio-5) var(--espacio-4)' }}>
        Horario y reglas
      </h1>

      {horario === null && <Esqueleto filas={4} alto={64} etiqueta="Cargando tu horario" />}

      {horario !== null && (
        <>
          <section className="bloque-panel">
            <h2 className="etiqueta">Cuándo abre el salón</h2>
            <p className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
              Es el techo: nadie de tu equipo puede tener horas fuera de aquí.
            </p>

            <div className="tira tira--envuelve" style={{ marginTop: 'var(--espacio-3)' }}>
              {DIAS.map((nombre, i) => (
                <button
                  key={i}
                  type="button"
                  className="ficha"
                  aria-pressed={horario.some((t) => t.dia === i)}
                  onClick={() => alternarDia(i)}
                >
                  {nombre.slice(0, 3)}
                </button>
              ))}
            </div>

            <ul className="tramos">
              {horario.map((t) => (
                <li key={t.dia} className="tramo">
                  <span className="tramo__dia">{DIAS[t.dia]}</span>
                  <input
                    type="time"
                    className="entrada cifras"
                    value={t.abre}
                    onChange={(e) =>
                      setHorario((p) =>
                        (p ?? []).map((x) => (x.dia === t.dia ? { ...x, abre: e.target.value } : x)),
                      )
                    }
                    aria-label={`${DIAS[t.dia]}, abre a las`}
                  />
                  <span aria-hidden="true">a</span>
                  <input
                    type="time"
                    className="entrada cifras"
                    value={t.cierra}
                    onChange={(e) =>
                      setHorario((p) =>
                        (p ?? []).map((x) => (x.dia === t.dia ? { ...x, cierra: e.target.value } : x)),
                      )
                    }
                    aria-label={`${DIAS[t.dia]}, cierra a las`}
                  />
                </li>
              ))}
            </ul>

            <div className="acciones" style={{ marginTop: 'var(--espacio-4)' }}>
              <button type="button" className="boton boton--cierra" onClick={guardarHorario} disabled={guardando}>
                {guardando ? 'Guardando…' : 'Guardar horario'}
              </button>
              {guardado && (
                <p role="status" className="aviso aviso--exito">
                  Guardado.
                </p>
              )}
            </div>
          </section>

          {ajustes && (
            <section className="bloque-panel">
              <h2 className="etiqueta">Reglas de reserva</h2>
              <p className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
                Se guardan solas al cambiarlas.
              </p>

              <div className="formulario" style={{ marginTop: 'var(--espacio-4)' }}>
                <label className="campo">
                  <span>Las horas se ofrecen cada</span>
                  <select
                    className="entrada"
                    value={ajustes.granularidad_minutos}
                    onChange={(e) => cambiarAjuste({ granularidad_minutos: Number(e.target.value) })}
                  >
                    {[5, 10, 15, 20, 30, 60].map((m) => (
                      <option key={m} value={m}>
                        {m} minutos
                      </option>
                    ))}
                  </select>
                </label>

                <label className="campo">
                  <span>Con cuánta antelación mínima</span>
                  <select
                    className="entrada"
                    value={ajustes.antelacion_minima_minutos}
                    onChange={(e) =>
                      cambiarAjuste({ antelacion_minima_minutos: Number(e.target.value) })
                    }
                  >
                    {[
                      [0, 'Sin mínimo'],
                      [30, 'Media hora antes'],
                      [60, 'Una hora antes'],
                      [120, 'Dos horas antes'],
                      [1440, 'El día anterior'],
                    ].map(([valor, texto]) => (
                      <option key={valor} value={valor}>
                        {texto}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="campo">
                  <span>Se puede reservar hasta</span>
                  <select
                    className="entrada"
                    value={ajustes.antelacion_maxima_dias}
                    onChange={(e) => cambiarAjuste({ antelacion_maxima_dias: Number(e.target.value) })}
                  >
                    {[7, 14, 30, 60, 90, 180].map((d) => (
                      <option key={d} value={d}>
                        {d} días por delante
                      </option>
                    ))}
                  </select>
                </label>

                <label className="campo">
                  <span>Se puede cancelar hasta</span>
                  <select
                    className="entrada"
                    value={ajustes.ventana_cancelacion_horas}
                    onChange={(e) =>
                      cambiarAjuste({ ventana_cancelacion_horas: Number(e.target.value) })
                    }
                  >
                    {[
                      [0, 'Hasta la hora de la cita'],
                      [2, '2 horas antes'],
                      [4, '4 horas antes'],
                      [12, '12 horas antes'],
                      [24, 'Un día antes'],
                      [48, 'Dos días antes'],
                    ].map(([valor, texto]) => (
                      <option key={valor} value={valor}>
                        {texto}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="interruptor">
                  <input
                    type="checkbox"
                    checked={ajustes.auto_confirmar}
                    onChange={(e) => cambiarAjuste({ auto_confirmar: e.target.checked })}
                  />
                  <span>Confirmar las citas automáticamente</span>
                </label>

                <label className="interruptor">
                  <input
                    type="checkbox"
                    checked={ajustes.permitir_cualquier_profesional}
                    onChange={(e) =>
                      cambiarAjuste({ permitir_cualquier_profesional: e.target.checked })
                    }
                  />
                  <span>Dejar elegir «cualquier profesional»</span>
                </label>

                <label className="interruptor">
                  <input
                    type="checkbox"
                    checked={ajustes.resumen_diario}
                    onChange={(e) => cambiarAjuste({ resumen_diario: e.target.checked })}
                  />
                  <span>Mandarme el resumen del día por la mañana</span>
                </label>
              </div>
            </section>
          )}

          <section className="bloque-panel">
            <div className="cabeza-seccion" style={{ marginBlock: 0 }}>
              <h2 className="etiqueta">Cierres y vacaciones</h2>
              <button type="button" className="boton boton--primario" onClick={() => setNuevaAusencia(true)}>
                Añadir cierre
              </button>
            </div>

            {ausencias.length === 0 ? (
              <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
                No hay ningún cierre apuntado. Un cierre bloquea esas horas para que nadie pueda
                reservarlas.
              </p>
            ) : (
              <ul className="filas" style={{ marginTop: 'var(--espacio-3)' }}>
                {ausencias.map((a) => (
                  <li key={a.id} className="fila">
                    <div className="fila__boton" style={{ cursor: 'default' }}>
                      <span className="fila__principal">
                        <span className="fila__nombre">{a.motivo ?? 'Cerrado'}</span>
                        <span className="fila__detalle cifras">
                          {a.profesional} · {formatearRango(a.desde, a.hasta)}
                        </span>
                      </span>
                      <button
                        type="button"
                        className="boton boton--llano"
                        onClick={async () => {
                          if (!sesion) return
                          await conSesion(`/api/v1/negocio/ausencias/${a.id}`, {
                            metodo: 'DELETE',
                            token: sesion.acceso,
                          })
                          void cargar(sesion)
                        }}
                      >
                        Quitar
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {feriados.length > 0 && (
              <>
                <h3 className="etiqueta" style={{ marginTop: 'var(--espacio-5)' }}>
                  Feriados de Panamá
                </h3>
                <p className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
                  Son una sugerencia, no una imposición: hay salones que abren.
                </p>
                <ul className="filas" style={{ marginTop: 'var(--espacio-2)' }}>
                  {feriados.slice(0, 6).map((f) => (
                    <li key={f.fecha} className="fila">
                      <div className="fila__boton" style={{ cursor: 'default' }}>
                        <span className="fila__principal">
                          <span className="fila__nombre">{f.nombre}</span>
                          <span className="fila__detalle cifras">{f.fecha}</span>
                        </span>
                        <span className="fila__cifra tenue">
                          {f.ya_cerrado ? 'Cerrado' : 'Abierto'}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        </>
      )}

      {nuevaAusencia && sesion && (
        <FormularioDeAusencia
          sesion={sesion}
          onCerrar={() => setNuevaAusencia(false)}
          onGuardado={() => {
            setNuevaAusencia(false)
            void cargar(sesion)
          }}
        />
      )}
    </div>
  )
}

function formatearRango(desde: string, hasta: string) {
  const f = new Intl.DateTimeFormat('es-PA', { day: 'numeric', month: 'short' })
  const a = new Date(desde)
  const b = new Date(hasta)
  return f.format(a) === f.format(b) ? f.format(a) : `${f.format(a)} a ${f.format(b)}`
}

function FormularioDeAusencia({
  sesion,
  onCerrar,
  onGuardado,
}: {
  sesion: Sesion
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [motivo, setMotivo] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  return (
    <Hoja titulo="Añadir un cierre" onCerrar={onCerrar}>
      <form
        className="formulario"
        onSubmit={async (evento) => {
          evento.preventDefault()
          setGuardando(true)
          setFallo(null)
          try {
            await conSesion('/api/v1/negocio/ausencias', {
              metodo: 'POST',
              token: sesion.acceso,
              cuerpo: {
                // Sin profesional es el salón entero: es lo que se quiere el 90 % de las veces
                // —vacaciones, un feriado, una reforma— y ahorra un selector.
                profesional_id: null,
                desde: new Date(`${desde}T00:00:00`).toISOString(),
                hasta: new Date(`${hasta}T23:59:59`).toISOString(),
                motivo: motivo.trim() || null,
              },
            })
            onGuardado()
          } catch (error) {
            setFallo(error instanceof Error ? error.message : 'No se pudo guardar.')
            setGuardando(false)
          }
        }}
      >
        <div className="pareja">
          <label className="campo">
            <span>Desde</span>
            <input
              type="date"
              className="entrada cifras"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              required
            />
          </label>
          <label className="campo">
            <span>Hasta</span>
            <input
              type="date"
              className="entrada cifras"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              required
            />
          </label>
        </div>

        <label className="campo">
          <span>Motivo (opcional)</span>
          <input
            className="entrada"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Vacaciones, feriado, reforma…"
          />
        </label>

        <p className="aviso aviso--info">
          Se cierra el salón entero esos días. Las citas que ya estén dentro no se cancelan
          solas: las tienes que mover tú desde la agenda.
        </p>

        {fallo && (
          <p role="alert" className="aviso aviso--error">
            {fallo}
          </p>
        )}

        <div className="hoja__pie">
          <button type="button" className="boton boton--llano" onClick={onCerrar}>
            Cancelar
          </button>
          <button type="submit" className="boton boton--cierra" disabled={guardando}>
            {guardando ? 'Guardando…' : 'Añadir cierre'}
          </button>
        </div>
      </form>
    </Hoja>
  )
}
