'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState, type ReactNode } from 'react'
import { Iconos, Pestanas } from '@/componentes/pestanas'
import { borrarSesionDeConsola, leerSesionDeConsola, type SesionDeConsola } from '@/lib/consola'

/**
 * La consola interna de M2G (superficie W2 del brief).
 *
 * No comparte armazón con el panel del salón aunque se parezcan, y es a propósito: comparten
 * aspecto pero **no comparten sesión**, y un armazón común invita a que un día alguien lea la
 * sesión equivocada. Aquí la barra dice siempre «M2G» y el nombre de quien ha entrado, para que
 * nadie confunda esta pantalla con el panel de un salón mientras suspende un negocio.
 */

const PESTANAS = [
  { href: '/consola/negocios', texto: 'Negocios', icono: Iconos.negocios },
  { href: '/consola/moderacion', texto: 'Moderación', icono: Iconos.moderacion },
  { href: '/consola/metricas', texto: 'Métricas', icono: Iconos.metricas },
  { href: '/consola/ranking', texto: 'Ranking', icono: Iconos.ajustes },
]

export default function DisposicionConsola({ children }: { children: ReactNode }) {
  const router = useRouter()
  const ruta = usePathname()
  const [sesion, setSesion] = useState<SesionDeConsola | null>(null)
  const [estado, setEstado] = useState<'comprobando' | 'dentro' | 'fuera'>('comprobando')

  useEffect(() => {
    // La pantalla de acceso es la única que se ve sin sesión: si no, no habría por dónde entrar.
    if (ruta === '/consola') {
      setEstado('fuera')
      return
    }
    const guardada = leerSesionDeConsola()
    if (!guardada) {
      router.replace('/consola')
      return
    }
    setSesion(guardada)
    setEstado('dentro')
  }, [router, ruta])

  if (estado === 'comprobando') return <div className="app" aria-hidden="true" />
  if (estado === 'fuera') return <>{children}</>

  return (
    <div className="app app--consola">
      <header className="app__barra">
        <Link href="/consola/negocios" className="marca-consola">
          M2G
        </Link>
        <span className="app__contexto">
          Consola interna · {sesion?.nombre} ({sesion?.rol})
        </span>
        <button
          type="button"
          className="boton boton--llano"
          onClick={() => {
            borrarSesionDeConsola()
            router.push('/consola')
          }}
        >
          Salir
        </button>
      </header>

      <Pestanas pestanas={PESTANAS} etiqueta="Consola de M2G" />

      <main className="app__cuerpo">{children}</main>
    </div>
  )
}
