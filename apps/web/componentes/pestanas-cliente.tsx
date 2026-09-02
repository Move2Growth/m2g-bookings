'use client'

import { useEffect, useState } from 'react'
import { Iconos, Pestanas } from '@/componentes/pestanas'
import { leerSesion } from '@/lib/sesion'

/**
 * Las cuatro pestañas del área de la clienta.
 *
 * Viven en su propio archivo porque las usan dos sitios con naturalezas distintas: el armazón
 * de `/mi/*`, que es una aplicación con sesión, y `/buscar`, que se sirve desde el servidor y
 * tiene que seguir siendo indexable. Duplicar la lista sería tener dos barras que un día dejan
 * de coincidir.
 */
export const PESTANAS_CLIENTE = [
  { href: '/buscar', texto: 'Buscar', icono: Iconos.buscar },
  { href: '/mi/citas', texto: 'Citas', icono: Iconos.citas },
  { href: '/mi/favoritos', texto: 'Guardados', icono: Iconos.corazon },
  { href: '/mi/perfil', texto: 'Perfil', icono: Iconos.persona },
]

/**
 * La barra de pestañas en una página pública.
 *
 * Solo aparece si hay sesión, y por eso se decide en el navegador: la página se sigue sirviendo
 * desde el servidor igual para todo el mundo —que es lo que la hace indexable— y la barra se
 * añade después. Al revés, `/buscar` dejaría de poder cachearse.
 */
export function PestanasClienteSiHaySesion() {
  const [hay, setHay] = useState(false)
  useEffect(() => setHay(Boolean(leerSesion())), [])
  if (!hay) return null
  return (
    <>
      <Pestanas pestanas={PESTANAS_CLIENTE} etiqueta="Tu cuenta" />
      {/* El hueco que deja la barra fija. Sin él, el último salón de la lista queda debajo. */}
      <div className="hueco-pestanas" aria-hidden="true" />
    </>
  )
}
