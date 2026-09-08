/**
 * Barre las pantallas a 390 px y comprueba, en la pantalla ya pintada:
 *
 *   · que responden y no dejan un error en la consola del navegador
 *   · que **no desbordan a lo ancho** (`scrollWidth`, no a ojo)
 *   · que cuando la pantalla se queda quieta **no hay ni una animación en marcha**
 *   · que ninguna combinación de texto baja de 4,5:1 (3:1 si el texto es grande)
 *
 * Se ejecuta con `pnpm --filter @agenda/web verificar` y deja las capturas en
 * `verificacion/capturas/`.
 */

import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  abrirNavegador,
  animacionesEnMarcha,
  esperarAQueSeQuede,
  medirAncho,
  medirContraste,
  nuevaPagina,
  sembrarSesion,
  WEB,
} from './comun.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const CAPTURAS = path.join(AQUI, 'capturas');

const PANTALLAS = [
  { nombre: '01-portada', url: '/', sesion: null },
  { nombre: '02-buscar', url: '/buscar', sesion: null },
  { nombre: '03-buscar-hoy', url: '/buscar?cuando=hoy', sesion: null },
  { nombre: '04-buscar-vacio', url: '/buscar?texto=zzzzz', sesion: null },
  { nombre: '05-buscar-error', url: '/buscar?simular=error', sesion: null },
  { nombre: '06-salon', url: '/salon/barberia-el-cangrejo', sesion: null },
  { nombre: '07-salon-no-publicado', url: '/salon/no-existe-este-salon', sesion: null },
  { nombre: '08-profesional', url: '/salon/barberia-el-cangrejo/con/kevin-ortega', sesion: null },
  { nombre: '09-reservar', url: '/reservar/barberia-el-cangrejo', sesion: null },
  { nombre: '10-entrar', url: '/entrar', sesion: null },
  { nombre: '11-mis-citas-sin-sesion', url: '/mis-citas', sesion: null },
  { nombre: '12-mis-citas', url: '/mis-citas', sesion: 'clienta' },
  { nombre: '13-local-sin-sesion', url: '/local', sesion: null },
  { nombre: '14-local', url: '/local', sesion: 'dueno' },
  { nombre: '15-no-encontrado', url: '/esto-no-existe', sesion: null },
];

const navegador = await abrirNavegador();
await mkdir(CAPTURAS, { recursive: true });

const informe = [];
let fallos = 0;

for (const pantalla of PANTALLAS) {
  const pagina = await nuevaPagina(navegador);
  if (pantalla.sesion) await sembrarSesion(pagina, pantalla.sesion);

  const respuesta = await pagina.goto(`${WEB}${pantalla.url}`, { waitUntil: 'networkidle', timeout: 60_000 });
  await esperarAQueSeQuede(pagina);

  const ancho = await medirAncho(pagina);
  const animaciones = await animacionesEnMarcha(pagina);
  const contraste = await medirContraste(pagina);
  const flojos = contraste.filter((medida) => !medida.pasa);
  const tieneCabecera = await pagina.locator('header.cabecera').count();
  const tienePie = await pagina.locator('footer.pie').count();

  await pagina.screenshot({ path: path.join(CAPTURAS, `${pantalla.nombre}.png`), fullPage: true });

  const problemas = pagina.problemas.filter(
    (texto) =>
      !texto.includes('Download the React DevTools') &&
      !texto.includes('favicon') &&
      // La pantalla de «no existe» **tiene** que responder 404: que el navegador lo apunte en
      // la consola es la prueba de que la ruta no se está inventando un 200.
      !(respuesta?.status() === 404 && texto.includes('404 (Not Found)')),
  );

  const fila = {
    pantalla: pantalla.nombre,
    url: pantalla.url,
    estado: respuesta?.status() ?? 0,
    scrollWidth: ancho.scrollWidth,
    desborda: ancho.scrollWidth > 390,
    culpables: ancho.culpables,
    animacionesEnMarcha: animaciones,
    combinacionesMedidas: contraste.length,
    contrastesFlojos: flojos.map((medida) => `${medida.razon}:1 (mín ${medida.minimo}) — ${medida.selector} — «${medida.texto}»`),
    cabecera: tieneCabecera > 0,
    pie: tienePie > 0,
    erroresDeConsola: problemas,
  };

  if (
    fila.desborda ||
    fila.animacionesEnMarcha.length > 0 ||
    flojos.length > 0 ||
    !fila.cabecera ||
    !fila.pie ||
    problemas.length > 0 ||
    fila.estado >= 500
  ) {
    fallos += 1;
  }

  informe.push(fila);
  console.log(
    [
      fila.desborda || flojos.length > 0 || animaciones.length > 0 || problemas.length > 0 || !fila.cabecera || !fila.pie
        ? 'FALLA'
        : '  ok ',
      pantalla.nombre.padEnd(26),
      `HTTP ${fila.estado}`,
      `ancho ${fila.scrollWidth}`,
      `AA ${contraste.length - flojos.length}/${contraste.length}`,
      `anim ${animaciones.length}`,
      fila.cabecera && fila.pie ? 'cab+pie' : 'SIN CABECERA/PIE',
      problemas.length ? `consola: ${problemas[0].slice(0, 80)}` : '',
    ].join(' · '),
  );
  if (flojos.length > 0) flojos.forEach((medida) => console.log(`        ${medida.razon}:1  ${medida.selector} «${medida.texto}»`));
  if (fila.desborda) console.log(`        culpables: ${fila.culpables.join(' | ')}`);

  await pagina.context().close();
}

await writeFile(path.join(AQUI, 'informe.json'), JSON.stringify(informe, null, 2));
await navegador.close();

console.log(`\n${PANTALLAS.length - fallos}/${PANTALLAS.length} pantallas limpias.`);
process.exit(fallos === 0 ? 0 : 1);
