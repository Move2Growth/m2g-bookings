'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Hoja } from '@/componentes/hoja'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * Las reseñas del salón.
 *
 * Lo primero son **las que faltan por responder**, porque responder es lo único accionable de
 * esta pantalla. Y el filtro arranca en «todas» y no en «sin responder»: quien entra por
 * primera vez tiene que ver lo que hay, no una lista vacía que parece un error.
 *
 * Solo se puede responder una vez y en público (REV-3). Se dice antes de escribir, no después
 * de mandarla.
 */

type Resena = {
  id: string
  nota: number
  texto: string | null
  fecha: string
  autor: string
  profesional: string | null
  fotos: { id: string; url: string }[]
  respuesta: { texto: string; fecha: string } | null
  reportes_abiertos: number
  estado: string
}

export default function ResenasDelSalon() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [resenas, setResenas] = useState<Resena[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [soloSinResponder, setSoloSinResponder] = useState(false)
  const [respondiendo, setRespondiendo] = useState<Resena | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion, filtrar: boolean) => {
    setError(null)
    try {
      setResenas(
        await conSesion<Resena[]>(
          `/api/v1/negocio/reviews${filtrar ? '?sin_responder=true' : ''}`,
          { token: actual.acceso },
        ),
      )
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar tus reseñas.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion, soloSinResponder)
  }, [sesion, soloSinResponder, cargar])

  const fecha = new Intl.DateTimeFormat('es-PA', { day: 'numeric', month: 'long', year: 'numeric' })

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Reseñas</h1>
        <div className="tira">
          <button
            type="button"
            className="ficha ficha--modo"
            aria-pressed={!soloSinResponder}
            onClick={() => setSoloSinResponder(false)}
          >
            Todas
          </button>
          <button
            type="button"
            className="ficha ficha--modo"
            aria-pressed={soloSinResponder}
            onClick={() => setSoloSinResponder(true)}
          >
            Sin responder
          </button>
        </div>
      </div>

      {error && (
        <BloqueDeError
          mensaje={error}
          reintentar={sesion ? () => void cargar(sesion, soloSinResponder) : undefined}
        />
      )}

      {resenas === null && !error && <Esqueleto filas={3} alto={130} etiqueta="Cargando tus reseñas" />}

      {resenas !== null && resenas.length === 0 && (
        <Vacio
          icono={Iconos.moderacion}
          titulo={soloSinResponder ? 'Las tienes todas respondidas' : 'Todavía no tienes reseñas'}
          texto={
            soloSinResponder
              ? 'Cuando llegue una nueva aparecerá aquí.'
              : 'Solo puede dejar una quien haya venido: se le pide después de la cita, y no antes.'
          }
        />
      )}

      {resenas && resenas.length > 0 && (
        <ul className="resenas escalona">
          {resenas.map((r) => (
            <li key={r.id} className="resena">
              <p className="resena__cabeza">
                <span className="cifras" aria-label={`${r.nota} de 5`}>
                  {'★'.repeat(r.nota)}
                  <span className="tenue">{'★'.repeat(5 - r.nota)}</span>
                </span>
                <span className="resena__autor">{r.autor}</span>
                <span className="tenue cifras">{fecha.format(new Date(r.fecha))}</span>
                {r.estado !== 'publicada' && <span className="fila__alerta">{r.estado}</span>}
              </p>

              {r.texto && <p className="resena__texto medida">{r.texto}</p>}

              {r.respuesta ? (
                <p className="resena__respuesta medida">
                  <strong>Respondiste:</strong> {r.respuesta.texto}
                </p>
              ) : (
                <p style={{ marginTop: 'var(--espacio-3)' }}>
                  <button
                    type="button"
                    className="boton boton--primario"
                    onClick={() => setRespondiendo(r)}
                  >
                    Responder
                  </button>
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      {respondiendo && sesion && (
        <FormularioDeRespuesta
          resena={respondiendo}
          sesion={sesion}
          onCerrar={() => setRespondiendo(null)}
          onGuardado={() => {
            setRespondiendo(null)
            void cargar(sesion, soloSinResponder)
          }}
        />
      )}
    </div>
  )
}

function FormularioDeRespuesta({
  resena,
  sesion,
  onCerrar,
  onGuardado,
}: {
  resena: Resena
  sesion: Sesion
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  return (
    <Hoja titulo={`Responder a ${resena.autor}`} onCerrar={onCerrar}>
      <p className="resena__respuesta medida" style={{ marginTop: 0 }}>
        {resena.texto ?? `${resena.autor} puso ${resena.nota} de 5 sin escribir nada.`}
      </p>

      <form
        className="formulario"
        style={{ marginTop: 'var(--espacio-4)' }}
        onSubmit={async (evento) => {
          evento.preventDefault()
          setEnviando(true)
          setFallo(null)
          try {
            await conSesion(`/api/v1/negocio/reviews/${resena.id}/responder`, {
              metodo: 'POST',
              token: sesion.acceso,
              cuerpo: { texto: texto.trim() },
            })
            onGuardado()
          } catch (error) {
            setFallo(error instanceof Error ? error.message : 'No se pudo mandar la respuesta.')
            setEnviando(false)
          }
        }}
      >
        <label className="campo">
          <span>Tu respuesta</span>
          <textarea
            className="entrada"
            rows={4}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            maxLength={1500}
            required
            autoFocus
          />
        </label>

        <p className="aviso aviso--info">
          Se publica debajo de la reseña y la ve todo el mundo. Solo se puede responder una vez.
        </p>

        {fallo && (
          <p role="alert" className="aviso aviso--error">
            {fallo}
          </p>
        )}

        <div className="hoja__pie">
          <button type="button" className="boton boton--llano" onClick={onCerrar}>
            Cancelar
          </button>
          <button
            type="submit"
            className="boton boton--cierra"
            disabled={enviando || texto.trim().length === 0}
          >
            {enviando ? 'Publicando…' : 'Publicar respuesta'}
          </button>
        </div>
      </form>
    </Hoja>
  )
}
