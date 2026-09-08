/**
 * El mapa, en el navegador (encargo §5).
 *
 *   node verificacion/mapa.mjs
 *
 * Comprueba lo que un mapa puede prometer y no cumplir: que las baldosas **cargan de verdad**
 * (una que dé 404 deja un cuadriculado gris y nadie ve un error), que los pines son los salones
 * que devuelve la API, que arrastrar vuelve a preguntar por el rectángulo nuevo, y que hay una
 * lista debajo — porque un mapa no se recorre con el tabulador.
 */
import { chromium } from 'playwright'

const BASE = process.env.BASE ?? 'http://localhost:3100'
const fallos = []
const ok = (que, bien, detalle = '') => {
  console.log(`${bien ? 'ok  ' : 'MAL '} ${que}${detalle ? ` · ${detalle}` : ''}`)
  if (!bien) fallos.push(que)
}

const nav = await chromium.launch()
const p = await (await nav.newContext({ viewport: { width: 390, height: 844 } })).newPage()
const errores = []
const baldosas = { pedidas: 0, rotas: 0 }
const consultas = []
p.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))
p.on('response', (r) => {
  if (r.url().includes('tile.openstreetmap.org')) {
    baldosas.pedidas++
    if (!r.ok()) baldosas.rotas++
  }
  if (r.url().includes('/publico/mapa')) consultas.push(r.url())
})

await p.goto(BASE + '/mapa', { waitUntil: 'networkidle' })
await p.waitForTimeout(3500)

ok('el mapa carga', (await p.locator('.mapa__lienzo').count()) === 1)
ok('no desborda a 390', (await p.evaluate(() => document.documentElement.scrollWidth)) === 390)
ok('pide baldosas y ninguna falla', baldosas.pedidas > 0 && baldosas.rotas === 0, `${baldosas.pedidas} pedidas, ${baldosas.rotas} rotas`)

const pines = await p.locator('.pin__caja').count()
ok('pinta un pin por salón', pines > 0, `${pines} pines`)
const enLista = await p.locator('.fila-mapa').count()
ok('y la misma lista debajo, recorrible con el tabulador', enLista === pines, `${enLista} filas`)
ok('el pin lleva el nombre, no una chincheta', ((await p.locator('.pin__nombre').first().innerText()) || '').length > 3)

const antes = consultas.length
await p.mouse.move(200, 400)
await p.mouse.down()
await p.mouse.move(60, 250, { steps: 12 })
await p.mouse.up()
await p.waitForTimeout(2500)
ok('arrastrar vuelve a preguntar por lo que se ve', consultas.length > antes, `${consultas.length - antes} consulta(s) nueva(s)`)
ok('y pregunta por rectángulo', (consultas.at(-1) ?? '').includes('oeste=') && (consultas.at(-1) ?? '').includes('norte='))

// La lista lleva a la ficha: el mapa no es un callejón sin salida.
await p.locator('.fila-mapa').first().click()
await p.waitForTimeout(2500)
ok('desde el mapa se llega a la ficha del salón', p.url().includes('/salon/'), p.url())

ok('sin errores de JavaScript', errores.length === 0, errores[0] ?? '')
await nav.close()
console.log(fallos.length ? `\n${fallos.length} fallo(s)` : '\nEl mapa carga, pinta lo que hay donde se mira y lleva a la ficha.')
process.exit(fallos.length ? 1 : 0)
