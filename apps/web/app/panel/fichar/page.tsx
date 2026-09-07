'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * Fichar entrada y salida (encargo 2026-09-07 §6).
 *
 * Dos condiciones del encargo, y las dos mandan sobre esta pantalla: el fichaje es **opcional**
 * y el dueño lo activa **persona a persona**. Así que lo primero que hace la pantalla es
 * preguntar si está activado, y si no lo está **no enseña ningún botón**: dice quién lo activa
 * y se acaba. Un botón que devuelve «no autorizado» al pulsarlo se lee como que el producto
 * está roto, no como que falta un permiso.
 *
 * Un solo botón grande y no dos: **o entras o sales**, nunca las dos cosas, y el servidor
 * rechaza dos entradas seguidas. Enseñar los dos obligaría a acordarse de cuál toca; con uno,
 * el estado de la jornada está escrito en el propio botón.
 *
 * El parte es **append-only** en la base: no se puede corregir una marca desde aquí porque no
 * se puede corregir en ningún sitio. Un registro horario que se reescribe no prueba nada, ni a
 * favor del salón ni de quien trabaja allí.
 */

type Marca = {
  id: string
  profesional_id: string
  clase: string
  instante: string
  origen: string
  nota: string | null
}

type Parte = {
  profesional_id: string
  nombre: string
  fichaje_activo: boolean
  minutos_trabajados: number
  jornada_abierta: boolean
  marcas: Marca[]
}

const HORA = new Intl.DateTimeFormat('es-PA', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: 'America/Panama',
})

const DIA = new Intl.DateTimeFormat('es-PA', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'America/Panama',
})

/** «7 h 20», no «440 minutos», que nadie dice al mirar sus horas de la semana. */
function horas(minutos: number): string {
  if (minutos < 60) return `${minutos} min`
  const h = Math.floor(minutos / 60)
  const resto = minutos % 60
  return resto === 0 ? `${h} h` : `${h} h ${resto}`
}

export default function Fichar() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [parte, setParte] = useState<Parte | null>(null)
  /**
   * `false` = esta cuenta no atiende en este salón (no tiene ficha de equipo). `null` = todavía
   * no se sabe. **No es lo mismo que no tener parte**: el parte falta también cuando la ficha
   * existe y el fichaje está apagado, y son dos mensajes distintos.
   */
  const [atiendeAqui, setAtiendeAqui] = useState<boolean | null>(null)
  /** Mi ficha de equipo en este salón. Va en el fichaje porque un dueño que además atiende
   *  **tiene que decir de quién es la marca**; a un profesional se le acepta la suya igual. */
  const [miFicha, setMiFicha] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fallo, setFallo] = useState<string | null>(null)
  const [fichando, setFichando] = useState(false)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      // **Quién soy yo dentro de este salón.** No vale coger el primer parte de la lista: a un
      // profesional la base solo le devuelve el suyo, pero a un dueño que además atiende le
      // devuelve el del equipo entero, y el primero sería el de otra persona. Sin ficha de
      // profesional esto responde 403, que es exactamente el caso de «aquí no atiendes».
      const yo = await conSesion<{ id: string }>('/api/v1/mi/perfil-profesional', {
        token: actual.acceso,
      }).catch(() => null)

      if (!yo) {
        setAtiendeAqui(false)
        setParte(null)
        return
      }
      setMiFicha(yo.id)
      setAtiendeAqui(true)

      // **Un parte vacío significa que el fichaje está apagado**, no que falte gente: la API
      // solo devuelve a quien lo tiene encendido, aunque no haya fichado nada. Confundir las
      // dos cosas hace que a quien sí atiende se le diga que no trabaja aquí.
      const partes = await conSesion<Parte[]>('/api/v1/negocio/fichajes', { token: actual.acceso })
      setParte(partes.find((p) => p.profesional_id === yo.id) ?? null)
    } catch (problema) {
      setError(problema instanceof Error ? problema.message : 'No se pudo cargar tu parte.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  async function fichar(clase: 'entrada' | 'salida') {
    if (!sesion) return
    setFichando(true)
    setFallo(null)
    try {
      await conSesion('/api/v1/negocio/fichajes', {
        metodo: 'POST',
        token: sesion.acceso,
        cuerpo: { clase, profesional_id: miFicha },
      })
      await cargar(sesion)
    } catch (problema) {
      setFallo(problema instanceof Error ? problema.message : 'No se pudo fichar.')
    } finally {
      setFichando(false)
    }
  }

  const abierta = parte?.jornada_abierta ?? false
  const ultima = parte?.marcas.at(-1) ?? null

  // Las marcas vienen del rango entero (siete días por defecto). Se agrupan por día porque un
  // parte plano de treinta marcas seguidas no se lee: nadie sabe dónde acabó el martes.
  const porDia = new Map<string, Marca[]>()
  for (const marca of parte?.marcas ?? []) {
    const clave = DIA.format(new Date(marca.instante))
    porDia.set(clave, [...(porDia.get(clave) ?? []), marca])
  }
  const dias = [...porDia.entries()].reverse()

  return (
    <div className="contenedor seccion" style={{ maxWidth: '34rem' }}>
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Fichar</h1>

      {error && (
        <div style={{ marginTop: 'var(--espacio-4)' }}>
          <BloqueDeError
            mensaje={error}
            reintentar={sesion ? () => void cargar(sesion) : undefined}
          />
        </div>
      )}

      {atiendeAqui === null && !error && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Esqueleto filas={2} alto={96} etiqueta="Mirando si tienes el fichaje activado" />
        </div>
      )}

      {/* Sin ficha de profesional en este salón —el caso de un dueño que no atiende— no hay
          nada que fichar, y decirlo es más útil que una lista vacía. */}
      {atiendeAqui === false && (
        <p className="aviso aviso--info" style={{ marginTop: 'var(--espacio-5)' }}>
          Esta pantalla es para quien atiende en el salón. Tu cuenta no tiene ficha de
          profesional aquí, así que no hay jornada que fichar.
        </p>
      )}

      {/* Atiende aquí, pero el interruptor está apagado. Ni un botón: solo de quién depende. */}
      {atiendeAqui === true && (!parte || !parte.fichaje_activo) && (
        <p className="aviso aviso--info" style={{ marginTop: 'var(--espacio-5)' }}>
          <strong>El fichaje no está activado para ti.</strong> Lo activa quien administra el
          salón, persona a persona, desde su panel. Mientras esté apagado no se apunta nada, y
          esta pantalla no aparece en tus pestañas.
        </p>
      )}

      {parte && parte.fichaje_activo && (
        <>
          {/* El estado antes que el botón: primero en qué situación estás, y después qué
              puedes hacer. Al revés se pulsa sin leer. */}
          <div className="panel" style={{ marginTop: 'var(--espacio-5)' }}>
            <p style={{ margin: 0, fontSize: 'var(--tipografia-tamano-mayor)', fontWeight: 'var(--tipografia-pesos-medio)' }}>
              {abierta ? 'Estás dentro' : 'Estás fuera'}
            </p>
            <p className="dato" style={{ margin: 0 }}>
              {ultima
                ? `Tu última marca fue ${ultima.clase === 'entrada' ? 'una entrada' : 'una salida'} a las ${HORA.format(new Date(ultima.instante))}`
                : 'Todavía no has fichado nada esta semana'}
              {ultima?.origen === 'dueno' ? ', y la puso el salón' : ''}
            </p>
          </div>

          {fallo && (
            <p role="alert" className="aviso aviso--error" style={{ marginTop: 'var(--espacio-4)' }}>
              {fallo}
            </p>
          )}

          <button
            type="button"
            disabled={fichando}
            onClick={() => void fichar(abierta ? 'salida' : 'entrada')}
            className={`boton boton--ancho ${abierta ? 'boton--peligro' : 'boton--cierra'}`}
            style={{ marginTop: 'var(--espacio-4)', minHeight: 64 }}
          >
            {fichando ? 'Un momento…' : abierta ? 'Ya salgo' : 'Ya llegué'}
          </button>

          <div className="datos vistazo" style={{ marginTop: 'var(--espacio-6)' }}>
            <div>
              <b className="cifras">{horas(parte.minutos_trabajados)}</b>
              <small>en los últimos siete días</small>
            </div>
          </div>
          {abierta && (
            <p className="tenue" style={{ marginTop: 'var(--espacio-2)', fontSize: 'var(--tipografia-tamano-menor)' }}>
              Sin contar la jornada de ahora, que sigue abierta.
            </p>
          )}

          <section className="bloque-panel">
            <h2>Tu parte</h2>
            {dias.length === 0 ? (
              <p className="apagado" style={{ marginTop: 'var(--espacio-3)' }}>
                Nada apuntado todavía. Toca «Ya llegué» al empezar y «Ya salgo» al acabar.
              </p>
            ) : (
              <ul className="filas" style={{ marginTop: 'var(--espacio-4)' }}>
                {dias.map(([dia, marcas]) => (
                  <li key={dia} className="fila">
                    <div className="fila__boton" style={{ cursor: 'default', minHeight: 56, alignItems: 'center' }}>
                      <span className="fila__nombre primera-mayuscula">{dia}</span>
                      <span className="fila__cifra cifras">
                        {marcas
                          .map(
                            (m) =>
                              `${m.clase === 'entrada' ? '↦' : '↤'} ${HORA.format(new Date(m.instante))}`,
                          )
                          .join('  ')}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <p className="tenue" style={{ marginTop: 'var(--espacio-4)', fontSize: 'var(--tipografia-tamano-menor)' }}>
              Las marcas no se pueden borrar ni corregir, ni por ti ni por el salón. Si hay una
              mal puesta, díselo a quien administra: se anota, no se reescribe.
            </p>
          </section>
        </>
      )}
    </div>
  )
}
