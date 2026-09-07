// Recorrido de una clienta NUEVA, en un navegador de verdad y a 390 px: se da de alta con
// correo y contraseña, busca, entra en un salón, elige una hora, le piden el teléfono, lo
// verifica y reserva.
//
// La cuenta se crea en cada pasada, y eso es a propósito: el camino de quien ya tiene cuenta y
// teléfono verificado se salta justo los dos pasos donde estaban los fallos.
//
// Es la prueba de humo que no se puede escribir de otra forma. Un build verde no dice nada de
// si el flujo funciona: la CSP, el CORS, el foco de los campos y el hecho de que la pantalla
// enseñe el código en local solo se ven ejecutándolo.
//
//   node scripts/recorrido-cliente.mjs
//
// Necesita la API y la web levantadas (`make arriba` y `pnpm --filter @agenda/web dev`) y
// `npm install --no-save playwright` la primera vez. Deja las capturas en docs/capturas/.
import { chromium, devices } from 'playwright'

const WEB = process.env.WEB ?? 'http://127.0.0.1:3100'
const CAPTURAS = process.env.CAPTURAS ?? 'docs/capturas'
const TELEFONO = process.env.TELEFONO ?? `+5076${String(Date.now()).slice(-7)}`
const CORREO = process.env.CORREO ?? `recorrido-${Date.now()}@demo.pa`
const CLAVE = 'una contrasena larga'
const API = process.env.API ?? 'http://127.0.0.1:8000'

const navegador = await chromium.launch()
const contexto = await navegador.newContext({ ...devices['iPhone 13'], locale: 'es-PA' })
const pagina = await contexto.newPage()

async function captura(nombre) {
  await pagina.screenshot({ path: `${CAPTURAS}/cliente-${nombre}.png` })
  console.log(`  captura: cliente-${nombre}.png`)
}

console.log('0. se da de alta con correo y contraseña')
await pagina.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' })
await pagina.getByRole('button', { name: /Créala/ }).click()
await pagina.fill('#nombre', 'Recorrido de Prueba')
await pagina.fill('#correo', CORREO)
await pagina.fill('#contrasena', CLAVE)
await pagina.click('button[type="submit"]')
await pagina.waitForURL((u) => !u.pathname.startsWith('/entrar'), { timeout: 20000 })
console.log('   cuenta creada:', CORREO)
await captura('0-alta')

console.log('1. abre el marketplace y busca «uñas»')
await pagina.goto(`${WEB}/`, { waitUntil: 'networkidle' })
await pagina.fill('input[name="texto"]', 'uñas')
await pagina.click('button[type="submit"]')
await pagina.waitForLoadState('networkidle')
await captura('1-busqueda')
console.log('   resultados:', await pagina.locator('.resultado__nombre').allTextContents())

console.log('2. entra en el primer salón')
// La espera mira el destino, no «que no sea la portada»: viniendo de /buscar esa condición ya
// se cumplía antes de pulsar y la prueba seguía en la página anterior sin enterarse.
const destino = await pagina.locator('a.resultado').first().getAttribute('href')
await Promise.all([
  pagina.waitForURL((u) => u.pathname === destino, { timeout: 15000 }),
  pagina.locator('a.resultado').first().click(),
])
await pagina.waitForLoadState('networkidle')
const salon = await pagina.locator('h1').first().textContent()
console.log('   salón:', salon)

console.log('3. elige un día con horas libres')
const dias = pagina.locator('nav[aria-label="Elegir día"] a')
let horas = 0
for (let i = 0; i < (await dias.count()); i++) {
  await Promise.all([pagina.waitForLoadState('networkidle'), dias.nth(i).click()])
  await pagina.waitForTimeout(400)
  horas = await pagina.locator('a[href^="/reservar"]').count()
  if (horas > 0) break
}
console.log('   huecos en ese día:', horas)
await captura('2-horas')

console.log('4. toca una hora')
const primeraHora = await pagina.locator('a[href^="/reservar"]').first().textContent()
await pagina.locator('a[href^="/reservar"]').first().click()
await pagina.waitForLoadState('networkidle')
console.log('   hora elegida:', primeraHora?.trim())
await captura('3-confirmar')

// Se verifica el teléfono, que es lo único que sigue pidiendo un código, y solo aquí: el
// salón tiene que poder llamar si hay que mover la cita.
console.log('5. verifica el teléfono sin salir de la pantalla')
await pagina.fill('input[type="tel"]', TELEFONO)
await pagina.click('button[type="submit"]')
await pagina.waitForSelector('input[inputmode="numeric"]')
const pista = await pagina.locator('text=Tu código es').textContent()
const codigo = pista.match(/(\d{6})/)[1]
console.log('   código que enseña la pantalla:', codigo)
await pagina.fill('input[inputmode="numeric"]', codigo)
await pagina.click('button[type="submit"]')
await pagina.waitForSelector('text=Confirmar la cita')
await captura('4-confirmar-con-sesion')

console.log('6. confirma la cita')
await pagina.click('text=Confirmar la cita')
await pagina.waitForURL('**/mi/citas**', { timeout: 15000 })
await pagina.waitForLoadState('networkidle')
// Se espera a que la lista exista antes de contarla. Contar sin esperar daba «0 citas» y a
// renglón seguido imprimía el texto de la primera: la lista aparecía entre las dos líneas, y
// el recorrido decía que no había reservado nada justo después de reservar.
await pagina.locator('.cita').first().waitFor({ timeout: 15000 })
await captura('5-mis-reservas')

const citas = await pagina.locator('.cita').count()
console.log('   citas en «Mis citas»:', citas)
console.log('   texto:', (await pagina.locator('.cita').first().innerText()).replace(/\n/g, ' · '))

// El final del flujo tiene que **decir** que la cita quedó hecha. Sin esto, la pantalla es una
// lista igual a la de siempre y la pregunta «¿se guardó?» se queda sin responder.
const aviso = await pagina.locator('[role="status"]').first().innerText().catch(() => '')
console.log('   confirmación:', aviso.replace(/\n/g, ' ') || 'NINGUNA')

await navegador.close()
if (citas < 1 || !/Cita confirmada/i.test(aviso)) {
  console.error('\nEl recorrido llegó hasta el final pero no confirmó la cita.')
  process.exit(1)
}
console.log('\nRecorrido completo sin un solo paso a mano.')
