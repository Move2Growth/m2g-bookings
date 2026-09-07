/**
 * Convierte el HTML de un brandbook en PDF apaisado.
 *
 *   node pipeline/libro.mjs direcciones/a-lo-que-sea/libro.html salida/Nombre_BrandBook.pdf
 *
 * El HTML se escribe con una página por `<section class="pagina">` de 297×210 mm exactos. Aquí
 * no se maqueta nada: esto solo imprime y **comprueba**. Y comprueba dos cosas que se pasan por
 * alto y arruinan un libro entero:
 *
 * · Que ninguna página se desborde. Una caja 3 mm más alta de la cuenta parte el libro en dos y
 *   el PDF sale con el doble de páginas sin avisar de nada.
 * · Que las tipografías declaradas sean las que de verdad se están pintando. Si falta un .woff2,
 *   el navegador cae a la de sistema en silencio y el PDF sale correcto y equivocado.
 */
import { chromium } from 'playwright'
import path from 'node:path'
import { mkdir } from 'node:fs/promises'
import { pathToFileURL } from 'node:url'

const [entrada, salida] = process.argv.slice(2)
if (!entrada || !salida) {
  console.error('uso: node pipeline/libro.mjs <libro.html> <salida.pdf>')
  process.exit(1)
}

const ANCHO = 1122.5 // 297 mm a 96 ppp
const ALTO = 793.7 //  210 mm

const navegador = await chromium.launch()
const pagina = await navegador.newPage({ viewport: { width: Math.round(ANCHO), height: Math.round(ALTO) } })

const fallos = []
pagina.on('pageerror', (e) => fallos.push(`error de JS: ${e.message}`))
pagina.on('requestfailed', (p) => fallos.push(`no cargó: ${p.url()}`))

await pagina.goto(pathToFileURL(path.resolve(entrada)).href, { waitUntil: 'networkidle' })
await pagina.evaluate(() => document.fonts.ready)

const revision = await pagina.evaluate(
  ({ ANCHO, ALTO }) => {
    const paginas = [...document.querySelectorAll('.pagina')]
    const desbordadas = paginas.flatMap((p, i) => {
      const r = p.getBoundingClientRect()
      // scrollHeight/Width delatan el desbordamiento aunque haya overflow:hidden encima.
      const alto = Math.max(p.scrollHeight, Math.round(r.height))
      const ancho = Math.max(p.scrollWidth, Math.round(r.width))
      return alto > ALTO + 1 || ancho > ANCHO + 1
        ? [`página ${i + 1}: ${ancho}×${alto} px, y la caja es ${Math.round(ANCHO)}×${Math.round(ALTO)}`]
        : []
    })

    // Las familias que el CSS declara, contra las que el navegador dice tener cargadas.
    const cargadas = new Set([...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family.replace(/["']/g, '')))
    const declaradas = new Set()
    for (const hoja of document.styleSheets) {
      let reglas
      try { reglas = hoja.cssRules } catch { continue }
      for (const regla of reglas ?? []) {
        if (regla.constructor.name === 'CSSFontFaceRule') declaradas.add(regla.style.fontFamily.replace(/["']/g, ''))
      }
    }
    const ausentes = [...declaradas].filter((f) => !cargadas.has(f))
    return { paginas: paginas.length, desbordadas, ausentes, familias: [...cargadas] }
  },
  { ANCHO, ALTO },
)

if (revision.paginas === 0) fallos.push('el HTML no tiene ninguna .pagina')
fallos.push(...revision.desbordadas)
if (revision.ausentes.length) fallos.push(`tipografías declaradas que no cargaron: ${revision.ausentes.join(', ')}`)

await mkdir(path.dirname(path.resolve(salida)), { recursive: true })
await pagina.pdf({
  path: path.resolve(salida),
  width: `${ANCHO}px`,
  height: `${ALTO}px`,
  printBackground: true,
  margin: { top: 0, right: 0, bottom: 0, left: 0 },
})
await navegador.close()

console.log(`${revision.paginas} páginas · tipografías: ${revision.familias.join(', ') || 'ninguna'}`)
if (fallos.length) {
  console.error('\nEL LIBRO NO PASA:')
  for (const f of fallos) console.error(` · ${f}`)
  process.exit(1)
}
console.log(`PDF en ${salida}`)
