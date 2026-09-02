// Contraste medido en las páginas de verdad, no en la paleta.
//
// Existe porque el verificador de `packages/tokens` comprueba **pares de tokens** y esto se
// rompió igual: la regla «el naranja nunca es color de texto» estaba escrita en el brandbook, en
// el ADR-0016 y hasta en un comentario del propio verificador explicando por qué no se
// comprobaba. Y estaba rota en cuatro pantallas a 2,34:1.
//
// La lección es que una regla sobre **cómo se usa** un color no la puede guardar un verificador
// que solo mira la paleta. Hace falta mirar los píxeles.
//
//   node scripts/verificar-contraste-en-pantalla.mjs
//
// Sale con error si hay algo por debajo de AA, para poder colgarlo de una comprobación.

import { chromium } from 'playwright'

const WEB = process.env.BASE ?? 'http://127.0.0.1:3100'
const RUTAS = [
  '/',
  '/buscar',
  '/como-funciona',
  '/para-negocios',
  '/spa-costa-del-este',
  '/entrar',
  '/legal/privacidad',
]
const ANCHOS = [390, 1440]

/** Se ejecuta dentro del navegador: necesita el color ya calculado, no el declarado. */
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
  // El fondo de verdad es el del primer antepasado que tenga uno: un elemento transparente
  // sobre un bloque azul se lee sobre azul, no sobre blanco.
  const fondoReal = (e) => {
    let n = e
    while (n && n !== document.documentElement) {
      const c = getComputedStyle(n).backgroundColor
      if (c && c !== 'rgba(0, 0, 0, 0)') return c
      n = n.parentElement
    }
    return 'rgb(255, 255, 255)'
  }

  const fallos = []
  for (const e of document.querySelectorAll('body *')) {
    if (!e.textContent?.trim() || e.children.length > 0) continue
    const c = getComputedStyle(e)
    if (c.visibility === 'hidden' || c.display === 'none' || c.opacity === '0') continue
    const px = parseFloat(c.fontSize)
    // AA pide 3:1 para texto grande y 4,5:1 para el resto.
    const grande = px >= 24 || (px >= 18.66 && parseInt(c.fontWeight, 10) >= 700)
    const minimo = grande ? 3 : 4.5
    const ratio = contraste(c.color, fondoReal(e))
    if (ratio < minimo) {
      fallos.push({
        texto: e.textContent.trim().slice(0, 40),
        ratio: +ratio.toFixed(2),
        minimo,
        px: Math.round(px),
        color: c.color,
        fondo: fondoReal(e),
        clase: e.className?.toString().slice(0, 40) ?? '',
      })
    }
  }
  return fallos
})()`

const navegador = await chromium.launch()
let total = 0

for (const ancho of ANCHOS) {
  const pagina = await navegador.newPage({ viewportSize: { width: ancho, height: 900 } })
  for (const ruta of RUTAS) {
    await pagina.goto(`${WEB}${ruta}`, { waitUntil: 'networkidle' })
    await pagina.waitForTimeout(600)
    const fallos = await pagina.evaluate(MEDIR)
    total += fallos.length
    const marca = fallos.length === 0 ? 'ok  ' : 'MAL '
    console.log(`${marca}${String(ancho).padStart(4)} px  ${ruta.padEnd(22)} ${fallos.length}`)
    for (const f of fallos) {
      console.log(
        `        ${f.ratio}:1 (mín. ${f.minimo})  ${f.px}px  «${f.texto}»  ${f.color} sobre ${f.fondo}  .${f.clase}`,
      )
    }
  }
  await pagina.close()
}

await navegador.close()

if (total > 0) {
  console.error(`\n${total} textos por debajo de AA en las páginas. Arréglalos.`)
  process.exit(1)
}
console.log(`\nNada por debajo de AA en ${RUTAS.length} páginas y ${ANCHOS.length} anchos.`)
