'use client'

import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState, type ReactNode } from 'react'
import { Armazon } from '@/componentes/armazon'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

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

/**
 * Un profesional ve su día y **lo suyo**: ni la caja, ni el equipo, ni la configuración del
 * salón. Desde el encargo del 7 de septiembre eso incluye su ficha pública y sus fotos, que
 * son suyas y no del salón (§3).
 *
 * «Fichar» **no está aquí**: se añade abajo, y solo si el dueño se lo ha activado. El fichaje
 * es opcional y por persona (§6), y esta misma pantalla dice tres líneas más arriba que enseñar
 * una puerta que no abre es peor que no enseñarla.
 */
const PESTANAS_PROFESIONAL = [
  { href: '/panel/agenda', texto: 'Mi agenda', icono: Iconos.agenda },
  { href: '/panel/horario', texto: 'Mi horario', icono: Iconos.horario },
  { href: '/panel/mi-perfil', texto: 'Mi ficha', icono: Iconos.persona },
  { href: '/panel/mis-fotos', texto: 'Mis fotos', icono: Iconos.ficha },
]

const PESTANA_FICHAR = { href: '/panel/fichar', texto: 'Fichar', icono: Iconos.horario }

/** Las rutas que un profesional puede abrir, incluida la de fichar cuando la tiene activada. */
const RUTAS_PROFESIONAL = [...PESTANAS_PROFESIONAL, PESTANA_FICHAR]

export default function DisposicionPanel({ children }: { children: ReactNode }) {
  const router = useRouter()
  const ruta = usePathname()
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [estado, setEstado] = useState<'comprobando' | 'dentro'>('comprobando')
  const [fichaje, setFichaje] = useState(false)

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
      !RUTAS_PROFESIONAL.some((p) => ruta === p.href || ruta.startsWith(`${p.href}/`))
    ) {
      router.replace('/panel/agenda')
      return
    }
    setSesion(guardada)
    setEstado('dentro')
  }, [router, ruta])

  /**
   * ¿Le han activado el fichaje?
   *
   * Se pregunta **sin bloquear** el resto del panel a propósito: la agenda es la pantalla que
   * más se abre del producto y no puede esperar a una consulta que solo decide una pestaña. El
   * precio es que la pestaña aparece un instante después de cargar; el precio de la otra
   * opción sería que la agenda tarde más cada vez que se abre.
   */
  useEffect(() => {
    if (!sesion || sesion.negocio_rol !== 'profesional') return
    let vigente = true
    conSesion<{ profesional_id: string; fichaje_activo: boolean }[]>('/api/v1/negocio/fichajes', {
      token: sesion.acceso,
    })
      // A un profesional la base solo le devuelve su parte, así que cualquiera de la lista es
      // el suyo. Si falla, la pestaña no sale: es lo mismo que no tenerlo activado.
      .then((partes) => vigente && setFichaje(partes.some((p) => p.fichaje_activo)))
      .catch(() => vigente && setFichaje(false))
    return () => {
      vigente = false
    }
  }, [sesion])

  if (estado === 'comprobando') return <div className="app" aria-hidden="true" />

  const esDueno = sesion?.negocio_rol !== 'profesional'
  const suyas = fichaje ? [...PESTANAS_PROFESIONAL, PESTANA_FICHAR] : PESTANAS_PROFESIONAL

  return (
    <Armazon
      pestanas={esDueno ? PESTANAS_DUENO : suyas}
      etiquetaPestanas="Tu salón"
      contexto={sesion?.negocio_nombre}
    >
      {children}
    </Armazon>
  )
}
