/**
 * Barre TODAS las pantallas del producto a 390 px, con sesión y sin ella.
 *
 *   node scripts/barrer-pantallas.mjs
 *
 * No juzga si algo se ve bonito —eso lo decide la dirección visual—: comprueba las tres cosas
 * que se rompen sin que nadie se entere y que un build verde no ve.
 *
 * · Que la pantalla **carga** con el rol que le toca.
 * · Que **no revienta**: ni error de JavaScript, ni pantalla de error de Next.
 * · Que **no desborda a lo ancho**. `scrollWidth` del documento es la medida honesta;
 *   `getBoundingClientRect` la recorta cualquier `overflow-x: hidden` de por medio y entonces
 *   el desbordamiento existe, se arrastra con el dedo, y la prueba dice que todo va bien.
 *
 * Encontró que el panel del salón medía 562 px dentro de una pantalla de 390.
 *
 * Necesita el entorno local levantado (`make arriba`) y la semilla cargada.
 */

import { chromium } from 'playwright'
import { createHmac } from 'node:crypto'

//: El puerto se puede cambiar con `BASE=http://localhost:3300 node scripts/barrer-pantallas.mjs`.
//: Hace falta cuando alguien trabaja en un árbol aparte y levanta **su** web en otro puerto: sin
//: esto barrería la del repositorio principal y diría que todo va bien sin haber mirado su código.
const BASE = process.env.BASE ?? 'http://localhost:3100'
const API = process.env.API ?? 'http://localhost:8000'
//: 390 es un iPhone y es donde vive esto; 1440 es un portátil. Se barren los dos porque los
//: fallos son distintos: en el teléfono desborda, en el escritorio se estira sin límite.
const ANCHOS = [390, 1440]
let ANCHO = ANCHOS[0]

const PUBLICAS = ['/', '/buscar', '/barberia-el-cangrejo', '/como-funciona', '/para-negocios', '/entrar']
const CLIENTA = ['/mi/citas', '/mi/favoritos', '/mi/perfil']
const NEGOCIO = ['/panel', '/panel/agenda', '/panel/servicios', '/panel/equipo', '/panel/clientes', '/panel/ficha']
//: El portal del dueño. Va aparte de NEGOCIO porque es una zona con su propia navegación y
//: porque un profesional **no puede entrar**: barrerlas con la sesión equivocada solo mediría el
//: desvío. El alta del local se barre aquí aunque no necesite negocio: la abre un dueño.
const DUENO = [
  '/panel/local',
  '/panel/local/calendarios',
  '/panel/local/finanzas',
  '/panel/local/mejor-del-mes',
  '/panel/local/publicidad',
  '/panel/local/fichaje',
  '/panel/local/personas',
  '/panel/alta',
]
const CONSOLA = ['/consola', '/consola/negocios', '/consola/moderacion', '/consola/metricas', '/consola/ranking']

//: La cuenta de consola de la semilla. Vive solo en local y su secreto está en `semilla.py`;
//: aquí se repite porque el script no importa Python. Nunca es una credencial de verdad.
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

const fallos = []
const navegador = await chromium.launch()

async function sesionDe(correo) {
  const r = await fetch(`${API}/api/v1/auth/entrar`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ correo, contrasena: 'demo-panama-2026' }),
  })
  if (!r.ok) throw new Error(`no se pudo entrar como ${correo}: ${r.status}`)
  return r.json()
}

async function barrer(titulo, rutas, sesion, llave = 'agenda.sesion') {
  console.log(`\n── ${titulo} ──`)
  const pagina = await navegador.newPage({ viewport: { width: ANCHO, height: 844 } })
  const errores = []
  pagina.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))
  if (sesion) {
    await pagina.goto(BASE, { waitUntil: 'domcontentloaded' })
    await pagina.evaluate(
      ([clave, valor]) => window.localStorage.setItem(clave, JSON.stringify(valor)),
      [llave, sesion],
    )
  }
  for (const ruta of rutas) {
    errores.length = 0
    const respuesta = await pagina.goto(BASE + ruta, { waitUntil: 'networkidle' }).catch(() => null)
    await pagina.waitForTimeout(900)
    const estado = respuesta?.status() ?? 0
    const ancho = await pagina.evaluate(() => document.documentElement.scrollWidth)
    const texto = await pagina.locator('body').innerText().catch(() => '')
    const roto = /Application error|Internal Server Error|Algo salió mal/i.test(texto)
    const bien = estado === 200 && ancho <= ANCHO && !roto && errores.length === 0
    console.log(`${bien ? 'OK  ' : 'MAL '} ${ruta.padEnd(26)} ${estado} · ancho ${ancho}${errores.length ? ` · ${errores[0]}` : ''}${roto ? ' · PANTALLA ROTA' : ''}`)
    if (!bien) fallos.push(`${titulo} ${ruta}: estado ${estado}, ancho ${ancho}${errores.length ? `, ${errores[0]}` : ''}${roto ? ', pantalla rota' : ''}`)
  }
  await pagina.close()
}

for (const ancho of ANCHOS) {
  ANCHO = ancho
  console.log(`\n══ ${ancho} px ══`)
  await todo()
}

async function todo() {
await barrer('Sin sesión', PUBLICAS, null)
await barrer('Clienta', CLIENTA, await sesionDe('abdiel@demo.pa'))

const duena = await sesionDe('dueno.salon-obarrio@demo.pa')
const negocios = await fetch(`${API}/api/v1/mi/negocios`, { headers: { Authorization: `Bearer ${duena.acceso}` } }).then((r) => r.json())
const conNegocio = await fetch(`${API}/api/v1/auth/modo-negocio`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${duena.acceso}` },
  body: JSON.stringify({ negocio_id: negocios[0].id }),
}).then((r) => r.json())
const sesionDeDuena = {
  ...conNegocio,
  negocio_nombre: negocios[0].nombre,
  negocio_rol: negocios[0].rol,
}
await barrer('Dueña de salón', NEGOCIO, sesionDeDuena)
await barrer('Portal del dueño', DUENO, sesionDeDuena)

// La consola es otro sistema de acceso entero: otras tablas, otro rol de base de datos y
// segundo factor obligatorio. Por eso entra por su propia puerta y guarda en otra llave.
const consola = await fetch(`${API}/api/v1/consola/entrar`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'consola@bukeo.local',
    password: 'consola-de-demo-solo-en-local',
    codigo_2fa: codigoDeDosFactores(CONSOLA_2FA),
  }),
})
if (!consola.ok) {
  fallos.push(`no se pudo entrar en la consola: ${consola.status}`)
} else {
  await barrer('Consola de M2G', CONSOLA, await consola.json(), 'agenda.consola')
}

}

await navegador.close()
if (fallos.length) {
  console.error(`\n${fallos.length} PANTALLAS MAL:`)
  for (const f of fallos) console.error(' · ' + f)
  process.exit(1)
}
console.log(`\nTodas las pantallas cargan, ninguna revienta y ninguna desborda, en ${ANCHOS.join(' y ')} px.`)
