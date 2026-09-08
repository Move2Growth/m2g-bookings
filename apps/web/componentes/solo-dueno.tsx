'use client';

/**
 * La puerta del portal del dueño.
 *
 * **La frontera de verdad es la API** —un profesional recibe 403 en las finanzas y en el podio—,
 * pero dos de las seis piezas se apoyan en endpoints que un profesional sí puede leer: el equipo
 * y los anuncios. Sin esta puerta, entrar a mano en `/local/equipo` con una cuenta de
 * profesional enseñaba la pantalla del dueño entera, con el interruptor del fichaje de sus
 * compañeros incluido. No es una fuga de datos —el botón lo habría rechazado la API— pero sí es
 * enseñarle a alguien una zona que no es la suya, que era justo lo que el encargo pedía separar.
 */

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { Cargando, Vacio } from '@/componentes/estados';
import { api, comoMensaje } from '@/lib/api';
import { conSesion, leerSesion } from '@/lib/sesion';

export function SoloDueno({ children }: { children: React.ReactNode }) {
  const [rol, setRol] = useState<'cargando' | 'dueno' | 'otro' | 'sin-sesion'>('cargando');

  useEffect(() => {
    if (!leerSesion()) {
      setRol('sin-sesion');
      return;
    }
    conSesion((acceso) => api.misNegocios(acceso))
      .then((negocios) => setRol(negocios.some((n) => n.rol === 'dueno') ? 'dueno' : 'otro'))
      .catch(() => setRol('otro'));
  }, []);

  if (rol === 'cargando') return <Cargando que="Comprobando quién eres" filas={2} />;

  if (rol === 'sin-sesion') {
    return (
      <Vacio
        titulo="Esta zona es del salón"
        explicacion="Entra con la cuenta que lleva el local para verla."
        accion={
          <Link className="boton boton--abre" href="/entrar">
            Entrar
          </Link>
        }
      />
    );
  }

  if (rol === 'otro') {
    return (
      <Vacio
        titulo="Esta zona es de quien lleva el salón"
        explicacion="Tu zona es tu día y tu ficha. El dinero, el equipo y la publicidad los lleva el dueño."
        accion={
          <Link className="boton boton--abre" href="/mi-agenda">
            Ir a mi día
          </Link>
        }
      />
    );
  }

  return <>{children}</>;
}
