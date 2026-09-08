/**
 * Piezas pequeñas que se repiten. Nada aquí guarda estado ni habla con la API.
 *
 * `Inicial` existe porque en los datos de ejemplo **no hay ni una foto** —la API devuelve 404
 * en `/fotos/*`— y una tarjeta con el icono de imagen rota no es una pantalla entregada. Un
 * bloque de color con la inicial es coherente con la dirección y no miente.
 */

import type { ReactNode } from 'react';

import { nota as formatearNota } from '@/lib/formato';

export function Inicial({
  texto,
  persona = false,
  grande = false,
}: {
  texto: string;
  persona?: boolean;
  grande?: boolean;
}) {
  const letra = texto.trim().charAt(0).toUpperCase() || '·';
  return (
    <span
      className={['inicial', persona ? 'inicial--persona' : '', grande ? 'inicial--grande' : ''].filter(Boolean).join(' ')}
      aria-hidden="true"
    >
      {letra}
    </span>
  );
}

export function Nota({ valor, resenas }: { valor: number | null; resenas?: number }) {
  const escrita = formatearNota(valor);
  if (escrita === null) {
    return <span className="menor">Sin opiniones todavía</span>;
  }
  return (
    <span>
      <span className="cifra">{escrita}</span>
      <span aria-hidden="true"> / 5</span>
      {resenas !== undefined ? <span className="solo-lectores"> sobre 5, con {resenas} opiniones</span> : null}
      {resenas !== undefined ? <span aria-hidden="true"> · {resenas} opiniones</span> : null}
    </span>
  );
}

export function Abierto({ abierto }: { abierto: boolean | null }) {
  if (abierto === null) return null;
  return <span className={`marca ${abierto ? 'marca--abierto' : 'marca--cerrado'}`}>{abierto ? 'Abierto' : 'Cerrado'}</span>;
}

/** MKT-4: un resultado pagado va etiquetado en pantalla, sin excepción. */
export function Patrocinado() {
  return <span className="marca marca--pagado">Pagado</span>;
}

export function Seccion({ titulo, extra, children }: { titulo: string; extra?: ReactNode; children: ReactNode }) {
  return (
    <section className="seccion">
      <div className="titulo-seccion">
        <h2 className="rotulo rotulo--medio">{titulo}</h2>
        {extra}
      </div>
      {children}
    </section>
  );
}
