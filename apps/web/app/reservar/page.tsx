'use client'

import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useState } from 'react'
import { API, conSesion, leerSesion } from '@/lib/sesion'

/**
 * Confirmar la cita. Es la **tercera y última pantalla** tras elegir servicio (RSV-1), y por
 * eso aquí no se elige nada nuevo: se lee lo elegido, se confirma y se acabó.
 *
 * Verificar el teléfono es obligatorio (D9) porque es lo único que sostiene el control de
 * no-shows sin pedir depósito, y porque el salón tiene que poder llamar si hay que mover la
 * cita. Pero se pide **aquí**, encima de esta pantalla y sin sacar a nadie del flujo, no en el
 * alta: al alta se entra con correo y contraseña y ya está.
 *
 * **Se verifica con `/mi/telefono`, no con `/auth/otp/verificar`.** Aquel es *entrar*: busca la
 * cuenta de ese número y, si no existe, crea una nueva. Llamarlo desde una sesión ya abierta
 * dejaba a la persona dentro de otra cuenta, vacía y sin sus citas, sin ningún error a la
 * vista. Es el peor tipo de fallo: parece que funcionó.
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
  //: `null` mientras no se sabe. Sirve para no parpadear entre las dos formas de la pantalla.
  const [telefonoVerificado, setTelefonoVerificado] = useState<boolean | null>(null)
  const [telefono, setTelefono] = useState('+507')
  const [nombreCliente, setNombreCliente] = useState('')
  const [codigo, setCodigo] = useState('')
  const [pista, setPista] = useState<string | null>(null)
  const [paso, setPaso] = useState<'telefono' | 'codigo'>('telefono')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    const actual = leerSesion()
    setSesion(actual)

    // Sin sesión no hay nada que hacer aquí: se va a entrar y se vuelve **a esta misma
    // pantalla con lo ya elegido**, que por eso viaja entero en la URL.
    if (!actual) {
      const aqui = window.location.pathname + window.location.search
      window.location.href = `/entrar?volver=${encodeURIComponent(aqui)}`
      return
    }

    fetch(`${API}/api/v1/mi/perfil`, { headers: { Authorization: `Bearer ${actual.acceso}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then((perfil) => {
        setTelefonoVerificado(Boolean(perfil?.telefono_verificado))
        if (perfil?.telefono) setTelefono(perfil.telefono)
        if (perfil?.nombre) setNombreCliente(perfil.nombre)
      })
      .catch(() => setTelefonoVerificado(false))
  }, [])

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
      const respuesta = await fetch(`${API}/api/v1/mi/telefono/solicitar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sesion?.acceso ?? ''}`,
        },
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
      const respuesta = await fetch(`${API}/api/v1/mi/telefono/verificar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${sesion?.acceso ?? ''}`,
        },
        body: JSON.stringify({ telefono, codigo }),
      })
      // Devuelve 204 y **ninguna credencial**: la sesión que había sigue siendo la buena.
      if (!respuesta.ok) {
        const datos = await respuesta.json().catch(() => null)
        throw new Error(datos?.error?.mensaje ?? 'Ese código no es válido.')
      }
      setTelefonoVerificado(true)
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
      const creada = await conSesion<{ id: string }>('/api/v1/mi/reservas', {
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
      // Con el identificador de la cita recién creada, para que la lista pueda decir «esta es
      // la que acabas de reservar» y no dejar a la persona preguntándose si se guardó.
      router.push(`/mi/citas?nueva=${creada.id}`)
    } catch (fallo) {
      // El caso que importa: alguien confirmó ese hueco mientras esta persona decidía. El
      // mensaje viene del servidor y se enseña tal cual, con el enlace para volver a elegir.
      setError(fallo instanceof Error ? fallo.message : 'No se pudo confirmar la reserva.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="contenedor seccion" style={{ maxWidth: '30rem' }}>
      <p style={{ marginBottom: 'var(--espacio-4)' }}>
        <Link href={`/${negocio}`}>← Volver a elegir hora</Link>
      </p>

      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Confirmar tu cita</h1>

      <dl className="panel" style={{ margin: 'var(--espacio-5) 0', display: 'grid', gap: 'var(--espacio-3)' }}>
        <div>
          <dt style={etiqueta}>Servicio</dt>
          <dd style={valor}>{nombre || 'El servicio elegido'}</dd>
        </div>
        <div>
          <dt style={etiqueta}>Cuándo</dt>
          <dd style={valor} className="cifras primera-mayuscula">
            {cuando}
          </dd>
        </div>
      </dl>

      {error && (
        <p role="alert" className="aviso aviso--error" style={{ marginBottom: 'var(--espacio-4)' }}>
          {error}{' '}
          <Link href={`/${negocio}`} style={{ color: 'inherit' }}>
            Elegir otra hora
          </Link>
        </p>
      )}

      {telefonoVerificado === null ? (
        <p className="tenue">Un momento…</p>
      ) : telefonoVerificado ? (
        <>
          <button onClick={confirmar} disabled={enviando} className="boton boton--cierra boton--ancho">
            {enviando ? 'Un momento…' : 'Confirmar la cita'}
          </button>
          <p
            style={{
              marginTop: 'var(--espacio-3)',
              color: 'var(--color-tinta-tenue)',
              fontSize: 'var(--tipografia-tamano-menor)',
            }}
          >
            Podrás cancelarla desde «Mis reservas» hasta dos horas antes. Después, hablando con
            el salón.
          </p>
        </>
      ) : (
        <form onSubmit={paso === 'telefono' ? pedirCodigo : verificar} style={{ display: 'grid', gap: 'var(--espacio-3)' }}>
          <p style={{ color: 'var(--color-tinta-suave)' }}>
            Falta tu teléfono para reservar: es por donde te llama el salón si hay que mover la
            cita. Te mandamos un código y listo.
          </p>
          <label style={{ display: 'grid', gap: 'var(--espacio-2)' }}>
            <span style={{ fontWeight: 'var(--tipografia-pesos-medio)' }}>Tu nombre</span>
            <input
              type="text"
              autoComplete="name"
              value={nombreCliente}
              onChange={(e) => setNombreCliente(e.target.value)}
              placeholder="Como quieres que te llamen en el salón"
              className="entrada"
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
              className="entrada cifras"
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
                className="entrada entrada--codigo"
              />
              {pista && (
                <span style={{ color: 'var(--color-tinta-tenue)', fontSize: 'var(--tipografia-tamano-menor)' }}>
                  En local no hay WhatsApp todavía. Tu código es <strong className="cifras">{pista}</strong>.
                </span>
              )}
            </label>
          )}
          <button
            type="submit"
            disabled={enviando}
            className={`boton boton--ancho ${paso === 'telefono' ? 'boton--primario' : 'boton--cierra'}`}
          >
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
  color: 'var(--color-tinta-suave)',
  fontSize: 'var(--tipografia-tamano-menor)',
  margin: 0,
}
const valor: React.CSSProperties = {
  margin: 0,
  fontWeight: 'var(--tipografia-pesos-medio)',
  fontSize: 'var(--tipografia-tamano-mayor)',
}
