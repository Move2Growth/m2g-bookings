/**
 * Verifica el prototipo de la dirección 3 (docs/marca/revision-3/direccion-3.html):
 *   1. Desplazamiento horizontal medido con scrollWidth a 390 y a 1440 px, pantalla por pantalla.
 *   2. Contraste WCAG de TODO texto visible, con el color calculado y el fondo real
 *      (si el fondo es una trama, se mide contra la raya, que es el peor caso).
 *   3. Cifras tabulares de verdad: se mide el ancho de dos cadenas de dígitos distintas.
 *   4. Animaciones en bucle: no puede haber ninguna con iterationCount infinito.
 *   5. Capturas a 390 y a 1440 px en docs/marca/revision-3/capturas/.
 *
 * Uso:  node scripts/direccion-3-verificar.mjs
 */
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const raiz = path.resolve(aqui, '..');
const archivo = path.join(raiz, 'docs/marca/revision-3/direccion-3.html');
const capturas = path.join(raiz, 'docs/marca/revision-3/capturas');
fs.mkdirSync(capturas, { recursive: true });

const PANTALLAS = [
  { id: 'portada', desplaza: { movil: 0, escritorio: 0 } },
  { id: 'resultados', desplaza: { movil: 120, escritorio: 0 } },
  { id: 'ficha', desplaza: { movil: 430, escritorio: 260 } },
  { id: 'agenda', desplaza: { movil: 150, escritorio: 0 } },
  { id: 'consola', desplaza: { movil: 180, escritorio: 0 } }
];

/* ---- la fórmula WCAG, dentro del navegador ---- */
const SONDA = `
(() => {
  const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  const contraste = (a, b) => { const l1 = lum(a), l2 = lum(b); const hi = Math.max(l1, l2), lo = Math.min(l1, l2); return (hi + 0.05) / (lo + 0.05); };
  const rgb = txt => { const m = (txt || '').match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(',').map(x => parseFloat(x)); return p.length > 3 && p[3] === 0 ? null : [p[0], p[1], p[2]]; };
  const mezcla = (frente, fondo, alfa) => frente.map((c, i) => Math.round(c * alfa + fondo[i] * (1 - alfa)));

  function fondoDe(el) {
    let n = el, fondo = [255, 255, 255];
    const pila = [];
    while (n && n.nodeType === 1) {
      const cs = getComputedStyle(n);
      const img = cs.backgroundImage;
      let c = rgb(cs.backgroundColor);
      // si hay trama o gradiente, el peor caso es su primer color
      if (!c && img && img !== 'none') c = rgb(img);
      if (c) {
        const a = parseFloat((cs.backgroundColor.match(/rgba\\([^)]*,([^)]+)\\)/) || [0, '1'])[1]) || 1;
        pila.push([c, isNaN(a) ? 1 : Math.max(a, 0.999)]);
        if (a >= 0.999 || (img && img !== 'none')) break;
      }
      n = n.parentElement;
    }
    for (let i = pila.length - 1; i >= 0; i--) fondo = mezcla(pila[i][0], fondo, pila[i][1]);
    return fondo;
  }

  const fallos = [];
  const medidos = [];
  document.querySelectorAll('*').forEach(el => {
    if (el.closest('[data-activa]') && el.closest('[data-activa]').dataset.activa !== 'si') return;
    const propio = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length);
    if (!propio) return;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) < 0.1) return;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const color = rgb(cs.color);
    if (!color) return;
    const fondo = fondoDe(el);
    const c = contraste(color, fondo);
    const px = parseFloat(cs.fontSize), peso = parseInt(cs.fontWeight, 10) || 400;
    const grande = px >= 24 || (px >= 18.66 && peso >= 700);
    const minimo = grande ? 3 : 4.5;
    const dato = {
      texto: el.textContent.trim().slice(0, 46), etiqueta: el.tagName.toLowerCase(),
      clase: (el.className || '').toString().slice(0, 40), color: cs.color, fondo: 'rgb(' + fondo.join(',') + ')',
      px, peso, ratio: Math.round(c * 100) / 100, minimo
    };
    medidos.push(dato);
    if (c < minimo) fallos.push(dato);
  });
  return { medidos: medidos.length, fallos, peor: medidos.slice().sort((a, b) => a.ratio - b.ratio).slice(0, 6) };
})()
`;

const url = 'file://' + archivo;
const navegador = await chromium.launch();
let problemas = 0;

for (const [nombre, viewport] of [['movil', { width: 390, height: 844 }], ['escritorio', { width: 1440, height: 900 }]]) {
  const ctx = await navegador.newContext({ viewport, deviceScaleFactor: 2, locale: 'es-PA' });
  const pagina = await ctx.newPage();
  const errores = [];
  pagina.on('pageerror', e => errores.push(String(e)));
  pagina.on('console', m => { if (m.type() === 'error') errores.push(m.text()); });
  await pagina.goto(url);
  await pagina.waitForTimeout(1400); // que carguen fuentes y entre la primera animación

  console.log('\n═══ ' + nombre.toUpperCase() + ' · ' + viewport.width + '×' + viewport.height + ' ═══');

  for (const p of PANTALLAS) {
    await pagina.click(`.cinta__b[data-ir="${p.id}"]`);
    await pagina.waitForTimeout(900);
    await pagina.evaluate(y => window.scrollTo(0, y), p.desplaza[nombre]);
    await pagina.waitForTimeout(400);

    const anchos = await pagina.evaluate(() => ({
      doc: document.documentElement.scrollWidth,
      cuerpo: document.body.scrollWidth,
      ventana: window.innerWidth
    }));
    const desborda = anchos.doc > anchos.ventana + 1;
    if (desborda) problemas++;
    const c = await pagina.evaluate(SONDA);
    if (c.fallos.length) problemas += c.fallos.length;

    console.log(
      `${p.id.padEnd(11)} scrollWidth ${String(anchos.doc).padStart(5)} / ${anchos.ventana}  ${desborda ? '✗ DESBORDA' : '✓'}` +
      `   contraste: ${c.medidos} textos, ${c.fallos.length} por debajo de AA  ${c.fallos.length ? '✗' : '✓'}` +
      `   peor: ${c.peor[0] ? c.peor[0].ratio + ':1' : '-'}`
    );
    c.fallos.slice(0, 8).forEach(f => console.log(`      ✗ ${f.ratio}:1 (mín ${f.minimo}) ${f.px}px/${f.peso} «${f.texto}» color ${f.color} sobre ${f.fondo} [${f.clase}]`));

    await pagina.screenshot({ path: path.join(capturas, `direccion-3-${p.id}-${nombre}.png`) });
    if (p.id === 'ficha') await pagina.screenshot({ path: path.join(capturas, `direccion-3-${nombre}.png`) });
  }

  /* cifras tabulares: dos cadenas de dígitos distintas tienen que medir igual */
  const tabular = await pagina.evaluate(() => {
    const m = document.createElement('span');
    m.style.cssText = 'position:absolute;visibility:hidden;font-family:inherit;font-size:32px;font-variant-numeric:tabular-nums lining-nums';
    document.body.appendChild(m);
    m.textContent = '11111111'; const a = m.getBoundingClientRect().width;
    m.textContent = '00000000'; const b = m.getBoundingClientRect().width;
    const familia = getComputedStyle(document.body).fontFamily;
    m.remove();
    return { a, b, familia };
  });
  const tabularOk = Math.abs(tabular.a - tabular.b) < 0.5;
  if (!tabularOk) problemas++;
  console.log(`cifras tabulares: 11111111=${tabular.a.toFixed(2)}px  00000000=${tabular.b.toFixed(2)}px  ${tabularOk ? '✓' : '✗'}   familia: ${tabular.familia}`);

  /* nada en bucle */
  const bucles = await pagina.evaluate(() =>
    document.getAnimations().filter(a => a.effect && a.effect.getTiming().iterations === Infinity).length);
  if (bucles) problemas++;
  console.log(`animaciones en bucle: ${bucles}  ${bucles ? '✗' : '✓'}`);

  /* apagado del movimiento */
  const ctxQuieto = await navegador.newContext({ viewport, reducedMotion: 'reduce', locale: 'es-PA' });
  const quieta = await ctxQuieto.newPage();
  await quieta.goto(url);
  await quieta.waitForTimeout(600);
  await quieta.click('.cinta__b[data-ir="agenda"]');
  const estadoQuieto = await quieta.evaluate(() => ({
    marca: document.body.dataset.movimiento,
    vivas: document.getAnimations().length,
    pantalla: document.querySelector('#p-agenda').dataset.activa
  }));
  const quietoOk = estadoQuieto.marca === 'no' && estadoQuieto.vivas === 0 && estadoQuieto.pantalla === 'si';
  if (!quietoOk) problemas++;
  console.log(`prefers-reduced-motion: marca=${estadoQuieto.marca} animaciones=${estadoQuieto.vivas} navega=${estadoQuieto.pantalla === 'si'}  ${quietoOk ? '✓' : '✗'}`);
  await ctxQuieto.close();

  if (errores.length) { problemas += errores.length; console.log('errores de consola: ' + errores.join(' | ')); }
  else console.log('errores de consola: 0 ✓');

  await ctx.close();
}

await navegador.close();
console.log(problemas ? `\nHAY ${problemas} PROBLEMAS` : '\nTODO EN VERDE');
process.exit(problemas ? 1 : 0);
