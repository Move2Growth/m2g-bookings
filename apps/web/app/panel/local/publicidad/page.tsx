'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Hoja } from '@/componentes/hoja'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'
import type { AnuncioDelSalon } from '@/lib/dueno'

/**
 * Publicidad flash: **el cartel del propio salón**.
 *
 * Lo primero que hay que dejar claro, y por eso está escrito en la pantalla y no solo aquí: esto
 * **no es publicidad del marketplace**. El posicionamiento pagado es otra cosa, se cobra y no
 * tiene nada que ver. Esto es gratis, sale en la ficha del salón y no compite con nadie. Sin esa
 * frase, medio mundo cree que le van a cobrar por escribir un texto.
 *
 * **Se ve antes de publicarlo.** El recuadro de la derecha es el mismo trozo de la ficha pública,
 * con el mismo texto y la misma forma: escribir un cartel a ciegas y descubrir en la calle que se
 * corta a mitad de frase es exactamente lo que hace que nadie vuelva a usar la función.
 *
 * Y apagarlo **no lo borra**: el «Martes de fade» de este mes se vuelve a encender en diciembre.
 */

/** El máximo que acepta la API. Está aquí para poder avisar antes de enviar, no para decidir. */
const LARGO_MAXIMO = 280

export default function Publicidad() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [anuncios, setAnuncios] = useState<AnuncioDelSalon[] | null>(null)
  const [ficha, setFicha] = useState<{ slug: string; nombre: string; estado: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [editando, setEditando] = useState<AnuncioDelSalon | 'nuevo' | null>(null)
  const [trabajando, setTrabajando] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      const [lista, mia] = await Promise.all([
        conSesion<AnuncioDelSalon[]>('/api/v1/negocio/anuncios', { token: actual.acceso }),
        conSesion<{ slug: string; nombre: string; estado: string }>('/api/v1/negocio/ficha', {
          token: actual.acceso,
        }),
      ])
      setAnuncios(lista)
      setFicha(mia)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar tus anuncios.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  async function cambiarEncendido(anuncio: AnuncioDelSalon, encender: boolean) {
    if (!sesion) return
    setTrabajando(anuncio.id)
    setError(null)
    try {
      if (encender) {
        await conSesion(`/api/v1/negocio/anuncios/${anuncio.id}`, {
          metodo: 'PATCH',
          token: sesion.acceso,
          cuerpo: { activo: true },
        })
      } else {
        await conSesion(`/api/v1/negocio/anuncios/${anuncio.id}`, {
          metodo: 'DELETE',
          token: sesion.acceso,
        })
      }
      await cargar(sesion)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cambiar el anuncio.')
    } finally {
      setTrabajando(null)
    }
  }

  const vigente = anuncios?.find((a) => a.vigente) ?? null

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Publicidad flash</h1>
        <button
          type="button"
          className="boton boton--primario"
          onClick={() => setEditando('nuevo')}
        >
          Escribir un anuncio
        </button>
      </div>

      <p className="tenue medida">
        Es el cartel de tu salón dentro de tu ficha. Es gratis y no compite con nadie: el
        posicionamiento pagado del buscador es otra cosa y no tiene nada que ver con esto.
      </p>

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      )}

      {anuncios === null && !error && (
        <Esqueleto filas={2} alto={96} etiqueta="Cargando tus anuncios" />
      )}

      {anuncios && (
        <section className="bloque-panel">
          <h2 className="etiqueta">Así se ve en tu ficha</h2>
          <VistaPrevia texto={vigente?.texto ?? null} nombre={ficha?.nombre ?? 'Tu salón'} />
          {/* La ficha pública se sirve cacheada un minuto para que aguante el tráfico de
              búsqueda. Se dice aquí porque, si no, quien acaba de guardar abre su ficha, ve el
              texto viejo y cree que no se ha guardado. */}
          <p className="campo-ayuda" style={{ marginTop: 'var(--espacio-2)' }}>
            En tu ficha pública puede tardar hasta un minuto en cambiar. Aquí ya está guardado.
          </p>
          {ficha && (
            <p style={{ marginTop: 'var(--espacio-3)' }}>
              {ficha.estado === 'publicado' ? (
                <Link href={`/${ficha.slug}`} className="boton boton--secundario">
                  Abrir mi ficha pública
                </Link>
              ) : (
                <span className="aviso aviso--info">
                  Tu ficha todavía está en borrador, así que este cartel no lo ve nadie fuera.
                  Publícala desde <Link href="/panel/ficha">Ficha</Link> y ya sale.
                </span>
              )}
            </p>
          )}
        </section>
      )}

      {anuncios && anuncios.length === 0 && (
        <Vacio
          icono={Iconos.negocios}
          titulo="Todavía no has escrito ninguno"
          texto="Un cartel corto —una promoción, un horario especial, unas vacaciones— y con fecha de fin, para que se apague solo."
        />
      )}

      {anuncios && anuncios.length > 0 && (
        <section className="bloque-panel">
          <h2 className="etiqueta">Tus anuncios</h2>
          <ul className="filas escalona" style={{ marginTop: 'var(--espacio-3)' }}>
            {anuncios.map((anuncio) => (
              <li key={anuncio.id} className="fila">
                <button
                  type="button"
                  className="fila__boton"
                  onClick={() => setEditando(anuncio)}
                >
                  <span className="fila__principal">
                    <span className="fila__nombre">{anuncio.texto}</span>
                    <span className="fila__detalle">
                      {anuncio.vigente ? (
                        'Se está viendo ahora'
                      ) : anuncio.activo ? (
                        <span className="fila__alerta">Encendido, pero fuera de fecha</span>
                      ) : (
                        'Apagado'
                      )}
                      {anuncio.hasta ? ` · hasta el ${soloFecha(anuncio.hasta)}` : ' · sin fecha de fin'}
                    </span>
                  </span>
                </button>
                {/* Apagar no está pegado a editar: es la acción que se lamenta, y en un teléfono
                    dos botones juntos se pulsan a ciegas. */}
                <div
                  className="acciones-fila"
                  style={{ padding: '0 var(--espacio-3) var(--espacio-3)' }}
                >
                  <button
                    type="button"
                    className={anuncio.activo ? 'boton boton--llano' : 'boton boton--secundario'}
                    disabled={trabajando === anuncio.id}
                    onClick={() => void cambiarEncendido(anuncio, !anuncio.activo)}
                  >
                    {trabajando === anuncio.id
                      ? 'Un momento…'
                      : anuncio.activo
                        ? 'Apagarlo'
                        : 'Volver a encenderlo'}
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
            Apagar un anuncio no lo borra: se queda aquí por si quieres volver a lanzarlo.
          </p>
        </section>
      )}

      {editando && sesion && (
        <FormularioDeAnuncio
          anuncio={editando === 'nuevo' ? null : editando}
          sesion={sesion}
          nombre={ficha?.nombre ?? 'Tu salón'}
          onCerrar={() => setEditando(null)}
          onGuardado={() => {
            setEditando(null)
            void cargar(sesion)
          }}
        />
      )}
    </div>
  )
}

/**
 * El trozo de la ficha pública donde sale el cartel, **con la misma forma que allí**.
 *
 * Si esta previsualización se dibujara «parecida», dejaría de servir el día que la ficha cambie:
 * es la misma marca y las mismas clases que `app/[slug]/page.tsx`.
 */
function VistaPrevia({ texto, nombre }: { texto: string | null; nombre: string }) {
  return (
    <div className="panel" style={{ marginTop: 'var(--espacio-3)' }}>
      <p className="etiqueta">{nombre}</p>
      {texto ? (
        <p className="aviso aviso--exito" style={{ marginTop: 'var(--espacio-2)' }}>
          {texto}
        </p>
      ) : (
        <p className="tenue" style={{ marginTop: 'var(--espacio-2)' }}>
          Sin ningún anuncio encendido, en tu ficha no aparece este recuadro. No queda un hueco
          vacío: sencillamente no está.
        </p>
      )}
    </div>
  )
}

function soloFecha(instante: string): string {
  return new Intl.DateTimeFormat('es-PA', { day: 'numeric', month: 'long' }).format(
    new Date(instante),
  )
}

/** `AAAA-MM-DD` para un `input[type=date]`, en la hora del navegador. */
function paraCampoDeFecha(instante: string | null | undefined): string {
  if (!instante) return ''
  const fecha = new Date(instante)
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  const dia = String(fecha.getDate()).padStart(2, '0')
  return `${fecha.getFullYear()}-${mes}-${dia}`
}

function FormularioDeAnuncio({
  anuncio,
  sesion,
  nombre,
  onCerrar,
  onGuardado,
}: {
  anuncio: AnuncioDelSalon | null
  sesion: Sesion
  nombre: string
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [texto, setTexto] = useState(anuncio?.texto ?? '')
  const [hasta, setHasta] = useState(paraCampoDeFecha(anuncio?.hasta))
  const [activo, setActivo] = useState(anuncio?.activo ?? true)
  const [guardando, setGuardando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault()
    setGuardando(true)
    setFallo(null)
    // La fecha se manda como el final del día elegido: quien pone «hasta el 30» quiere que el
    // cartel siga puesto el día 30, no que se apague a las doce de la noche del 29.
    const finDelDia = hasta ? new Date(`${hasta}T23:59:59`).toISOString() : null
    try {
      if (anuncio) {
        await conSesion(`/api/v1/negocio/anuncios/${anuncio.id}`, {
          metodo: 'PATCH',
          token: sesion.acceso,
          cuerpo: {
            texto: texto.trim(),
            hasta: finDelDia,
            quitar_fin: hasta === '',
            activo,
          },
        })
      } else {
        await conSesion('/api/v1/negocio/anuncios', {
          metodo: 'POST',
          token: sesion.acceso,
          cuerpo: { texto: texto.trim(), hasta: finDelDia, activo },
        })
      }
      onGuardado()
    } catch (error) {
      setFallo(error instanceof Error ? error.message : 'No se pudo guardar el anuncio.')
      setGuardando(false)
    }
  }

  const quedan = LARGO_MAXIMO - texto.length

  return (
    <Hoja titulo={anuncio ? 'Cambiar el anuncio' : 'Escribir un anuncio'} onCerrar={onCerrar}>
      <form onSubmit={guardar} className="formulario">
        <label className="campo">
          <span>Qué quieres decir</span>
          <textarea
            className="entrada"
            rows={3}
            maxLength={LARGO_MAXIMO}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Martes de fade: 20 % en cortes de caballero hasta fin de mes."
            required
            autoFocus
          />
          <span className={quedan < 20 ? 'campo-error' : 'campo-ayuda'}>
            {quedan} {quedan === 1 ? 'carácter' : 'caracteres'} de {LARGO_MAXIMO}
          </span>
        </label>

        <label className="campo">
          <span>Hasta cuándo (opcional)</span>
          <input
            type="date"
            className="entrada cifras"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
          />
          <span className="campo-ayuda">
            Sin fecha se queda puesto hasta que lo apagues. Con fecha se apaga solo, que es lo que
            hace que no se quede en la ficha una promoción de hace tres meses.
          </span>
        </label>

        <label className="interruptor">
          <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
          <span>Encendido</span>
        </label>

        {/* Se ve **mientras se escribe**, no después de guardar. */}
        <div className="bloque-panel">
          <h3 className="etiqueta">Así va a quedar</h3>
          <VistaPrevia texto={texto.trim() || null} nombre={nombre} />
        </div>

        {fallo && (
          <p role="alert" className="aviso aviso--error">
            {fallo}
          </p>
        )}

        <div className="hoja__pie">
          <button type="button" className="boton boton--llano" onClick={onCerrar}>
            Cancelar
          </button>
          <button type="submit" className="boton boton--cierra" disabled={guardando}>
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </form>
    </Hoja>
  )
}
