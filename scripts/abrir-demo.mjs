// Abre el producto para mirarlo: **tres pestañas en una sola ventana**, ni una más.
//
//   1. La vista de la clienta, con la sesión ya iniciada.
//   2. La pública, tal cual la ve alguien que llega de Google.
//   3. La consola interna de M2G, con su segundo factor ya pasado.
//
// Las tres caben en un mismo contexto porque la sesión de la clienta vive en `localStorage` y la
// de la consola en `sessionStorage` con otra clave: no se pisan. La del salón sí pisaría a la de
// la clienta, y por eso no está aquí; para verla, `TELEFONO_SALON=... node scripts/abrir-panel.mjs`.
//
//   node scripts/abrir-demo.mjs
//
// El proceso se queda vivo a propósito: al pararlo se cierra el navegador.

import { execSync } from 'node:child_process'
import { chromium } from 'playwright'

const WEB = process.env.BASE ?? 'http://127.0.0.1:3100'
const CLIENTA = process.env.TELEFONO_CLIENTA ?? '+50761234567'

const navegador = await chromium.launch({ headless: false, args: ['--window-size=1512,950'] })
const contexto = await navegador.newContext({ viewport: null })

// ── 1 · La clienta
const clienta = await contexto.newPage()
await clienta.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' })
await clienta.fill('input[type="tel"]', CLIENTA)
await clienta.click('button[type="submit"]')
await clienta.waitForSelector('input[inputmode="numeric"]', { timeout: 20000 })
const pista = await clienta.locator('text=Tu código es').textContent()
await clienta.fill('input[inputmode="numeric"]', pista.match(/(\d{6})/)[1])
await clienta.click('button[type="submit"]')
await clienta.waitForURL('**/mi/**', { timeout: 20000 })
console.log('1 · clienta →', clienta.url())

// ── 2 · La pública
const publica = await contexto.newPage()
await publica.goto(`${WEB}/`, { waitUntil: 'domcontentloaded' })
console.log('2 · pública →', publica.url())

// ── 3 · La consola de M2G
const consola = await contexto.newPage()
const codigo = execSync('./.venv/bin/python -m agenda.consola_codigo', { cwd: 'apps/api' })
  .toString()
  .match(/(\d{6})/)[1]
await consola.goto(`${WEB}/consola`, { waitUntil: 'networkidle' })
await consola.fill('input[type="email"]', 'consola@bukeo.local')
await consola.fill('input[type="password"]', 'consola-de-demo-solo-en-local')
await consola.fill('input[inputmode="numeric"]', codigo)
await consola.click('button[type="submit"]')
await consola.waitForURL('**/consola/**', { timeout: 20000 })
console.log('3 · consola →', consola.url())

// Se deja delante la de la clienta, que es por donde se empieza a mirar.
await clienta.bringToFront()
console.log('\nTres pestañas abiertas. El navegador se cierra al parar este proceso.')
await new Promise(() => {})
