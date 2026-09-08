/**
 * Una fila de resultado.
 *
 * La decisión de esta dirección está en el botón de la derecha: lo que se ofrece no es «ver el
 * salón», es **una hora**. El nombre lleva a la ficha (cobalto: abre e informa) y la hora lleva
 * a reservar (fucsia: cierra). Son dos objetivos distintos y los dos miden 44 px, para que en
 * el pulgar no haya que apuntar.
 *
 * Si la API no calculó próxima hora, no se inventa nada: se dice que hoy no quedan huecos y se
 * ofrece abrir la ficha para mirar otro día.
 */

import Link from 'next/link';

import type { ResultadoDeBusqueda } from '@/lib/api';
import { cuandoEs, dinero, fechaLocal, hora } from '@/lib/formato';
import { Abierto, Inicial, Nota, Patrocinado } from './piezas';

export function FilaSalon({ salon }: { salon: ResultadoDeBusqueda }) {
  const proxima = salon.proxima_hora;

  return (
    <li className="fila fila--resultado">
      <Inicial texto={salon.nombre} />

      <div className="fila__cuerpo">
        <div className="tira">
          <Link href={`/salon/${salon.slug}`} className="fila__titulo">
            {salon.nombre}
          </Link>
          {salon.patrocinado ? <Patrocinado /> : null}
        </div>

        <p className="fila__datos">
          {salon.zona ? <span>{salon.zona}</span> : null}
          {salon.categorias.length > 0 ? <span>{salon.categorias.join(' · ')}</span> : null}
          <Nota valor={salon.rating} resenas={salon.numero_reviews} />
          {salon.servicios_desde_centavos !== null ? <span>desde {dinero(salon.servicios_desde_centavos)}</span> : null}
        </p>

        <div className="fila__pie">
          <Abierto abierto={salon.abierto_ahora} />
          {proxima ? (
            <Link
              className="hora-suelta"
              href={`/reservar/${salon.slug}?dia=${fechaLocal(new Date(proxima))}`}
              aria-label={`Reservar en ${salon.nombre}, primera hora libre ${cuandoEs(proxima)} a las ${hora(proxima)}`}
            >
              <span aria-hidden="true">
                {cuandoEs(proxima)} · {hora(proxima)}
              </span>
            </Link>
          ) : (
            <span className="menor">Hoy no le quedan huecos. Mira otro día desde la ficha.</span>
          )}
        </div>
      </div>
    </li>
  );
}
