// Contraste medido en las páginas de verdad, no en la paleta.
//
// Existe porque el verificador de `packages/tokens` comprueba **pares de tokens** y esto se
// rompió igual: la regla «el naranja nunca es color de texto» estaba escrita en el brandbook, en
// el ADR-0016 y hasta en un comentario del propio verificador explicando por qué no se
// comprobaba. Y estaba rota en cuatro pantallas a 2,34:1.
//
// La lección es que una regla sobre **cómo se usa** un color no la puede guardar un verificador
// que solo mira la paleta. Hace falta mirar los píxeles.
//
//   node scripts/verificar-contraste-en-pantalla.mjs
//
// Sale con error si hay algo por debajo de AA, para poder colgarlo de una comprobación.

import { createHmac } from 'node:crypto'
import { chromium } from 'playwright'

//: La cuenta de consola de la semilla, que vive solo en local. El código del segundo factor se
//: calcula aquí en vez de sacarlo llamando a Python: una dependencia menos y un fallo menos.
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
const RUTAS = [
  '/',
  '/buscar',
  '/mapa',
  '/salon/spa-costa-del-este',
  //: La ficha de una persona: la pantalla con más piezas del marketplace.
  '/salon/spa-costa-del-este/con/ivonne-saavedra',
  //: Reservar sin entrar, que es el camino por el que llega la mayoría.
  '/reservar/spa-costa-del-este',
  '/entrar',
  '/legal/privacidad',
  '/legal/terminos',
  '/consola',
]

/** Las pantallas con sesión. Se recorren aparte porque hay que entrar antes. */
const CON_SESION = {
  //: El salón entero, que es donde hay más números pequeños y más color de estado.
  salon: [
    '/local',
    '/local/equipo',
    '/local/horario',
    '/local/finanzas',
    '/local/mejor-del-mes',
    '/local/publicidad',
    '/local/alta',
  ],
  //: Lo del profesional, que es otra zona con otras piezas.
  profesional: ['/mi-agenda', '/mi-ficha'],
  //: Y lo de la clienta cuando ya tiene citas y salones guardados.
  clienta: ['/mis-citas', '/mis-salones'],
  consola: ['/consola/negocios', '/consola/moderacion'],
}
const ANCHOS = [390, 1440]

/** Se ejecuta dentro del navegador: necesita el color ya calculado, no el declarado. */
const MEDIR = `(() => {
  const canal = (v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
  const luminancia = (s) => {
    const [r, g, b] = s.match(/\\d+/g).slice(0, 3).map((n) => n / 255)
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)
  }
  const contraste = (a, b) => {
    const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p)
    return (x + 0.05) / (y + 0.05)
  }
  // El fondo de verdad es el del primer antepasado que tenga uno: un elemento transparente
  // sobre un bloque azul se lee sobre azul, no sobre blanco.
  const fondoReal = (e) => {
    let n = e
    while (n && n !== document.documentElement) {
      const c = getComputedStyle(n).backgroundColor
      if (c && c !== 'rgba(0, 0, 0, 0)') return c
      n = n.parentElement
    }
    return 'rgb(255, 255, 255)'
  }

  const fallos = []
  for (const e of document.querySelectorAll('body *')) {
    if (!e.textContent?.trim() || e.children.length > 0) continue
    const c = getComputedStyle(e)
    if (c.visibility === 'hidden' || c.display === 'none' || c.opacity === '0') continue

    // **El texto que solo leen los lectores de pantalla no se mide.** No se ve, así que su
    // contraste no significa nada: en la pantalla de finanzas eran doce descripciones de la
    // gráfica, medidas contra un fondo sobre el que nunca se pintan.
    //
    // Pero no se salta por su clase, sino **comprobando que de verdad está oculto**: un
    // «oculto-visualmente» al que le falta el antepasado posicionado se ve, y ya rompió una
    // pantalla en este proyecto. Si mide más de dos píxeles, se mide como cualquier otro texto.
    // Lo que de verdad lo esconde es el recorte, no el tamaño de la caja: con
    // clip-path: inset(50%) no se pinta ni un píxel aunque el rectángulo mida 28 de ancho.
    // Se mira el recorte y también la caja, por si alguien lo esconde de otra manera.
    const caja = e.getBoundingClientRect()
    const recortado = (c.clipPath || '').split(' ').join('').startsWith('inset(50%')
    if (recortado || caja.width <= 2 || caja.height <= 2) continue
    const px = parseFloat(c.fontSize)
    // AA pide 3:1 para texto grande y 4,5:1 para el resto.
    const grande = px >= 24 || (px >= 18.66 && parseInt(c.fontWeight, 10) >= 700)
    const minimo = grande ? 3 : 4.5
    const ratio = contraste(c.color, fondoReal(e))
    if (ratio < minimo) {
      fallos.push({
        texto: e.textContent.trim().slice(0, 40),
        ratio: +ratio.toFixed(2),
        minimo,
        px: Math.round(px),
        color: c.color,
        fondo: fondoReal(e),
        clase: e.className?.toString().slice(0, 40) ?? '',
      })
    }
  }
  return fallos
})()`

const navegador = await chromium.launch()
let total = 0

for (const ancho of ANCHOS) {
  const pagina = await navegador.newPage({ viewportSize: { width: ancho, height: 900 } })
  for (const ruta of RUTAS) {
    await pagina.goto(`${WEB}${ruta}`, { waitUntil: 'networkidle' })
    await pagina.waitForTimeout(600)
    const fallos = await pagina.evaluate(MEDIR)
    total += fallos.length
    const marca = fallos.length === 0 ? 'ok  ' : 'MAL '
    console.log(`${marca}${String(ancho).padStart(4)} px  ${ruta.padEnd(22)} ${fallos.length}`)
    for (const f of fallos) {
      console.log(
        `        ${f.ratio}:1 (mín. ${f.minimo})  ${f.px}px  «${f.texto}»  ${f.color} sobre ${f.fondo}  .${f.clase}`,
      )
    }
  }
  await pagina.close()
}

// ── Las pantallas con sesión ─────────────────────────────────────────────────
// Son la mitad del producto y hasta ahora no se comprobaban: el panel de un salón y la consola
// de M2G solo se ven después de entrar, así que un fallo de contraste ahí podía vivir años.

async function recorrerConSesion(contexto, rutas, etiqueta) {
  const pagina = await contexto.newPage()
  for (const ruta of rutas) {
    await pagina.goto(`${WEB}${ruta}`, { waitUntil: 'networkidle' })
    await pagina.waitForTimeout(1200)
    const fallos = await pagina.evaluate(MEDIR)
    total += fallos.length
    console.log(`${fallos.length === 0 ? 'ok  ' : 'MAL '}${etiqueta.padEnd(8)} ${ruta.padEnd(22)} ${fallos.length}`)
    for (const f of fallos) {
      console.log(`        ${f.ratio}:1 (mín. ${f.minimo})  ${f.px}px  «${f.texto}»  ${f.color} sobre ${f.fondo}  .${f.clase}`)
    }
  }
  await pagina.close()
}

try {
  // Se entra con correo y contraseña, como se entra ahora. Antes esto pedía un código por
  // teléfono y fallaba cuando el límite de envíos se agotaba, que es como decir «no pude
  // mirar» y contarlo igual que «hay un fallo de contraste»: dos cosas distintas.
  const CLAVE = process.env.CONTRASENA_DEMO ?? 'demo-panama-2026'

  /** Entra por la pantalla de verdad y devuelve el contexto ya con sesión. */
  const entrarComo = async (correo) => {
    const contexto = await navegador.newContext({ viewport: { width: 390, height: 844 } })
    const entrada = await contexto.newPage()
    await entrada.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' })
    await entrada.fill('#correo', correo)
    await entrada.fill('#contrasena', CLAVE)
    await entrada.click('button[type="submit"]')
    //: Cada rol aterriza donde le toca —el dueño en el salón, la clienta en sus citas—, así que
    //: no se espera una URL concreta: se espera a salir de la pantalla de entrar.
    await entrada.waitForURL((url) => !url.pathname.startsWith('/entrar'), { timeout: 20000 })
    await entrada.close()
    return contexto
  }

  const salon = await entrarComo(process.env.CORREO_SALON ?? 'dueno.barberia-el-cangrejo@demo.pa')
  await recorrerConSesion(salon, CON_SESION.salon, 'salón')

  const profesional = await entrarComo('pro.barberia-el-cangrejo@demo.pa')
  await recorrerConSesion(profesional, CON_SESION.profesional, 'pro')

  const clienta = await entrarComo('abdiel@demo.pa')
  await recorrerConSesion(clienta, CON_SESION.clienta, 'clienta')

  const consola = await navegador.newContext({ viewport: { width: 390, height: 844 } })
  const c = await consola.newPage()
  const codigo = codigoDeDosFactores(CONSOLA_2FA)
  await c.goto(`${WEB}/consola`, { waitUntil: 'networkidle' })
  await c.fill('input[type="email"]', 'consola@bukeo.local')
  await c.fill('input[type="password"]', 'consola-de-demo-solo-en-local')
  await c.fill('input[inputmode="numeric"]', codigo)
  await c.click('button[type="submit"]')
  await c.waitForTimeout(3000)
  await c.close()
  await recorrerConSesion(consola, CON_SESION.consola, 'consola')
} catch (error) {
  // Que no se pueda entrar no puede dar el visto bueno por omisión: se dice y se cuenta.
  const limitado = /DEMASIADOS|muchos intentos/i.test(error.message)
  console.error(
    `\nNo se pudieron comprobar las pantallas con sesión: ${error.message}` +
      (limitado
        ? '\nEs el límite de códigos por teléfono. Espera unos minutos o pasa TELEFONO_SALON.'
        : ''),
  )
  total += 1
}

await navegador.close()

if (total > 0) {
  console.error(`\n${total} textos por debajo de AA en las páginas. Arréglalos.`)
  process.exit(1)
}
console.log(`\nNada por debajo de AA en ${RUTAS.length} páginas y ${ANCHOS.length} anchos.`)
