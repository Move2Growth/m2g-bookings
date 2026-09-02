'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * Las citas de una persona, en todos los salones donde ha estado.
 *
 * Es la pantalla de vuelta: la que se abre para comprobar a qué hora era, y la que se usa para
 * cancelar. Por eso lo primero que se lee es **cuándo y dónde**, y el estado va debajo.
 *
 * Quién puede cancelar lo decide el servidor, no esta pantalla: si lo calculara el navegador,
 * un reloj mal puesto daría permiso donde no lo hay.
 */

type Cita = {
  id: string
  negocio: string
  negocio_slug: string
  inicio: string
  fin: string
  estado: string
  zona_horaria: string
  servicios: { nombre: string; duracion_minutos: number; precio_centavos: number | null }[]
  total_centavos: number
  se_puede_cancelar: boolean
}

const ETIQUETA: Record<string, string> = {
  pendiente: 'Por confirmar',
  confirmada: 'Confirmada',
  completada: 'Atendida',
  no_show: 'No asististe',
  cancelada_cliente: 'Cancelaste esta cita',
  cancelada_negocio: 'El salón canceló esta cita',
}

export default function MisCitas() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [citas, setCitas] = useState<Cita[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cancelando, setCancelando] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      setCitas(await conSesion<Cita[]>('/api/v1/mi/reservas', { token: actual.acceso }))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar tus citas.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  async function cancelar(cita: Cita) {
    if (!sesion) return
    setCancelando(cita.id)
    try {
      await conSesion(`/api/v1/mi/reservas/${cita.id}/cancelar`, {
        metodo: 'POST',
        token: sesion.acceso,
      })
      await cargar(sesion)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cancelar.')
    } finally {
      setCancelando(null)
    }
  }

  const proximas = (citas ?? []).filter((c) => ['pendiente', 'confirmada'].includes(c.estado))
  const pasadas = (citas ?? []).filter((c) => !['pendiente', 'confirmada'].includes(c.estado))

  return (
    <div className="contenedor seccion">
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Mis citas</h1>

      {error && (
        <div style={{ marginTop: 'var(--espacio-4)' }}>
          <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
        </div>
      )}

      {citas === null && !error && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Esqueleto filas={3} alto={132} etiqueta="Cargando tus citas" />
        </div>
      )}

      {citas !== null && citas.length === 0 && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Vacio
            icono={Iconos.citas}
            titulo="Todavía no tienes citas"
            texto="Cuando reserves en un salón, aparecerá aquí con la hora, la dirección y el botón de cancelar."
            accion={{ href: '/buscar', texto: 'Buscar un salón' }}
          />
        </div>
      )}

      {proximas.length > 0 && (
        <Grupo titulo="Próximas" citas={proximas} onCancelar={cancelar} cancelando={cancelando} />
      )}
      {pasadas.length > 0 && <Grupo titulo="Anteriores" citas={pasadas} />}
    </div>
  )
}

function Grupo({
  titulo,
  citas,
  onCancelar,
  cancelando,
}: {
  titulo: string
  citas: Cita[]
  onCancelar?: (cita: Cita) => void
  cancelando?: string | null
}) {
  return (
    <section style={{ marginTop: 'var(--espacio-6)' }}>
      <h2 className="etiqueta">{titulo}</h2>
      <ul className="citas escalona">
        {citas.map((cita) => {
          const cuando = new Intl.DateTimeFormat('es-PA', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
            timeZone: cita.zona_horaria,
          }).format(new Date(cita.inicio))

          return (
            <li key={cita.id} className="cita">
              <p className="cita__cuando cifras primera-mayuscula">{cuando}</p>
              <p className="cita__donde">
                <Link href={`/${cita.negocio_slug}`}>{cita.negocio}</Link>
              </p>
              <p className="cita__que">
                {cita.servicios.map((s) => s.nombre).join(' + ')}
                {cita.total_centavos > 0 && (
                  <span className="cifras"> · ${(cita.total_centavos / 100).toFixed(2)}</span>
                )}
              </p>

              <p className="cita__estado">
                <span className={`estado estado--${cita.estado}`}>
                  {ETIQUETA[cita.estado] ?? cita.estado}
                </span>
              </p>

              {onCancelar && cita.se_puede_cancelar && (
                <p className="cita__acciones">
                  <button
                    onClick={() => onCancelar(cita)}
                    disabled={cancelando === cita.id}
                    className="boton boton--peligro"
                  >
                    {cancelando === cita.id ? 'Cancelando…' : 'Cancelar'}
                  </button>
                </p>
              )}
              {onCancelar && !cita.se_puede_cancelar && (
                /* Fuera de la ventana no se esconde el botón sin más: se explica, porque si
                   no, la persona cree que la aplicación está rota. */
                <p className="cita__nota">
                  Ya pasó el plazo para cancelar por tu cuenta. Escríbele al salón y lo arreglan.
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
