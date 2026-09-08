/**
 * La consola interna de M2G, a clics.
 *
 *   node verificacion/consola.mjs
 *
 * Lo que hay que comprobar aquí antes que nada es **que está separada**: que sin entrar no
 * enseña nada, que la sesión de una clienta no vale, y que su sesión vive en otra llave y muere
 * al cerrar la pestaña. Después, que las tres pantallas hacen lo que dicen — incluido suspender
 * un salón de verdad y devolverlo.
 */
import { createHmac } from 'node:crypto'
import { chromium } from 'playwright'

const BASE = process.env.BASE ?? 'http://localhost:3100'
const API = process.env.API ?? 'http://localhost:8000'
const fallos = []
const ok = (que, bien, detalle = '') => {
  console.log(`${bien ? 'ok  ' : 'MAL '} ${que}${detalle ? ` · ${detalle}` : ''}`)
  if (!bien) fallos.push(que)
}

/** El segundo factor de la cuenta de demo. Su secreto vive en la semilla y solo en local. */
const SECRETO = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'
const base32 = (s) => {
  const abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  let bits = ''
  for (const c of s) bits += abc.indexOf(c).toString(2).padStart(5, '0')
  const bytes = []
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2))
  return Buffer.from(bytes)
}
const codigo2fa = () => {
  const contador = Math.floor(Date.now() / 1000 / 30)
  const m = Buffer.alloc(8)
  m.writeUInt32BE(Math.floor(contador / 2 ** 32), 0)
  m.writeUInt32BE(contador >>> 0, 4)
  const d = createHmac('sha1', base32(SECRETO)).update(m).digest()
  const i = d[19] & 0xf
  return String((d.readUInt32BE(i) & 0x7fffffff) % 1e6).padStart(6, '0')
}

const nav = await chromium.launch()
const p = await (await nav.newContext({ viewport: { width: 390, height: 844 } })).newPage()
const errores = []
p.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))

/* Sin entrar */
await p.goto(BASE + '/consola', { waitUntil: 'networkidle' })
await p.waitForTimeout(1500)
ok('sin entrar no enseña nada', (await p.locator('.cifras-grandes__valor').count()) === 0)
ok('y pide el segundo factor', (await p.locator('#codigo').count()) === 1)
ok('dice que no es la cuenta de reservar', (await p.locator('main').innerText()).includes('No es la cuenta'))

/* La sesión de una clienta no vale */
const clienta = await (
  await fetch(`${API}/api/v1/auth/entrar`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ correo: 'abdiel@demo.pa', contrasena: 'demo-panama-2026', superficie: 'web' }),
  })
).json()
await p.evaluate(
  ([c]) => localStorage.setItem('agenda.sesion', JSON.stringify({ acceso: c.acceso, refresco: c.refresco, usuarioId: c.usuario_id, negocioActivo: null })),
  [clienta],
)
await p.reload({ waitUntil: 'networkidle' })
await p.waitForTimeout(1500)
ok('la sesión de una clienta no abre la consola', (await p.locator('#codigo').count()) === 1)

/* Entrar de verdad */
await p.fill('#email', 'consola@bukeo.local')
await p.fill('#password', 'consola-de-demo-solo-en-local')
await p.fill('#codigo', codigo2fa())
await p.getByRole('button', { name: /Entrar en la consola/i }).click()
await p.waitForTimeout(3000)
ok('con las tres credenciales entra', (await p.locator('.cifras-grandes__valor').count()) >= 4)
ok('no desborda a 390', (await p.evaluate(() => document.documentElement.scrollWidth)) === 390)

const donde = await p.evaluate(() => ({
  sesion: window.sessionStorage.getItem('agenda.consola') !== null,
  local: window.localStorage.getItem('agenda.consola') !== null,
}))
ok('su sesión vive en la pestaña, no en el disco', donde.sesion && !donde.local)

/* Salones: suspender y devolver */
await p.getByRole('link', { name: 'Salones' }).click()
await p.waitForTimeout(2500)
await p.fill('input[aria-label="Buscar un salón"]', 'maquillaje')
await p.getByRole('button', { name: /^Buscar$/ }).click()
await p.waitForTimeout(2500)
const encontrados = await p.locator('.ficha-persona').count()
ok('busca salones por nombre', encontrados > 0, `${encontrados} encontrados`)

const motivo = 'Prueba de la consola'
await p.locator('.ficha-persona').first().locator('input').fill(motivo)
await p.getByRole('button', { name: /^Suspender$/ }).first().click()
await p.waitForTimeout(3000)
const publica = await fetch(`${API}/api/v1/publico/negocios/maquillaje-por-karla`)
ok('suspender lo saca del marketplace de verdad', publica.status === 404, `ficha pública ${publica.status}`)
ok('y la consola dice por qué', (await p.locator('.ficha-persona').first().innerText()).includes(motivo))

await p.getByRole('button', { name: /^Reactivar$/ }).first().click()
await p.waitForTimeout(3000)
const vuelta = await fetch(`${API}/api/v1/publico/negocios/maquillaje-por-karla`)
ok('reactivar lo devuelve', vuelta.status === 200, `ficha pública ${vuelta.status}`)

/* Moderación */
await p.getByRole('link', { name: 'Moderación' }).click()
await p.waitForTimeout(2500)
const texto = await p.locator('main').innerText()
ok('la moderación enseña sus dos colas', texto.includes('Reseñas reportadas') && texto.includes('Fotos por revisar'))

/* Salir */
await p.locator('.nav-local__sitio', { hasText: 'Salir' }).click()
await p.waitForTimeout(2000)
ok('salir cierra la consola', (await p.evaluate(() => window.sessionStorage.getItem('agenda.consola'))) === null)

ok('sin errores de JavaScript', errores.length === 0, errores[0] ?? '')
await nav.close()
console.log(fallos.length ? `\n${fallos.length} fallo(s)` : '\nLa consola está separada, entra con sus tres credenciales y lo que hace se nota fuera.')
process.exit(fallos.length ? 1 : 0)
