'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState, type ReactNode } from 'react'
import { Armazon } from '@/componentes/armazon'
import { PESTANAS_CLIENTE } from '@/componentes/pestanas-cliente'
import { leerSesion } from '@/lib/sesion'

/**
 * El área de la clienta: citas, guardados y perfil.
 *
 * La comprobación de sesión vive aquí y no en cada página. Puesta en cada página acaba
 * escribiéndose tres veces con tres comportamientos distintos, y la tercera se olvida.
 *
 * Mientras se comprueba no se pinta nada: enseñar la pantalla y quitarla medio segundo después
 * es peor que esperar ese medio segundo.
 */
export default function DisposicionCliente({ children }: { children: ReactNode }) {
  const router = useRouter()
  const [estado, setEstado] = useState<'comprobando' | 'dentro'>('comprobando')

  useEffect(() => {
    if (leerSesion()) setEstado('dentro')
    else router.replace('/entrar')
  }, [router])

  if (estado === 'comprobando') return <div className="app" aria-hidden="true" />

  return (
    <Armazon pestanas={PESTANAS_CLIENTE} etiquetaPestanas="Tu cuenta">
      {children}
    </Armazon>
  )
}
