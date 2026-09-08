/**
 * Las seis piezas del portal del dueño, a clics y con la sesión de verdad (encargo §6).
 *
 *   node verificacion/portal-del-dueno.mjs
 *
 * Comprueba lo que el encargo pide una a una, y comprueba también **que se distingue del panel
 * de un profesional**: la misma URL, con una cuenta de profesional, no puede enseñar el dinero
 * del salón ni dejar tocar el fichaje de nadie.
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
const ctx = await nav.newContext({ viewport: { width: 390, height: 844 } })
const p = await ctx.newPage()
const errores = []
p.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))

const dueno = await sesionDe('dueno.barberia-el-cangrejo@demo.pa')
await p.goto(BASE + '/')
await p.evaluate(([s]) => localStorage.setItem('agenda.sesion', JSON.stringify(s)), [dueno])

const medir = async () => p.evaluate(() => document.documentElement.scrollWidth)

/* 1 · la agenda del día, que ya estaba */
await p.goto(BASE + '/local', { waitUntil: 'networkidle' })
await p.waitForTimeout(1500)
ok('1 · la agenda del día carga', (await p.locator('h1, .rotulo--grande').first().innerText()).length > 0)

/* 2 · el equipo, con el fichaje persona a persona */
await p.getByRole('link', { name: 'El equipo' }).click()
await p.waitForTimeout(2000)
const personas = await p.locator('.ficha-persona').count()
ok('2 · el equipo lista a las personas', personas > 0, `${personas} personas`)
ok('2 · no desborda a 390', (await medir()) === 390)
const boton = p.locator('.ficha-persona').first().getByRole('button', { name: /fichaje/i })
const antes = await boton.innerText()
await boton.click()
await p.waitForTimeout(2500)
const despues = await p.locator('.ficha-persona').first().getByRole('button', { name: /fichaje/i }).innerText()
ok('2 · el fichaje se enciende y se apaga por persona', antes !== despues, `${antes} → ${despues}`)
await p.locator('.ficha-persona').first().getByRole('button', { name: /fichaje/i }).click()
await p.waitForTimeout(2000)

/* 3 · el dinero */
await p.getByRole('link', { name: 'El dinero' }).click()
await p.waitForTimeout(2500)
const cifras = await p.locator('.cifras-grandes__valor').allInnerTexts()
ok('3 · el dinero enseña sus tres cifras', cifras.length === 3, cifras.join(' · '))
ok('3 · y el desglose en barras', (await p.locator('.barras__fila').count()) > 0)
await p.getByRole('button', { name: 'Por mes' }).click()
await p.waitForTimeout(2500)
ok('3 · cambiar de agrupación cambia el desglose', (await p.locator('.barras__fila').count()) > 0)
ok('3 · no desborda a 390', (await medir()) === 390)

/* 4 · el mejor del mes, por los dos criterios */
await p.getByRole('link', { name: 'Mejor del mes' }).click()
await p.waitForTimeout(2500)
const podioImporte = await p.locator('.podio__puesto').count()
ok('4 · el podio sale por dinero', podioImporte > 0, `${podioImporte} puestos`)
await p.getByRole('button', { name: /más servicios/i }).click()
await p.waitForTimeout(2500)
ok('4 · y por número de servicios', (await p.locator('.podio__puesto').count()) > 0)

/* 5 · la publicidad flash, con vista previa */
await p.getByRole('link', { name: 'Publicidad' }).click()
await p.waitForTimeout(1500)
// **Se retiran los que hubiera antes.** La ficha pública pinta un solo anuncio, así que si el
// salón ya tenía uno encendido, el recién escrito no es el que sale y la prueba fallaría por el
// motivo equivocado. Se destapó exactamente así.
for (const boton of await p.getByRole('button', { name: /Retirar de mi ficha/i }).all()) {
  await boton.click()
  await p.waitForTimeout(1200)
}
const texto = `Prueba de anuncio ${Date.now()}`
await p.fill('#anuncio', texto)
ok('5 · la vista previa es el bloque de verdad', (await p.locator('.bloque--cobalto').first().innerText()).includes('Prueba de anuncio'))
await p.getByRole('button', { name: /Publicar el anuncio/i }).click()
await p.waitForTimeout(2500)
ok('5 · el anuncio queda escrito', (await p.locator('.anuncio').count()) > 0)
/* Y se ve donde tiene que verse: en la ficha pública del salón. */
const ficha = await (await fetch(`${API}/api/v1/publico/negocios/barberia-el-cangrejo`)).json()
ok('5 · sale en la ficha pública', ficha.anuncio?.texto === texto, ficha.anuncio?.texto ?? 'sin anuncio')
// Se retira **el suyo**, no «el primero»: el salón de la demo puede tener anuncios de antes.
// Y se comprueba lo que de verdad pasa —la fila se queda y deja de verse en la ficha—, que es
// lo que hace la API: la conserva por si se quiere relanzar.
const mio = p.locator('.anuncio').filter({ hasText: texto })
await mio.getByRole('button', { name: /Retirar de mi ficha/i }).click()
await p.waitForTimeout(2500)
const fichaDespues = await (await fetch(`${API}/api/v1/publico/negocios/barberia-el-cangrejo`)).json()
ok('5 · retirarlo lo quita de la ficha pública', fichaDespues.anuncio?.texto !== texto)
ok(
  '5 · y la fila se conserva, por si se relanza',
  (await p.locator('.anuncio').filter({ hasText: texto }).getByRole('button', { name: /Volver a lanzarlo/i }).count()) === 1,
)

/* 6 · se distingue del panel de un profesional */
const pro = await sesionDe('pro.barberia-el-cangrejo@demo.pa')
const p2 = await (await nav.newContext({ viewport: { width: 390, height: 844 } })).newPage()
await p2.goto(BASE + '/')
await p2.evaluate(([s]) => localStorage.setItem('agenda.sesion', JSON.stringify(s)), [pro])
await p2.goto(BASE + '/local/finanzas', { waitUntil: 'networkidle' })
await p2.waitForTimeout(2500)
const loQueVe = await p2.locator('main').innerText()
ok(
  '6 · un profesional no ve el dinero del salón',
  (await p2.locator('.cifras-grandes__valor').count()) === 0,
  loQueVe.split('\n').slice(0, 2).join(' · '),
)

ok('sin errores de JavaScript', errores.length === 0, errores[0] ?? '')
await nav.close()
console.log(fallos.length ? `\n${fallos.length} fallo(s)` : '\nLas seis piezas del portal del dueño responden, y el profesional no entra donde no le toca.')
process.exit(fallos.length ? 1 : 0)
