/**
 * D1, comprobado por los dos lados.
 *
 * A · **En el código**: ni un hexadecimal, ni un `rgb()`/`hsl()` escrito a mano, ni una familia
 *     tipográfica entre comillas en la hoja de estilo ni en los componentes.
 *
 * B · **En la pantalla pintada**: se recogen TODOS los colores que el navegador acaba usando
 *     —texto, fondo, borde, contorno y sombra— en las quince pantallas, y se comprueba que cada
 *     uno está en `packages/tokens/tokens.json`. Esto es lo que pilla el fallo que ya ocurrió
 *     una vez: importar los tokens y taparlos después con color escrito a mano.
 *
 * C · Y que la letra que el navegador acaba usando es la de los tokens y no una de respaldo.
 */

import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { abrirNavegador, esperarAQueSeQuede, nuevaPagina, sembrarSesion, WEB } from './comun.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const WEB_DIR = path.join(AQUI, '..');
const TOKENS = path.join(WEB_DIR, '../../packages/tokens/tokens.json');

let fallos = 0;
function decir(bien, texto, extra = '') {
  if (!bien) fallos += 1;
  console.log(`${bien ? '  ok ' : 'FALLA'} · ${texto}${extra ? ` · ${extra}` : ''}`);
}

/* ═══ A · En el código ═══════════════════════════════════════════════════════════════════ */

async function archivos(carpeta, extensiones) {
  const encontrados = [];
  for (const entrada of await readdir(carpeta, { withFileTypes: true })) {
    if (entrada.name === 'node_modules' || entrada.name === '.next' || entrada.name === 'verificacion') continue;
    const completo = path.join(carpeta, entrada.name);
    if (entrada.isDirectory()) encontrados.push(...(await archivos(completo, extensiones)));
    else if (extensiones.some((extension) => entrada.name.endsWith(extension))) encontrados.push(completo);
  }
  return encontrados;
}

const fuentesDelProducto = await archivos(WEB_DIR, ['.css', '.ts', '.tsx']);
const culpables = { hex: [], rgb: [], familia: [] };

for (const archivo of fuentesDelProducto) {
  const texto = await readFile(archivo, 'utf8');
  texto.split('\n').forEach((linea, numero) => {
    const sitio = `${path.relative(WEB_DIR, archivo)}:${numero + 1}`;
    const sinComentario = linea.replace(/\/\/.*$/, '');
    if (/#[0-9a-fA-F]{3,8}\b/.test(sinComentario)) culpables.hex.push(`${sitio} → ${linea.trim()}`);
    if (/\b(rgba?|hsla?)\(/.test(sinComentario)) culpables.rgb.push(`${sitio} → ${linea.trim()}`);
    if (/font-family\s*:\s*['"]/.test(sinComentario) || /fontFamily\s*:\s*['"]/.test(sinComentario)) {
      culpables.familia.push(`${sitio} → ${linea.trim()}`);
    }
  });
}

decir(culpables.hex.length === 0, 'ni un hexadecimal en el código de la web', culpables.hex.join(' | '));
decir(culpables.rgb.length === 0, 'ni un rgb()/hsl() escrito a mano', culpables.rgb.join(' | '));
decir(culpables.familia.length === 0, 'ni una familia tipográfica escrita a mano', culpables.familia.join(' | '));

/* ═══ B · En la pantalla pintada ══════════════════════════════════════════════════════════ */

const tokens = JSON.parse(await readFile(TOKENS, 'utf8'));

/** Todos los colores que declaran los tokens, en el formato en que los devuelve el navegador. */
const permitidos = new Set(['rgba(0, 0, 0, 0)', 'rgb(0, 0, 0)']);
const nombresDeToken = new Map();

function aRgb(hex) {
  const limpio = hex.replace('#', '');
  const partes =
    limpio.length === 3
      ? limpio.split('').map((letra) => parseInt(letra + letra, 16))
      : [0, 2, 4].map((salto) => parseInt(limpio.slice(salto, salto + 2), 16));
  return `rgb(${partes.join(', ')})`;
}

function recorrer(nodo, camino) {
  for (const [clave, valor] of Object.entries(nodo)) {
    if (clave.startsWith('_')) continue;
    if (typeof valor === 'string') {
      if (/^#[0-9a-fA-F]{3,8}$/.test(valor)) {
        const rgb = aRgb(valor);
        permitidos.add(rgb);
        nombresDeToken.set(rgb, `${camino}.${clave}`);
      } else if (valor.startsWith('rgba(')) {
        permitidos.add(valor);
        nombresDeToken.set(valor, `${camino}.${clave}`);
      }
    } else if (typeof valor === 'object' && valor !== null) {
      recorrer(valor, `${camino}.${clave}`);
    }
  }
}
recorrer(tokens, 'tokens');

// `transparent` y el negro puro de una sombra sin color propio no son decisiones de paleta.
// El blanco puro sí está en los tokens (`lienzo`, `superficie.local`).

const PANTALLAS = [
  ['/', null],
  ['/buscar', null],
  ['/buscar?cuando=hoy', null],
  ['/buscar?texto=zzzzz', null],
  ['/buscar?simular=error', null],
  ['/salon/barberia-el-cangrejo', null],
  ['/salon/no-existe-este-salon', null],
  ['/salon/barberia-el-cangrejo/con/kevin-ortega', null],
  ['/reservar/barberia-el-cangrejo', null],
  ['/entrar', null],
  ['/mis-citas', null],
  ['/mis-citas', 'clienta'],
  ['/local', null],
  ['/local', 'dueno'],
  ['/esto-no-existe', null],
];

const navegador = await abrirNavegador();
const intrusos = new Map();
const familias = new Set();
let medidos = 0;

for (const [url, cuenta] of PANTALLAS) {
  const pagina = await nuevaPagina(navegador);
  if (cuenta) await sembrarSesion(pagina, cuenta);
  await pagina.goto(`${WEB}${url}`, { waitUntil: 'networkidle', timeout: 60_000 });
  await esperarAQueSeQuede(pagina);

  const cosecha = await pagina.evaluate(() => {
    const colores = [];
    const letras = new Set();
    const propiedades = [
      'color',
      'backgroundColor',
      'borderTopColor',
      'borderRightColor',
      'borderBottomColor',
      'borderLeftColor',
      'outlineColor',
      'textDecorationColor',
      'caretColor',
      'fill',
      'stroke',
    ];
    for (const elemento of document.querySelectorAll('html, body, body *')) {
      // `nextjs-portal` es la consola de errores que Next inyecta EN DESARROLLO. No es
      // producto: no se compila en `next build` y no la ve nadie que no sea quien programa.
      if (elemento.closest('nextjs-portal') || elemento.tagName.toLowerCase() === 'nextjs-portal') continue;
      const estilo = getComputedStyle(elemento);
      for (const propiedad of propiedades) {
        const valor = estilo[propiedad];
        if (valor && valor !== 'none') {
          colores.push({
            valor,
            donde: `${elemento.tagName.toLowerCase()}.${String(elemento.className).slice(0, 40)} · ${propiedad}`,
          });
        }
      }
      letras.add(estilo.fontFamily);
    }
    return { colores, letras: Array.from(letras) };
  });

  cosecha.letras.forEach((familia) => familias.add(familia));
  for (const { valor, donde } of cosecha.colores) {
    medidos += 1;
    // El navegador escribe `rgba(r, g, b, 1)` en algunos sitios; se normaliza a `rgb()`.
    const normalizado = valor.replace(/^rgba\((\d+), (\d+), (\d+), 1\)$/, 'rgb($1, $2, $3)');
    if (!permitidos.has(normalizado) && !intrusos.has(normalizado)) intrusos.set(normalizado, `${url} → ${donde}`);
  }

  await pagina.context().close();
}

await navegador.close();

decir(
  intrusos.size === 0,
  `los ${medidos} colores que se pintan salen todos de los tokens`,
  Array.from(intrusos.entries())
    .map(([color, donde]) => `${color} en ${donde}`)
    .join(' | '),
);

/* ═══ C · La letra ════════════════════════════════════════════════════════════════════════ */

const familiasDeToken = [tokens.tipografia.familia, tokens.tipografia['familia-display']];
const familiasVistas = Array.from(familias);
const extranas = familiasVistas.filter(
  (familia) => !familiasDeToken.some((deToken) => normalizar(deToken) === normalizar(familia)),
);

function normalizar(texto) {
  return texto.replace(/["']/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
}

decir(
  extranas.length === 0,
  `las únicas familias que se pintan son las dos de los tokens`,
  extranas.join(' | '),
);
console.log(`        familias vistas: ${familiasVistas.map((f) => f.split(',')[0]).join(' · ')}`);

console.log(`\n${fallos === 0 ? 'D1 cumplido: el color y la letra salen de los tokens, en el código y en la pantalla.' : `${fallos} comprobaciones fallaron.`}`);
process.exit(fallos === 0 ? 0 : 1);
