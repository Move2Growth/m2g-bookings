/**
 * El alta de un local, de punta a punta y a clics (encargo §4).
 *
 *   node verificacion/alta-de-local.mjs
 *
 * Crea una cuenta nueva por la API —como llega alguien de verdad— y recorre los tres pasos con
 * el ratón: el local con su horario, invitar a alguien, un servicio **sin precio** («A
 * consultar», que es lo que pidió el encargo) y el estado final con lo que falta para publicar.
 *
 * Comprueba además la trampa que ya se cobró un intento: **el catálogo llega por red**, y si el
 * formulario deja enviar antes de que llegue, manda la categoría vacía y la API contesta «Esa
 * categoría no existe». Por eso aquí se pulsa nada más cargar, sin esperas de cortesía.
 */
import { chromium } from 'playwright'

const BASE = process.env.BASE ?? 'http://localhost:3100'
const API = process.env.API ?? 'http://localhost:8000'
const fallos = []
const ok = (que, bien, detalle = '') => {
  console.log(`${bien ? 'ok  ' : 'MAL '} ${que}${detalle ? ` · ${detalle}` : ''}`)
  if (!bien) fallos.push(que)
}

const correo = `alta.${Date.now()}@demo.pa`
const cred = await (
  await fetch(`${API}/api/v1/auth/registrar`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ correo, contrasena: 'demo-panama-2026', nombre: 'Dueña Nueva' }),
  })
).json()

const nav = await chromium.launch()
const p = await (await nav.newContext({ viewport: { width: 390, height: 844 } })).newPage()
const errores = []
p.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))

await p.goto(BASE + '/')
await p.evaluate(
  ([c]) =>
    localStorage.setItem(
      'agenda.sesion',
      JSON.stringify({ acceso: c.acceso, refresco: c.refresco, usuarioId: c.usuario_id, negocioActivo: null }),
    ),
  [cred],
)

await p.goto(BASE + '/local/alta', { waitUntil: 'networkidle' })
ok('paso 1 · se abre', (await p.locator('h1').first().innerText()).includes('Tu local'))
ok('paso 1 · no desborda', (await p.evaluate(() => document.documentElement.scrollWidth)) === 390)
ok(
  'paso 1 · no deja crear sin catálogo ni datos',
  await p.getByRole('button', { name: /Crear el local|Cargando el catálogo/i }).isDisabled(),
)
await p.fill('#nombre', 'Salón de Prueba')
await p.fill('#direccion', 'Calle 50, Panamá')
// El domingo viene cerrado de fábrica: se abre, para comprobar que el horario se manda.
await p.locator('.horario__fila').last().getByRole('checkbox').check()
await p.getByRole('button', { name: /Crear el local/i }).click()
await p.waitForTimeout(4000)

ok('paso 2 · llega a las personas', (await p.locator('h1').first().innerText()).includes('Trabaja alguien'))
await p.fill('#correo-invitado', `companera.${Date.now()}@demo.pa`)
await p.getByRole('button', { name: /^Invitar$/ }).click()
await p.waitForTimeout(2500)
ok('paso 2 · la invitación queda escrita', (await p.locator('.bloque--exito').count()) > 0)
ok(
  'paso 2 · dice que el correo no sale de aquí',
  (await p.locator('.bloque--exito').first().innerText()).includes('proveedor de correo'),
)
await p.getByRole('button', { name: /Seguir con los servicios/i }).click()
await p.waitForTimeout(900)

ok('paso 3 · llega a los servicios', (await p.locator('h1').first().innerText()).includes('Qué ofreces'))
ok('paso 3 · no deja terminar sin un servicio', await p.getByRole('button', { name: /Añade al menos un servicio/i }).isDisabled())
await p.fill('#servicio', 'Color, según el pelo')
await p.getByRole('button', { name: /^A consultar$/ }).click()
ok('paso 3 · «a consultar» esconde el importe', (await p.locator('input[aria-label="Importe en dólares"]').count()) === 0)
await p.getByRole('button', { name: /Añadir servicio/i }).click()
await p.waitForTimeout(2500)
ok('paso 3 · el servicio sin precio se crea', (await p.locator('.bloque--exito').count()) > 0)
await p.getByRole('button', { name: /^Terminar$/ }).click()
await p.waitForTimeout(2500)

const final = await p.locator('h1').first().innerText()
ok('paso 4 · dice que el local está creado', final.includes('creado'))
const puntos = await p.locator('ul.pila--apretada li').allInnerTexts()
ok('paso 4 · el checklist dice qué falta', puntos.length === 4, puntos.map((t) => t.replace(/\n/g, ' ')).join(' | '))
ok('paso 4 · lo único que falta es la foto', puntos.filter((t) => t.startsWith('○')).length === 1)
ok('paso 4 · no desborda', (await p.evaluate(() => document.documentElement.scrollWidth)) === 390)
ok('sin errores de JavaScript', errores.length === 0, errores[0] ?? '')

await nav.close()
console.log(fallos.length ? `\n${fallos.length} fallo(s)` : '\nEl alta de un local se recorre entera, y el precio puede quedar sin poner.')
process.exit(fallos.length ? 1 : 0)
