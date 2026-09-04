// Verificación en vivo del prototipo de marca `docs/marca/revision-3/direccion-1.html`.
//
//   node scripts/revision-3-direccion-1.mjs
//
// Hace tres cosas, y ninguna es «build verde»:
//  1. Abre las cinco pantallas en Chromium a 390 y a 1440 px, recorre los flujos
//     (elegir servicio, encender horas, abrir la cortina) y anota errores de
//     consola y desplazamiento horizontal.
//  2. Mide el contraste WCAG de CADA nodo de texto con el color ya calculado por
//     el navegador, no con la paleta declarada. Sale con error si algo baja de AA.
//  3. Deja las dos hojas de contactos en docs/marca/revision-3/capturas/.

import { chromium } from 'playwright'
import { mkdir, writeFile, rm } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const archivo = path.join(raiz, 'docs/marca/revision-3/direccion-1.html')
const url = 'file://' + archivo
const dirCapturas = path.join(raiz, 'docs/marca/revision-3/capturas')
const tmp = path.join(raiz, 'docs/marca/revision-3/.tmp-capturas')

const PANELES = [
  { id: 'portada',    rotulo: '1 · Portada (la calle)' },
  { id: 'resultados', rotulo: '2 · Resultados (la calle)' },
  { id: 'ficha',      rotulo: '3 · Ficha: horas encendidas' },
  { id: 'ficha',      rotulo: '4 · Ficha: paso 2 de 3', cortina: true, sufijo: '-cortina' },
  { id: 'agenda',     rotulo: '5 · Agenda del salón' },
  { id: 'consola',    rotulo: '6 · Consola interna de M2G' }
]

/** El medidor: se ejecuta dentro de la página con los colores ya resueltos. */
const MEDIR = `(() => {
  const canal = (v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
  const lum = (s) => {
    const m = s.match(/[\\d.]+/g).map(Number)
    return 0.2126 * canal(m[0]/255) + 0.7152 * canal(m[1]/255) + 0.0722 * canal(m[2]/255)
  }
  const opaco = (s) => { const m = s.match(/[\\d.]+/g); return m && (m.length < 4 || Number(m[3]) > 0.85) }
  const fondoDe = (el) => {
    let n = el
    while (n && n !== document.documentElement) {
      const b = getComputedStyle(n).backgroundColor
      if (opaco(b) && !/rgba\\(0, 0, 0, 0\\)/.test(b)) return b
      n = n.parentElement
    }
    return getComputedStyle(document.body).backgroundColor
  }
  const fallos = [], vistos = new Set()
  for (const el of document.querySelectorAll('body *')) {
    if (!el.offsetParent && el.tagName !== 'BODY') continue
    const propio = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim())
    if (!propio) continue
    const cs = getComputedStyle(el)
    if (cs.visibility === 'hidden' || cs.opacity === '0') continue
    const px = parseFloat(cs.fontSize)
    const grande = px >= 24 || (px >= 18.66 && Number(cs.fontWeight) >= 700)
    const min = grande ? 3 : 4.5
    const f = fondoDe(el)
    const a = lum(cs.color), b = lum(f)
    const r = (Math.max(a,b) + 0.05) / (Math.min(a,b) + 0.05)
    const clave = cs.color + '|' + f + '|' + Math.round(px)
    if (!vistos.has(clave)) {
      vistos.add(clave)
      if (r < min) fallos.push({ texto: el.textContent.trim().slice(0,40), color: cs.color, fondo: f, px, ratio: +r.toFixed(2), min })
    }
  }
  return fallos
})()`

async function prepara (page, panel) {
  await page.goto(url + '#' + panel.id, { waitUntil: 'load' })
  await page.waitForTimeout(1500)                       // deja terminar las cargas
  if (panel.id === 'ficha') {
    await page.click('.servicio[data-servicio="Corte + barba"]')
    await page.waitForTimeout(900)
    if (panel.cortina) {
      await page.click('#rejilla .hora:not(.hora--ocupada) >> nth=3')
      await page.waitForTimeout(700)
    }
  }
  if (panel.id === 'agenda') await page.waitForTimeout(400)
}

async function corre () {
  await mkdir(dirCapturas, { recursive: true })
  await mkdir(tmp, { recursive: true })
  const navegador = await chromium.launch()
  const problemas = []
  const informe = []

  for (const ancho of [390, 1440]) {
    const ctx = await navegador.newContext({ viewport: { width: ancho, height: ancho === 390 ? 844 : 900 }, deviceScaleFactor: 1 })
    const page = await ctx.newPage()
    page.on('console', m => { if (m.type() === 'error') problemas.push(`[consola ${ancho}] ${m.text()}`) })
    page.on('pageerror', e => problemas.push(`[error ${ancho}] ${e.message}`))

    for (const panel of PANELES) {
      await prepara(page, panel)

      const desborde = await page.evaluate(() => ({
        doc: document.documentElement.scrollWidth,
        vista: document.documentElement.clientWidth
      }))
      if (desborde.doc > desborde.vista + 1) {
        problemas.push(`[desborde ${ancho}] ${panel.rotulo}: ${desborde.doc} > ${desborde.vista}`)
      }

      const fallos = await page.evaluate(MEDIR)
      for (const f of fallos) problemas.push(`[contraste ${ancho}] ${panel.rotulo} «${f.texto}» ${f.ratio}:1 (mínimo ${f.min}) color ${f.color} sobre ${f.fondo}`)

      informe.push({ ancho, panel: panel.rotulo, anchoDoc: desborde.doc, vista: desborde.vista, contrastesMal: fallos.length })

      const destino = path.join(tmp, `${ancho}-${panel.id}${panel.sufijo ?? ''}.png`)
      const alto = await page.evaluate(() => document.documentElement.scrollHeight)
      await page.screenshot({
        path: destino,
        clip: { x: 0, y: 0, width: ancho, height: Math.min(alto, ancho === 390 ? 2400 : 1500) }
      })
    }
    await ctx.close()
  }

  // --- Hojas de contactos -------------------------------------------------
  const hoja = (titulo, ancho, columnas) => `<!doctype html><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Chivo:wght@400;800&display=swap');
  body{ margin:0; background:#07050A; color:#F6EFE8; font-family:Chivo,Arial,sans-serif; padding:28px; }
  h1{ font-size:20px; letter-spacing:.12em; text-transform:uppercase; margin:0 0 6px; }
  h1 b{ color:#FF2D87; }
  p{ margin:0 0 24px; color:#C3B4C0; font-size:16px; }
  .rejilla{ display:grid; grid-template-columns:repeat(${columnas}, max-content); gap:26px; }
  figure{ margin:0; }
  figcaption{ font-size:15px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; color:#FFC46B; padding:0 0 8px; }
  img{ display:block; width:${ancho}px; border:1px solid #71627A; }
</style>
<h1><b>Bukeo</b> · Dirección 1 · Noche de barrio panameño</h1>
<p>${titulo}</p>
<div class="rejilla">
${PANELES.map(p => `<figure><figcaption>${p.rotulo}</figcaption><img src="file://${path.join(tmp, `${ancho}-${p.id}${p.sufijo ?? ''}.png`)}"></figure>`).join('\n')}
</div>`

  const ctx = await navegador.newContext({ deviceScaleFactor: 1 })
  const page = await ctx.newPage()

  await page.setViewportSize({ width: 6 * 390 + 7 * 26 + 56, height: 1200 })
  await page.setContent(hoja('Seis vistas a 390 px de ancho, el teléfono donde vive esto.', 390, 6))
  await page.waitForTimeout(1200)
  await page.screenshot({ path: path.join(dirCapturas, 'direccion-1-movil.png'), fullPage: true })

  await page.setViewportSize({ width: 2 * 1440 + 3 * 26 + 56, height: 1200 })
  await page.setContent(hoja('Seis vistas a 1440 px de ancho, escritorio.', 1440, 2))
  await page.waitForTimeout(1200)
  await page.screenshot({ path: path.join(dirCapturas, 'direccion-1-escritorio.png'), fullPage: true })

  await ctx.close()
  await navegador.close()
  await rm(tmp, { recursive: true, force: true })

  console.table(informe)
  if (problemas.length) {
    console.error('\nPROBLEMAS:\n' + problemas.join('\n'))
    process.exitCode = 1
  } else {
    console.log('\nSin errores de consola, sin desplazamiento horizontal y sin un solo texto por debajo de AA.')
  }
}

corre()
