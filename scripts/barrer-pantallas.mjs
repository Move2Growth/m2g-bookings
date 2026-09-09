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
 * · Que **no está enseñando su propio error**. Esto faltaba, y es lo que convierte el barrido en
 *   una promesa que no cumple: ocho pantallas salían «OK» diciendo «Failed to fetch» porque el
 *   CORS las bloqueaba. Respondían 200, no desbordaban y no reventaban; el HTTP estaba bien y la
 *   pantalla no servía para nada.
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

//: El 3100 es el entorno de `make arriba`. Se puede apuntar a otro con
//: `BASE=http://localhost:3300 node scripts/barrer-pantallas.mjs`, y hace falta cuando alguien
//: trabaja en un árbol aparte y levanta **su** web en otro puerto: sin esto se barrería la del
//: repositorio principal y se diría que todo va bien sin haber mirado su código.
//:
//: Si se cambia, el puerto tiene que estar en `ORIGENES_PERMITIDOS` de la API o las pantallas con
//: sesión cargan enteras y no sale ni una petición.
const BASE = process.env.BASE ?? 'http://localhost:3100'
const API = process.env.API ?? 'http://localhost:8000'
//: 390 es un iPhone y es donde vive esto; 1440 es un portátil. Se barren los dos porque los
//: fallos son distintos: en el teléfono desborda, en el escritorio se estira sin límite.
const ANCHOS = [390, 1440]
let ANCHO = ANCHOS[0]

const PUBLICAS = [
  '/',
  '/buscar',
  //: El mapa. Se barre como pública porque lo es, y porque es la única pantalla que carga algo
  //: de fuera —las baldosas—: si ese proveedor se cae, aquí se ve.
  '/mapa',
  '/salon/barberia-el-cangrejo',
  //: El perfil de una persona. Es la pantalla con más piezas del marketplace —datos, servicios,
  //: horas, fotos y reseñas— y la que más fácil desborda a lo ancho.
  '/salon/barberia-el-cangrejo/con/kevin-ortega',
  //: Una dirección que no existe: comprueba que el «no está» tiene salida y no es una página en
  //: blanco.
  '/salon/no-existe-este-salon',
  //: Reservar sin sesión: se puede elegir servicio, persona y hora, y solo al confirmar se pide
  //: entrar. Es el camino por el que llega la mayoría.
  '/reservar/barberia-el-cangrejo',
  '/entrar',
  '/legal/privacidad',
  '/legal/terminos',
]
const CLIENTA = ['/mis-citas', '/mis-salones']

//: Lo del profesional, que no es lo del dueño: su día y su ficha, y nada más. Se barren con una
//: cuenta de profesional porque con la del dueño ni siquiera cargan igual.
const PROFESIONAL = ['/mi-agenda', '/mi-ficha']

//: El portal del dueño: su propia navegación y su propia puerta. Un profesional **no puede
//: entrar**, así que barrerlas con la sesión equivocada solo mediría el desvío. El alta del
//: local se barre aquí aunque no necesite negocio: la abre un dueño.
const DUENO = [
  '/local',
  '/local/equipo',
  '/local/horario',
  '/local/finanzas',
  '/local/mejor-del-mes',
  '/local/publicidad',
  '/local/alta',
]
const CONSOLA = ['/consola', '/consola/negocios', '/consola/moderacion']

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
    body: JSON.stringify({ correo, contrasena: 'demo-panama-2026', superficie: 'web' }),
  })
  if (!r.ok) throw new Error(`no se pudo entrar como ${correo}: ${r.status}`)
  return r.json()
}

/**
 * `llave` dice **dónde** guarda su sesión cada zona, y no es un detalle: la consola la guarda en
 * `sessionStorage` a propósito —muere al cerrar la pestaña, que es lo que se quiere de una sesión
 * con acceso a todos los negocios— y el resto en `localStorage`.
 *
 * Guardarlas todas en `localStorage` hacía que **las cinco pantallas de la consola se barrieran
 * sin sesión**: respondían 200 porque su armazón carga igual, y el barrido las daba por buenas
 * sin haber mirado ni una.
 */
async function barrer(titulo, rutas, sesion, llave = 'agenda.sesion') {
  console.log(`\n── ${titulo} ──`)
  const pagina = await navegador.newPage({ viewport: { width: ANCHO, height: 844 } })
  const errores = []
  pagina.on('pageerror', (e) => errores.push(e.message.slice(0, 120)))
  if (sesion) {
    await pagina.goto(BASE, { waitUntil: 'domcontentloaded' })
    await pagina.evaluate(
      ([clave, valor, enSesion]) =>
        (enSesion ? window.sessionStorage : window.localStorage).setItem(
          clave,
          JSON.stringify(valor),
        ),
      [llave, sesion, llave === 'agenda.consola'],
    )
  }
  for (const ruta of rutas) {
    errores.length = 0
    const respuesta = await pagina.goto(BASE + ruta, { waitUntil: 'networkidle' }).catch(() => null)
    await pagina.waitForTimeout(900)
    //: Un 404 se espera en las rutas que se barren justamente para ver su página de «no está».
    const seEsperaUn404 = ruta.includes('no-existe')
    const estado = respuesta?.status() ?? 0

    //: **Medir puede pillar la página a media navegación.** Alguna pantalla redirige sola
    //: —cambia de sitio después de mirar la sesión—, y si eso pasa justo mientras se mide,
    //: Playwright tira «Execution context was destroyed» y con ella el barrido **entero**: se
    //: queda sin decir nada de las treinta y cuatro pantallas restantes. Pasó una vez de
    //: veinte, que es lo peor que puede pasar: enseña a volver a lanzarlo hasta que salga
    //: verde. Se espera a que se pose y se vuelve a medir; si aun así no se puede, se dice.
    const medir = async (recuerdo) => {
      for (let intento = 0; intento < 3; intento++) {
        try {
          return await pagina.evaluate(recuerdo)
        } catch (fallo) {
          if (!/Execution context was destroyed|Target closed/.test(String(fallo))) throw fallo
          await pagina.waitForLoadState('networkidle').catch(() => {})
          await pagina.waitForTimeout(600)
        }
      }
      return null
    }

    const ancho = await medir(() => document.documentElement.scrollWidth)
    const texto = await pagina.locator('body').innerText().catch(() => '')
    const roto = /Application error|Internal Server Error|Algo salió mal/i.test(texto)

    // **Una pantalla que carga enseñando su propio error no está bien.** Este barredor daba «OK»
    // a ocho pantallas que decían «Failed to fetch» porque el CORS las bloqueaba: respondían 200,
    // no desbordaban y no reventaban. El HTTP estaba bien y la pantalla no servía para nada.
    //
    // Se mira el bloque de error del producto —`.aviso--error`, `role="alert"`— y solo si está
    // **visible**: uno oculto es el que se pinta cuando algo falla, y aquí no ha fallado nada.
    const buscarError = () =>
      medir(() => {
        const posibles = [...document.querySelectorAll('.aviso--error, [role="alert"]')]
        const visible = posibles.find((e) => e.getClientRects().length > 0)
        return visible ? (visible.textContent || '').trim().slice(0, 90) : null
      }).catch(() => null)

    // **Se mira dos veces antes de acusar.** En desarrollo, Next compila cada ruta la primera
    // vez que se pide —ocho segundos largos— y la llamada al servidor de dentro puede vencer,
    // así que la pantalla se pinta con su estado de error sin que nada esté roto. Un fallo de
    // verdad se repite; uno de la primera compilación, no. Un aviso falso enseña a no hacer
    // caso del barrido, que es peor que no tenerlo.
    let avisoDeError = await buscarError()
    if (avisoDeError) {
      await pagina.reload({ waitUntil: 'networkidle' })
      await pagina.waitForTimeout(900)
      avisoDeError = await buscarError()
    }

    //: Sin medida no hay aprobado. `null <= 390` es cierto en JavaScript, así que una pantalla
    //: que no se pudo medir pasaba por buena: el fallo silencioso que este barredor existe para
    //: no tener.
    const bien =
      (estado === 200 || (seEsperaUn404 && estado === 404)) &&
      ancho !== null &&
      ancho <= ANCHO &&
      !roto &&
      !avisoDeError &&
      errores.length === 0
    const porque = [
      errores.length ? errores[0] : '',
      roto ? 'PANTALLA ROTA' : '',
      ancho === null ? 'no se pudo medir: la pantalla no se estuvo quieta' : '',
      avisoDeError ? `enseña un error: «${avisoDeError}»` : '',
    ]
      .filter(Boolean)
      .join(' · ')
    console.log(`${bien ? 'OK  ' : 'MAL '} ${ruta.padEnd(26)} ${estado} · ancho ${ancho}${porque ? ` · ${porque}` : ''}`)
    if (!bien) fallos.push(`${titulo} ${ruta}: estado ${estado}, ancho ${ancho}${porque ? `, ${porque}` : ''}`)
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

/**
 * La sesión **con la forma que lee el front**, que es camelCase y no la respuesta cruda de la
 * API. Escribirla en snake_case dejaba una sesión que el navegador acepta y no entiende: las
 * pantallas cargaban, no reventaban, y se barrían sin sesión sin que nada lo dijera.
 */
const comoLaLeeLaWeb = (credenciales) => ({
  acceso: credenciales.acceso,
  refresco: credenciales.refresco,
  usuarioId: credenciales.usuario_id,
  negocioActivo: credenciales.negocio_activo ?? null,
})

await barrer('Clienta', CLIENTA, comoLaLeeLaWeb(await sesionDe('abdiel@demo.pa')))

//: **Al dueño y al profesional se les da la sesión de plataforma a secas, sin modo negocio.**
//: Es la que deja `/entrar`, y es la que tiene quien vuelve al día siguiente por su marcador.
//: Dársela ya en modo negocio era tapar el camino por el que entra la gente: así fue como
//: pasaron desapercibidos cinco `403` en el portal entero.
await barrer('Dueño de salón', DUENO, comoLaLeeLaWeb(await sesionDe('dueno.barberia-el-cangrejo@demo.pa')))
await barrer('Profesional del salón', PROFESIONAL, comoLaLeeLaWeb(await sesionDe('pro.barberia-el-cangrejo@demo.pa')))

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
