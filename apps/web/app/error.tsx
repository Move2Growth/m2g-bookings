'use client';

import Link from 'next/link';

import { Boton } from '@/componentes/boton';

/**
 * La red de seguridad: si una pantalla revienta por algo que no se previó, esto es lo que se
 * ve. Sigue siendo una pantalla entera, con su cabecera y su pie, y con dos salidas.
 */
export default function AlgoSeRompio({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="contenido seccion">
      <div className="hueco bloque bloque--peligro relleno--grande" role="alert">
        <span className="etiqueta">Se rompió</span>
        <h1 className="hueco__titulo">Esta pantalla no pudo terminar de cargar</h1>
        <p className="parrafo">{error.message || 'No llegó ninguna explicación.'}</p>
        <div className="tira">
          <Boton tono="abre" onClick={reset} hijos="Volver a intentarlo" />
          <Link className="boton boton--secundario" href="/">
            Ir a la portada
          </Link>
        </div>
      </div>
    </div>
  );
}
