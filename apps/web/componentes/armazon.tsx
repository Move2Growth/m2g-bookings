'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import type { ReactNode } from 'react'
import { Marca } from '@/componentes/marca'
import { Pestanas, type Pestana } from '@/componentes/pestanas'
import { borrarSesion } from '@/lib/sesion'

/**
 * El armazón de las tres zonas con sesión: el panel del salón, el área de la clienta y la
 * consola de M2G.
 *
 * Una sola pieza para las tres porque **la diferencia entre ellas son las pestañas y el
 * contexto, no la estructura**. Tener tres armazones parecidos es tener tres sitios donde
 * arreglar el mismo fallo de la barra fija, y dos de ellos se olvidan.
 *
 * La cabecera es pegajosa y las pestañas también: en una agenda se navega de arriba abajo
 * decenas de veces al día y volver arriba para cambiar de pestaña es un gesto de más cada vez.
 */
export function Armazon({
  pestanas,
  etiquetaPestanas,
  contexto,
  acciones,
  children,
}: {
  pestanas: Pestana[]
  etiquetaPestanas: string
  /** En qué salón o con qué cuenta estás. Un panel que no lo dice es un panel donde se apunta
   *  una cita en la agenda equivocada. */
  contexto?: string | null
  acciones?: ReactNode
  children: ReactNode
}) {
  const router = useRouter()

  return (
    <div className="app">
      <header className="app__barra">
        <Link href="/" aria-label="Bukeo, inicio">
          <Marca alto={20} />
        </Link>
        {contexto && (
          <span className="app__contexto" title={contexto}>
            {contexto}
          </span>
        )}
        {!contexto && <span className="app__contexto" />}
        {acciones}
        <button
          type="button"
          className="boton boton--llano"
          onClick={() => {
            borrarSesion()
            router.push('/entrar')
          }}
        >
          Salir
        </button>
      </header>

      <Pestanas pestanas={pestanas} etiqueta={etiquetaPestanas} />

      <main className="app__cuerpo">{children}</main>
    </div>
  )
}
