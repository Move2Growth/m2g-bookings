'use client'

import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState, type ReactNode } from 'react'
import { Armazon } from '@/componentes/armazon'
import { Iconos } from '@/componentes/pestanas'
import { leerSesion, type Sesion } from '@/lib/sesion'

/**
 * El panel del salón.
 *
 * Seis pestañas y ninguna más. El orden no es alfabético ni el del menú de un ERP: es el de la
 * frecuencia con que se abre cada una. La agenda se mira cuarenta veces al día; la ficha
 * pública, una vez al mes.
 *
 * Quién puede hacer qué lo decide el servidor, no esta pantalla: un profesional que llame a la
 * API de clientas recibe un 403 venga de donde venga. Lo de aquí es **cortesía, no seguridad**,
 * y aun así importa: sin ella, un profesional que escribiera `/panel/ficha` en la barra se
 * encontraba el editor del salón entero, con el nombre y las fotos en campos rellenables, y solo
 * descubría que no era suyo al pulsar «Guardar» y comerse un error. Enseñar una puerta que no
 * abre es peor que no enseñarla.
 */

const PESTANAS_DUENO = [
  { href: '/panel/agenda', texto: 'Agenda', icono: Iconos.agenda },
  { href: '/panel/servicios', texto: 'Servicios', icono: Iconos.servicios },
  { href: '/panel/equipo', texto: 'Equipo', icono: Iconos.equipo },
  { href: '/panel/horario', texto: 'Horario', icono: Iconos.horario },
  { href: '/panel/clientes', texto: 'Clientas', icono: Iconos.clientes },
  { href: '/panel/resenas', texto: 'Reseñas', icono: Iconos.moderacion },
  { href: '/panel/ficha', texto: 'Ficha', icono: Iconos.ficha },
]

/** Un profesional ve su día y poco más: ni la caja, ni el equipo, ni la configuración. */
const PESTANAS_PROFESIONAL = [
  { href: '/panel/agenda', texto: 'Mi agenda', icono: Iconos.agenda },
  { href: '/panel/horario', texto: 'Mi horario', icono: Iconos.horario },
]

export default function DisposicionPanel({ children }: { children: ReactNode }) {
  const router = useRouter()
  const ruta = usePathname()
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [estado, setEstado] = useState<'comprobando' | 'dentro'>('comprobando')

  useEffect(() => {
    const guardada = leerSesion()
    if (!guardada) {
      router.replace('/entrar')
      return
    }
    if (!guardada.negocio_activo) {
      // No es un error: es una cuenta de clienta mirando la puerta del personal. Se la manda a
      // lo suyo en vez de enseñarle un mensaje de permisos que no le dice nada.
      router.replace('/mi/citas')
      return
    }
    // Un profesional que llegue por la URL a una pantalla del dueño va a su agenda. No se le
    // enseña un aviso de permisos: no ha hecho nada raro, sencillamente esa pantalla no es suya.
    if (
      guardada.negocio_rol === 'profesional' &&
      !PESTANAS_PROFESIONAL.some((p) => ruta === p.href || ruta.startsWith(`${p.href}/`))
    ) {
      router.replace('/panel/agenda')
      return
    }
    setSesion(guardada)
    setEstado('dentro')
  }, [router, ruta])

  if (estado === 'comprobando') return <div className="app" aria-hidden="true" />

  const esDueno = sesion?.negocio_rol !== 'profesional'

  return (
    <Armazon
      pestanas={esDueno ? PESTANAS_DUENO : PESTANAS_PROFESIONAL}
      etiquetaPestanas="Tu salón"
      contexto={sesion?.negocio_nombre}
    >
      {children}
    </Armazon>
  )
}
