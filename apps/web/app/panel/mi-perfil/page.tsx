'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * La ficha pública de un profesional, editada por él mismo (encargo 2026-09-07 §3).
 *
 * Es **suya, no del salón**: el dueño edita el equipo desde `/panel/equipo`, y esta pantalla
 * habla con `/mi/perfil-profesional`, que no lleva ni un `if` de rol porque solo alcanza a
 * quien la pide. Por eso un profesional puede escribir aquí su descripción sin poder tocar la
 * de nadie más.
 *
 * Lo que se edita es lo que el encargo enumera: **titular, descripción, años y redes**. El
 * nombre y el slug no se tocan aquí a propósito: el nombre es el que el salón puso en la
 * agenda y cambiarlo por libre descuadra lo que ve la clienta; el slug es la URL que ya está
 * compartida.
 *
 * Las redes se escriben **por usuario, no por dirección completa**: la API monta la URL. Quien
 * pega `https://instagram.com/kevin/?utm=...` no está dando su usuario, está dando un enlace de
 * una sesión suya, y eso caduca.
 */

type MiPerfil = {
  id: string
  slug: string | null
  nombre: string
  titular: string | null
  descripcion: string | null
  foto: string | null
  anos_de_experiencia: number | null
  instagram: string | null
  instagram_url: string | null
  facebook: string | null
  facebook_url: string | null
  x: string | null
  x_url: string | null
  citas_atendidas: number
  clientes_atendidos: number
  activo: boolean
  visible_en_marketplace: boolean
}

/** Quita lo que la gente pega de más: la URL entera, la arroba y la barra final. */
function soloUsuario(escrito: string): string {
  return escrito
    .trim()
    .replace(/^https?:\/\/(www\.)?(instagram|facebook|twitter|x)\.com\//i, '')
    .replace(/^@/, '')
    .replace(/\/+$/, '')
    .split(/[?#]/)[0]
}

export default function MiPerfilProfesional() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [perfil, setPerfil] = useState<MiPerfil | null>(null)
  /** El slug del salón activo. Hace falta para el enlace a la página pública, y no viaja en la
   *  sesión: la sesión guarda el nombre, que es lo que se pinta, no lo que se enlaza. */
  const [salon, setSalon] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [guardando, setGuardando] = useState(false)
  const [guardado, setGuardado] = useState(false)

  const [titular, setTitular] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [anos, setAnos] = useState('')
  const [instagram, setInstagram] = useState('')
  const [facebook, setFacebook] = useState('')
  const [equis, setEquis] = useState('')

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      const datos = await conSesion<MiPerfil>('/api/v1/mi/perfil-profesional', {
        token: actual.acceso,
      })
      setPerfil(datos)
      setTitular(datos.titular ?? '')
      setDescripcion(datos.descripcion ?? '')
      setAnos(datos.anos_de_experiencia === null ? '' : String(datos.anos_de_experiencia))
      setInstagram(datos.instagram ?? '')
      setFacebook(datos.facebook ?? '')
      setEquis(datos.x ?? '')
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar tu ficha.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  useEffect(() => {
    if (!sesion) return
    // Que falle esto no puede tumbar la pantalla: lo único que se pierde es el enlace de
    // «ver mi página pública», y el formulario funciona igual.
    conSesion<{ id: string; slug: string }[]>('/api/v1/mi/negocios', { token: sesion.acceso })
      .then((negocios) =>
        setSalon(negocios.find((n) => n.id === sesion.negocio_activo)?.slug ?? null),
      )
      .catch(() => setSalon(null))
  }, [sesion])

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault()
    if (!sesion) return
    setGuardando(true)
    setGuardado(false)
    setError(null)
    try {
      const actualizado = await conSesion<MiPerfil>('/api/v1/mi/perfil-profesional', {
        metodo: 'PATCH',
        token: sesion.acceso,
        cuerpo: {
          titular: titular.trim() || null,
          descripcion: descripcion.trim() || null,
          // Cadena vacía es «no lo sé», y eso es un nulo. Un cero significaría «empecé hoy».
          anos_de_experiencia: anos.trim() === '' ? null : Number(anos),
          instagram: instagram.trim() ? soloUsuario(instagram) : null,
          facebook: facebook.trim() ? soloUsuario(facebook) : null,
          x: equis.trim() ? soloUsuario(equis) : null,
        },
      })
      setPerfil(actualizado)
      setInstagram(actualizado.instagram ?? '')
      setFacebook(actualizado.facebook ?? '')
      setEquis(actualizado.x ?? '')
      setGuardado(true)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron guardar los cambios.')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="contenedor seccion" style={{ maxWidth: '38rem' }}>
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Mi ficha</h1>
      <p className="apagado medida" style={{ marginTop: 'var(--espacio-2)' }}>
        Esto es lo que ve una clienta cuando te elige a ti antes que al salón.
      </p>

      {error && (
        <div style={{ marginTop: 'var(--espacio-4)' }}>
          <BloqueDeError
            mensaje={error}
            reintentar={sesion ? () => void cargar(sesion) : undefined}
          />
        </div>
      )}

      {perfil === null && !error && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Esqueleto filas={4} alto={72} etiqueta="Cargando tu ficha" />
        </div>
      )}

      {perfil && (
        <>
          {/* Lo que no se edita, pero que hay que ver: quién eres, cuánta gente has atendido y
              **el enlace a tu página pública**. Sin ese enlace, nadie comprueba nunca cómo se
              ve lo que acaba de escribir. */}
          <div className="datos vistazo" style={{ marginTop: 'var(--espacio-5)' }}>
            <div>
              <b className="cifras">{perfil.clientes_atendidos}</b>
              <small>personas atendidas</small>
            </div>
            <div>
              <b className="cifras">{perfil.citas_atendidas}</b>
              <small>citas hechas</small>
            </div>
          </div>

          {perfil.visible_en_marketplace && salon ? (
            <p style={{ marginTop: 'var(--espacio-3)' }}>
              <Link href={`/${salon}/${perfil.slug ?? perfil.id}`} prefetch={false}>
                Ver mi página pública
              </Link>
            </p>
          ) : !perfil.visible_en_marketplace ? (
            <p className="aviso aviso--info" style={{ marginTop: 'var(--espacio-4)' }}>
              Tu ficha está oculta en el marketplace ahora mismo. Lo que escribas aquí se guarda,
              pero no se ve fuera hasta que quien administra el salón la vuelva a mostrar.
            </p>
          ) : null}

          <form onSubmit={guardar} className="formulario" style={{ marginTop: 'var(--espacio-5)', display: 'grid', gap: 'var(--espacio-5)' }}>
            <label className="campo">
              <span>Tu oficio en una línea</span>
              <input
                className="entrada"
                value={titular}
                maxLength={140}
                onChange={(e) => setTitular(e.target.value)}
                placeholder="Barbero. Fades y perfilado de barba"
              />
              <span className="campo-ayuda">
                Es lo que se lee debajo de tu nombre en la búsqueda. {140 - titular.length}{' '}
                caracteres libres.
              </span>
            </label>

            <label className="campo">
              <span>Sobre ti</span>
              <textarea
                className="entrada"
                rows={5}
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                placeholder="Dónde aprendiste, qué haces mejor, cómo trabajas."
              />
              <span className="campo-ayuda">
                Va entera en tu página. Cuenta lo que te distingue, no lo que hace el salón.
              </span>
            </label>

            <label className="campo">
              <span>Años en el oficio</span>
              <input
                className="entrada cifras"
                type="number"
                inputMode="numeric"
                min={0}
                max={80}
                value={anos}
                onChange={(e) => setAnos(e.target.value)}
                placeholder="9"
                style={{ maxWidth: '9rem' }}
              />
              <span className="campo-ayuda">Déjalo vacío si prefieres no decirlo.</span>
            </label>

            <fieldset style={{ border: 0, padding: 0, margin: 0, display: 'grid', gap: 'var(--espacio-4)' }}>
              <legend style={{ fontWeight: 'var(--tipografia-pesos-medio)', padding: 0 }}>
                Tus redes
              </legend>
              <p className="campo-ayuda" style={{ margin: 0 }}>
                Solo el usuario, sin la arroba y sin el enlace entero. Si pegas la dirección
                completa, la recortamos.
              </p>

              <label className="campo">
                <span>Instagram</span>
                <input
                  className="entrada"
                  value={instagram}
                  onChange={(e) => setInstagram(e.target.value)}
                  placeholder="kevincortes507"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                />
                {perfil.instagram_url && (
                  <span className="campo-ayuda">
                    Ahora enlaza a <code>{perfil.instagram_url}</code>
                  </span>
                )}
              </label>

              <label className="campo">
                <span>Facebook</span>
                <input
                  className="entrada"
                  value={facebook}
                  onChange={(e) => setFacebook(e.target.value)}
                  placeholder="tu.usuario"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                />
              </label>

              <label className="campo">
                <span>X</span>
                <input
                  className="entrada"
                  value={equis}
                  onChange={(e) => setEquis(e.target.value)}
                  placeholder="tuusuario"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                />
              </label>
            </fieldset>

            <div className="acciones">
              <button type="submit" disabled={guardando} className="boton boton--cierra">
                {guardando ? 'Guardando…' : 'Guardar mi ficha'}
              </button>
              {guardado && (
                <p role="status" className="aviso aviso--exito">
                  Guardado. Ya se ve así en tu página.
                </p>
              )}
            </div>
          </form>

          <p className="apagado medida" style={{ marginTop: 'var(--espacio-6)' }}>
            ¿Tu foto o tu nombre están mal? Los pone quien administra el salón desde su panel de
            equipo. Tus fotos de trabajo sí son tuyas: están en{' '}
            <Link href="/panel/mis-fotos">Mis fotos</Link>.
          </p>
        </>
      )}
    </div>
  )
}
