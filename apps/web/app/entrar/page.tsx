'use client'

import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useState } from 'react'
import { Marca } from '@/componentes/marca'
import { API, guardarSesion } from '@/lib/sesion'

/**
 * Entrar y darse de alta. La misma puerta para la clienta y para el salón: quien tiene negocio
 * acaba en su agenda y quien no, en sus citas. Tener dos accesos distintos obligaría a la
 * persona a saber de antemano qué es, y la mitad de las veces es las dos cosas.
 *
 * **Correo y contraseña.** El código por WhatsApp era un peaje —pedirlo, buscarlo y teclearlo
 * antes de que caducara— y no daba ninguna seguridad que la contraseña no dé. El código se
 * queda para verificar el teléfono antes de la primera reserva, que es donde hace falta porque
 * el salón tiene que poder llamar.
 *
 * En el alta **no se pide el teléfono**, por lo mismo: pedirlo aquí devuelve el trámite que se
 * quitó. Se pide cuando se va a reservar.
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

/** El mínimo del servidor, repetido aquí solo para avisar antes de enviar. Quien manda es la API. */
const LARGO_MINIMO = 10

type Modo = 'entrar' | 'alta'

function Contenido() {
  const router = useRouter()
  const parametros = useSearchParams()
  const volver = destinoSeguro(parametros.get('volver'), '/mi/citas')

  const [modo, setModo] = useState<Modo>('entrar')
  const [negocios, setNegocios] = useState<{ id: string; nombre: string; rol: string }[]>([])
  const [eligiendoNegocio, setEligiendoNegocio] = useState(false)
  const [nombre, setNombre] = useState('')
  const [correo, setCorreo] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  /**
   * Entra en el negocio elegido y va al panel.
   *
   * Cambiar de negocio es **pedir otro token**, no mandar un parámetro distinto: si el negocio
   * activo viajara en cada llamada, cambiar de salón sería cambiar un número en la URL.
   */
  async function entrarEnNegocio(
    acceso: string,
    negocio: { id: string; nombre: string; rol: string },
  ) {
    const conNegocio = await fetch(`${API}/api/v1/auth/modo-negocio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${acceso}` },
      body: JSON.stringify({ negocio_id: negocio.id }),
    }).then((r) => (r.ok ? r.json() : null))
    if (!conNegocio) return false
    guardarSesion({ ...conNegocio, negocio_nombre: negocio.nombre, negocio_rol: negocio.rol })
    router.push('/panel')
    return true
  }

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setError(null)
    try {
      const ruta = modo === 'alta' ? '/api/v1/auth/registrar' : '/api/v1/auth/entrar'
      const cuerpo = modo === 'alta' ? { nombre, correo, contrasena } : { correo, contrasena }

      const respuesta = await fetch(`${API}${ruta}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cuerpo),
      })
      const datos = await respuesta.json()
      if (!respuesta.ok) {
        // Un solo formato para todos los errores de la API, incluidos los de validación: eso se
        // arregló en el servidor. Aquí solo queda el respaldo por si un día llega algo sin
        // mensaje, que no es lo mismo que sostener dos formatos a la vez.
        const mensaje =
          datos?.error?.mensaje ??
          (modo === 'alta' ? 'No se pudo crear la cuenta.' : 'Correo o contraseña incorrectos.')
        throw new Error(mensaje)
      }
      guardarSesion(datos)

      // El token recién emitido todavía no lleva negocio, así que aquí se pregunta en cuáles
      // trabaja esta persona. Con uno solo se cambia de contexto sin preguntar nada: hacerle
      // elegir entre una única opción es una pantalla que no informa de nada. Con varios, se
      // elige; sin ninguno, es una clienta y va a sus citas.
      const suyos = await fetch(`${API}/api/v1/mi/negocios`, {
        headers: { Authorization: `Bearer ${datos.acceso}` },
      })
        .then((r) => (r.ok ? r.json() : []))
        .catch(() => [])

      if (suyos.length === 1 && (await entrarEnNegocio(datos.acceso, suyos[0]))) return

      if (suyos.length > 1) {
        setNegocios(suyos)
        setEligiendoNegocio(true)
        return
      }

      router.push(volver)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo entrar.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="acceso">
      {/* Columna de marca. En un teléfono desaparece: ahí lo único que importa es el campo. */}
      <aside className="acceso__marca">
        <Link href="/" aria-label="Inicio">
          <Marca alto={24} />
        </Link>
        <div>
          <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>La hora que sí existe</h1>
          <p style={{ marginTop: 'var(--espacio-4)', opacity: 0.82, maxWidth: '34ch' }}>
            Tu agenda y tus clientas en el mismo sitio. Gratis para el salón, sin tarjeta y sin
            comisión por cita.
          </p>
        </div>
        <p className="tenue">Ciudad de Panamá</p>
      </aside>

      <div className="acceso__panel">
        <div className="acceso__caja">
          <Link href="/" aria-label="Inicio" className="acceso__marca-movil">
            <Marca alto={22} />
          </Link>

          <h2 style={{ marginTop: 'var(--espacio-5)' }}>
            {eligiendoNegocio
              ? 'Con qué salón entras'
              : modo === 'entrar'
                ? 'Entra en tu cuenta'
                : 'Crea tu cuenta'}
          </h2>
          <p className="apagado" style={{ marginTop: 'var(--espacio-2)' }}>
            {eligiendoNegocio
              ? 'Trabajas en más de uno. Puedes cambiar cuando quieras.'
              : modo === 'entrar'
                ? 'Con tu correo y tu contraseña.'
                : 'Solo tu nombre, tu correo y una contraseña. El teléfono te lo pedimos cuando vayas a reservar.'}
          </p>

          {eligiendoNegocio && (
            <ul
              className="lista-filete"
              style={{ marginTop: 'var(--espacio-5)', borderTop: '1px solid var(--color-borde)' }}
            >
              {negocios.map((n) => (
                <li key={n.id} style={{ borderBottom: '1px solid var(--color-borde)' }}>
                  <button
                    className="boton boton--llano boton--ancho"
                    style={{ justifyContent: 'space-between', paddingInline: 0 }}
                    onClick={async () => {
                      const guardada = JSON.parse(
                        window.localStorage.getItem('agenda.sesion') ?? 'null',
                      )
                      if (guardada) await entrarEnNegocio(guardada.acceso, n)
                    }}
                  >
                    <span style={{ color: 'var(--color-tinta)' }}>{n.nombre}</span>
                    <span className="tenue">{n.rol === 'dueno' ? 'Dueño' : 'Profesional'}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {!eligiendoNegocio && (
            <form
              onSubmit={enviar}
              style={{ display: 'grid', gap: 'var(--espacio-4)', marginTop: 'var(--espacio-5)' }}
            >
              {modo === 'alta' && (
                <div className="campo">
                  <label htmlFor="nombre">Tu nombre</label>
                  <input
                    id="nombre"
                    className="entrada"
                    type="text"
                    autoComplete="name"
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    required
                  />
                </div>
              )}

              <div className="campo">
                <label htmlFor="correo">Tu correo</label>
                <input
                  id="correo"
                  className="entrada"
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  value={correo}
                  onChange={(e) => setCorreo(e.target.value)}
                  required
                />
              </div>

              <div className="campo">
                <label htmlFor="contrasena">Tu contraseña</label>
                <input
                  id="contrasena"
                  className="entrada"
                  type="password"
                  // `new-password` en el alta y `current-password` al entrar: es lo que hace que
                  // el gestor del navegador ofrezca guardar una nueva en vez de rellenar la vieja.
                  autoComplete={modo === 'alta' ? 'new-password' : 'current-password'}
                  minLength={modo === 'alta' ? LARGO_MINIMO : undefined}
                  value={contrasena}
                  onChange={(e) => setContrasena(e.target.value)}
                  required
                />
                {modo === 'alta' && (
                  <p className="tenue">
                    Al menos {LARGO_MINIMO} caracteres. Una frase que recuerdes vale más que un
                    jeroglífico.
                  </p>
                )}
              </div>

              {error && (
                <p role="alert" className="aviso aviso--error">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={enviando}
                className="boton boton--ancho boton--cierra"
              >
                {enviando ? 'Un momento…' : modo === 'entrar' ? 'Entrar' : 'Crear mi cuenta'}
              </button>

              <button
                type="button"
                className="boton boton--llano"
                style={{ justifySelf: 'start', paddingInline: 0 }}
                onClick={() => {
                  setModo(modo === 'entrar' ? 'alta' : 'entrar')
                  setError(null)
                  setContrasena('')
                }}
              >
                {modo === 'entrar'
                  ? '¿No tienes cuenta? Créala'
                  : '¿Ya tienes cuenta? Entra'}
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
