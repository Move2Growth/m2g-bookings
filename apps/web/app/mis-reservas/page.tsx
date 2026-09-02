'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Suspense, useCallback, useEffect, useState } from 'react'
import { borrarSesion, conSesion, leerSesion, type Sesion } from '@/lib/sesion'

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

function Contenido() {
  const router = useRouter()
  const [sesion, setSesion] = useState<Sesion | null>(null)
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

  const cargar = useCallback(async (actual: Sesion) => {
    setCargando(true)
    try {
      setCitas(await conSesion<Cita[]>('/api/v1/mi/reservas', { token: actual.acceso }))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar tus citas.')
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  async function cancelar(cita: Cita) {
    if (!sesion) return
    try {
      await conSesion(`/api/v1/mi/reservas/${cita.id}/cancelar`, {
        metodo: 'POST',
        token: sesion.acceso,
      })
      await cargar(sesion)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cancelar.')
    }
  }

  const proximas = citas.filter((c) => ['pendiente', 'confirmada'].includes(c.estado))
  const pasadas = citas.filter((c) => !['pendiente', 'confirmada'].includes(c.estado))

  return (
    <main className="contenido">
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--espacio-3)',
          marginBottom: 'var(--espacio-5)',
        }}
      >
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Mis citas</h1>
        <button
          onClick={() => {
            borrarSesion()
            router.push('/')
          }}
          style={{
            minHeight: 'var(--espacio-toque-minimo)',
            padding: '0 var(--espacio-3)',
            border: 'none',
            background: 'transparent',
            color: 'var(--color-texto-suave)',
            fontFamily: 'inherit',
            cursor: 'pointer',
          }}
        >
          Salir
        </button>
      </header>

      {cargando && <p style={{ color: 'var(--color-texto-suave)' }}>Cargando tus citas…</p>}

      {error && (
        <p
          role="alert"
          style={{
            background: 'var(--color-peligro-suave)',
            color: 'var(--color-peligro)',
            padding: 'var(--espacio-3)',
            borderRadius: 'var(--radio-normal)',
            marginBottom: 'var(--espacio-4)',
          }}
        >
          {error}
        </p>
      )}

      {!cargando && citas.length === 0 && (
        <p
          style={{
            background: 'var(--color-superficie)',
            border: '1px solid var(--color-borde)',
            borderRadius: 'var(--radio-grande)',
            padding: 'var(--espacio-4)',
            color: 'var(--color-texto-suave)',
          }}
        >
          Todavía no tienes citas. <Link href="/">Busca un salón</Link> y reserva en un minuto.
        </p>
      )}

      {proximas.length > 0 && <Grupo titulo="Próximas" citas={proximas} onCancelar={cancelar} />}
      {pasadas.length > 0 && <Grupo titulo="Anteriores" citas={pasadas} />}
    </main>
  )
}

function Grupo({
  titulo,
  citas,
  onCancelar,
}: {
  titulo: string
  citas: Cita[]
  onCancelar?: (cita: Cita) => void
}) {
  return (
    <section style={{ marginBottom: 'var(--espacio-6)' }}>
      <h2
        style={{
          fontSize: 'var(--tipografia-tamano-menor)',
          color: 'var(--color-texto-suave)',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          marginBottom: 'var(--espacio-3)',
        }}
      >
        {titulo}
      </h2>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--espacio-3)' }}>
        {citas.map((cita) => {
          const cuando = new Intl.DateTimeFormat('es-PA', {
            weekday: 'short',
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
            timeZone: cita.zona_horaria,
          }).format(new Date(cita.inicio))

          return (
            <li
              key={cita.id}
              style={{
                background: 'var(--color-superficie)',
                border: '1px solid var(--color-borde)',
                borderRadius: 'var(--radio-grande)',
                padding: 'var(--espacio-4)',
              }}
            >
              <p className="cifras" style={{ fontWeight: 'var(--tipografia-pesos-fuerte)', textTransform: 'capitalize' }}>
                {cuando}
              </p>
              <p style={{ marginTop: 'var(--espacio-1)' }}>
                <Link href={`/${cita.negocio_slug}`}>{cita.negocio}</Link>
              </p>
              <p
                style={{
                  color: 'var(--color-texto-suave)',
                  fontSize: 'var(--tipografia-tamano-menor)',
                  marginTop: 'var(--espacio-1)',
                }}
              >
                {cita.servicios.map((s) => s.nombre).join(' + ')}
                {cita.total_centavos > 0 && (
                  <span className="cifras"> · ${(cita.total_centavos / 100).toFixed(2)}</span>
                )}
              </p>
              <p
                style={{
                  marginTop: 'var(--espacio-2)',
                  fontSize: 'var(--tipografia-tamano-micro)',
                  color: 'var(--color-texto-suave)',
                }}
              >
                {ETIQUETA[cita.estado] ?? cita.estado}
              </p>

              {onCancelar && cita.se_puede_cancelar && (
                <button
                  onClick={() => onCancelar(cita)}
                  style={{
                    marginTop: 'var(--espacio-3)',
                    minHeight: 'var(--espacio-toque-minimo)',
                    padding: '0 var(--espacio-3)',
                    border: '1px solid var(--color-borde-fuerte)',
                    borderRadius: 'var(--radio-normal)',
                    background: 'transparent',
                    color: 'var(--color-peligro)',
                    fontFamily: 'inherit',
                    cursor: 'pointer',
                  }}
                >
                  Cancelar
                </button>
              )}
              {onCancelar && !cita.se_puede_cancelar && (
                /* Fuera de la ventana no se esconde el botón sin más: se explica, porque si
                   no, la persona cree que la aplicación está rota. */
                <p
                  style={{
                    marginTop: 'var(--espacio-3)',
                    fontSize: 'var(--tipografia-tamano-menor)',
                    color: 'var(--color-texto-tenue)',
                  }}
                >
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

export default function MisReservas() {
  return (
    <Suspense fallback={<main className="contenido">Cargando…</main>}>
      <Contenido />
    </Suspense>
  )
}
