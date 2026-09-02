'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Hoja } from '@/componentes/hoja'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * Las citas de una persona, en todos los salones donde ha estado.
 *
 * Es la pantalla de vuelta: la que se abre para comprobar a qué hora era, y la que se usa para
 * cancelar. Por eso lo primero que se lee es **cuándo y dónde**, y el estado va debajo.
 *
 * Quién puede cancelar lo decide el servidor, no esta pantalla: si lo calculara el navegador,
 * un reloj mal puesto daría permiso donde no lo hay.
 */

type Cita = {
  id: string
  negocio: string
  negocio_slug: string
  inicio: string
  fin: string
  estado: string
  zona_horaria: string
  servicios: { nombre: string; duracion_minutos: number; precio_centavos: number | null }[]
  total_centavos: number
  se_puede_cancelar: boolean
  /** Si todavía está dentro de la ventana para opinar. Lo decide el servidor: cada salón pone
   *  la suya y un reloj mal puesto en el teléfono daría permiso donde no lo hay. */
  se_puede_resenar?: boolean
  ya_resenada?: boolean
}

const ETIQUETA: Record<string, string> = {
  pendiente: 'Por confirmar',
  confirmada: 'Confirmada',
  completada: 'Atendida',
  no_show: 'No asististe',
  cancelada_cliente: 'Cancelaste esta cita',
  cancelada_negocio: 'El salón canceló esta cita',
}

export default function MisCitas() {
  const router = useRouter()
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [resenando, setResenando] = useState<Cita | null>(null)
  const [repitiendo, setRepitiendo] = useState<string | null>(null)
  const [citas, setCitas] = useState<Cita[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cancelando, setCancelando] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      setCitas(await conSesion<Cita[]>('/api/v1/mi/reservas', { token: actual.acceso }))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar tus citas.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  async function cancelar(cita: Cita) {
    if (!sesion) return
    setCancelando(cita.id)
    try {
      await conSesion(`/api/v1/mi/reservas/${cita.id}/cancelar`, {
        metodo: 'POST',
        token: sesion.acceso,
      })
      await cargar(sesion)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cancelar.')
    } finally {
      setCancelando(null)
    }
  }

  /**
   * Reservar otra vez lo mismo.
   *
   * Pregunta primero al servidor si el servicio y la profesional siguen existiendo, porque un
   * salón cambia su carta y mandar a alguien a reservar un servicio que ya no está es peor que
   * no ofrecer el atajo.
   */
  async function repetir(cita: Cita) {
    if (!sesion) return
    setRepitiendo(cita.id)
    try {
      const plan = await conSesion<{
        negocio_slug: string
        servicios: { id: string; sigue_disponible: boolean }[]
        se_puede_repetir: boolean
      }>(`/api/v1/mi/reservas/${cita.id}/repetir`, { token: sesion.acceso })
      const servicio = plan.servicios.find((s) => s.sigue_disponible)
      router.push(
        plan.se_puede_repetir && servicio
          ? `/${plan.negocio_slug}?servicio=${servicio.id}`
          : `/${plan.negocio_slug}`,
      )
    } catch {
      // Si el atajo falla, la ficha del salón sigue siendo el sitio correcto al que ir.
      router.push(`/${cita.negocio_slug}`)
    } finally {
      setRepitiendo(null)
    }
  }

  const proximas = (citas ?? []).filter((c) => ['pendiente', 'confirmada'].includes(c.estado))
  const pasadas = (citas ?? []).filter((c) => !['pendiente', 'confirmada'].includes(c.estado))

  return (
    <div className="contenedor seccion">
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Mis citas</h1>

      {error && (
        <div style={{ marginTop: 'var(--espacio-4)' }}>
          <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
        </div>
      )}

      {citas === null && !error && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Esqueleto filas={3} alto={132} etiqueta="Cargando tus citas" />
        </div>
      )}

      {citas !== null && citas.length === 0 && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Vacio
            icono={Iconos.citas}
            titulo="Todavía no tienes citas"
            texto="Cuando reserves en un salón, aparecerá aquí con la hora, la dirección y el botón de cancelar."
            accion={{ href: '/buscar', texto: 'Buscar un salón' }}
          />
        </div>
      )}

      {proximas.length > 0 && (
        <Grupo titulo="Próximas" citas={proximas} onCancelar={cancelar} cancelando={cancelando} />
      )}
      {pasadas.length > 0 && (
        <Grupo
          titulo="Anteriores"
          citas={pasadas}
          onRepetir={repetir}
          repitiendo={repitiendo}
          onResenar={setResenando}
        />
      )}

      {resenando && sesion && (
        <FormularioDeResena
          cita={resenando}
          sesion={sesion}
          onCerrar={() => setResenando(null)}
          onGuardado={() => {
            setResenando(null)
            void cargar(sesion)
          }}
        />
      )}
    </div>
  )
}

/**
 * Dejar una reseña.
 *
 * La nota es obligatoria y el texto no: la mayoría de la gente puntúa y no escribe, y exigir
 * un texto no consigue textos, consigue que no se puntúe.
 *
 * Las estrellas son botones de verdad, no un `div` con `onClick`: así funcionan con teclado y
 * un lector de pantalla anuncia cuál está elegida.
 */
function FormularioDeResena({
  cita,
  sesion,
  onCerrar,
  onGuardado,
}: {
  cita: Cita
  sesion: Sesion
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [nota, setNota] = useState(0)
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  return (
    <Hoja titulo={`¿Qué tal en ${cita.negocio}?`} onCerrar={onCerrar}>
      <form
        className="formulario"
        onSubmit={async (evento) => {
          evento.preventDefault()
          setEnviando(true)
          setFallo(null)
          try {
            await conSesion(`/api/v1/mi/reservas/${cita.id}/review`, {
              metodo: 'POST',
              token: sesion.acceso,
              cuerpo: { rating: nota, texto: texto.trim() || null },
            })
            onGuardado()
          } catch (error) {
            setFallo(error instanceof Error ? error.message : 'No se pudo mandar tu reseña.')
            setEnviando(false)
          }
        }}
      >
        <fieldset className="grupo">
          <legend className="campo-etiqueta">Tu nota</legend>
          <div className="estrellas">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                className="estrella"
                aria-pressed={nota === n}
                aria-label={`${n} de 5`}
                onClick={() => setNota(n)}
              >
                <span aria-hidden="true">{n <= nota ? '★' : '☆'}</span>
              </button>
            ))}
          </div>
        </fieldset>

        <label className="campo">
          <span>Cuéntalo si quieres (opcional)</span>
          <textarea
            className="entrada"
            rows={4}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Lo que le dirías a una amiga que te pregunta por este sitio."
            maxLength={2000}
          />
        </label>

        <p className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
          Sale con tu nombre de pila y la inicial del apellido. El salón puede responderte una
          vez, en público.
        </p>

        {fallo && (
          <p role="alert" className="aviso aviso--error">
            {fallo}
          </p>
        )}

        <div className="hoja__pie">
          <button type="button" className="boton boton--llano" onClick={onCerrar}>
            Ahora no
          </button>
          <button type="submit" className="boton boton--cierra" disabled={nota === 0 || enviando}>
            {enviando ? 'Mandando…' : 'Mandar reseña'}
          </button>
        </div>
      </form>
    </Hoja>
  )
}

function Grupo({
  titulo,
  citas,
  onCancelar,
  cancelando,
  onRepetir,
  repitiendo,
  onResenar,
}: {
  titulo: string
  citas: Cita[]
  onCancelar?: (cita: Cita) => void
  cancelando?: string | null
  onRepetir?: (cita: Cita) => void
  repitiendo?: string | null
  onResenar?: (cita: Cita) => void
}) {
  return (
    <section style={{ marginTop: 'var(--espacio-6)' }}>
      <h2 className="etiqueta">{titulo}</h2>
      <ul className="citas escalona">
        {citas.map((cita) => {
          const cuando = new Intl.DateTimeFormat('es-PA', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
            timeZone: cita.zona_horaria,
          }).format(new Date(cita.inicio))

          return (
            <li key={cita.id} className="cita">
              <p className="cita__cuando cifras primera-mayuscula">{cuando}</p>
              <p className="cita__donde">
                <Link href={`/${cita.negocio_slug}`}>{cita.negocio}</Link>
              </p>
              <p className="cita__que">
                {cita.servicios.map((s) => s.nombre).join(' + ')}
                {cita.total_centavos > 0 && (
                  <span className="cifras"> · ${(cita.total_centavos / 100).toFixed(2)}</span>
                )}
              </p>

              <p className="cita__estado">
                <span className={`estado estado--${cita.estado}`}>
                  {ETIQUETA[cita.estado] ?? cita.estado}
                </span>
              </p>

              {onCancelar && cita.se_puede_cancelar && (
                <p className="cita__acciones">
                  <button
                    onClick={() => onCancelar(cita)}
                    disabled={cancelando === cita.id}
                    className="boton boton--peligro"
                  >
                    {cancelando === cita.id ? 'Cancelando…' : 'Cancelar'}
                  </button>
                </p>
              )}
              {onRepetir && (
                <p className="cita__acciones">
                  <button
                    type="button"
                    className="boton boton--secundario"
                    disabled={repitiendo === cita.id}
                    onClick={() => onRepetir(cita)}
                  >
                    {repitiendo === cita.id ? 'Un momento…' : 'Reservar otra vez'}
                  </button>
                  {onResenar && cita.estado === 'completada' && !cita.ya_resenada && (
                    <button
                      type="button"
                      className="boton boton--primario"
                      onClick={() => onResenar(cita)}
                    >
                      Dejar reseña
                    </button>
                  )}
                </p>
              )}

              {onCancelar && !cita.se_puede_cancelar && (
                /* Fuera de la ventana no se esconde el botón sin más: se explica, porque si
                   no, la persona cree que la aplicación está rota. */
                <p className="cita__nota">
                  Ya pasó el plazo para cancelar por tu cuenta. Escríbele al salón y lo arreglan.
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
