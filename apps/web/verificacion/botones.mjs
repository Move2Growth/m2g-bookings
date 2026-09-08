/**
 * Los seis estados del botón, fotografiados **en las pantallas de verdad**, no en un muestrario.
 *
 * Un muestrario de botones demuestra que el muestrario está bien. Esto demuestra que el botón
 * que la clienta va a pulsar tiene sus seis estados: se abre `/entrar`, se le hace de todo al
 * botón «Entrar» y se comprueba con `getComputedStyle` que cada estado cambia algo de verdad
 * —el canto, la posición, el fondo o el contorno—, no solo la clase.
 *
 * El estado de carga se consigue retrasando dos segundos la respuesta de la API con el
 * interceptor del navegador: es latencia simulada, no un botón falso.
 */

import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { abrirNavegador, API, CUENTAS, nuevaPagina, WEB } from './comun.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const CAPTURAS = path.join(AQUI, 'capturas');
await mkdir(CAPTURAS, { recursive: true });

const navegador = await abrirNavegador();
const pagina = await nuevaPagina(navegador);
const medidas = {};

async function medir(nombre, selector) {
  const datos = await pagina.evaluate((sel) => {
    const elemento = document.querySelector(sel);
    const estilo = getComputedStyle(elemento);
    return {
      fondo: estilo.backgroundColor,
      texto: estilo.color,
      sombra: estilo.boxShadow,
      transformacion: estilo.transform,
      contorno: `${estilo.outlineWidth} ${estilo.outlineStyle} ${estilo.outlineColor}`,
      cursor: estilo.cursor,
      inhabilitado: elemento.disabled === true,
      ocupado: elemento.getAttribute('aria-busy'),
      rotulo: elemento.innerText.trim(),
    };
  }, selector);
  medidas[nombre] = datos;
  await pagina.locator(selector).screenshot({ path: path.join(CAPTURAS, `boton-${nombre}.png`) });
  console.log(
    `  ${nombre.padEnd(14)} · fondo ${datos.fondo.padEnd(20)} · canto ${datos.sombra.slice(0, 42).padEnd(44)} · ${datos.transformacion.slice(0, 26)}`,
  );
}

await pagina.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' });
const boton = 'form button.boton';

console.log('\nLOS SEIS ESTADOS DEL BOTÓN «ENTRAR», medidos en /entrar');

// 5 · inhabilitado — con los campos vacíos no hay nada que enviar
await medir('inhabilitado', boton);

await pagina.fill('#correo', CUENTAS.clienta.correo);
await pagina.fill('#contrasena', CUENTAS.clienta.contrasena);
await pagina.waitForTimeout(300);

// 1 · reposo
await pagina.mouse.move(5, 5);
await medir('reposo', boton);

// 2 · encima
await pagina.locator(boton).hover();
await pagina.waitForTimeout(250);
await medir('encima', boton);

// 6 · foco de teclado — antes que el pulsado, porque el pulsado acaba soltando el ratón
await pagina.mouse.move(5, 5);
await pagina.locator('#contrasena').focus();
await pagina.keyboard.press('Tab');
await pagina.waitForTimeout(250);
await medir('foco', boton);

// 3 · pulsado — se aprieta encima y se suelta FUERA, para que no llegue a enviarse el formulario
const caja = await pagina.locator(boton).boundingBox();
await pagina.mouse.move(caja.x + caja.width / 2, caja.y + caja.height / 2);
await pagina.mouse.down();
await pagina.waitForTimeout(250);
await medir('pulsado', boton);
await pagina.mouse.move(5, 5);
await pagina.mouse.up();
await pagina.waitForTimeout(150);

// 4 · cargando — se retrasa la respuesta de la API para poder verlo
await pagina.route(`${API}/api/v1/auth/entrar`, async (ruta) => {
  await new Promise((seguir) => setTimeout(seguir, 2500));
  await ruta.continue();
});
await pagina.locator(boton).click();
await pagina.waitForTimeout(700);
await medir('cargando', boton);

await writeFile(path.join(AQUI, 'informe-botones.json'), JSON.stringify(medidas, null, 2));

/* ── Que cada estado sea de verdad distinto de los otros ─────────────────────────────────── */
const huella = (estado) =>
  [estado.fondo, estado.sombra, estado.transformacion, estado.contorno, estado.ocupado, estado.inhabilitado].join('|');

const huellas = Object.entries(medidas).map(([nombre, estado]) => [nombre, huella(estado)]);
const repetidos = [];
for (let i = 0; i < huellas.length; i += 1) {
  for (let j = i + 1; j < huellas.length; j += 1) {
    if (huellas[i][1] === huellas[j][1]) repetidos.push(`${huellas[i][0]} = ${huellas[j][0]}`);
  }
}

console.log('');
if (repetidos.length > 0) {
  console.log(`FALLA · hay estados que se pintan igual: ${repetidos.join(', ')}`);
} else {
  console.log('  ok  · los seis estados se pintan distintos y quedan fotografiados uno a uno.');
}

await navegador.close();
process.exit(repetidos.length === 0 ? 0 : 1);
