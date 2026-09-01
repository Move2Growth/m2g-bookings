// Genera, a partir de tokens.json, las dos formas en que se consumen los tokens:
//
//   variables.css  variables CSS para la web (Next) y el back-office (Vite)
//   tokens.ts      objeto tipado para la app (React Native no entiende CSS)
//
// Se ejecuta con `pnpm --filter @agenda/tokens generar`. Los archivos generados no se editan
// a mano: se regeneran. Por eso llevan un aviso en la primera línea.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const aqui = dirname(fileURLToPath(import.meta.url));
const tokens = JSON.parse(readFileSync(join(aqui, "tokens.json"), "utf8"));

const AVISO = "/* Generado por generar.mjs a partir de tokens.json. No editar a mano. */";

const esComentario = (clave) => clave.startsWith("_");

/** Aplana el árbol de tokens a pares `--nombre-anidado: valor`. */
function aplanar(objeto, prefijo = []) {
  const salida = [];
  for (const [clave, valor] of Object.entries(objeto)) {
    if (esComentario(clave)) continue;
    const camino = [...prefijo, clave];
    if (valor && typeof valor === "object" && !Array.isArray(valor)) {
      salida.push(...aplanar(valor, camino));
    } else {
      salida.push([camino.join("-"), String(valor)]);
    }
  }
  return salida;
}

// El color se trata aparte: los dos modos comparten nombre de variable y solo cambia el valor,
// que es lo que permite que activar el modo oscuro no sea un rediseño.
const { claro, oscuro, ...restoColor } = tokens.color;
const comunes = { ...tokens, color: restoColor };

const lineas = (pares, sangria = "  ") =>
  pares.map(([nombre, valor]) => `${sangria}--${nombre}: ${valor};`).join("\n");

const css = `${AVISO}

:root {
  color-scheme: light;
${lineas(aplanar(claro, ["color"]))}
${lineas(aplanar(comunes))}
}

/* El modo oscuro está definido desde el día uno pero no se activa en la Fase 1: se enciende
   añadiendo data-tema="oscuro" a la raíz. Modo claro por defecto. */
[data-tema="oscuro"] {
  color-scheme: dark;
${lineas(aplanar(oscuro, ["color"]))}
}
`;

const ts = `${AVISO}

export const tokens = ${JSON.stringify(tokens, null, 2)} as const;

export type Tokens = typeof tokens;
`;

writeFileSync(join(aqui, "variables.css"), css);
writeFileSync(join(aqui, "tokens.ts"), ts);

console.log("Tokens generados: variables.css y tokens.ts");
