/**
 * D3, comprobado en la pantalla pintada: **cero redondeo decorativo y cero degradado**.
 *
 * No se mira la hoja de estilo, se mira lo que el navegador acaba dibujando en las quince
 * pantallas. Los tokens definen tres radios: `superficie` (0), `control` (4 px) y `pildora`
 * (999 px). Esta dirección usa **dos**: 0 en todo lo que es superficie y 4 px en lo que se
 * toca. La píldora no aparece, ni siquiera en los avatares —que aquí son bloques cuadrados de
 * color con la inicial dentro—.
 */

import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { abrirNavegador, esperarAQueSeQuede, nuevaPagina, sembrarSesion, WEB } from './comun.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const WEB_DIR = path.join(AQUI, '..');

let fallos = 0;
function decir(bien, texto, extra = '') {
  if (!bien) fallos += 1;
  console.log(`${bien ? '  ok ' : 'FALLA'} · ${texto}${extra ? ` · ${extra}` : ''}`);
}

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

/* ── En el código: ni un degradado ───────────────────────────────────────────────────────── */
const degradados = [];
for (const archivo of await archivos(WEB_DIR, ['.css', '.ts', '.tsx'])) {
  const texto = await readFile(archivo, 'utf8');
  texto.split('\n').forEach((linea, numero) => {
    if (/gradient\(/.test(linea)) degradados.push(`${path.relative(WEB_DIR, archivo)}:${numero + 1}`);
  });
}
decir(degradados.length === 0, 'ni un degradado en el código', degradados.join(' | '));

/* ── En la pantalla: solo dos radios y ningún fondo de imagen ────────────────────────────── */
const PANTALLAS = [
  ['/', null],
  ['/buscar', null],
  ['/buscar?cuando=hoy', null],
  ['/buscar?texto=zzzzz', null],
  ['/buscar?simular=error', null],
  ['/salon/barberia-el-cangrejo', null],
  ['/salon/barberia-el-cangrejo/con/kevin-ortega', null],
  ['/reservar/barberia-el-cangrejo', null],
  ['/entrar', null],
  ['/mis-citas', 'clienta'],
  ['/local', 'dueno'],
  ['/esto-no-existe', null],
];

const PERMITIDOS = new Set(['0px', '4px']);
const navegador = await abrirNavegador();
const radiosRaros = new Map();
const fondosDeImagen = new Map();
let medidos = 0;

for (const [url, cuenta] of PANTALLAS) {
  const pagina = await nuevaPagina(navegador);
  if (cuenta) await sembrarSesion(pagina, cuenta);
  await pagina.goto(`${WEB}${url}`, { waitUntil: 'networkidle', timeout: 60_000 });
  await esperarAQueSeQuede(pagina);

  const cosecha = await pagina.evaluate(() => {
    const salida = [];
    for (const elemento of document.querySelectorAll('body *')) {
      if (elemento.closest('nextjs-portal') || elemento.tagName.toLowerCase() === 'nextjs-portal') continue;
      const caja = elemento.getBoundingClientRect();
      if (caja.width === 0 || caja.height === 0) continue;
      const estilo = getComputedStyle(elemento);
      salida.push({
        radios: [
          estilo.borderTopLeftRadius,
          estilo.borderTopRightRadius,
          estilo.borderBottomRightRadius,
          estilo.borderBottomLeftRadius,
        ],
        fondo: estilo.backgroundImage,
        donde: `${elemento.tagName.toLowerCase()}.${String(elemento.className).slice(0, 46)}`,
      });
    }
    return salida;
  });

  for (const { radios, fondo, donde } of cosecha) {
    for (const radio of radios) {
      medidos += 1;
      if (!PERMITIDOS.has(radio) && !radiosRaros.has(radio)) radiosRaros.set(radio, `${url} → ${donde}`);
    }
    if (fondo && fondo !== 'none' && !fondosDeImagen.has(fondo)) fondosDeImagen.set(fondo, `${url} → ${donde}`);
  }

  await pagina.context().close();
}

await navegador.close();

decir(
  radiosRaros.size === 0,
  `los ${medidos} radios que se pintan son 0 o 4 px, y nada más`,
  Array.from(radiosRaros.entries())
    .map(([radio, donde]) => `${radio} en ${donde}`)
    .join(' | '),
);

decir(
  fondosDeImagen.size === 0,
  'ningún elemento lleva fondo de imagen ni degradado',
  Array.from(fondosDeImagen.entries())
    .map(([fondo, donde]) => `${fondo.slice(0, 40)} en ${donde}`)
    .join(' | '),
);

console.log(`\n${fallos === 0 ? 'D3 cumplido: dos radios, ninguno decorativo, y ni un degradado.' : `${fallos} comprobaciones fallaron.`}`);
process.exit(fallos === 0 ? 0 : 1);
