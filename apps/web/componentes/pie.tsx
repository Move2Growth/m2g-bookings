/**
 * El pie. Va en TODAS las pantallas, igual que la cabecera: una pantalla sin pie está a medias.
 *
 * Solo enlaza a sitios que existen. Un pie lleno de enlaces muertos es peor que un pie corto.
 * La última línea dice de dónde salen los datos, que en un prototipo que se va a criticar es
 * información y no adorno: quien lo mire sabe contra qué está hablando la pantalla.
 */

import Link from 'next/link';

import { BASE_API } from '@/lib/api';
import { LEMA, NOMBRE_COMERCIAL } from '@/lib/marca';

export function Pie() {
  return (
    <footer className="pie">
      <div className="contenido pie__caja">
        <div className="pila pila--apretada">
          <span className="etiqueta etiqueta--clara">{NOMBRE_COMERCIAL} · Panamá</span>
          <p className="pie__lema">{LEMA}</p>
        </div>

        <div className="pila pila--apretada">
          <nav className="pie__enlaces" aria-label="Pie">
            <Link href="/">Portada</Link>
            <Link href="/buscar">Buscar</Link>
            <Link href="/mapa">Mapa</Link>
            <Link href="/mis-citas">Mis citas</Link>
            <Link href="/local">Mi salón</Link>
            <Link href="/entrar">Entrar</Link>
          </nav>
          {/* **Los legales van aparte del resto.** No son navegación: son lo que hay que poder
              encontrar sin buscarlo, y mezclados con «Buscar» y «Entrar» se pierden. Faltaban
              las dos páginas y el enlace a las dos. */}
          <nav className="pie__enlaces pie__enlaces--legal" aria-label="Legal">
            <Link href="/legal/privacidad">Qué hacemos con tus datos</Link>
            <Link href="/legal/terminos">Términos de uso</Link>
          </nav>
          <p className="pie__nota">
            Prototipo local. Todo lo que se ve en pantalla sale de la API en <code>{BASE_API}</code>: no hay ni un dato
            escrito a mano.
          </p>
        </div>
      </div>
    </footer>
  );
}
