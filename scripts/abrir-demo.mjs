// Abre el producto entero en un navegador de verdad, con las tres sesiones ya iniciadas.
//
// Tres ventanas y no una porque **la sesión de la clienta y la del salón viven en la misma
// clave** de almacenamiento del mismo origen: en una sola ventana, entrar en el panel te saca
// de la cuenta de clienta. La consola sí podría convivir —usa `sessionStorage` con otra clave—
// pero va aparte para que no se confunda con el panel de un salón.
//
//   node scripts/abrir-demo.mjs
//
// El proceso se queda vivo a propósito: al matarlo se cierra el navegador.

import { chromium } from 'playwright'
import { execSync } from 'node:child_process'

const WEB = process.env.BASE ?? 'http://127.0.0.1:3100'
const API = process.env.API ?? 'http://127.0.0.1:8000'

const CLIENTA = '+50761234567'
const DUENO = '+50760000001' // Barbería El Cangrejo

/** Pide el código y lo lee de la respuesta: en local el proveedor lo devuelve en claro. */
async function entrarConTelefono(pagina, telefono) {
  await pagina.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' })
  await pagina.fill('input[type="tel"]', telefono)
  await pagina.click('button[type="submit"]')
  await pagina.waitForSelector('input[inputmode="numeric"]', { timeout: 20000 })
  const pista = await pagina.locator('text=Tu código es').textContent()
  await pagina.fill('input[inputmode="numeric"]', pista.match(/(\d{6})/)[1])
  await pagina.click('button[type="submit"]')
  await pagina.waitForTimeout(3500)
}

const navegador = await chromium.launch({
  headless: false,
  args: ['--window-size=1440,960'],
})

// ── Ventana 1 · la clienta, con las pantallas públicas en pestañas
const clienta = await navegador.newContext({ viewport: null })
const entrada = await clienta.newPage()
await entrarConTelefono(entrada, CLIENTA)
console.log('1. clienta dentro →', entrada.url())

for (const ruta of ['/', '/buscar', '/spa-costa-del-este', '/como-funciona', '/para-negocios', '/mi/citas']) {
  const p = await clienta.newPage()
  await p.goto(`${WEB}${ruta}`, { waitUntil: 'domcontentloaded' })
}
await entrada.close()

// ── Ventana 2 · el salón
const salon = await navegador.newContext({ viewport: null })
const panel = await salon.newPage()
await entrarConTelefono(panel, DUENO)
console.log('2. salón dentro →', panel.url())
for (const ruta of ['/panel/servicios', '/panel/equipo', '/panel/horario', '/panel/clientes', '/panel/resenas', '/panel/ficha']) {
  const p = await salon.newPage()
  await p.goto(`${WEB}${ruta}`, { waitUntil: 'domcontentloaded' })
}

// ── Ventana 3 · la consola de M2G
const consola = await navegador.newContext({ viewport: null })
const c = await consola.newPage()
const codigo = execSync('./.venv/bin/python -m agenda.consola_codigo', { cwd: 'apps/api' })
  .toString()
  .match(/(\d{6})/)[1]
await c.goto(`${WEB}/consola`, { waitUntil: 'networkidle' })
await c.fill('input[type="email"]', 'consola@bukeo.local')
await c.fill('input[type="password"]', 'consola-de-demo-solo-en-local')
await c.fill('input[inputmode="numeric"]', codigo)
await c.click('button[type="submit"]')
await c.waitForTimeout(3000)
console.log('3. consola dentro →', c.url())
for (const ruta of ['/consola/moderacion', '/consola/metricas', '/consola/ranking']) {
  const p = await consola.newPage()
  await p.goto(`${WEB}${ruta}`, { waitUntil: 'domcontentloaded' })
}

console.log('\nTodo abierto. El navegador se cierra cuando pares este proceso.')
// Sin esto, Playwright cierra el navegador al terminar el script.
await new Promise(() => {})
