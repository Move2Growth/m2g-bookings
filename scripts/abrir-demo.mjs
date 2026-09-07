// Abre el producto para mirarlo: **tres pestañas en una sola ventana**, ni una más.
//
//   1. La vista de la clienta, con la sesión ya iniciada.
//   2. La pública, tal cual la ve alguien que llega de Google.
//   3. La consola interna de M2G, con su segundo factor ya pasado.
//
// Las tres caben en un mismo contexto porque la sesión de la clienta vive en `localStorage` y la
// de la consola en `sessionStorage` con otra clave: no se pisan. La del salón sí pisaría a la de
// la clienta, y por eso no está aquí.
//
// Se entra con correo y contraseña: `abdiel@demo.pa` y la contraseña de la semilla. Las
// credenciales de todas las cuentas de ejemplo están en docs/operacion/CREDENCIALES-DE-DEMO.md.
//
//   node scripts/abrir-demo.mjs
//
// El proceso se queda vivo a propósito: al pararlo se cierra el navegador.

import { createHmac } from 'node:crypto'
import { chromium } from 'playwright'

//: La cuenta de consola de la semilla, solo en local. El código del segundo factor se calcula
//: aquí en vez de llamar a Python: una dependencia menos y un fallo menos.
const CONSOLA_2FA = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'

/** TOTP a mano: base32 a bytes, contador de 30 s, HMAC-SHA1 y truncado dinámico. */
function base32aBytes(texto) {
  const alfabeto = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  let bits = ''
  for (const letra of texto.replace(/=+$/, '')) {
    bits += alfabeto.indexOf(letra.toUpperCase()).toString(2).padStart(5, '0')
  }
  const bytes = []
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2))
  return Buffer.from(bytes)
}

function codigoDeDosFactores(secreto) {
  const contador = Math.floor(Date.now() / 1000 / 30)
  const mensaje = Buffer.alloc(8)
  mensaje.writeUInt32BE(Math.floor(contador / 2 ** 32), 0)
  mensaje.writeUInt32BE(contador >>> 0, 4)
  const resumen = createHmac('sha1', base32aBytes(secreto)).update(mensaje).digest()
  const desde = resumen[19] & 0xf
  return String((resumen.readUInt32BE(desde) & 0x7fffffff) % 1e6).padStart(6, '0')
}

const WEB = process.env.BASE ?? 'http://127.0.0.1:3100'
const CLIENTA = process.env.CORREO_CLIENTA ?? 'abdiel@demo.pa'
const CLAVE = process.env.CONTRASENA_DEMO ?? 'demo-panama-2026'

const navegador = await chromium.launch({ headless: false, args: ['--window-size=1512,950'] })
const contexto = await navegador.newContext({ viewport: null })

// ── 1 · La clienta
const clienta = await contexto.newPage()
await clienta.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' })
await clienta.fill('#correo', CLIENTA)
await clienta.fill('#contrasena', CLAVE)
await clienta.click('button[type="submit"]')
await clienta.waitForURL('**/mi/**', { timeout: 20000 })
console.log('1 · clienta →', clienta.url())

// ── 2 · La pública
const publica = await contexto.newPage()
await publica.goto(`${WEB}/`, { waitUntil: 'domcontentloaded' })
console.log('2 · pública →', publica.url())

// ── 3 · La consola de M2G
const consola = await contexto.newPage()
const codigo = codigoDeDosFactores(CONSOLA_2FA)
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
