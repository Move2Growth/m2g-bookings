'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { API, guardarSesion } from '@/lib/sesion'

/**
 * Entrar al panel: teléfono y código, dos pasos y ninguno más.
 *
 * No hay contraseña que recordar ni registro aparte: quien verifica su teléfono ya tiene
 * cuenta (ONB-1). El objetivo es que el dueño del salón entre desde el móvil con una mano.
 */
export default function Entrar() {
  const router = useRouter()
  const [paso, setPaso] = useState<'telefono' | 'codigo'>('telefono')
  const [telefono, setTelefono] = useState('+507')
  const [codigo, setCodigo] = useState('')
  const [pista, setPista] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

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
      // En local no hay canal todavía, así que la API devuelve el código y se enseña aquí
      // para poder probar el flujo entero sin credenciales de Meta.
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
      guardarSesion(datos)
      // Quien tiene negocio va a su agenda; quien no, a sus citas. La misma cuenta puede ser
      // las dos cosas (ONB-3), y en ese caso manda el modo negocio, que es el que trae el
      // token con el salón activo.
      router.push(datos.negocio_activo ? '/panel' : '/mis-reservas')
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'Ese código no es válido.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="contenido" style={{ maxWidth: '26rem' }}>
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Entrar a tu negocio</h1>
      <p style={{ color: 'var(--color-texto-suave)', marginTop: 'var(--espacio-2)' }}>
        Te mandamos un código por WhatsApp. No hay contraseña que recordar.
      </p>

      <form
        onSubmit={paso === 'telefono' ? pedirCodigo : verificar}
        style={{ display: 'grid', gap: 'var(--espacio-4)', marginTop: 'var(--espacio-5)' }}
      >
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
            <span style={{ fontWeight: 'var(--tipografia-pesos-medio)' }}>Código de 6 dígitos</span>
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
              style={{ ...campo, letterSpacing: '0.4em', fontSize: 'var(--tipografia-tamano-mayor)' }}
            />
            {pista && (
              <span style={{ color: 'var(--color-texto-tenue)', fontSize: 'var(--tipografia-tamano-menor)' }}>
                En local no hay WhatsApp todavía. Tu código es <strong className="cifras">{pista}</strong>.
              </span>
            )}
          </label>
        )}

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

        <button type="submit" disabled={enviando} style={boton}>
          {enviando ? 'Un momento…' : paso === 'telefono' ? 'Mandarme el código' : 'Entrar'}
        </button>
      </form>
    </main>
  )
}

const campo: React.CSSProperties = {
  // 16 px o iOS hace zoom al enfocar y descuadra la pantalla sin que nadie haya tocado nada.
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
}
