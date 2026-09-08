'use client';

/**
 * El botón, con sus seis estados.
 *
 *   1 reposo        · el canto macizo de 4 px por dentro (2 px en el de texto)
 *   2 encima        · el canto crece a 6 px y la chapa se levanta
 *   3 pulsado       · la chapa se traga el canto y baja
 *   4 cargando      · `aria-busy`, la barra que tapa la espera y el rótulo cambia
 *   5 inhabilitado  · arena, sin canto de color y sin movimiento
 *   6 foco          · contorno de tinta de 3 px con 2 px de aire (regla global)
 *
 * Los cinco primeros están en `globales.css`; aquí solo se decide cuál toca.
 *
 * `tono` no es decoración: **cobalto abre e informa, fucsia cierra**. Un botón que confirma
 * una cita es `cierra`; uno que busca o que lleva a otra pantalla es `abre`. Nunca compiten en
 * la misma acción.
 */

import Link from 'next/link';
import type { ComponentProps, ReactNode } from 'react';

type Tono = 'abre' | 'cierra' | 'secundario' | 'texto' | 'riesgo' | 'riesgo-suave';

type PropiedadesComunes = {
  tono?: Tono;
  bloque?: boolean;
  hijos: ReactNode;
};

export function Boton({
  tono = 'abre',
  bloque = false,
  cargando = false,
  rotuloCargando = 'Un momento',
  hijos,
  ...resto
}: PropiedadesComunes & {
  cargando?: boolean;
  rotuloCargando?: string;
} & Omit<ComponentProps<'button'>, 'children'>) {
  return (
    <button
      {...resto}
      className={clases(tono, bloque, resto.className)}
      aria-busy={cargando || undefined}
      disabled={resto.disabled || cargando}
    >
      {cargando ? (
        <>
          <span className="boton__espera" aria-hidden="true" />
          {rotuloCargando}
        </>
      ) : (
        hijos
      )}
    </button>
  );
}

/** El mismo botón cuando lo que hace es ir a otro sitio: entonces es un enlace, no un botón. */
export function BotonEnlace({
  tono = 'abre',
  bloque = false,
  hijos,
  ...resto
}: PropiedadesComunes & ComponentProps<typeof Link>) {
  return (
    <Link {...resto} className={clases(tono, bloque, resto.className)}>
      {hijos}
    </Link>
  );
}

function clases(tono: Tono, bloque: boolean, extra?: string): string {
  return ['boton', `boton--${tono}`, bloque ? 'boton--bloque' : '', extra ?? ''].filter(Boolean).join(' ');
}
