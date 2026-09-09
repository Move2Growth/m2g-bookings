'use client';

/**
 * La puerta del salón: **entra** en él y, si hace falta, comprueba que quien entra es el dueño.
 *
 * ## Entrar no es lo mismo que tener sesión
 *
 * La sesión de la plataforma —la que deja `/entrar`— **no sirve** para las llamadas del negocio:
 * hay que pasarla a modo negocio primero. Eso lo hacía únicamente la agenda del día, y la
 * consecuencia era que quien llegaba **directo** a cualquier otra pantalla del salón —un
 * marcador, una recarga, un enlace pegado en el grupo de WhatsApp del equipo— recibía `403` en
 * todo: «El dinero» salía sin un número, «El equipo» decía «esto no cargó», y el día de un
 * profesional —su pantalla más usada, la que abre cada mañana— decía «Cambia a modo negocio
 * para hacer eso».
 *
 * No se veía porque las verificaciones entraban **navegando desde la agenda**, que es donde el
 * modo ya se había puesto: recorrer el producto por dentro tapaba justo el camino por el que
 * entra la gente. Salió al mirar la consola del navegador en pantallas que, por lo demás, se
 * pintaban enteras.
 *
 * **Por eso hay un solo sitio donde se entra en el salón y no ocho.** El primer arreglo lo puso
 * solo en la puerta del dueño; el barrido de pantallas encontró a las dos horas que el
 * profesional seguía roto. Repartir esto por pantalla es garantizar que la siguiente se olvide.
 *
 * ## Y la puerta del dueño, además, comprueba quién eres
 *
 * **La frontera de verdad es la API** —un profesional recibe 403 en las finanzas y en el podio—,
 * pero dos de las piezas del portal se apoyan en endpoints que un profesional sí puede leer: el
 * equipo y los anuncios. Sin esta comprobación, entrar a mano en `/local/equipo` con una cuenta
 * de profesional enseñaba la pantalla del dueño entera, con el interruptor del fichaje de sus
 * compañeros incluido. No es una fuga de datos —el botón lo habría rechazado la API— pero sí es
 * enseñarle a alguien una zona que no es la suya, que era justo lo que el encargo pedía separar.
 */

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { Cargando, Vacio } from '@/componentes/estados';
import { api, comoMensaje } from '@/lib/api';
import { conSesion, guardarSesion, leerSesion } from '@/lib/sesion';

type Estado = 'cargando' | 'dentro' | 'no-es-suya' | 'sin-sesion';

export function EnElSalon({
  children,
  soloDueno = false,
}: {
  children: React.ReactNode;
  /** Con `true`, además de entrar exige que la persona sea dueña de algún salón. */
  soloDueno?: boolean;
}) {
  const [estado, setEstado] = useState<Estado>('cargando');

  useEffect(() => {
    if (!leerSesion()) {
      setEstado('sin-sesion');
      return;
    }
    (async () => {
      try {
        const negocios = await conSesion((acceso) => api.misNegocios(acceso));
        const activo = leerSesion()?.negocioActivo ?? null;
        const vale = (negocio: { rol: string }) => !soloDueno || negocio.rol === 'dueno';
        // Si ya se estaba dentro de uno que vale, se sigue en ese: cambiarlo por debajo movería
        // a alguien de salón sin decírselo.
        const suyo =
          negocios.find((negocio) => negocio.id === activo && vale(negocio)) ??
          negocios.find(vale) ??
          null;
        if (suyo === null) {
          setEstado('no-es-suya');
          return;
        }
        if (activo !== suyo.id) {
          guardarSesion(await conSesion((acceso) => api.modoNegocio(suyo.id, acceso)));
        }
        setEstado('dentro');
      } catch (error) {
        // Un fallo de red no es «esta zona no es tuya». Se dice lo que pasó.
        setEstado(comoMensaje(error) === 'SIN_SESION' ? 'sin-sesion' : 'no-es-suya');
      }
    })();
  }, [soloDueno]);

  if (estado === 'cargando') return <Cargando que="Entrando en el salón" filas={2} />;

  if (estado === 'sin-sesion') {
    return (
      <Vacio
        titulo="Esta zona es del salón"
        explicacion="Entra con la cuenta que trabaja en el local para verla."
        accion={
          <Link className="boton boton--abre" href="/entrar">
            Entrar
          </Link>
        }
      />
    );
  }

  if (estado === 'no-es-suya') {
    return soloDueno ? (
      <Vacio
        titulo="Esta zona es de quien lleva el salón"
        explicacion="Tu zona es tu día y tu ficha. El dinero, el equipo y la publicidad los lleva el dueño."
        accion={
          <Link className="boton boton--abre" href="/mi-agenda">
            Ir a mi día
          </Link>
        }
      />
    ) : (
      <Vacio
        titulo="No trabajas en ningún salón"
        explicacion="Esta cuenta no está en el equipo de ningún local. Si te han invitado a uno, abre el enlace de la invitación."
        accion={
          <Link className="boton boton--abre" href="/mis-citas">
            Ver mis citas
          </Link>
        }
      />
    );
  }

  return <>{children}</>;
}

/** La puerta del portal del dueño. Es la misma, con la comprobación de rol encendida. */
export function SoloDueno({ children }: { children: React.ReactNode }) {
  return <EnElSalon soloDueno>{children}</EnElSalon>;
}
