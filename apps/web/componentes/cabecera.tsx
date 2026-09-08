'use client';

/**
 * La cabecera. Va en TODAS las pantallas, sin excepción, y es la misma en la calle y en el
 * local: cambia lo que ofrece, no la forma.
 *
 * El filo macizo de 6 px debajo del enlace dice «estás aquí». Es el mismo grosor que separa
 * los bloques en el resto de la aplicación: una sola medida para «esto está elegido».
 */

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { NOMBRE_COMERCIAL } from '@/lib/marca';
import { alCambiarLaSesion, borrarSesion, leerSesion } from '@/lib/sesion';
import { Sello } from './sello';

export function Cabecera() {
  const camino = usePathname();
  const router = useRouter();
  const [conSesion, setConSesion] = useState(false);
  const [montado, setMontado] = useState(false);

  useEffect(() => {
    const mirar = () => setConSesion(leerSesion() !== null);
    mirar();
    setMontado(true);
    return alCambiarLaSesion(mirar);
  }, []);

  const enlaces: { href: string; rotulo: string }[] = [
    { href: '/buscar', rotulo: 'Buscar' },
    { href: '/mis-citas', rotulo: 'Mis citas' },
    { href: '/mis-salones', rotulo: 'Mis salones' },
    { href: '/local', rotulo: 'Mi salón' },
  ];

  return (
    <header className="cabecera">
      <div className="contenido cabecera__caja">
        <Link href="/" className="cabecera__marca">
          <Sello medida={30} />
          <span className="cabecera__nombre">{NOMBRE_COMERCIAL}</span>
        </Link>

        <nav className="cabecera__enlaces" aria-label="Principal">
          {enlaces.map((enlace) => (
            <Link
              key={enlace.href}
              href={enlace.href}
              className="cabecera__enlace"
              aria-current={camino === enlace.href ? 'page' : undefined}
            >
              {enlace.rotulo}
            </Link>
          ))}

          {/* Hasta que el navegador no ha montado no se sabe si hay sesión: se pinta el hueco
              vacío en vez de adivinar, o el servidor y el cliente dirían cosas distintas. */}
          {!montado ? (
            <span className="cabecera__enlace" aria-hidden="true">
              &nbsp;
            </span>
          ) : conSesion ? (
            <button
              type="button"
              className="cabecera__enlace cabecera__enlace--boton"
              onClick={() => {
                borrarSesion();
                router.push('/');
              }}
            >
              Salir
            </button>
          ) : (
            <Link href="/entrar" className="cabecera__enlace" aria-current={camino === '/entrar' ? 'page' : undefined}>
              Entrar
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
