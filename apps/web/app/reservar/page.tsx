'use client'

import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useState } from 'react'
import { API, conSesion, leerSesion } from '@/lib/sesion'

/**
 * Confirmar la cita. Es la **tercera y última pantalla** tras elegir servicio (RSV-1), y por
 * eso aquí no se elige nada nuevo: se lee lo elegido, se confirma y se acabó.
 *
 * Quien llega sin sesión no se topa con un muro: se le pide el teléfono **encima** de esta
 * pantalla, sin sacarlo del flujo ni perder lo que ya había elegido. Verificar el teléfono es
 * obligatorio (D9) porque es lo único que sostiene el control de no-shows sin pedir depósito,
 * pero eso no obliga a que parezca un trámite.
 */

function Contenido() {
  const parametros = useSearchParams()
  const router = useRouter()

  const negocio = parametros.get('negocio') ?? ''
  const servicio = parametros.get('servicio') ?? ''
  const profesional = parametros.get('profesional') ?? ''
  const inicio = parametros.get('inicio') ?? ''
  const nombre = parametros.get('nombre') ?? ''
  const zona = parametros.get('zona') ?? 'America/Panama'

  const [sesion, setSesion] = useState(() => leerSesion())
  const [telefono, setTelefono] = useState('+507')
  const [nombreCliente, setNombreCliente] = useState('')
  const [codigo, setCodigo] = useState('')
  const [pista, setPista] = useState<string | null>(null)
  const [paso, setPaso] = useState<'telefono' | 'codigo'>('telefono')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => setSesion(leerSesion()), [])

  const cuando = inicio
    ? new Intl.DateTimeFormat('es-PA', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: zona,
      }).format(new Date(inicio))
    : ''

  async function pedirCodigo(evento: React.FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      const respuesta = await fetch(`${API}/api/v1/auth/otp/solicitar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telefono }),
      })
      const datos = await respuesta.json()
      if (!respuesta.ok) throw new Error(datos?.error?.mensaje ?? 'No se pudo enviar el código.')
      setPista(datos.codigo_de_desarrollo ?? null)
      setPaso('codigo')
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo enviar el código.')
    } finally {
      setEnviando(false)
    }
  }

  async function verificar(evento: React.FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      const respuesta = await fetch(`${API}/api/v1/auth/otp/verificar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telefono, codigo }),
      })
      const datos = await respuesta.json()
      if (!respuesta.ok) throw new Error(datos?.error?.mensaje ?? 'Ese código no es válido.')
      window.localStorage.setItem('agenda.sesion', JSON.stringify(datos))
      setSesion(datos)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'Ese código no es válido.')
    } finally {
      setEnviando(false)
    }
  }

  async function confirmar() {
    if (!sesion) return
    setEnviando(true)
    setError(null)
    try {
      await conSesion('/api/v1/mi/reservas', {
        metodo: 'POST',
        token: sesion.acceso,
        cuerpo: {
          negocio_slug: negocio,
          servicios: [servicio],
          profesional_id: profesional,
          inicio,
          nombre: nombreCliente || undefined,
        },
      })
      router.push('/mis-reservas?nueva=1')
    } catch (fallo) {
      // El caso que importa: alguien confirmó ese hueco mientras esta persona decidía. El
      // mensaje viene del servidor y se enseña tal cual, con el enlace para volver a elegir.
      setError(fallo instanceof Error ? fallo.message : 'No se pudo confirmar la reserva.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="contenido" style={{ maxWidth: '28rem' }}>
      <p style={{ marginBottom: 'var(--espacio-4)' }}>
        <Link href={`/${negocio}`}>← Volver a elegir hora</Link>
      </p>

      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Confirmar tu cita</h1>

      <dl
        style={{
          margin: 'var(--espacio-5) 0',
          padding: 'var(--espacio-4)',
          background: 'var(--color-superficie)',
          border: '1px solid var(--color-borde)',
          borderRadius: 'var(--radio-grande)',
          display: 'grid',
          gap: 'var(--espacio-3)',
        }}
      >
        <div>
          <dt style={etiqueta}>Servicio</dt>
          <dd style={valor}>{nombre || 'El servicio elegido'}</dd>
        </div>
        <div>
          <dt style={etiqueta}>Cuándo</dt>
          <dd style={{ ...valor, textTransform: 'capitalize' }} className="cifras">
            {cuando}
          </dd>
        </div>
      </dl>

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
          {error}{' '}
          <Link href={`/${negocio}`} style={{ color: 'inherit' }}>
            Elegir otra hora
          </Link>
        </p>
      )}

      {sesion ? (
        <>
          <button onClick={confirmar} disabled={enviando} style={boton}>
            {enviando ? 'Un momento…' : 'Confirmar la cita'}
          </button>
          <p
            style={{
              marginTop: 'var(--espacio-3)',
              color: 'var(--color-texto-tenue)',
              fontSize: 'var(--tipografia-tamano-menor)',
            }}
          >
            Podrás cancelarla desde «Mis reservas» hasta dos horas antes. Después, hablando con
            el salón.
          </p>
        </>
      ) : (
        <form onSubmit={paso === 'telefono' ? pedirCodigo : verificar} style={{ display: 'grid', gap: 'var(--espacio-3)' }}>
          <p style={{ color: 'var(--color-texto-suave)' }}>
            Para reservar necesitamos tu teléfono. Te mandamos un código y listo — no hay
            contraseña que recordar.
          </p>
          <label style={{ display: 'grid', gap: 'var(--espacio-2)' }}>
            <span style={{ fontWeight: 'var(--tipografia-pesos-medio)' }}>Tu nombre</span>
            <input
              type="text"
              autoComplete="name"
              value={nombreCliente}
              onChange={(e) => setNombreCliente(e.target.value)}
              placeholder="Como quieres que te llamen en el salón"
              style={campo}
            />
          </label>
          <label style={{ display: 'grid', gap: 'var(--espacio-2)' }}>
            <span style={{ fontWeight: 'var(--tipografia-pesos-medio)' }}>Tu teléfono</span>
            <input
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              value={telefono}
              onChange={(e) => setTelefono(e.target.value)}
              disabled={paso === 'codigo'}
              required
              className="cifras"
              style={campo}
            />
          </label>
          {paso === 'codigo' && (
            <label style={{ display: 'grid', gap: 'var(--espacio-2)' }}>
              <span style={{ fontWeight: 'var(--tipografia-pesos-medio)' }}>Código</span>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={codigo}
                onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ''))}
                required
                autoFocus
                className="cifras"
                style={{ ...campo, letterSpacing: '0.4em' }}
              />
              {pista && (
                <span style={{ color: 'var(--color-texto-tenue)', fontSize: 'var(--tipografia-tamano-menor)' }}>
                  En local no hay WhatsApp todavía. Tu código es <strong className="cifras">{pista}</strong>.
                </span>
              )}
            </label>
          )}
          <button type="submit" disabled={enviando} style={boton}>
            {enviando ? 'Un momento…' : paso === 'telefono' ? 'Mandarme el código' : 'Verificar'}
          </button>
        </form>
      )}
    </main>
  )
}

export default function Reservar() {
  return (
    <Suspense fallback={<main className="contenido">Cargando…</main>}>
      <Contenido />
    </Suspense>
  )
}

const etiqueta: React.CSSProperties = {
  color: 'var(--color-texto-suave)',
  fontSize: 'var(--tipografia-tamano-menor)',
  margin: 0,
}
const valor: React.CSSProperties = {
  margin: 0,
  fontWeight: 'var(--tipografia-pesos-medio)',
  fontSize: 'var(--tipografia-tamano-mayor)',
}
const campo: React.CSSProperties = {
  fontSize: 'var(--tipografia-tamano-cuerpo)',
  fontFamily: 'inherit',
  minHeight: 'var(--espacio-toque-minimo)',
  padding: 'var(--espacio-3)',
  border: '1px solid var(--color-borde-fuerte)',
  borderRadius: 'var(--radio-normal)',
  background: 'var(--color-superficie)',
  color: 'var(--color-texto)',
}
const boton: React.CSSProperties = {
  minHeight: 'var(--espacio-toque-minimo)',
  padding: 'var(--espacio-3) var(--espacio-4)',
  border: 'none',
  borderRadius: 'var(--radio-normal)',
  background: 'var(--color-acento)',
  color: 'var(--color-acento-texto)',
  fontSize: 'var(--tipografia-tamano-cuerpo)',
  fontWeight: 'var(--tipografia-pesos-medio)',
  fontFamily: 'inherit',
  cursor: 'pointer',
  width: '100%',
}
