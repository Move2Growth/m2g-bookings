/**
 * El portal del profesional: su día y su ficha (encargo §6, la otra mitad).
 *
 *   node verificacion/portal-del-profesional.mjs
 *
 * Lo que de verdad hay que comprobar aquí no es que las dos pantallas carguen: es **que son
 * distintas de las del dueño**. Un profesional no puede ver el dinero del salón, ni el equipo,
 * ni la publicidad, y su navegación tiene dos puertas y no seis. Si tuviera seis y cuatro
 * dieran error, la zona sería una promesa incumplida.
 */
import { chromium } from 'playwright'

const BASE = process.env.BASE ?? 'http://localhost:3100'
const API = process.env.API ?? 'http://localhost:8000'
const fallos = []
const ok = (que, bien, detalle = '') => {
  console.log(`${bien ? 'ok  ' : 'MAL '} ${que}${detalle ? ` · ${detalle}` : ''}`)
  if (!bien) fallos.push(que)
}

async function sesionDe(correo) {
  const cred = await (
    await fetch(`${API}/api/v1/auth/entrar`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ correo, contrasena: 'demo-panama-2026', superficie: 'web' }),
    })
  ).json()
  const negocios = await (await fetch(`${API}/api/v1/mi/negocios`, { headers: { authorization: `Bearer ${cred.acceso}` } })).json()
  const enModo = await (
    await fetch(`${API}/api/v1/auth/modo-negocio`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${cred.acceso}` },
      body: JSON.stringify({ negocio_id: negocios[0].id, superficie: 'web' }),
    })
  ).json()
  return { acceso: enModo.acceso, refresco: enModo.refresco, usuarioId: enModo.usuario_id, negocioActivo: enModo.negocio_activo }
}

const nav = await chromium.launch()
const p = await (await nav.newContext({ viewport: { width: 390, height: 844 } })).newPage()
const errores = []
p.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))

await p.goto(BASE + '/')
await p.evaluate(([s]) => localStorage.setItem('agenda.sesion', JSON.stringify(s)), [await sesionDe('pro.barberia-el-cangrejo@demo.pa')])

/* Su día */
await p.goto(BASE + '/mi-agenda', { waitUntil: 'networkidle' })
await p.waitForTimeout(2500)
ok('su día carga', (await p.locator('h1').first().innerText()).includes('Mi día'))
ok('no desborda a 390', (await p.evaluate(() => document.documentElement.scrollWidth)) === 390)
ok('la navegación tiene dos puertas, no seis', (await p.locator('.nav-local__sitio').count()) === 2)
ok('enseña las dos cifras del día', (await p.locator('.cifras-grandes__valor').count()) === 2)

// Se busca un día con citas: hoy puede estar vacío y eso no prueba nada.
let citas = await p.locator('.cita-mia').count()
for (let i = 0; i < 4 && citas === 0; i++) {
  await p.getByRole('button', { name: /Mañana/i }).click()
  await p.waitForTimeout(2000)
  citas = await p.locator('.cita-mia').count()
}
ok('lista sus citas con hora, clienta y servicio', citas > 0, `${citas} citas`)
if (citas > 0) {
  const primera = await p.locator('.cita-mia').first().innerText()
  ok('cada cita dice a quién atiende', primera.split('\n').length >= 3, primera.replace(/\n/g, ' · ').slice(0, 80))
  ok('y ofrece llamarla', (await p.locator('.cita-mia a[href^="tel:"]').count()) > 0)
}

/* Su ficha */
await p.getByRole('link', { name: 'Mi ficha' }).click()
await p.waitForTimeout(2500)
ok('su ficha carga', (await p.locator('h1').first().innerText()).includes('Mi ficha'))
ok('enseña cuánta gente ha atendido', (await p.locator('.cifras-grandes__valor').count()) === 2)
const nuevoTitular = `Barbero. Prueba ${Date.now()}`
await p.fill('#titular', nuevoTitular)
await p.getByRole('button', { name: /Guardar mi ficha/i }).click()
await p.waitForTimeout(2500)
ok('lo que escribe se guarda', (await p.locator('[role="status"]').count()) > 0)
const publico = await (await fetch(`${API}/api/v1/publico/negocios/barberia-el-cangrejo/profesionales/kevin-ortega`)).json()
ok('y sale en su ficha pública', publico.titular === nuevoTitular, publico.titular)

/* Lo que NO puede */
for (const prohibida of ['/local/finanzas', '/local/equipo', '/local/publicidad']) {
  await p.goto(BASE + prohibida, { waitUntil: 'networkidle' })
  await p.waitForTimeout(2200)
  const cifras = await p.locator('.cifras-grandes__valor').count()
  const fichas = await p.locator('.ficha-persona').count()
  const anuncios = await p.locator('.anuncio').count()
  ok(`un profesional no entra en ${prohibida}`, cifras === 0 && fichas === 0 && anuncios === 0)
}

ok('sin errores de JavaScript', errores.length === 0, errores[0] ?? '')
await nav.close()
console.log(fallos.length ? `\n${fallos.length} fallo(s)` : '\nEl profesional tiene su día y su ficha, y nada del salón que no le toca.')
process.exit(fallos.length ? 1 : 0)
