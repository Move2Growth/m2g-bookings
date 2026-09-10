/**
 * Subir una foto de verdad desde la pantalla, y que se vea fuera (NEG-1, D11 · ADR-0023).
 *
 * Es lo último que le faltaba a un salón para publicarse, así que lo que se comprueba no es que
 * haya un botón: es **la consecuencia entera**. Se elige un archivo en el navegador —como lo
 * haría un dueño—, se espera a que suba, y después se pregunta a la ficha **pública** si esa
 * foto se ve. Una foto que sube y no aparece en la ficha no sirve para nada, y es exactamente
 * el fallo que esto busca.
 *
 * La foto se fabrica aquí, byte a byte: nada de descargar una imagen de internet en una prueba.
 */

import { writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';

import { abrirNavegador, nuevaPagina, sembrarSesion, esperarAQueSeQuede, medirAncho, API, WEB } from './comun.mjs';

const bien = [];
const mal = [];
const ok = (q, d = '') => { bien.push(q); console.log(`ok   ${q}${d ? ' · ' + d : ''}`); };
const nok = (q, d = '') => { mal.push(q); console.log(`MAL  ${q}${d ? ' · ' + d : ''}`); };
const j = async (r) => { const t = await r.text(); try { return JSON.parse(t) } catch { return t } };

/** Un PNG válido de 24×24, hecho a mano. */
function pngDeVerdad(lado = 24) {
  const trozo = (tipo, datos) => {
    const largo = Buffer.alloc(4);
    largo.writeUInt32BE(datos.length);
    const cuerpo = Buffer.concat([Buffer.from(tipo, 'ascii'), datos]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(zlib.crc32 ? zlib.crc32(cuerpo) : crc32(cuerpo));
    return Buffer.concat([largo, cuerpo, crc]);
  };
  // CRC32 a mano: `zlib.crc32` no existe en todas las versiones de Node.
  function crc32(buf) {
    let c = ~0;
    for (const b of buf) {
      c ^= b;
      for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
    }
    return (~c) >>> 0;
  }
  const cabecera = Buffer.alloc(13);
  cabecera.writeUInt32BE(lado, 0);
  cabecera.writeUInt32BE(lado, 4);
  cabecera[8] = 8; cabecera[9] = 2;
  const filas = Buffer.concat(
    Array.from({ length: lado }, () => Buffer.concat([Buffer.from([0]), Buffer.from(Array.from({ length: lado * 3 }, (_, i) => (i % 3 === 0 ? 0x1b : i % 3 === 1 ? 0x34 : 0xc4)))])),
  );
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    trozo('IHDR', cabecera),
    trozo('IDAT', zlib.deflateSync(filas)),
    trozo('IEND', Buffer.alloc(0)),
  ]);
}

const archivo = path.join(tmpdir(), `prueba-salon-${Date.now()}.png`);
await writeFile(archivo, pngDeVerdad());

const navegador = await abrirNavegador();
try {
  const pagina = await nuevaPagina(navegador);
  await sembrarSesion(pagina, 'dueno');
  await pagina.goto(`${WEB}/local/fotos`, { waitUntil: 'domcontentloaded' });
  await esperarAQueSeQuede(pagina);

  // **Hay dos campos de archivo y no uno**: la portada y la galería. Apuntar a
  // `input[type=file]` a secas coge el primero —la portada— y luego se comprueba la galería,
  // que no ha cambiado: la prueba cantaba un fallo mientras la foto subía perfectamente. Cada
  // uno se elige por su sitio.
  const campoPortada = pagina.locator('.foto-grande, .vacio').locator('xpath=..').locator('input[type="file"]');
  const campos = pagina.locator('input[type="file"]');
  if ((await campos.count()) !== 2) nok('la pantalla no ofrece los dos sitios', `${await campos.count()} campos`);
  else ok('la pantalla separa la portada de las demás');

  // 1 · La portada, que es lo que desbloquea publicar (D11).
  await campos.nth(0).setInputFiles(archivo);
  const portadaPuesta = await pagina
    .waitForSelector('.foto-grande img', { timeout: 45_000 })
    .then(() => true)
    .catch(() => false);
  if (portadaPuesta) ok('la portada se sube desde la pantalla');
  else {
    const queja = await pagina.locator('.campo__fallo').first().textContent().catch(() => null);
    nok('la portada no se puso', queja ? queja.trim() : 'sin mensaje');
  }

  // 2 · Y una de la galería, con el otro campo.
  //
  // Se cuenta **después de que la portada se asiente**, y no antes: poner una portada nueva
  // manda la anterior a la galería —lo hace la API a propósito, para no borrar la foto de
  // nadie—, así que contar demasiado pronto veía «+2» y acusaba a la pantalla de un fallo que
  // era una decisión de producto.
  await esperarAQueSeQuede(pagina);
  await pagina.waitForTimeout(800);
  const antes = await pagina.locator('.galeria__pieza').count();
  await campos.nth(1).setInputFiles(archivo);
  await pagina
    .waitForFunction((cuantas) => document.querySelectorAll('.galeria__pieza').length > cuantas, antes, { timeout: 45_000 })
    .catch(() => null);

  const despues = await pagina.locator('.galeria__pieza').count();
  if (despues === antes + 1) ok('y otra más a la galería', `${antes} → ${despues}`);
  else {
    const queja = await pagina.locator('.campo__fallo').first().textContent().catch(() => null);
    nok('la foto no llegó a la galería', `${antes} → ${despues}${queja ? ' · ' + queja.trim() : ''}`);
  }

  // Y se ve de verdad: no un hueco roto.
  const pintada = await pagina.evaluate(() => {
    const img = document.querySelector('.foto-grande img');
    return img ? { alto: img.naturalHeight, ancho: img.naturalWidth, src: img.src } : null;
  });
  if (pintada && pintada.alto > 0) ok('y el navegador la pinta', `${pintada.ancho}×${pintada.alto}`);
  else nok('la foto está en la lista pero no se pinta', JSON.stringify(pintada));

  // Lo que de verdad importa: que se vea desde fuera, en la ficha pública.
  const ficha = await j(await fetch(`${API}/api/v1/publico/negocios/barberia-el-cangrejo`));
  const delAlmacen = (ficha.fotos ?? []).filter((u) => u.includes('/negocios/'));
  if (delAlmacen.length > 0) ok('y sale en la ficha pública', `${delAlmacen.length} foto(s) del almacén`);
  else nok('la foto no llega a la ficha pública', JSON.stringify(ficha.fotos ?? []).slice(0, 120));

  const respuesta = await pagina.request.get(delAlmacen[0] ?? pintada?.src ?? '');
  if (respuesta.status() === 200) ok('y el almacén la sirve a cualquiera', `HTTP 200 · ${respuesta.headers()['content-type']}`);
  else nok('el almacén no la sirve', `HTTP ${respuesta.status()}`);

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
console.log('Un salón sube su foto desde la pantalla y se ve en su ficha pública.');
