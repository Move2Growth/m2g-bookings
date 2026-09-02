'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * El perfil de la clienta.
 *
 * Tiene poco a propósito: aquí no se pide nada que el producto no necesite. El nombre es lo
 * único obligatorio —es lo que ve el salón en su agenda— y el correo es opcional y sirve para
 * el recibo. **El teléfono no se edita**: es la identidad de la cuenta, y cambiarlo es cambiar
 * de cuenta.
 *
 * Y lleva el borrado, que no es un extra: la pantalla de acceso promete que se puede borrar la
 * cuenta desde aquí, y una promesa sin botón es una promesa rota.
 */

type Perfil = {
  nombre: string | null
  correo: string | null
  telefono: string
}

export default function PerfilCliente() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [perfil, setPerfil] = useState<Perfil | null>(null)
  const [nombre, setNombre] = useState('')
  const [correo, setCorreo] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [guardado, setGuardado] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [confirmandoBorrado, setConfirmandoBorrado] = useState(false)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      const datos = await conSesion<Perfil>('/api/v1/mi/perfil', { token: actual.acceso })
      setPerfil(datos)
      setNombre(datos.nombre ?? '')
      setCorreo(datos.correo ?? '')
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar tu perfil.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault()
    if (!sesion) return
    setGuardando(true)
    setGuardado(false)
    setError(null)
    try {
      await conSesion('/api/v1/mi/perfil', {
        metodo: 'PATCH',
        token: sesion.acceso,
        cuerpo: { nombre: nombre.trim(), correo: correo.trim() || null },
      })
      setGuardado(true)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron guardar los cambios.')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="contenedor seccion" style={{ maxWidth: '38rem' }}>
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Tu perfil</h1>

      {error && (
        <div style={{ marginTop: 'var(--espacio-4)' }}>
          <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
        </div>
      )}

      {perfil === null && !error && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Esqueleto filas={3} alto={72} etiqueta="Cargando tu perfil" />
        </div>
      )}

      {perfil && (
        <>
          <form onSubmit={guardar} className="formulario" style={{ marginTop: 'var(--espacio-5)' }}>
            <label className="campo">
              <span>Tu nombre</span>
              <input
                className="entrada"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Como quieres que te llamen en el salón"
                autoComplete="name"
                required
              />
            </label>

            <label className="campo">
              <span>Tu correo (opcional)</span>
              <input
                className="entrada"
                type="email"
                value={correo}
                onChange={(e) => setCorreo(e.target.value)}
                placeholder="Para mandarte el recibo de la cita"
                autoComplete="email"
              />
            </label>

            <div className="campo">
              <span>Tu teléfono</span>
              <p className="entrada entrada--fija cifras">{perfil.telefono}</p>
              <p className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
                Es con lo que entras. Para cambiarlo, escríbenos.
              </p>
            </div>

            <div className="acciones">
              <button type="submit" disabled={guardando} className="boton boton--cierra">
                {guardando ? 'Guardando…' : 'Guardar cambios'}
              </button>
              {guardado && (
                <p role="status" className="aviso aviso--exito">
                  Guardado.
                </p>
              )}
            </div>
          </form>

          <section style={{ marginTop: 'var(--espacio-8)', borderTop: '2px solid var(--color-tinta)', paddingTop: 'var(--espacio-4)' }}>
            <h2 style={{ fontSize: 'var(--tipografia-tamano-titulo-4)' }}>Borrar mi cuenta</h2>
            <p className="apagado medida" style={{ marginTop: 'var(--espacio-2)' }}>
              Se borran tus datos y tus citas futuras se cancelan. Las citas que ya pasaron se
              quedan en el salón sin tu nombre, porque son parte de su contabilidad.
            </p>
            {!confirmandoBorrado ? (
              <button
                type="button"
                className="boton boton--peligro"
                style={{ marginTop: 'var(--espacio-3)' }}
                onClick={() => setConfirmandoBorrado(true)}
              >
                Borrar mi cuenta
              </button>
            ) : (
              /* La confirmación va en la misma pantalla y con las dos salidas a la vista. Un
                 diálogo del navegador se acepta sin leer. */
              <div className="aviso aviso--error" style={{ marginTop: 'var(--espacio-3)' }}>
                <p>
                  <strong>Esto no se puede deshacer.</strong> ¿Seguro?
                </p>
                <div className="acciones" style={{ marginTop: 'var(--espacio-3)' }}>
                  <button
                    type="button"
                    className="boton boton--peligro"
                    onClick={async () => {
                      if (!sesion) return
                      try {
                        await conSesion('/api/v1/mi/cuenta', { metodo: 'DELETE', token: sesion.acceso })
                        window.localStorage.clear()
                        window.location.href = '/'
                      } catch (fallo) {
                        setError(fallo instanceof Error ? fallo.message : 'No se pudo borrar la cuenta.')
                        setConfirmandoBorrado(false)
                      }
                    }}
                  >
                    Sí, bórrala
                  </button>
                  <button
                    type="button"
                    className="boton boton--secundario"
                    onClick={() => setConfirmandoBorrado(false)}
                  >
                    No, cancelar
                  </button>
                </div>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
