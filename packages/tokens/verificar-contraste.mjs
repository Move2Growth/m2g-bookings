// Comprueba que las combinaciones de color que de verdad se usan cumplen WCAG AA.
//
// Existe porque el contraste es lo que más fácil se rompe al retocar un color «solo un poco»,
// y porque aquí importa de verdad: esto se mira en un salón con luz fuerte, en un teléfono de
// gama media, y los colores de estado tienen que leerse. Si falla, el proceso sale con error.
//
//   pnpm --filter @agenda/tokens contraste

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const tokens = JSON.parse(readFileSync(join(aqui, "tokens.json"), "utf8"));

const canal = (v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);

function luminancia(hex) {
  const n = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(n.slice(i, i + 2), 16) / 255);
  return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b);
}

function contraste(a, b) {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

const { claro, oscuro } = tokens.color;
const estados = tokens["estado-reserva"];

// AA pide 4,5 para texto normal y 3 para texto grande y para bordes y elementos de interfaz.
const comprobaciones = [
  ["texto sobre superficie (claro)", claro.texto, claro.superficie, 4.5],
  ["texto suave sobre superficie (claro)", claro["texto-suave"], claro.superficie, 4.5],
  ["texto sobre superficie suave (claro)", claro.texto, claro["superficie-suave"], 4.5],
  ["texto del acento sobre acento (claro)", claro["acento-texto"], claro.acento, 4.5],
  ["acento sobre superficie (claro)", claro.acento, claro.superficie, 4.5],
  ["peligro sobre superficie (claro)", claro.peligro, claro.superficie, 4.5],
  ["aviso sobre superficie (claro)", claro.aviso, claro.superficie, 4.5],
  ["éxito sobre superficie (claro)", claro.exito, claro.superficie, 4.5],
  ["borde fuerte sobre superficie (claro)", claro["borde-fuerte"], claro.superficie, 3],
  // El anillo de foco es un elemento de interfaz: AA le pide 3, y si no se ve, la navegación
  // con teclado deja de existir para quien la necesita.
  ["anillo de foco sobre superficie (claro)", claro.foco, claro.superficie, 3],
  ["anillo de foco sobre superficie (oscuro)", oscuro.foco, oscuro.superficie, 3],
  ["éxito sobre su fondo suave (claro)", claro.exito, claro["exito-suave"], 4.5],
  ["aviso sobre su fondo suave (claro)", claro.aviso, claro["aviso-suave"], 4.5],
  ["peligro sobre su fondo suave (claro)", claro.peligro, claro["peligro-suave"], 4.5],
  ["texto sobre superficie (oscuro)", oscuro.texto, oscuro.superficie, 4.5],
  ["texto suave sobre superficie (oscuro)", oscuro["texto-suave"], oscuro.superficie, 4.5],
  ["texto del acento sobre acento (oscuro)", oscuro["acento-texto"], oscuro.acento, 4.5],
  ["acento sobre superficie (oscuro)", oscuro.acento, oscuro.superficie, 4.5],
  ["peligro sobre superficie (oscuro)", oscuro.peligro, oscuro.superficie, 4.5],
  ...Object.entries(estados)
    .filter(([clave]) => !clave.startsWith("_"))
    .map(([clave, v]) => [`estado ${clave}`, v.texto, v.fondo, 4.5]),
];

let fallos = 0;
for (const [nombre, frente, fondo, minimo] of comprobaciones) {
  const ratio = contraste(frente, fondo);
  const pasa = ratio >= minimo;
  if (!pasa) fallos += 1;
  console.log(
    `${pasa ? "ok  " : "MAL "} ${ratio.toFixed(2)} (mín. ${minimo})  ${nombre}  ${frente} sobre ${fondo}`,
  );
}

if (fallos > 0) {
  console.error(`\n${fallos} combinación(es) por debajo de AA. Ajusta los tokens.`);
  process.exit(1);
}
console.log("\nTodas las combinaciones cumplen AA.");
