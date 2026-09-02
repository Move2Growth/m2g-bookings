// Comprueba que las combinaciones de color que de verdad se usan cumplen WCAG AA.
//
// Existe porque el contraste es lo que más fácil se rompe al retocar un color «solo un poco», y
// porque aquí importa: esto se mira en un salón con luz fuerte, en un teléfono de gama media.
// Si falla, el proceso sale con error.
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

// AA pide 4,5 para texto normal y 3 para texto grande y para elementos de interfaz.
const comprobaciones = [];

for (const [modo, p] of [["claro", claro], ["oscuro", oscuro]]) {
  comprobaciones.push(
    [`texto sobre papel (${modo})`, p.tinta, p.papel, 4.5],
    [`texto sobre lienzo (${modo})`, p.tinta, p.lienzo, 4.5],
    [`texto sobre arena (${modo})`, p.tinta, p.arena, 4.5],
    [`texto suave sobre papel (${modo})`, p["tinta-suave"], p.papel, 4.5],
    [`texto tenue sobre papel (${modo})`, p["tinta-tenue"], p.papel, 4.5],
    [`acento sobre papel (${modo})`, p.acento, p.papel, 4.5],
    [`texto del acento sobre acento (${modo})`, p["acento-texto"], p.acento, 4.5],
    [`peligro sobre papel (${modo})`, p.peligro, p.papel, 4.5],
    [`peligro sobre su fondo suave (${modo})`, p.peligro, p["peligro-suave"], 4.5],
    [`exito sobre papel (${modo})`, p.exito, p.papel, 4.5],
    [`exito sobre su fondo suave (${modo})`, p.exito, p["exito-suave"], 4.5],
    [`aviso sobre papel (${modo})`, p.aviso, p.papel, 4.5],
    [`aviso sobre su fondo suave (${modo})`, p.aviso, p["aviso-suave"], 4.5],
    // El anillo de foco es un elemento de interfaz: si no se ve, la navegación con teclado
    // deja de existir para quien la necesita.
    [`anillo de foco sobre papel (${modo})`, p.foco, p.papel, 3],
    [`borde fuerte sobre papel (${modo})`, p["borde-fuerte"], p.papel, 3],
  );
}

for (const [clave, v] of Object.entries(estados)) {
  if (clave.startsWith("_")) continue;
  comprobaciones.push([`estado ${clave}`, v.texto, v.fondo, 4.5]);
}

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
console.log(`\n${comprobaciones.length} combinaciones, todas cumplen AA.`);
