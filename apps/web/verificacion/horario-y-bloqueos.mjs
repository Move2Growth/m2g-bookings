/**
 * El horario y los ratos bloqueados (AGD-2, AGD-3).
 *
 *   node verificacion/horario-y-bloqueos.mjs
 *
 * Lo que hay que comprobar no son los formularios: es **que cambiar el horario cambia las horas
 * que se ofrecen** y que bloquear un rato lo quita de la reserva. Y una cosa más, que es la que
 * de verdad protege a un salón: **si dentro del rato ya hay citas, no se bloquea nada** y se
 * dice — con la mitad bloqueada, el lunes por la mañana se descubre a base de clientas plantadas.
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
    body: JSON.stringify({ correo: 'dueno.barberia-el-cangrejo@demo.pa', contrasena: 'demo-panama-2026', superficie: 'web' }),
  })
).json()
const negocios = await (await fetch(`${API}/api/v1/mi/negocios`, { headers: { authorization: `Bearer ${cred.acceso}` } })).json()
const modo = await (
  await fetch(`${API}/api/v1/auth/modo-negocio`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${cred.acceso}` },
    body: JSON.stringify({ negocio_id: negocios[0].id, superficie: 'web' }),
  })
).json()
const cabecera = { authorization: `Bearer ${modo.acceso}` }
const original = await (await fetch(`${API}/api/v1/negocio/horario`, { headers: cabecera })).json()

const nav = await chromium.launch()
const p = await (await nav.newContext({ viewport: { width: 390, height: 844 } })).newPage()
const errores = []
p.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))
await p.goto(BASE + '/')
await p.evaluate(
  ([s]) => localStorage.setItem('agenda.sesion', JSON.stringify(s)),
  [{ acceso: modo.acceso, refresco: modo.refresco, usuarioId: modo.usuario_id, negocioActivo: modo.negocio_activo }],
)

await p.goto(BASE + '/local/horario', { waitUntil: 'networkidle' })
await p.waitForTimeout(2500)
ok('el horario carga', (await p.locator('.horario__fila').count()) >= 7)
ok('no desborda a 390', (await p.evaluate(() => document.documentElement.scrollWidth)) === 390)
ok('avisa de que no cancela las citas de fuera', (await p.locator('main').innerText()).includes('no toca las citas'))

/* Cerrar el lunes y comprobar que deja de ofrecer horas ese día */
const lunes = p.locator('.horario__fila').filter({ hasText: 'Lunes' }).first()
const abiertoAntes = await lunes.getByRole('checkbox').isChecked()
if (abiertoAntes) {
  await lunes.getByRole('checkbox').uncheck()
  await p.getByRole('button', { name: /Guardar el horario/i }).click()
  await p.waitForTimeout(2500)
  const tras = await (await fetch(`${API}/api/v1/negocio/horario`, { headers: cabecera })).json()
  ok('cerrar un día lo quita del horario', !tras.some((t) => t.dia === 0), `${tras.length} días abiertos`)
  ok('y lo dice en pantalla', (await p.locator('[role="status"]').count()) > 0)
}

/* Devolverlo tal cual estaba: la demostración es de todos */
await fetch(`${API}/api/v1/negocio/horario`, {
  method: 'PUT',
  headers: { 'content-type': 'application/json', ...cabecera },
  body: JSON.stringify(original),
})
const vuelto = await (await fetch(`${API}/api/v1/negocio/horario`, { headers: cabecera })).json()
ok('el horario se devuelve como estaba', vuelto.length === original.length, `${vuelto.length} días`)

/* Bloquear un rato libre, y comprobar que deja de ofrecerse */
await p.reload({ waitUntil: 'networkidle' })
await p.waitForTimeout(2500)
const equipo = await (await fetch(`${API}/api/v1/negocio/profesionales`, { headers: cabecera })).json()
const persona = equipo.find((x) => x.activo)
const d0 = new Date(Date.now() + 3 * 86400e3)
d0.setUTCHours(0, 0, 0, 0)
const d1 = new Date(d0.getTime() + 86400e3)
const huecos = await (
  await fetch(
    `${API}/api/v1/publico/profesionales/${persona.id}/disponibilidad?servicios=${persona.servicios[0]}&desde=${d0.toISOString()}&hasta=${d1.toISOString()}`,
  )
).json()
const antes = (huecos.slots ?? []).length
ok('ese día tiene huecos antes de bloquear', antes > 0, `${antes} huecos`)

// **La ventana se saca del motor, no se estira a ojo.** Coger el primer hueco y sumarle tres
// horas pisaba citas que había en medio, y la API contestaba —con razón— «Ese tramo ya tiene
// citas dentro». Un hueco libre entero es, por definición, un rato sin nada.
const ultimo = huecos.slots[huecos.slots.length - 1]
const inicio = new Date(ultimo.inicio)
const fin = new Date(ultimo.fin)
const local = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
await p.selectOption('#quien-bloqueo', persona.id)
await p.fill('#desde-bloqueo', local(inicio))
await p.fill('#hasta-bloqueo', local(fin))
await p.fill('#motivo-bloqueo', 'Curso de prueba')
await p.getByRole('button', { name: /Bloquear ese rato/i }).click()
await p.waitForTimeout(3000)

const enPantalla = await p.locator('.ficha-persona').filter({ hasText: 'Curso de prueba' }).count()
const quejaAlBloquear = (await p.locator('[role="alert"]').allInnerTexts()).join(' | ')
ok('el bloqueo queda listado', enPantalla === 1, quejaAlBloquear ? `dice: «${quejaAlBloquear}»` : 'sin decir nada')
const despues = await (
  await fetch(
    `${API}/api/v1/publico/profesionales/${persona.id}/disponibilidad?servicios=${persona.servicios[0]}&desde=${d0.toISOString()}&hasta=${d1.toISOString()}`,
  )
).json()
ok('y quita horas de la reserva de verdad', (despues.slots ?? []).length < antes, `${antes} → ${(despues.slots ?? []).length}`)

await p.locator('.ficha-persona').filter({ hasText: 'Curso de prueba' }).getByRole('button', { name: /Levantar/i }).click()
await p.waitForTimeout(3000)
const final = await (
  await fetch(
    `${API}/api/v1/publico/profesionales/${persona.id}/disponibilidad?servicios=${persona.servicios[0]}&desde=${d0.toISOString()}&hasta=${d1.toISOString()}`,
  )
).json()
ok('levantarlo devuelve las horas', (final.slots ?? []).length === antes, `${(final.slots ?? []).length} de ${antes}`)

/* Y lo que protege al salón: sobre un rato con citas no se bloquea nada */
const conCitas = await (await fetch(`${API}/api/v1/negocio/agenda/columnas`, { headers: cabecera })).json()
const ocupada = conCitas.columnas
  .flatMap((c) => c.citas.map((cita) => ({ ...cita, profesional_id: c.profesional_id })))
  .find((c) => c.estado === 'confirmada')
if (ocupada) {
  await p.selectOption('#quien-bloqueo', ocupada.profesional_id)
  await p.fill('#desde-bloqueo', local(new Date(ocupada.inicio)))
  await p.fill('#hasta-bloqueo', local(new Date(new Date(ocupada.inicio).getTime() + 3600e3)))
  // La agenda en columnas trae el profesional en la columna, no en la cita.
  await p.getByRole('button', { name: /Bloquear ese rato/i }).click()
  await p.waitForTimeout(2500)
  const queja = (await p.locator('[role="alert"]').allInnerTexts()).join(' ')
  ok('sobre un rato con citas no bloquea y lo dice', queja.toLowerCase().includes('cita'), queja.slice(0, 90))
}

ok('sin errores de JavaScript', errores.length === 0, errores[0] ?? '')
await nav.close()
console.log(fallos.length ? `\n${fallos.length} fallo(s)` : '\nEl horario y los bloqueos cambian lo que se puede reservar, y con citas dentro no bloquean nada.')
process.exit(fallos.length ? 1 : 0)
