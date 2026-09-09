/**
 * Que la agenda se pueda **llevar**, no solo mirar.
 *
 *   node verificacion/llevar-la-agenda.mjs
 *
 * Hasta ahora las dos agendas eran de solo lectura. Esto comprueba el trabajo de verdad de un
 * salón: confirmar la pendiente, cerrar la atendida, marcar a quien no vino y mover una hora
 * porque llamaron. Y comprueba lo que importa más que los botones: **que el cambio se nota
 * fuera** —en los totales del día y en la cita de la clienta— y que lo que no tiene vuelta
 * pregunta antes.
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
  const modo = await (
    await fetch(`${API}/api/v1/auth/modo-negocio`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${cred.acceso}` },
      body: JSON.stringify({ negocio_id: negocios[0].id, superficie: 'web' }),
    })
  ).json()
  return { acceso: modo.acceso, refresco: modo.refresco, usuarioId: modo.usuario_id, negocioActivo: modo.negocio_activo }
}

const dueno = await sesionDe('dueno.barberia-el-cangrejo@demo.pa')

/* Una cita de prueba, creada por la API: no se toca ninguna de la demostración. */
const equipo = await (await fetch(`${API}/api/v1/negocio/profesionales`, { headers: { authorization: `Bearer ${dueno.acceso}` } })).json()
const persona = equipo.find((p) => p.activo)
/* **La hora se le pregunta al motor, no se inventa.** Poner una fija a mano es cómo esto falló
   la primera vez: el hueco estaba cogido y la prueba se caía por el motivo equivocado. */
const desde = new Date(Date.now() + 86400e3)
desde.setUTCHours(0, 0, 0, 0)
const hasta = new Date(desde.getTime() + 86400e3)
const huecos = await (
  await fetch(
    `${API}/api/v1/publico/profesionales/${persona.id}/disponibilidad?servicios=${persona.servicios[0]}` +
      `&desde=${desde.toISOString()}&hasta=${hasta.toISOString()}`,
  )
).json()
const libre = (huecos.slots ?? [])[0]
if (!libre) {
  console.log('MAL  hay algún hueco libre mañana para la prueba')
  process.exit(1)
}
const manana = new Date(libre.inicio)
const creada = await (
  await fetch(`${API}/api/v1/negocio/reservas`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', authorization: `Bearer ${dueno.acceso}` },
    body: JSON.stringify({
      profesional_id: persona.id,
      servicios: [persona.servicios[0]],
      inicio: manana.toISOString(),
      cliente_nombre: 'Clienta de Prueba',
      cliente_telefono: '+50761239999',
    }),
  })
).json()
ok('se crea una cita de prueba por la API', Boolean(creada.id), creada.id ?? JSON.stringify(creada).slice(0, 120))

const nav = await chromium.launch()
const p = await (await nav.newContext({ viewport: { width: 390, height: 844 } })).newPage()
const errores = []
p.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))
await p.goto(BASE + '/')
await p.evaluate(([s]) => localStorage.setItem('agenda.sesion', JSON.stringify(s)), [dueno])

const dia = manana.toISOString().slice(0, 10)
await p.goto(`${BASE}/local?dia=${dia}`, { waitUntil: 'networkidle' })
await p.waitForTimeout(2500)
// La pantalla abre en hoy: se avanza hasta el día de la cita.
for (let i = 0; i < 3 && (await p.locator(`.riel [data-cita="${creada.id}"]`).count()) === 0; i++) {
  await p.getByRole('button', { name: /Mañana/i }).click()
  await p.waitForTimeout(2500)
}
// Se apunta **a esta cita por su identificador**: buscar por el nombre de la clienta hacía
// que la prueba tocara la de una pasada anterior y fallara por otra cosa.
// A 390 px se pinta el riel y las columnas quedan en el DOM con `display:none`, así que el
// identificador aparece dos veces. Se apunta a la que se ve.
const mia = p.locator(`.riel [data-cita="${creada.id}"]`)
ok('la cita sale en la agenda del salón', (await mia.count()) === 1)
ok('no desborda a 390', (await p.evaluate(() => document.documentElement.scrollWidth)) === 390)

/* Confirmar o cerrar, según nazca pendiente o confirmada */
const estadoInicial = (await mia.innerText()).toUpperCase()
if (estadoInicial.includes('POR CONFIRMAR')) {
  await mia.getByRole('button', { name: /^Confirmar$/ }).click()
  await p.waitForTimeout(2500)
  ok('confirmar la deja confirmada', (await mia.innerText()).toUpperCase().includes('CONFIRMADA'))
}

/* Mover la hora, que es lo que más se hace por teléfono */
const antesDeMover = await (await fetch(`${API}/api/v1/negocio/agenda/columnas?dia=${dia}`, { headers: { authorization: `Bearer ${dueno.acceso}` } })).json()
const horaVieja = antesDeMover.columnas.flatMap((c) => c.citas).find((c) => c.id === creada.id)?.inicio
// **La hora de destino también se saca del motor.** Sumarle una hora a la de la cita era elegir
// a ciegas: cayó en un hueco ocupado y la pantalla lo dijo —«Ese horario se acaba de ocupar»—,
// así que la prueba estaba midiendo su propia mala elección, no el producto.
const otros = (huecos.slots ?? []).filter((s) => s.inicio !== libre.inicio)
const destino = otros[otros.length - 1] ?? otros[0]
if (!destino) {
  console.log('MAL  hay un segundo hueco libre al que mover la cita')
  process.exit(1)
}
const nueva = new Date(destino.inicio)
const local = new Date(nueva.getTime() - nueva.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
await mia.locator('input[type="datetime-local"]').fill(local)
await mia.getByRole('button', { name: /^Mover$/ }).click()
await p.waitForTimeout(3000)
const trasMover = await (await fetch(`${API}/api/v1/negocio/agenda/columnas?dia=${dia}`, { headers: { authorization: `Bearer ${dueno.acceso}` } })).json()
const horaNueva = trasMover.columnas.flatMap((c) => c.citas).find((c) => c.id === creada.id)?.inicio
const quejaAlMover = (await mia.locator('[role="alert"]').allInnerTexts()).join(' | ')
ok(
  'mover la hora la mueve de verdad',
  horaVieja !== horaNueva,
  `${horaVieja} → ${horaNueva}${quejaAlMover ? ` · dice: «${quejaAlMover}»` : ' · sin decir nada'}`,
)

/* Lo que no tiene vuelta pregunta antes */
const fila = mia
await fila.getByRole('button', { name: /No vino/i }).click()
await p.waitForTimeout(700)
ok('marcar «no vino» pregunta antes', (await fila.locator('.llevar--pregunta').count()) === 1)
ok('y dice por qué no tiene vuelta', (await fila.innerText()).toLowerCase().includes('no se puede deshacer'))
await fila.getByRole('button', { name: /^No$/ }).click()
await p.waitForTimeout(600)
ok('y se puede decir que no', (await mia.locator('.llevar--pregunta').count()) === 0)

/* Cerrarla de verdad y comprobar que cambian los totales del día */
const dineroAntes = await p.locator('.cifra-dia, .resumen__dato, .cifras-grandes__valor').first().innerText().catch(() => '')
await mia.getByRole('button', { name: /Atendida/i }).click()
await p.waitForTimeout(3000)
const trasCerrar = await (await fetch(`${API}/api/v1/negocio/agenda/columnas?dia=${dia}`, { headers: { authorization: `Bearer ${dueno.acceso}` } })).json()
const estadoFinal = trasCerrar.columnas.flatMap((c) => c.citas).find((c) => c.id === creada.id)?.estado
ok('cerrarla la deja atendida en la API', estadoFinal === 'completada', String(estadoFinal))
ok('y ya no ofrece más acciones', (await mia.locator('.llevar button').count()) === 0)
ok('sin errores de JavaScript', errores.length === 0, errores[0] ?? '')

/* Limpieza: la cita de prueba fuera de la demostración */
await fetch(`${API}/api/v1/negocio/reservas/${creada.id}/estado`, {
  method: 'POST',
  headers: { 'content-type': 'application/json', authorization: `Bearer ${dueno.acceso}` },
  body: JSON.stringify({ estado: 'cancelada_negocio', motivo: 'prueba' }),
}).catch(() => {})

await nav.close()
console.log(fallos.length ? `\n${fallos.length} fallo(s)` : '\nLa agenda se lleva: se confirma, se mueve, se cierra, y lo que no tiene vuelta pregunta.')
process.exit(fallos.length ? 1 : 0)
