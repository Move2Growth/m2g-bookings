/**
 * Contraste de **lo que no es texto**: el anillo de foco y el texto al pasar por encima.
 *
 *   node verificacion/foco-y-hover.mjs
 *
 * Existe porque las tres direcciones de la ronda adversarial fallaron el mismo descarte por el
 * mismo punto ciego: los verificadores medían texto en reposo. El foco de teclado y el `hover`
 * son estados que nadie visitaba, y ahí estaban los tres fallos —1,04:1, 1,54:1 y un 1,00:1 con
 * la palabra literalmente invisible—.
 */
import { chromium } from 'playwright'

const BASE = process.env.BASE ?? 'http://localhost:3100'
const RUTAS = ['/', '/buscar?texto=corte', '/salon/barberia-el-cangrejo', '/salon/barberia-el-cangrejo/con/kevin-ortega', '/entrar', '/esta-ruta-no-existe']

const canal = (v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
const rgb = (c) => (c.match(/\d+(\.\d+)?/g) ?? []).slice(0, 3).map(Number)
const lum = (c) => { const [r, g, b] = rgb(c).map((v) => canal(v / 255)); return 0.2126 * r + 0.7152 * g + 0.0722 * b }
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return Math.floor(((x + 0.05) / (y + 0.05)) * 100) / 100 }

/** El fondo pintado de verdad: sube por los padres hasta encontrar uno que no sea transparente. */
const FONDO_REAL = `(el) => {
  let n = el
  while (n) {
    const c = getComputedStyle(n).backgroundColor
    if (c && !/rgba?\\([^)]*,\\s*0\\)/.test(c) && c !== 'transparent') return c
    n = n.parentElement
  }
  return 'rgb(255,255,255)'
}`

const nav = await chromium.launch()
const p = await (await nav.newContext({ viewport: { width: 390, height: 844 } })).newPage()
const fallos = []
let medidas = 0

for (const ruta of RUTAS) {
  await p.goto(BASE + ruta, { waitUntil: 'networkidle' })
  await p.waitForTimeout(700)

  // ── El anillo de foco, tabulando de verdad hasta dar la vuelta ──────────────────────────
  const vistos = new Set()
  for (let i = 0; i < 60; i++) {
    await p.keyboard.press('Tab')
    const dato = await p.evaluate(
      ([fondoReal]) => {
        const el = document.activeElement
        if (!el || el === document.body) return null
        const cs = getComputedStyle(el)
        if (cs.outlineStyle === 'none' || parseFloat(cs.outlineWidth) === 0) return null
        const fondo = new Function('return ' + fondoReal)()(el)
        // **El indicador puede tener más de un aro.** Aquí son dos —uno de tinta dentro y uno de
        // hueso fuera, hecho con `box-shadow`— justamente para que uno de los dos contraste
        // siempre, sobre papel o sobre tinta. Medir solo `outlineColor` daba por roto un
        // indicador que se ve perfectamente, así que se miran los dos y vale el mejor.
        const aros = [cs.outlineColor]
        for (const m of (cs.boxShadow || '').matchAll(/rgba?\([^)]*\)/g)) aros.push(m[0])
        return { clave: el.tagName + '.' + (el.className || '') + (el.textContent || '').slice(0, 20), aros, fondo }
      },
      [FONDO_REAL],
    )
    if (!dato) continue
    if (vistos.has(dato.clave)) break
    vistos.add(dato.clave)
    const r = Math.max(...dato.aros.map((a) => ratio(a, dato.fondo)))
    medidas++
    if (r < 3)
      fallos.push(
        `${ruta} · anillo de foco ${r}:1 en ${dato.clave.slice(0, 60)} (mejor de ${dato.aros.join(' / ')} sobre ${dato.fondo})`,
      )
  }

  // ── El texto al pasar por encima de cada enlace y cada botón ────────────────────────────
  const tocables = await p.locator('a, button').all()
  for (const t of tocables.slice(0, 40)) {
    if (!(await t.isVisible().catch(() => false))) continue
    await t.hover({ timeout: 1500 }).catch(() => {})
    await p.waitForTimeout(60)
    const dato = await t.evaluate(
      (el, fondoReal) => {
        const cs = getComputedStyle(el)
        if (!(el.textContent || '').trim()) return null
        return { texto: cs.color, fondo: new Function('return ' + fondoReal)()(el), rotulo: (el.textContent || '').trim().slice(0, 28), tam: parseFloat(cs.fontSize), peso: cs.fontWeight }
      },
      FONDO_REAL,
    ).catch(() => null)
    if (!dato) continue
    const grande = dato.tam >= 24 || (dato.tam >= 18.66 && Number(dato.peso) >= 700)
    const minimo = grande ? 3 : 4.5
    const r = ratio(dato.texto, dato.fondo)
    medidas++
    if (r < minimo) fallos.push(`${ruta} · «${dato.rotulo}» al pasar por encima: ${r}:1 (mín. ${minimo})`)
  }
}

await nav.close()
console.log(`${medidas} medidas de foco y de «encima» en ${RUTAS.length} pantallas`)
if (fallos.length) {
  console.error('\nPOR DEBAJO DEL MÍNIMO:')
  for (const f of fallos) console.error(' · ' + f)
  process.exit(1)
}
console.log('Ni el anillo de foco ni el texto al pasar por encima bajan del mínimo.')
