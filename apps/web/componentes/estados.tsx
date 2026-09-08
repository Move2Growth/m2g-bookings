/**
 * Los tres estados que toda pantalla tiene que saber pintar: cargando, vacío y roto.
 *
 * Están aquí juntos a propósito. Cuando cada pantalla se inventa el suyo, unas los tienen y
 * otras no; teniéndolos en un sitio, olvidarse cuesta más que ponerlos.
 *
 * El movimiento del estado de carga es la única animación que repite en toda la aplicación, y
 * solo existe mientras hay una petición en vuelo: tapar una espera es motivo suficiente. En
 * cuanto llega la respuesta desaparece, y con `prefers-reduced-motion` se queda quieta y lo
 * que informa es el texto.
 */

import type { ReactNode } from 'react';

export function Cargando({ que, filas = 3 }: { que: string; filas?: number }) {
  return (
    <div className="cargando" role="status" aria-live="polite">
      <p className="cargando__aviso">
        <span className="cargando__barra" aria-hidden="true" />
        {que}
      </p>
      <div className="pila pila--apretada" aria-hidden="true">
        {Array.from({ length: filas }).map((_, indice) => (
          <div key={indice} className="pila pila--apretada">
            <span className="hueso hueso--linea" />
            <span className="hueso hueso--fila" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function Vacio({ titulo, explicacion, accion }: { titulo: string; explicacion: string; accion?: ReactNode }) {
  return (
    <div className="hueco bloque bloque--arena relleno--grande">
      <span className="etiqueta">Nada por aquí</span>
      <h2 className="hueco__titulo">{titulo}</h2>
      <p className="parrafo">{explicacion}</p>
      {accion}
    </div>
  );
}

export function Roto({ mensaje, accion }: { mensaje: string; accion?: ReactNode }) {
  return (
    <div className="hueco bloque bloque--peligro relleno--grande" role="alert">
      <span className="etiqueta">No se pudo</span>
      <h2 className="hueco__titulo">Esto no cargó</h2>
      <p className="parrafo">{mensaje}</p>
      {accion}
    </div>
  );
}
