'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'
import {
  diaRelativo,
  dinero,
  type AnuncioDelSalon,
  type Caja,
  type DiaEnColumnas,
} from '@/lib/dueno'

/**
 * La portada del portal del dueño: **hoy, y a dónde ir**.
 *
 * No es un escritorio con gráficas. Son las cuatro cifras del día y las seis puertas, porque lo
 * que hace un dueño al abrir el teléfono a media mañana es una de dos cosas: mirar cómo va el día
 * o ir a una pantalla concreta. Todo lo demás estorba.
 *
 * **Lo facturado son las citas atendidas, no las apuntadas.** Una cita confirmada es una promesa;
 * a las once de la mañana el número es pequeño a propósito y lo dice el rótulo. Y al lado va
 * siempre **cuántas citas no tenían precio**: sin ese número, un total de cero con la agenda
 * llena parece un fallo del producto en vez de lo que es.
 */

type Estado = {
  dia: DiaEnColumnas
  caja: Caja
  anuncios: AnuncioDelSalon[]
}

const SECCIONES = [
  {
    href: '/panel/local/calendarios',
    texto: 'Todos los calendarios',
    detalle: 'El día del salón con una columna por persona',
  },
  {
    href: '/panel/local/finanzas',
    texto: 'Finanzas',
    detalle: 'Lo facturado por día, por semana y por mes',
  },
  {
    href: '/panel/local/mejor-del-mes',
    texto: 'Mejor del mes',
    detalle: 'Quién facturó más y quién hizo más servicios',
  },
  {
    href: '/panel/local/publicidad',
    texto: 'Publicidad flash',
    detalle: 'El anuncio que sale en tu ficha pública',
  },
  {
    href: '/panel/local/fichaje',
    texto: 'Fichaje',
    detalle: 'El interruptor de cada persona y el parte de horas',
  },
  {
    href: '/panel/local/personas',
    texto: 'Personas del local',
    detalle: 'Quién trabaja aquí, con qué papel, y cómo invitar',
  },
]

export default function PortadaDelLocal() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [datos, setDatos] = useState<Estado | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    const desde = diaRelativo(0)
    const hasta = diaRelativo(1)
    try {
      const [dia, caja, anuncios] = await Promise.all([
        conSesion<DiaEnColumnas>('/api/v1/negocio/agenda/columnas', { token: actual.acceso }),
        conSesion<Caja>(
          `/api/v1/negocio/finanzas?desde=${desde.toISOString()}&hasta=${hasta.toISOString()}&agrupacion=dia`,
          { token: actual.acceso },
        ),
        conSesion<AnuncioDelSalon[]>('/api/v1/negocio/anuncios', { token: actual.acceso }),
      ])
      setDatos({ dia, caja, anuncios })
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar tu local.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  const citasDeHoy =
    datos?.dia.columnas.reduce(
      (cuenta, columna) =>
        cuenta +
        columna.citas.filter((c) => !c.estado.startsWith('cancelada')).length,
      0,
    ) ?? 0
  const conAgenda = datos?.dia.columnas.filter((c) => c.citas.length > 0).length ?? 0
  const vigente = datos?.anuncios.find((a) => a.vigente) ?? null

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Tu local hoy</h1>
        <Link href="/panel/local/calendarios" className="boton boton--primario">
          Ver los calendarios
        </Link>
      </div>

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      )}

      {/* El esqueleto tiene la forma de las cuatro cifras que van a llegar, no una ruedecita:
          así la pantalla no da un salto cuando entran los datos. */}
      {!datos && !error && <Esqueleto filas={4} alto={84} etiqueta="Cargando el día" />}

      {datos && (
        <>
          <div className="cifras-clave">
            <Cifra
              titulo="Cobrado hoy · citas ya atendidas"
              valor={dinero(datos.caja.importe_centavos, datos.caja.moneda)}
            />
            <Cifra titulo="Citas hoy" valor={String(citasDeHoy)} />
            <Cifra
              titulo={`Con agenda hoy · de ${datos.dia.columnas.length}`}
              valor={String(conAgenda)}
            />
            <Cifra
              titulo="Citas hoy sin precio · no suman"
              valor={String(datos.caja.citas_sin_precio)}
            />
          </div>

          {datos.caja.citas_sin_precio > 0 && (
            <p className="aviso aviso--info" style={{ marginTop: 'var(--espacio-4)' }}>
              Hoy hay {datos.caja.citas_sin_precio}{' '}
              {datos.caja.citas_sin_precio === 1 ? 'cita' : 'citas'} con algún servicio «a
              consultar». No tienen precio, así que no suman al total: lo cobrado de verdad es más
              que lo que se ve arriba.
            </p>
          )}

          <section className="bloque-panel">
            <div className="cabeza-seccion" style={{ marginBlock: 0 }}>
              <h2 className="etiqueta">Publicidad flash</h2>
              <Link href="/panel/local/publicidad" className="boton boton--llano">
                {vigente ? 'Cambiarlo' : 'Escribir uno'}
              </Link>
            </div>
            {vigente ? (
              <p className="aviso aviso--exito" style={{ marginTop: 'var(--espacio-3)' }}>
                Ahora mismo tu ficha enseña: «{vigente.texto}»
              </p>
            ) : (
              <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
                No tienes ningún anuncio encendido. Es el cartel que ve quien abre tu ficha.
              </p>
            )}
          </section>

          <section className="bloque-panel">
            <h2 className="etiqueta">Lo que solo puedes hacer tú</h2>
            <ul className="filas escalona" style={{ marginTop: 'var(--espacio-3)' }}>
              {SECCIONES.map((s) => (
                <li key={s.href} className="fila">
                  <Link href={s.href} className="fila__boton">
                    <span className="fila__principal">
                      <span className="fila__nombre">{s.texto}</span>
                      <span className="fila__detalle">{s.detalle}</span>
                    </span>
                    <span className="fila__cifra" aria-hidden="true">
                      →
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <section className="bloque-panel">
            <h2 className="etiqueta">¿Vas a abrir otro local?</h2>
            <p className="tenue" style={{ marginTop: 'var(--espacio-2)' }}>
              Se da de alta en tres pasos: crearlo, decir quién trabaja allí y cargar los
              servicios. Este salón se queda como está.
            </p>
            <p style={{ marginTop: 'var(--espacio-3)' }}>
              <Link href="/panel/alta" className="boton boton--secundario">
                Dar de alta otro local
              </Link>
            </p>
          </section>
        </>
      )}
    </div>
  )
}

function Cifra({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div className="cifra-clave">
      <span className="cifra-clave__valor cifra-grande cifras">{valor}</span>
      <span className="cifra-clave__titulo">{titulo}</span>
    </div>
  )
}
