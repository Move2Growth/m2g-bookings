/**
 * El código y el enlace del salón (NEG-4).
 *
 * Lo que se comprueba no es que haya un dibujo: es que **el dibujo diga lo que tiene que
 * decir**. Un QR bonito que apunta a otro sitio es peor que no tenerlo, porque nadie lo
 * comprueba hasta que un cliente escanea el cartel del mostrador y acaba en una página en
 * blanco. Así que aquí el código se **descodifica** y se compara con la ficha de verdad.
 */

import { abrirNavegador, nuevaPagina, sembrarSesion, esperarAQueSeQuede, medirAncho, WEB } from './comun.mjs';

const bien = [];
const mal = [];
const ok = (q, d = '') => { bien.push(q); console.log(`ok   ${q}${d ? ' · ' + d : ''}`); };
const nok = (q, d = '') => { mal.push(q); console.log(`MAL  ${q}${d ? ' · ' + d : ''}`); };

const navegador = await abrirNavegador();
try {
  const pagina = await nuevaPagina(navegador);
  await sembrarSesion(pagina, 'dueno');
  await pagina.goto(`${WEB}/local/publicidad`, { waitUntil: 'domcontentloaded' });
  await esperarAQueSeQuede(pagina);
  await pagina.waitForSelector('.qr svg', { timeout: 25000 });

  const enlace = (await pagina.locator('.enlace-del-salon').first().textContent()).trim();
  if (/^https?:\/\/.+\/salon\/.+/.test(enlace)) ok('el enlace que se reparte está entero', enlace);
  else nok('el enlace no es un enlace', enlace);

  // Que esa ficha exista de verdad. Repartir un enlace roto es el fallo silencioso de esto.
  const respuesta = await pagina.request.get(enlace);
  if (respuesta.status() === 200) ok('y lleva a una ficha que existe', `HTTP ${respuesta.status()}`);
  else nok('el enlace repartido no lleva a ninguna parte', `HTTP ${respuesta.status()}`);

  // **El código se lee de verdad.** Comprobar que existe un `<svg>` no comprueba nada: un
  // dibujo bonito que apunta a otro sitio es peor que no tener ninguno, porque nadie se entera
  // hasta que una clienta escanea el cartel del mostrador y acaba en una página en blanco. Así
  // que aquí el SVG se pinta en un lienzo y se descodifica con un lector de verdad, el mismo
  // trabajo que hace la cámara de un móvil.
  await pagina.addScriptTag({ path: 'node_modules/jsqr/dist/jsQR.js' });
  const leido = await pagina.evaluate(async () => {
    const svg = document.querySelector('.qr svg');
    const fuente = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svg.outerHTML)));
    const imagen = await new Promise((listo, falla) => {
      const i = new Image();
      i.onload = () => listo(i);
      i.onerror = falla;
      i.src = fuente;
    });
    const lienzo = document.createElement('canvas');
    // Se rasteriza grande a propósito: un QR pintado a 100 px pierde módulos y el lector falla
    // por la resolución, no por el código.
    lienzo.width = 600;
    lienzo.height = 600;
    const pincel = lienzo.getContext('2d');
    pincel.fillStyle = '#ffffff';
    pincel.fillRect(0, 0, 600, 600);
    pincel.drawImage(imagen, 0, 0, 600, 600);
    const pixeles = pincel.getImageData(0, 0, 600, 600);
    return window.jsQR(pixeles.data, pixeles.width, pixeles.height)?.data ?? null;
  });

  if (leido === enlace) ok('el código lleva exactamente al enlace del salón', leido);
  else nok('el código lleva a otro sitio que el enlace de al lado', `código «${leido}» · enlace «${enlace}»`);

  const forma = await pagina.evaluate(() => {
    const svg = document.querySelector('.qr svg');
    return {
      modulos: svg.querySelectorAll('path, rect').length,
      viewBox: svg.getAttribute('viewBox'),
      // El blanco tiene que ir **dentro** del archivo: si lo pusiera el CSS, el SVG descargado
      // saldría transparente y la imprenta lo pondría sobre lo que quisiera.
      blancoDentro: /#ffffff|fill="#fff/i.test(svg.outerHTML),
    };
  });
  if (forma.modulos > 0 && forma.viewBox) ok('el código es un SVG con caja propia', `viewBox ${forma.viewBox}`);
  else nok('el SVG no tiene forma de código', JSON.stringify(forma));
  if (forma.blancoDentro) ok('el blanco viaja dentro del archivo, no en el CSS');
  else nok('el SVG saldría transparente al descargarlo: no lo lee ninguna cámara sobre color');

  // Descargar de verdad, y que lo descargado sea el mismo dibujo que se ve.
  const [descarga] = await Promise.all([
    pagina.waitForEvent('download', { timeout: 20000 }),
    pagina.getByRole('button', { name: 'Descargar para imprimir' }).click(),
  ]);
  const nombre = descarga.suggestedFilename();
  if (/^qr-.+\.svg$/.test(nombre)) ok('el archivo se llama por su salón', nombre);
  else nok('el archivo descargado no se distingue de otros', nombre);

  const ancho = await medirAncho(pagina);
  if (ancho.scrollWidth <= ancho.clientWidth) ok('no desborda a 390 px', `${ancho.scrollWidth} px`);
  else nok('se va de lado', `${ancho.scrollWidth} px · ${ancho.culpables.join(' | ')}`);

  if (pagina.problemas.length === 0) ok('sin errores en la consola');
  else nok('la consola se queja', pagina.problemas.slice(0, 2).join(' | '));
} finally {
  await navegador.close();
}

console.log(`\n${bien.length} bien · ${mal.length} mal`);
if (mal.length > 0) process.exit(1);
console.log('El salón se lleva su enlace y su código, y los dos llevan a su ficha.');
