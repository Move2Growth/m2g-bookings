'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { use, useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { API, guardarSesion, leerSesion } from '@/lib/sesion'

/**
 * Aceptar la invitación al equipo de un salón.
 *
 * **La ruta es la que escribe el correo**, no una elegida aquí: `apps/api/agenda/servicios/
 * miembros.py` monta `{URL_PUBLICA_WEB}/invitacion/{token}`. Si esta pantalla viviera en otra
 * dirección, el enlace del correo llevaría a un 404 y nadie se enteraría hasta que alguien
 * intentara entrar de verdad.
 *
 * Son **dos formularios distintos en la misma pantalla**, y la diferencia no es cosmética:
 *
 * · `cuenta_ya_tiene_dueno: false` → la cuenta la creó la propia invitación y no hay otra forma
 *   de entrar en ella. Se elige aquí la contraseña y con eso queda activada. Haber abierto el
 *   enlace es la prueba de que ese buzón es suyo.
 * · `cuenta_ya_tiene_dueno: true` → esa cuenta es de alguien: tiene contraseña, teléfono
 *   verificado o Google/Apple. Entonces **hay que estar dentro con ella**, y el token viaja con
 *   la sesión puesta. Un enlace de correo no puede dar acceso a la cuenta de otra persona: quien
 *   lo interceptara no entraría en un salón, entraría en una cuenta.
 *
 * En cliente y no en servidor porque `ver` es un POST con el token en el cuerpo, y porque al
 * aceptar hay que guardar la sesión que devuelve —ya en modo negocio— en el navegador.
 */

type Invitacion = {
  negocio: string
  rol: string
  correo: string
  nombre: string
  caduca: string
  cuenta_ya_tiene_dueno: boolean
}

const PAPEL: Record<string, string> = {
  dueno: 'administrar el salón',
  profesional: 'atender y llevar tu agenda',
}

/** Qué puede hacer cada papel, en una frase. «Rol: dueno» no le dice nada a nadie. */
function queHace(rol: string): string {
  return PAPEL[rol] ?? rol
}

export default function AceptarInvitacion({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params)
  const router = useRouter()

  const [invitacion, setInvitacion] = useState<Invitacion | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fallo, setFallo] = useState<string | null>(null)
  const [contrasena, setContrasena] = useState('')
  const [aceptando, setAceptando] = useState(false)
  const [sesion, setSesion] = useState(() => leerSesion())

  const mirar = useCallback(async () => {
    setError(null)
    try {
      const respuesta = await fetch(`${API}/api/v1/invitaciones/ver`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      })
      const datos = await respuesta.json().catch(() => null)
      if (!respuesta.ok) {
        throw new Error(datos?.error?.mensaje ?? 'Esa invitación ya no vale.')
      }
      setInvitacion(datos as Invitacion)
    } catch (problema) {
      setError(problema instanceof Error ? problema.message : 'No pudimos abrir la invitación.')
    }
  }, [token])

  useEffect(() => {
    setSesion(leerSesion())
    void mirar()
  }, [mirar])

  async function aceptar(evento: React.FormEvent) {
    evento.preventDefault()
    setAceptando(true)
    setFallo(null)
    try {
      const respuesta = await fetch(`${API}/api/v1/invitaciones/aceptar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Solo cuando la cuenta ya existe: es la prueba de que quien acepta es su dueño.
          ...(sesion ? { Authorization: `Bearer ${sesion.acceso}` } : {}),
        },
        body: JSON.stringify({
          token,
          contrasena: invitacion?.cuenta_ya_tiene_dueno ? undefined : contrasena,
          superficie: 'web',
        }),
      })
      const datos = await respuesta.json().catch(() => null)
      if (!respuesta.ok) {
        throw new Error(datos?.error?.mensaje ?? 'No se pudo aceptar la invitación.')
      }
      // Vuelve **ya en modo negocio**: se guarda tal cual con el nombre del salón y el papel,
      // porque el panel sin contexto es un panel donde se apunta la cita en la agenda de otro.
      guardarSesion({
        acceso: datos.acceso,
        refresco: datos.refresco,
        usuario_id: datos.usuario_id,
        negocio_activo: datos.negocio_activo ?? null,
        negocio_nombre: invitacion?.negocio ?? null,
        negocio_rol: invitacion?.rol ?? null,
      })
      router.push('/panel/agenda')
    } catch (problema) {
      setFallo(problema instanceof Error ? problema.message : 'No se pudo aceptar la invitación.')
    } finally {
      setAceptando(false)
    }
  }

  const caduca = invitacion
    ? new Intl.DateTimeFormat('es-PA', {
        day: 'numeric',
        month: 'long',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(new Date(invitacion.caduca))
    : ''

  // Ya está dentro, pero con otra cuenta. Es el caso que más despista: la pantalla parece que
  // funciona y luego el servidor dice que no. Se avisa antes de que toque nada.
  const otraCuenta =
    invitacion?.cuenta_ya_tiene_dueno === true && sesion === null

  return (
    <main className="contenedor seccion" style={{ maxWidth: '30rem' }}>
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Te han invitado a un salón</h1>

      {error && (
        <div style={{ marginTop: 'var(--espacio-4)' }}>
          <BloqueDeError mensaje={error} reintentar={() => void mirar()} />
          <p style={{ marginTop: 'var(--espacio-4)' }}>
            <Link href="/">Volver al inicio</Link>
          </p>
        </div>
      )}

      {!invitacion && !error && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Esqueleto filas={2} alto={84} etiqueta="Abriendo la invitación" />
        </div>
      )}

      {invitacion && (
        <>
          {/* Lo primero, y con el nombre del salón grande: a qué salón y con qué papel. Es
              literalmente lo que pide el encargo, y es lo que hay que saber antes de aceptar
              nada. */}
          <dl
            className="panel"
            style={{ margin: 'var(--espacio-5) 0', display: 'grid', gap: 'var(--espacio-3)' }}
          >
            <div>
              <dt className="dato">Salón</dt>
              <dd style={{ margin: 0, fontWeight: 'var(--tipografia-pesos-medio)', fontSize: 'var(--tipografia-tamano-mayor)' }}>
                {invitacion.negocio}
              </dd>
            </div>
            <div>
              <dt className="dato">Qué vas a poder hacer</dt>
              <dd style={{ margin: 0, fontWeight: 'var(--tipografia-pesos-medio)' }}>
                {queHace(invitacion.rol)}
              </dd>
            </div>
            <div>
              <dt className="dato">A nombre de</dt>
              <dd style={{ margin: 0 }}>
                {invitacion.nombre} · <span className="tenue">{invitacion.correo}</span>
              </dd>
            </div>
            <div>
              <dt className="dato">Caduca</dt>
              <dd style={{ margin: 0 }} className="cifras">
                {caduca}
              </dd>
            </div>
          </dl>

          {fallo && (
            <p role="alert" className="aviso aviso--error" style={{ marginBottom: 'var(--espacio-4)' }}>
              {fallo}
            </p>
          )}

          {invitacion.cuenta_ya_tiene_dueno ? (
            otraCuenta ? (
              /* Ya tiene cuenta y no está dentro. No se le pide contraseña aquí —esta pantalla
                 no es la de acceso— y se le manda a entrar con el enlace de vuelta puesto, para
                 que caiga otra vez en esta misma invitación. */
              <>
                <p className="aviso aviso--info">
                  Ya tienes cuenta con <strong>{invitacion.correo}</strong>. Entra con ella y
                  vuelves aquí solo.
                </p>
                <Link
                  href={`/entrar?volver=${encodeURIComponent(`/invitacion/${token}`)}`}
                  className="boton boton--cierra boton--ancho"
                  style={{ marginTop: 'var(--espacio-4)' }}
                >
                  Entrar con mi cuenta
                </Link>
              </>
            ) : (
              <form onSubmit={aceptar}>
                <p style={{ color: 'var(--color-tinta-suave)', marginBottom: 'var(--espacio-4)' }}>
                  Al aceptar, {invitacion.negocio} aparece en tu cuenta y entras directo a su
                  agenda.
                </p>
                <button type="submit" disabled={aceptando} className="boton boton--cierra boton--ancho">
                  {aceptando ? 'Un momento…' : `Aceptar y entrar a ${invitacion.negocio}`}
                </button>
                {/* La salida para el caso que no se puede detectar antes de pulsar: hay sesión,
                    pero es de otra cuenta. El servidor lo dice arriba y esto es a dónde ir. */}
                <p style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-menor)' }}>
                  ¿No es tu cuenta?{' '}
                  <Link href={`/entrar?volver=${encodeURIComponent(`/invitacion/${token}`)}`}>
                    Entra con {invitacion.correo}
                  </Link>{' '}
                  y vuelves aquí solo.
                </p>
              </form>
            )
          ) : (
            /* La cuenta la creó la invitación: aquí se elige la contraseña y con eso queda
               activada. Es un formulario distinto, no el mismo con un campo de más. */
            <form onSubmit={aceptar} className="formulario" style={{ display: 'grid', gap: 'var(--espacio-4)' }}>
              <p style={{ color: 'var(--color-tinta-suave)' }}>
                Te creamos la cuenta con <strong>{invitacion.correo}</strong>. Elige una
                contraseña y ya estás dentro.
              </p>
              <label className="campo">
                <span>Tu contraseña</span>
                <input
                  className="entrada"
                  type="password"
                  autoComplete="new-password"
                  minLength={10}
                  required
                  value={contrasena}
                  onChange={(e) => setContrasena(e.target.value)}
                  placeholder="Al menos diez caracteres"
                />
                <span className="campo-ayuda">
                  Diez caracteres o más. Es con lo que vas a entrar a partir de ahora.
                </span>
              </label>
              <button type="submit" disabled={aceptando} className="boton boton--cierra boton--ancho">
                {aceptando ? 'Un momento…' : `Aceptar y entrar a ${invitacion.negocio}`}
              </button>
            </form>
          )}

          <p className="tenue" style={{ marginTop: 'var(--espacio-5)', fontSize: 'var(--tipografia-tamano-menor)' }}>
            Si no esperabas esto, no hagas nada: la invitación caduca sola y quien la mandó lo
            verá en su panel.
          </p>
        </>
      )}
    </main>
  )
}
