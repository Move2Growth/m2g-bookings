/**
 * Lo que le faltaba a la clienta: guardar un salón, opinar de una cita y repetirla.
 *
 *   node verificacion/clienta.mjs
 *
 * Lo importante no es que los formularios se pinten: es que **lo que se hace aquí se nota
 * fuera**. Guardar un salón tiene que aparecer en la lista; una reseña tiene que salir en la
 * ficha pública del salón y mover su media; y repetir tiene que llegar al flujo de reserva con
 * el servicio ya elegido.
 */
import { chromium } from 'playwright'

const BASE = process.env.BASE ?? 'http://localhost:3100'
const API = process.env.API ?? 'http://localhost:8000'
const fallos = []
const ok = (que, bien, detalle = '') => {
  console.log(`${bien ? 'ok  ' : 'MAL '} ${que}${detalle ? ` · ${detalle}` : ''}`)
  if (!bien) fallos.push(que)
}

const cred = await (
  await fetch(`${API}/api/v1/auth/entrar`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ correo: 'abdiel@demo.pa', contrasena: 'demo-panama-2026', superficie: 'web' }),
  })
).json()

const nav = await chromium.launch()
const p = await (await nav.newContext({ viewport: { width: 390, height: 844 } })).newPage()
const errores = []
p.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))
await p.goto(BASE + '/')
await p.evaluate(
  ([c]) => localStorage.setItem('agenda.sesion', JSON.stringify({ acceso: c.acceso, refresco: c.refresco, usuarioId: c.usuario_id, negocioActivo: null })),
  [cred],
)

/* Guardar un salón desde su ficha */
await p.goto(BASE + '/salon/spa-urbano-el-cangrejo', { waitUntil: 'networkidle' })
await p.waitForTimeout(2000)
const guardar = p.getByRole('button', { name: /Guardar este salón|Guardado/ })
ok('la ficha ofrece guardar el salón', (await guardar.count()) === 1)
const rotuloAntes = await guardar.innerText()
if (rotuloAntes.includes('GUARDADO')) await guardar.click(), await p.waitForTimeout(1500)
await p.getByRole('button', { name: /Guardar este salón/i }).click()
await p.waitForTimeout(2500)
ok('guardarlo cambia el botón', (await p.getByRole('button', { name: /Guardado/i }).count()) === 1)

await p.goto(BASE + '/mis-salones', { waitUntil: 'networkidle' })
await p.waitForTimeout(2000)
const enLista = await p.locator('.ficha-persona').filter({ hasText: 'Spa Urbano' }).count()
ok('y aparece en mis salones', enLista === 1)
ok('no desborda a 390', (await p.evaluate(() => document.documentElement.scrollWidth)) === 390)
await p.locator('.ficha-persona').filter({ hasText: 'Spa Urbano' }).getByRole('button', { name: 'Quitar' }).click()
await p.waitForTimeout(2000)
ok('y se puede quitar', (await p.locator('.ficha-persona').filter({ hasText: 'Spa Urbano' }).count()) === 0)

/* Opinar de una cita que lo permite */
// Se busca por páginas, que es lo que hace la pantalla: las citas atendidas están detrás de las
// treinta primeras, y esa era exactamente la razón de que no se pudiera opinar de ninguna.
let opinable = null
for (let pagina = 1; pagina <= 3 && !opinable; pagina++) {
  const trozo = await (
    await fetch(`${API}/api/v1/mi/reservas?pagina=${pagina}`, { headers: { authorization: `Bearer ${cred.acceso}` } })
  ).json()
  opinable = trozo.find((c) => c.se_puede_resenar) ?? null
}
if (!opinable) {
  ok('hay alguna cita opinable en la demo', false, 'ninguna de las 60 tiene se_puede_resenar')
} else {
  const antes = await (await fetch(`${API}/api/v1/publico/negocios/${opinable.negocio_slug}/reviews`)).json()
  await p.goto(BASE + '/mis-citas', { waitUntil: 'networkidle' })
  await p.waitForTimeout(2500)
  await p.locator('details.plegable').evaluate((d) => d.setAttribute('open', ''))
  await p.waitForTimeout(600)
  // Desplegar la historia hasta encontrar una cita que se pueda opinar, que es lo que haría
  // quien quiere opinar de la del mes pasado.
  for (let i = 0; i < 3 && (await p.getByRole('button', { name: /Contar qué tal fue/i }).count()) === 0; i++) {
    await p.locator('.plegable__cuerpo button', { hasText: 'Ver más de antes' }).click()
    await p.waitForTimeout(2500)
  }
  // **Se opina de la cita que se miró, no de la primera de la lista.** Comparando después el
  // recuento de reseñas de *su* salón, pulsar otra cualquiera hacía que la prueba dijera que la
  // reseña no había llegado cuando sí había llegado — a otro sitio.
  const suya = p.locator(`[data-cita="${opinable.id}"]`)
  for (let i = 0; i < 4 && (await suya.count()) === 0; i++) {
    await p.locator('.plegable__cuerpo button', { hasText: 'Ver más de antes' }).click()
    await p.waitForTimeout(2500)
  }
  const boton = suya.getByRole('button', { name: /Contar qué tal fue/i })
  ok('la cita atendida ofrece opinar', (await boton.count()) === 1)
  await boton.click()
  await p.waitForTimeout(800)
  ok('sin nota no deja enviar', await p.getByRole('button', { name: /Elige una nota/i }).isDisabled())
  await p.getByRole('button', { name: /5 · Muy bien/i }).click()
  await p.getByRole('button', { name: /Enviar mi opinión/i }).click()
  await p.waitForTimeout(3000)
  const despues = await (await fetch(`${API}/api/v1/publico/negocios/${opinable.negocio_slug}/reviews`)).json()
  ok('la reseña llega a la ficha pública', despues.resumen.total === antes.resumen.total + 1, `${antes.resumen.total} → ${despues.resumen.total}`)
  ok('y la cita queda marcada como opinada', (await suya.locator('text=Ya opinaste').count()) > 0)
}

/* Repetir una cita */
await p.goto(BASE + '/mis-citas', { waitUntil: 'networkidle' })
await p.waitForTimeout(2500)
await p.locator('details.plegable').evaluate((d) => d.setAttribute('open', ''))
await p.waitForTimeout(800)
const repetir = p.getByRole('button', { name: /Repetir esta cita/i }).first()
if ((await repetir.count()) === 1) {
  await repetir.click()
  await p.waitForTimeout(3500)
  ok('repetir lleva a reservar con el servicio puesto', p.url().includes('/reservar/') && p.url().includes('servicio='), p.url())
} else {
  ok('hay alguna cita repetible', false)
}

ok('sin errores de JavaScript', errores.length === 0, errores[0] ?? '')
await nav.close()
console.log(fallos.length ? `\n${fallos.length} fallo(s)` : '\nGuardar, opinar y repetir funcionan, y se nota fuera.')
process.exit(fallos.length ? 1 : 0)
