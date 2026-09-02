'use client'

import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useState } from 'react'
import { Marca } from '@/componentes/marca'
import { API, guardarSesion } from '@/lib/sesion'

/**
 * Entrar. La misma puerta para la clienta y para el salón: quien tiene negocio acaba en su
 * agenda y quien no, en sus citas. Tener dos accesos distintos obligaría a la persona a saber
 * de antemano qué es, y la mitad de las veces es las dos cosas.
 *
 * Dos pasos y ninguno más. No hay contraseña que recordar ni registro aparte: quien verifica
 * su teléfono ya tiene cuenta (ONB-1).
 */
/**
 * A dónde se vuelve después de entrar.
 *
 * Quien pulsa «guardar» en la ficha de un salón y acaba en la pantalla de acceso tiene que
 * volver **a esa ficha**, no a un listado genérico: si no, pierde lo que estaba haciendo y casi
 * nadie lo retoma.
 *
 * Solo se admiten rutas internas. Un `volver` con un dominio de fuera convertiría esta pantalla
 * en un trampolín para llevarse a alguien a otro sitio después de entrar, que es un fallo de
 * seguridad clásico y barato de evitar.
 */
function destinoSeguro(crudo: string | null, porDefecto: string) {
  if (!crudo) return porDefecto
  if (!crudo.startsWith('/') || crudo.startsWith('//')) return porDefecto
  return crudo
}

function Contenido() {
  const router = useRouter()
  const parametros = useSearchParams()
  const volver = destinoSeguro(parametros.get('volver'), '/mi/citas')
  const [paso, setPaso] = useState<'telefono' | 'codigo' | 'negocio'>('telefono')
  const [negocios, setNegocios] = useState<{ id: string; nombre: string; rol: string }[]>([])
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
      // En local no hay canal todavía, así que la API devuelve el código y se enseña aquí para
      // poder probar el flujo entero sin credenciales de Meta.
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

      // El token recién emitido todavía no lleva negocio, así que aquí se pregunta en cuáles
      // trabaja esta persona. Con uno solo se cambia de contexto sin preguntar nada: hacerle
      // elegir entre una única opción es una pantalla que no informa de nada. Con varios, se
      // elige; sin ninguno, es una clienta y va a sus citas.
      const negocios = await fetch(`${API}/api/v1/mi/negocios`, {
        headers: { Authorization: `Bearer ${datos.acceso}` },
      })
        .then((r) => (r.ok ? r.json() : []))
        .catch(() => [])

      if (negocios.length === 1) {
        const conNegocio = await fetch(`${API}/api/v1/auth/modo-negocio`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${datos.acceso}` },
          body: JSON.stringify({ negocio_id: negocios[0].id }),
        }).then((r) => (r.ok ? r.json() : null))
        if (conNegocio) {
          guardarSesion({ ...conNegocio, negocio_nombre: negocios[0].nombre, negocio_rol: negocios[0].rol })
          router.push('/panel')
          return
        }
      }

      if (negocios.length > 1) {
        setNegocios(negocios)
        setPaso('negocio')
        return
      }

      router.push(volver)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'Ese código no es válido.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="acceso">
      {/* Columna de marca. En un teléfono desaparece: ahí lo único que importa es el campo. */}
      <aside className="acceso__marca">
        <Link href="/" aria-label="Bukeo, inicio">
          <Marca alto={24} />
        </Link>
        <div>
          <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>
            La hora que sí existe
          </h1>
          <p style={{ marginTop: 'var(--espacio-4)', opacity: 0.82, maxWidth: '34ch' }}>
            Tu agenda y tus clientas en el mismo sitio. Gratis para el salón, sin tarjeta y sin
            comisión por cita.
          </p>
        </div>
        <p className="tenue">
          Ciudad de Panamá
        </p>
      </aside>

      <div className="acceso__panel">
        <div className="acceso__caja">
          <Link href="/" aria-label="Bukeo, inicio" className="acceso__marca-movil">
            <Marca alto={22} />
          </Link>

          <h2 style={{ marginTop: 'var(--espacio-5)' }}>
            {paso === 'telefono' && 'Entra con tu teléfono'}
            {paso === 'codigo' && 'Escribe tu código'}
            {paso === 'negocio' && 'Con qué salón entras'}
          </h2>
          <p className="apagado" style={{ marginTop: 'var(--espacio-2)' }}>
            {paso === 'telefono' && 'Te mandamos un código por WhatsApp. No hay contraseña que recordar.'}
            {paso === 'codigo' && `Te llegó un código de 6 dígitos al ${telefono}.`}
            {paso === 'negocio' && 'Trabajas en más de uno. Puedes cambiar cuando quieras.'}
          </p>

          {paso === 'negocio' && (
            <ul className="lista-filete" style={{ marginTop: 'var(--espacio-5)', borderTop: '1px solid var(--color-borde)' }}>
              {negocios.map((n) => (
                <li key={n.id} style={{ borderBottom: '1px solid var(--color-borde)' }}>
                  <button
                    className="boton boton--llano boton--ancho"
                    style={{ justifyContent: 'space-between', paddingInline: 0 }}
                    onClick={async () => {
                      const guardada = JSON.parse(window.localStorage.getItem('agenda.sesion') ?? 'null')
                      const conNegocio = await fetch(`${API}/api/v1/auth/modo-negocio`, {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                          Authorization: `Bearer ${guardada.acceso}`,
                        },
                        body: JSON.stringify({ negocio_id: n.id }),
                      }).then((r) => (r.ok ? r.json() : null))
                      if (conNegocio) {
                        guardarSesion({ ...conNegocio, negocio_nombre: n.nombre, negocio_rol: n.rol })
                        router.push('/panel')
                      }
                    }}
                  >
                    <span style={{ color: 'var(--color-tinta)' }}>{n.nombre}</span>
                    <span className="tenue">{n.rol === 'dueno' ? 'Dueño' : 'Profesional'}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {paso !== 'negocio' && (
          <form
            onSubmit={paso === 'telefono' ? pedirCodigo : verificar}
            style={{ display: 'grid', gap: 'var(--espacio-4)', marginTop: 'var(--espacio-5)' }}
          >
            <div className="campo">
              <label htmlFor="telefono">Tu teléfono</label>
              <input
                id="telefono"
                className="entrada cifras"
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                value={telefono}
                onChange={(e) => setTelefono(e.target.value)}
                disabled={paso === 'codigo'}
                required
              />
            </div>

            {paso === 'codigo' && (
              <div className="campo">
                <label htmlFor="codigo">Código de 6 dígitos</label>
                <input
                  id="codigo"
                  className="entrada entrada--codigo"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value.replace(/\D/g, ''))}
                  required
                  autoFocus
                />
                {pista && (
                  <p className="tenue">
                    En local todavía no hay WhatsApp. Tu código es{' '}
                    <strong className="cifras">{pista}</strong>.
                  </p>
                )}
                <button
                  type="button"
                  className="boton boton--llano"
                  style={{ justifySelf: 'start', paddingInline: 0 }}
                  onClick={() => {
                    setPaso('telefono')
                    setCodigo('')
                    setError(null)
                  }}
                >
                  Cambiar el número
                </button>
              </div>
            )}

            {error && (
              <p role="alert" className="aviso aviso--error">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={enviando}
              className={`boton boton--ancho ${paso === 'telefono' ? 'boton--primario' : 'boton--cierra'}`}
            >
              {enviando ? 'Un momento…' : paso === 'telefono' ? 'Mandarme el código' : 'Entrar'}
            </button>
          </form>
          )}

          <p className="tenue" style={{ marginTop: 'var(--espacio-5)' }}>
            Al entrar aceptas los <Link href="/legal/terminos">términos</Link> y la{' '}
            <Link href="/legal/privacidad">política de privacidad</Link>. Puedes borrar tu cuenta
            cuando quieras desde tus ajustes.
          </p>
        </div>
      </div>
    </main>
  )
}

/**
 * `useSearchParams` obliga a un límite de suspensión: sin él, Next no puede prerenderizar esta
 * página y el build falla. El respaldo es el armazón vacío, no un «cargando», porque en la
 * práctica se resuelve en el mismo fotograma.
 */
export default function Entrar() {
  return (
    <Suspense fallback={<div className="acceso" aria-hidden="true" />}>
      <Contenido />
    </Suspense>
  )
}
