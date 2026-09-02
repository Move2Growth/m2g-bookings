'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { API, guardarSesionDeConsola, leerSesionDeConsola, type SesionDeConsola } from '@/lib/consola'

/**
 * Entrar en la consola.
 *
 * Correo, contraseña y segundo factor **en la misma pantalla**, no en dos pasos. Aquí no hay
 * descubrimiento que hacer: quien entra tiene ya su autenticador abierto, y partirlo en dos
 * pantallas solo añade una espera de red en medio.
 *
 * No dice si falló el correo, la contraseña o el código. Distinguirlos le confirma a quien
 * prueba credenciales cuáles existen.
 */
export default function EntrarEnConsola() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [codigo, setCodigo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (leerSesionDeConsola()) router.replace('/consola/negocios')
  }, [router])

  async function entrar(evento: React.FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      const respuesta = await fetch(`${API}/api/v1/consola/entrar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password, codigo_2fa: codigo.trim() }),
      })
      if (!respuesta.ok) throw new Error('No pudimos entrar con esos datos.')
      guardarSesionDeConsola((await respuesta.json()) as SesionDeConsola)
      router.push('/consola/negocios')
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No pudimos entrar con esos datos.')
      setEnviando(false)
    }
  }

  return (
    <main className="acceso-consola">
      <form onSubmit={entrar} className="formulario acceso-consola__caja">
        <p className="marca-consola">M2G</p>
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Consola interna</h1>
        <p className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
          Esta puerta no es la de los salones ni la de las clientas.
        </p>

        <label className="campo">
          <span>Correo</span>
          <input
            className="entrada"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
            autoFocus
          />
        </label>

        <label className="campo">
          <span>Contraseña</span>
          <input
            className="entrada"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        <label className="campo">
          <span>Código del autenticador</span>
          <input
            className="entrada entrada--codigo"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value.replace(/\D/g, '').slice(0, 8))}
            required
          />
        </label>

        {error && (
          <p role="alert" className="aviso aviso--error">
            {error}
          </p>
        )}

        <button type="submit" className="boton boton--cierra boton--ancho" disabled={enviando}>
          {enviando ? 'Comprobando…' : 'Entrar'}
        </button>
      </form>
    </main>
  )
}
