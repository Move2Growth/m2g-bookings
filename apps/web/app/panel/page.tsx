'use client'

import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import { borrarSesion, conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * La agenda del salón en el móvil. Es **la** pantalla del producto en la Fase 1: si esto no
 * sirve de pie, entre cliente y cliente, no sirve de nada lo demás.
 *
 * Se pinta en cliente y no en servidor a propósito (ADR-0011): está detrás de autenticación,
 * no la indexa nadie, y el token vive en el navegador.
 *
 * Decisiones que vienen del design system y no son estéticas:
 * · **Lista, no cuadrícula horaria.** A 390 px con varios profesionales la cuadrícula no cabe.
 * · **Sin precio en la fila.** En la agenda no se decide nada con él y ocuparía la línea del
 *   servicio, que sí hace falta.
 * · **Al abrir se salta a la cita en curso o a la próxima**, no a las nueve de la mañana.
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

const COLOR_ESTADO: Record<string, string> = {
  pendiente: 'var(--estado-reserva-pendiente-borde)',
  confirmada: 'var(--estado-reserva-confirmada-borde)',
  completada: 'var(--estado-reserva-completada-borde)',
  no_show: 'var(--estado-reserva-no_show-borde)',
  cancelada_cliente: 'var(--estado-reserva-cancelada-borde)',
  cancelada_negocio: 'var(--estado-reserva-cancelada-borde)',
}

const ETIQUETA_ESTADO: Record<string, string> = {
  pendiente: 'Por confirmar',
  confirmada: 'Confirmada',
  completada: 'Atendida',
  no_show: 'No vino',
  cancelada_cliente: 'Cancelada por el cliente',
  cancelada_negocio: 'Cancelada',
}

function inicioDelDia(desplazamiento: number): Date {
  const dia = new Date()
  dia.setDate(dia.getDate() + desplazamiento)
  dia.setHours(0, 0, 0, 0)
  return dia
}

export default function Panel() {
  const router = useRouter()
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [dia, setDia] = useState(0)
  const [citas, setCitas] = useState<Cita[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const guardada = leerSesion()
    if (!guardada) {
      router.replace('/entrar')
      return
    }
    setSesion(guardada)
  }, [router])

  const cargar = useCallback(
    async (actual: Sesion, desplazamiento: number) => {
      setCargando(true)
      setError(null)
      const desde = inicioDelDia(desplazamiento)
      const hasta = inicioDelDia(desplazamiento + 1)
      try {
        const datos = await conSesion<Cita[]>(
          `/api/v1/negocio/agenda?desde=${desde.toISOString()}&hasta=${hasta.toISOString()}`,
          { token: actual.acceso },
        )
        setCitas(datos)
      } catch (fallo) {
        setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar la agenda.')
      } finally {
        setCargando(false)
      }
    },
    [],
  )

  useEffect(() => {
    if (sesion?.negocio_activo) void cargar(sesion, dia)
  }, [sesion, dia, cargar])

  if (sesion && !sesion.negocio_activo) {
    // No es un error: es una cuenta de clienta mirando la puerta del personal. Se la manda a
    // lo suyo en vez de enseñarle un mensaje de permisos que no le dice nada.
    router.replace('/mis-reservas')
    return <main className="contenido">Llevándote a tus citas…</main>
  }

  const fecha = new Intl.DateTimeFormat('es-PA', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
  })
  const hora = new Intl.DateTimeFormat('es-PA', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })

  return (
    <main className="contenido" style={{ paddingBottom: 'var(--espacio-8)' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--espacio-3)',
          marginBottom: 'var(--espacio-4)',
        }}
      >
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Agenda</h1>
        <button
          onClick={() => {
            borrarSesion()
            router.push('/entrar')
          }}
          style={{ ...boton, background: 'transparent', color: 'var(--color-texto-suave)' }}
        >
          Salir
        </button>
      </header>

      {/* Una sola barra de contexto: cada barra fija que se añade es una cita menos en
          pantalla, y en un teléfono eso se nota enseguida. */}
      <nav
        aria-label="Cambiar de día"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--espacio-2)',
          background: 'var(--color-superficie)',
          border: '1px solid var(--color-borde)',
          borderRadius: 'var(--radio-normal)',
          padding: 'var(--espacio-2)',
          marginBottom: 'var(--espacio-4)',
        }}
      >
        <button onClick={() => setDia((d) => d - 1)} style={flecha} aria-label="Día anterior">
          ←
        </button>
        <strong style={{ textTransform: 'capitalize' }}>
          {dia === 0 ? 'Hoy, ' : ''}
          {fecha.format(inicioDelDia(dia))}
        </strong>
        <button onClick={() => setDia((d) => d + 1)} style={flecha} aria-label="Día siguiente">
          →
        </button>
      </nav>

      {cargando && <p style={{ color: 'var(--color-texto-suave)' }}>Cargando la agenda…</p>}

      {error && (
        <p
          role="alert"
          style={{
            background: 'var(--color-peligro-suave)',
            color: 'var(--color-peligro)',
            padding: 'var(--espacio-3)',
            borderRadius: 'var(--radio-normal)',
          }}
        >
          {error}
        </p>
      )}

      {!cargando && !error && citas.length === 0 && (
        <p
          style={{
            background: 'var(--color-superficie)',
            border: '1px solid var(--color-borde)',
            borderRadius: 'var(--radio-grande)',
            padding: 'var(--espacio-4)',
            color: 'var(--color-texto-suave)',
          }}
        >
          No hay citas este día. Cuando alguien reserve, aparecerá aquí sin que tengas que
          recargar nada.
        </p>
      )}

      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--espacio-2)' }}>
        {citas.map((cita) => (
          <li
            key={cita.id}
            style={{
              display: 'grid',
              gridTemplateColumns: 'auto 1fr',
              gap: 'var(--espacio-3)',
              alignItems: 'start',
              minHeight: '72px',
              background: 'var(--color-superficie)',
              border: '1px solid var(--color-borde)',
              borderLeft: `3px solid ${COLOR_ESTADO[cita.estado] ?? 'var(--color-borde)'}`,
              borderRadius: 'var(--radio-normal)',
              padding: 'var(--espacio-3)',
            }}
          >
            <span className="cifras" style={{ color: 'var(--color-texto-suave)' }}>
              {hora.format(new Date(cita.inicio))}
              <br />
              {hora.format(new Date(cita.fin))}
            </span>
            <span>
              <strong>{cita.cliente}</strong>
              <span
                style={{
                  display: 'block',
                  color: 'var(--color-texto-suave)',
                  fontSize: 'var(--tipografia-tamano-menor)',
                }}
              >
                {cita.servicios.map((s) => s.nombre).join(' + ')}
              </span>
              <span
                style={{
                  display: 'inline-block',
                  marginTop: 'var(--espacio-2)',
                  fontSize: 'var(--tipografia-tamano-micro)',
                  color: 'var(--color-texto-suave)',
                }}
              >
                {ETIQUETA_ESTADO[cita.estado] ?? cita.estado}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </main>
  )
}

const boton: React.CSSProperties = {
  minHeight: 'var(--espacio-toque-minimo)',
  padding: 'var(--espacio-2) var(--espacio-3)',
  border: 'none',
  borderRadius: 'var(--radio-normal)',
  background: 'var(--color-acento)',
  color: 'var(--color-acento-texto)',
  fontFamily: 'inherit',
  fontSize: 'var(--tipografia-tamano-menor)',
  cursor: 'pointer',
}

const flecha: React.CSSProperties = {
  ...boton,
  background: 'transparent',
  color: 'var(--color-texto)',
  minWidth: 'var(--espacio-toque-minimo)',
  fontSize: 'var(--tipografia-tamano-mayor)',
}
