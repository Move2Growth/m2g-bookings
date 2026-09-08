/**
 * El sello de la marca: un círculo de seis porciones al que le falta una.
 *
 * La porción que falta es el turno que viene y **no se rellena nunca** (ADR-0022). Va dibujado
 * como geometría —cinco sectores de 60° con 3° de aire— y no como letra: así aguanta a 16 px y
 * no depende de que cargue ninguna fuente. Los sectores se calcularon una vez con centro
 * (12, 12) y radio 11 sobre un lienzo de 24×24.
 *
 * El color lo hereda de quien lo pinta (`currentColor`): dentro de un bloque cobalto sale en
 * claro y sobre papel sale en tinta, sin que aquí haya ni un color escrito.
 */

const SECTORES = [
  'M12 12L12.288 1.004A11 11 0 0 1 21.379 6.253Z',
  'M12 12L21.667 6.751A11 11 0 0 1 21.667 17.249Z',
  'M12 12L21.379 17.747A11 11 0 0 1 12.288 22.996Z',
  'M12 12L11.712 22.996A11 11 0 0 1 2.621 17.747Z',
  'M12 12L2.333 17.249A11 11 0 0 1 2.333 6.751Z',
];

export function Sello({ medida = 28 }: { medida?: number }) {
  return (
    <svg
      className="sello"
      width={medida}
      height={medida}
      viewBox="0 0 24 24"
      role="img"
      aria-hidden="true"
      focusable="false"
    >
      {SECTORES.map((sector) => (
        <path key={sector} d={sector} fill="currentColor" />
      ))}
    </svg>
  );
}
