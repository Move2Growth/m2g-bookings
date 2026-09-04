// Comprueba la dirección 2 de la revisión 3: contraste AA medido en pantalla y capturas
// a 390 y 1440. Sale con error si algo baja de AA.
//
//   node scripts/revision-3-direccion-2.mjs

import { chromium } from 'playwright'
import { mkdirSync, writeFileSync, rmSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const raiz = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const pagina = pathToFileURL(resolve(raiz, 'docs/marca/revision-3/direccion-2.html')).href
const salida = resolve(raiz, 'docs/marca/revision-3/capturas')
mkdirSync(salida, { recursive: true })

const PANTALLAS = [
  ['portada', '01-portada'],
  ['buscar', '02-buscar'],
  ['salon', '03-salon'],
  ['agenda', '04-agenda'],
  ['consola', '05-consola'],
]
const ANCHOS = [['movil', 390, 844], ['escritorio', 1440, 900]]

const MEDIR = `(() => {
  const canal = (v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
  const luminancia = (s) => {
    const [r, g, b] = s.match(/\\d+/g).slice(0, 3).map((n) => n / 255)
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)
  }
  const contraste = (a, b) => {
    const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p)
    return (x + 0.05) / (y + 0.05)
  }
  const fondoReal = (e) => {
    let n = e
    while (n && n !== document.documentElement) {
      const c = getComputedStyle(n).backgroundColor
      if (c && c !== 'rgba(0, 0, 0, 0)') return c
      n = n.parentElement
    }
    return 'rgb(255, 255, 255)'
  }
  const fallos = [], medidos = []
  const visible = (e) => e.getClientRects().length > 0
  for (const e of document.querySelectorAll('section:not([hidden]) *, header *')) {
    if (!e.textContent?.trim() || e.children.length > 0 || !visible(e)) continue
    const c = getComputedStyle(e)
    if (c.visibility === 'hidden' || c.display === 'none' || +c.opacity === 0) continue
    const px = parseFloat(c.fontSize)
    const grande = px >= 24 || (px >= 18.66 && parseInt(c.fontWeight, 10) >= 700)
    const minimo = grande ? 3 : 4.5
    const ratio = +contraste(c.color, fondoReal(e)).toFixed(2)
    const dato = { texto: e.textContent.trim().slice(0, 44), ratio, minimo, px: Math.round(px), color: c.color, fondo: fondoReal(e) }
    medidos.push(dato)
    if (ratio < minimo) fallos.push(dato)
  }
  return { fallos, total: medidos.length, minimo: medidos.reduce((a, b) => (b.ratio < a.ratio ? b : a), medidos[0]) }
})()`

const navegador = await chromium.launch()
let fallos = 0
const resumen = []

for (const [nombre, ancho, alto] of ANCHOS) {
  const ctx = await navegador.newContext({ viewport: { width: ancho, height: alto }, deviceScaleFactor: 2 })
  const pag = await ctx.newPage()
  pag.on('pageerror', (e) => { console.error(`  JS roto en ${nombre}: ${e.message}`); fallos++ })

  for (const [id, archivo] of PANTALLAS) {
    await pag.goto(`${pagina}#/${id}`, { waitUntil: 'networkidle' })
    await pag.evaluate(() => document.fonts.ready)
    await pag.waitForTimeout(1400) // que resuelvan los estados de carga y las animaciones
    const r = await pag.evaluate(MEDIR)
    resumen.push({ pantalla: id, ancho: nombre, textos: r.total, peor: r.minimo?.ratio, cual: r.minimo?.texto })
    if (r.fallos.length) {
      fallos += r.fallos.length
      console.error(`✗ ${id} @${ancho}px: ${r.fallos.length} por debajo de AA`)
      r.fallos.forEach((f) => console.error(`   ${f.ratio}:1 (mín ${f.minimo}) ${f.px}px «${f.texto}» ${f.color} sobre ${f.fondo}`))
    }
    await pag.screenshot({ path: `${salida}/direccion-2-${nombre}-${archivo}.png`, fullPage: true })
  }
  await ctx.close()
}

// Contacto: las cinco pantallas en una sola imagen por ancho.
for (const [nombre, ancho] of ANCHOS) {
  const ctx = await navegador.newContext({ viewport: { width: ancho, height: 900 }, deviceScaleFactor: 1 })
  const pag = await ctx.newPage()
  const filas = PANTALLAS.map(([id, archivo]) => `
    <figure><figcaption>${id.toUpperCase()} · ${ancho} px</figcaption>
    <img src="${pathToFileURL(`${salida}/direccion-2-${nombre}-${archivo}.png`).href}"></figure>`).join('')
  // Se escribe al lado de las capturas: una página about:blank no puede leer file://
  const contacto = `${salida}/.contacto-${nombre}.html`
  writeFileSync(contacto, `<meta charset="utf-8"><style>
    body{margin:0;background:#0F2A20;font:12px/1.4 ui-monospace,monospace}
    figure{margin:0}
    figcaption{color:#8FBFA6;letter-spacing:.16em;padding:10px 14px}
    img{display:block;width:${ancho}px}
  </style>${filas}`)
  await pag.goto(pathToFileURL(contacto).href, { waitUntil: 'networkidle' })
  await pag.waitForTimeout(400)
  await pag.screenshot({ path: `${salida}/direccion-2-${nombre}.png`, fullPage: true })
  rmSync(contacto)
  await ctx.close()
}

await navegador.close()
console.table(resumen)
if (fallos) { console.error(`\n${fallos} problemas.`); process.exit(1) }
console.log('\nTodo el texto pasa AA en las cinco pantallas, a 390 y a 1440.')
