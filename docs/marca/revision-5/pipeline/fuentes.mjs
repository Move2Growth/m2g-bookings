/**
 * Descarga las tipografías de Google Fonts a disco y escribe un CSS con rutas locales.
 *
 * Existe porque un brandbook que se renderiza pidiendo la fuente por red es un brandbook que
 * **algún día sale con la fuente de sistema y nadie se entera**: el PDF se genera igual, sin
 * error, con Helvetica. Descargando los .woff2 y apuntando a `file://`, si falta una fuente el
 * fallo es ruidoso y se ve en la primera página.
 *
 *   node pipeline/fuentes.mjs direcciones/mi-direccion/fuentes "Archivo:wght@400..700"
 *
 * Escribe `<destino>/<familia>-<hash>.woff2` y `<destino>/fuentes.css`.
 */
import { mkdir, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import path from 'node:path'

// El destino es el primer argumento: cada dirección baja sus fuentes a su propia carpeta, y así
// tres direcciones trabajando a la vez no se pisan el fuentes.css entre ellas.

// Sin este User-Agent, Google devuelve `ttf` en vez de `woff2`: sirve según quién pregunta.
const NAVEGADOR =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'

const [destino, ...familias] = process.argv.slice(2)
if (!destino || familias.length === 0) {
  console.error('uso: node pipeline/fuentes.mjs <carpeta-destino> "Archivo:wght@400..700" ...')
  process.exit(1)
}
const DESTINO = path.resolve(destino)

await mkdir(DESTINO, { recursive: true })

const url =
  'https://fonts.googleapis.com/css2?' +
  familias.map((f) => `family=${encodeURIComponent(f)}`).join('&') +
  '&display=swap'

const respuesta = await fetch(url, { headers: { 'User-Agent': NAVEGADOR } })
if (!respuesta.ok) {
  console.error(`Google Fonts respondió ${respuesta.status} a ${url}`)
  process.exit(1)
}
let css = await respuesta.text()

// Cada URL remota se baja una vez y se sustituye por su ruta local.
const remotas = [...new Set([...css.matchAll(/url\((https:\/\/[^)]+)\)/g)].map((m) => m[1]))]
let bajadas = 0

for (const remota of remotas) {
  const familia = decodeURIComponent(remota).split('/').slice(-2, -1)[0] ?? 'fuente'
  const hash = createHash('sha1').update(remota).digest('hex').slice(0, 10)
  const nombre = `${familia}-${hash}.woff2`
  const binaria = await fetch(remota, { headers: { 'User-Agent': NAVEGADOR } })
  if (!binaria.ok) {
    console.error(`No se pudo bajar ${remota}: ${binaria.status}`)
    process.exit(1)
  }
  await writeFile(path.join(DESTINO, nombre), Buffer.from(await binaria.arrayBuffer()))
  css = css.split(remota).join(`./${nombre}`)
  bajadas++
}

await writeFile(path.join(DESTINO, 'fuentes.css'), css)
console.log(`${bajadas} archivos de fuente en fuentes/, y fuentes/fuentes.css apuntando a ellos`)
