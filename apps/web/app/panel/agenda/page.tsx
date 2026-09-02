'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Vacio } from '@/componentes/estados'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * La agenda del salón en el móvil. Es **la** pantalla del producto: si esto no sirve de pie,
 * entre clienta y clienta, no sirve de nada lo demás.
 *
 * Se pinta en cliente y no en servidor a propósito (ADR-0011): está detrás de autenticación,
 * no la indexa nadie y el token vive en el navegador.
 *
 * Tres decisiones que vienen del uso real y no del gusto:
 * · **Lista, no cuadrícula horaria.** A 390 px con cuatro profesionales la cuadrícula no cabe.
 * · **La hora manda en la fila.** Es el único dato que se busca de un vistazo.
 * · **Sin precio en la fila.** En la agenda no se decide nada con él y le quita la línea al
 *   servicio, que sí hace falta.
 */

type Cita = {
  id: string
  inicio: string
  fin: string
  estado: string
  profesional_id: string
  cliente: string
  tiene_telefono: boolean
  servicios: { nombre: string; duracion_minutos: number; precio_centavos: number | null }[]
}

const ETIQUETA: Record<string, string> = {
  pendiente: 'Por confirmar',
  confirmada: 'Confirmada',
  completada: 'Atendida',
  no_show: 'No vino',
  cancelada_cliente: 'Cancelada por la clienta',
  cancelada_negocio: 'Cancelada',
}

function inicioDelDia(desplazamiento: number): Date {
  const dia = new Date()
  dia.setDate(dia.getDate() + desplazamiento)
  dia.setHours(0, 0, 0, 0)
  return dia
}

export default function Agenda() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [dia, setDia] = useState(0)
  const [citas, setCitas] = useState<Cita[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion, desplazamiento: number) => {
    setCargando(true)
    setError(null)
    const desde = inicioDelDia(desplazamiento)
    const hasta = inicioDelDia(desplazamiento + 1)
    try {
      setCitas(
        await conSesion<Cita[]>(
          `/api/v1/negocio/agenda?desde=${desde.toISOString()}&hasta=${hasta.toISOString()}`,
          { token: actual.acceso },
        ),
      )
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar la agenda.')
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    if (sesion?.negocio_activo) void cargar(sesion, dia)
  }, [sesion, dia, cargar])

  const fecha = new Intl.DateTimeFormat('es-PA', { weekday: 'long', day: 'numeric', month: 'long' })
  const hora = new Intl.DateTimeFormat('es-PA', { hour: '2-digit', minute: '2-digit', hour12: false })

  const activas = citas.filter((c) => ['pendiente', 'confirmada'].includes(c.estado))

  return (
    <div className="contenedor">
        {/* El título va oculto y no impreso: la barra de días de debajo ya dice de qué va la
            pantalla, pero sin un h1 quien navega con lector de pantalla no sabe dónde está. */}
        <h1 className="oculto-visualmente">Agenda del salón</h1>

        {/* Una sola barra de contexto. Cada barra fija que se añade es una cita menos en
            pantalla, y en un teléfono eso se nota enseguida. */}
        <nav aria-label="Cambiar de día" className="dias">
          <button onClick={() => setDia((d) => d - 1)} className="dias__flecha" aria-label="Día anterior">
            ←
          </button>
          <div>
            <strong className="primera-mayuscula">
              {dia === 0 ? 'Hoy, ' : ''}
              {fecha.format(inicioDelDia(dia))}
            </strong>
            <span className="tenue" style={{ display: 'block' }}>
              {activas.length === 0
                ? 'sin citas'
                : `${activas.length} ${activas.length === 1 ? 'cita' : 'citas'}`}
            </span>
          </div>
          <button onClick={() => setDia((d) => d + 1)} className="dias__flecha" aria-label="Día siguiente">
            →
          </button>
        </nav>

        {cargando && (
          /* Esqueleto con la forma de lo que va a llegar, no una ruedita: en 3G esto se ve
             varios segundos y una ruedita no dice cuánto falta ni qué va a aparecer. */
          <ul className="agenda" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <li key={i} className="agenda__fila agenda__fila--esqueleto">
                <span className="agenda__hora" />
                <span className="agenda__cuerpo" />
              </li>
            ))}
          </ul>
        )}

        {error && (
          <BloqueDeError
            mensaje={error}
            reintentar={sesion ? () => void cargar(sesion, dia) : undefined}
          />
        )}

        {!cargando && !error && citas.length === 0 && (
          <Vacio
            icono={Iconos.agenda}
            titulo="No hay citas este día"
            texto="Cuando alguien reserve, aparece aquí sin que tengas que recargar nada."
          />
        )}

        {!cargando && citas.length > 0 && (
          <ul className="agenda">
            {citas.map((cita) => (
              <li key={cita.id} className={`agenda__fila agenda__fila--${cita.estado}`}>
                <span className="agenda__hora cifras">
                  <strong>{hora.format(new Date(cita.inicio))}</strong>
                  <span className="tenue">{hora.format(new Date(cita.fin))}</span>
                </span>
                <span>
                  <strong>{cita.cliente}</strong>
                  <span className="apagado" style={{ display: 'block', fontSize: 'var(--tipografia-tamano-menor)' }}>
                    {cita.servicios.map((s) => s.nombre).join(' + ')}
                  </span>
                  <span className={`estado estado--${cita.estado}`} style={{ marginTop: 'var(--espacio-2)' }}>
                    {ETIQUETA[cita.estado] ?? cita.estado}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
    </div>
  )
}
