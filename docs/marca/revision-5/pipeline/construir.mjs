/**
 * Construye el `libro.html` de una dirección a partir de su `marca.json` y su logotipo.
 *
 *   node pipeline/construir.mjs direcciones/a-buenamano
 *
 * Existe para que las tres direcciones no puedan mentir en lo comprobable. El **ratio de
 * contraste que sale impreso en la página de color se calcula aquí**, de los mismos hex que
 * pinta el libro: no se teclea a mano, así que no puede decir 4,8 y estar pintando 2,3. Esa
 * mentira ya coló una vez.
 *
 * Cada dirección trae su propia maqueta —`editorial`, `sistema`, `bloques`— y comparten solo la
 * caja de página de 297×210 mm y la numeración. Lo demás se separa a propósito: tres pieles del
 * mismo libro no serían tres direcciones, serían una con tres paletas.
 */
import { readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'

const carpeta = process.argv[2]
if (!carpeta) {
  console.error('uso: node pipeline/construir.mjs direcciones/<clave>')
  process.exit(1)
}
const raiz = path.resolve(carpeta)
const marca = JSON.parse(readFileSync(path.join(raiz, 'marca.json'), 'utf8'))

/* ── Contraste ───────────────────────────────────────────────────────────────────────────── */

const canal = (v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
const luminancia = (hex) => {
  const [r, g, b] = rgb(hex).map((v) => canal(v / 255))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
/** El ratio de la WCAG, redondeado hacia abajo: nunca se anuncia más contraste del que hay. */
const ratio = (a, b) => {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p)
  return Math.floor(((x + 0.05) / (y + 0.05)) * 100) / 100
}
const nivel = (r, grande = false) => (r >= (grande ? 4.5 : 7) ? 'AAA' : r >= (grande ? 3 : 4.5) ? 'AA' : 'NO PASA')

/* ── Logotipo ────────────────────────────────────────────────────────────────────────────── */

/** El SVG de potrace, listo para incrustar: sin cabecera XML, sin metadatos y con `currentColor`. */
function marcaSvg(alto) {
  const bruto = readFileSync(path.join(raiz, 'logo', 'principal.svg'), 'utf8')
  const caja = bruto.match(/viewBox="([^"]+)"/)[1]
  const cuerpo = bruto.slice(bruto.indexOf('<g '), bruto.lastIndexOf('</svg>'))
  return `<svg viewBox="${caja}" height="${alto}" role="img" aria-label="${marca.nombre}" style="display:block">${cuerpo}</svg>`
}

const P = Object.fromEntries(marca.paleta.map((c) => [c.nombre.toLowerCase(), c.hex]))
const fondo = P.papel ?? P.cemento ?? P.hueso
const texto = P.tinta ?? P.negro
const acento = P.savia ?? P.señal ?? P.fucsia
const apoyo = P.humo ?? P.gris ?? P.cobalto

/* ── Piezas comunes ──────────────────────────────────────────────────────────────────────── */

let numero = 0
const pagina = (clase, contenido, pie = '') => {
  numero++
  return `<section class="pagina ${clase}">
  ${contenido}
  <footer class="folio"><span>${marca.nombre}</span><span>${pie}</span><span class="cifra">${String(numero).padStart(2, '0')}</span></footer>
</section>`
}

const rotulo = (t) => `<p class="rotulo">${t}</p>`

/* ── Las diez páginas ────────────────────────────────────────────────────────────────────── */

const portada = () => {
  if (marca.layout === 'bloques') {
    return pagina(
      'portada',
      `<div class="portada-bloques">
        <div class="bloque bloque--cobalto"><div class="marca-grande">${marcaSvg(150)}</div></div>
        <div class="bloque bloque--hueso">
          <h1 class="titulazo">${marca.nombre}</h1>
          <p class="promesa">${marca.promesa}</p>
        </div>
        <div class="bloque bloque--fucsia"><p class="grito">Te toca</p></div>
        <div class="bloque bloque--amarillo"><p class="dato"><span class="cifra">1</span> minuto</p></div>
      </div>`,
      'Portada',
    )
  }
  if (marca.layout === 'sistema') {
    return pagina(
      'portada',
      `<div class="portada-sistema">
        <div class="barra"><span>${marca.nombre.toUpperCase()}</span><span class="cifra">REV 5 · 2026</span></div>
        <div class="centro">
          ${marcaSvg(190)}
          <h1 class="titulazo">${marca.nombre}</h1>
        </div>
        <p class="promesa">${marca.promesa}</p>
        <div class="rejilla-cupos">${Array.from({ length: 24 }, (_, i) => `<i class="${i === 17 ? 'libre' : ''}"></i>`).join('')}</div>
      </div>`,
      'Portada',
    )
  }
  return pagina(
    'portada',
    `<div class="portada-editorial">
      <div class="filete"></div>
      <div class="cabecera-portada">
        ${marcaSvg(64)}
        <span class="rotulo">Manual de marca · Revisión 5 · Septiembre 2026</span>
      </div>
      <h1 class="titulazo">${marca.nombre}</h1>
      <p class="promesa">${marca.promesa}</p>
      <div class="filete"></div>
      <div class="pie-portada">
        <p class="entradilla">${marca.idea}</p>
        <div class="marca-fantasma">${marcaSvg(150)}</div>
      </div>
    </div>`,
    'Portada',
  )
}

const estrategia = () =>
  pagina(
    'estrategia',
    `${rotulo('02 · Estrategia')}
    <h2 class="titulo">${marca.idea}</h2>
    <p class="nota-nombre"><strong>Por qué se llama así.</strong> ${marca.porQueElNombre}</p>
    <div class="verdades">
      ${marca.verdades
        .map(
          ([t, d], i) =>
            `<article><span class="cifra ordinal">0${i + 1}</span><h3>${t}</h3><p>${d}</p></article>`,
        )
        .join('')}
    </div>`,
    'Estrategia',
  )

/** Seis piezas **dibujadas**, no fotos: color, trama y materia salen de la propia paleta. */
const moodboard = () =>
  pagina(
    'moodboard',
    `${rotulo('03 · Moodboard')}
    <h2 class="titulo">De qué está hecho</h2>
    <div class="mosaico">
      <div class="pieza pieza--llena"><span>Bloque</span></div>
      <div class="pieza pieza--rayas"><span>Trama fina</span></div>
      <div class="pieza pieza--rejilla"><span>Retícula</span></div>
      <div class="pieza pieza--arco"><span>Curva</span></div>
      <div class="pieza pieza--cifras"><span class="cifra">09:45</span></div>
      <div class="pieza pieza--puntos"><span>Grano</span></div>
    </div>`,
    'Moodboard',
  )

const logotipo = () =>
  pagina(
    'logotipo',
    `${rotulo('04 · Logotipo')}
    <h2 class="titulo">Tres versiones y ninguna más</h2>
    <div class="versiones">
      <figure class="v v--principal">${marcaSvg(96)}<figcaption>Principal · sobre fondo claro</figcaption></figure>
      <figure class="v v--invertida">${marcaSvg(96)}<figcaption>Invertida · sobre tinta</figcaption></figure>
      <figure class="v v--tinta">${marcaSvg(96)}<figcaption>Una tinta · sello y sobre acento</figcaption></figure>
    </div>
    <p class="regla"><strong>Lo que nunca se le hace.</strong> ${marca.reglaLogo}</p>`,
    'Logotipo',
  )

const icono = () =>
  pagina(
    'icono',
    `${rotulo('05 · Ícono')}
    <h2 class="titulo">Qué se cae en cada escalón</h2>
    <div class="escalones">
      <figure><div class="caja-icono i48">${marcaSvg(30)}</div><figcaption><span class="cifra">48 px</span><br>Se ve entera: se usa en la pestaña y en el atajo del móvil.</figcaption></figure>
      <figure><div class="caja-icono i32">${marcaSvg(20)}</div><figcaption><span class="cifra">32 px</span><br>Se pierden los remates finos; la silueta aguanta.</figcaption></figure>
      <figure><div class="caja-icono i16">${marcaSvg(11)}</div><figcaption><span class="cifra">16 px</span><br>Queda la mancha. Por eso la marca es maciza y no de línea.</figcaption></figure>
    </div>
    <p class="regla"><strong>La prueba.</strong> A 16 px se mira entornando los ojos: si dos formas se tocan y se funden, el ícono está mal dibujado, no mal exportado.</p>`,
    'Ícono',
  )

const color = () => {
  const filas = marca.paleta
    .map((c) => {
      const contraFondo = ratio(c.hex, fondo)
      const contraTexto = ratio(c.hex, texto)
      const mejor = contraFondo >= contraTexto ? { r: contraFondo, sobre: 'papel' } : { r: contraTexto, sobre: 'tinta' }
      return `<tr>
        <td><span class="muestra" style="background:${c.hex}"></span></td>
        <th>${c.nombre}</th>
        <td class="cifra">${c.hex.toUpperCase()}</td>
        <td class="cifra">${rgb(c.hex).join(' · ')}</td>
        <td class="cifra">${mejor.r.toFixed(2)}:1<small> sobre ${mejor.sobre}</small></td>
        <td><span class="sello ${nivel(mejor.r) === 'NO PASA' ? 'sello--mal' : ''}">${nivel(mejor.r)}</span></td>
        <td class="uso">${c.uso}</td>
      </tr>`
    })
    .join('')
  const barra = marca.paleta
    .map((c) => `<span style="flex:${c.proporcion};background:${c.hex}"></span>`)
    .join('')
  return pagina(
    'color',
    `${rotulo('06 · Color')}
    <h2 class="titulo">Cinco tintas, cada una con su trabajo</h2>
    <table class="tabla-color">
      <thead><tr><th></th><th>Nombre</th><th>Hex</th><th>RGB</th><th>Contraste</th><th>WCAG</th><th>Para qué</th></tr></thead>
      <tbody>${filas}</tbody>
    </table>
    <div class="proporcion">${barra}</div>
    <p class="regla"><strong>Los ratios están calculados, no escritos.</strong> Salen de estos mismos hex al generar el libro, así que no pueden decir una cosa y pintar otra.</p>`,
    'Color',
  )
}

const tipografia = () =>
  pagina(
    'tipografia',
    `${rotulo('07 · Tipografía')}
    <h2 class="titulo">${marca.tipos.display.familia} y ${marca.tipos.texto.familia}</h2>
    <div class="tipos">
      <div class="columna-tipo">
        <p class="rotulo">Rótulo · ${marca.tipos.display.familia}</p>
        <p class="espec-display">Aa Bb Cc Ññ</p>
        <p class="espec-cifras cifra">0123456789 · 09:45 · $18.00</p>
        <p class="nota">${marca.tipos.display.nota}</p>
      </div>
      <div class="columna-tipo">
        <p class="rotulo">Texto · ${marca.tipos.texto.familia}</p>
        <p class="espec-texto">Reserva con Kevin el martes a las nueve y cuarto. Si no puedes, lo cambias desde aquí sin llamar a nadie.</p>
        <p class="nota">${marca.tipos.texto.nota}</p>
      </div>
    </div>
    <table class="jerarquia">
      <tr><th>Display</th><td class="j-display">40 / 40</td><td>Portada y titulares de página</td></tr>
      <tr><th>H1</th><td class="j-h1">28 / 32</td><td>Título de pantalla</td></tr>
      <tr><th>H2</th><td class="j-h2">20 / 26</td><td>Sección dentro de una pantalla</td></tr>
      <tr><th>Cuerpo</th><td class="j-cuerpo">15 / 23</td><td>Todo lo que se lee seguido</td></tr>
      <tr><th>Etiqueta</th><td class="j-etiqueta">12 / 16</td><td>Rótulos, unidades y estados</td></tr>
    </table>`,
    'Tipografía',
  )

const componentes = () =>
  pagina(
    'componentes',
    `${rotulo('08 · Componentes')}
    <h2 class="titulo">Un botón son seis estados</h2>
    <div class="estados">
      ${['Reposo', 'Encima', 'Pulsado', 'Cargando', 'Inhabilitado', 'Con foco']
        .map(
          (e, i) =>
            `<figure><button class="btn e${i}" ${i === 4 ? 'disabled' : ''}>${i === 3 ? '<span class="rueda"></span>Reservando' : 'Reservar'}</button><figcaption>${e}</figcaption></figure>`,
        )
        .join('')}
    </div>
    <div class="otros">
      <div>
        <p class="rotulo">Campo</p>
        <div class="campo"><label>Tu teléfono</label><div class="entrada"><span class="cifra">+507 6000-0000</span></div></div>
      </div>
      <div>
        <p class="rotulo">Hora libre y hora tomada</p>
        <div class="horas"><span class="hora">09:00</span><span class="hora">09:15</span><span class="hora hora--elegida">09:30</span><span class="hora hora--ida">09:45</span><span class="hora">10:00</span></div>
      </div>
      <div>
        <p class="rotulo">Aviso</p>
        <p class="aviso">Sin cupo este día. El jueves abre a las nueve.</p>
      </div>
    </div>`,
    'Componentes',
  )

const pantalla = () =>
  pagina(
    'pantalla',
    `${rotulo('09 · Pantalla entera')}
    <h2 class="titulo">La ficha de un salón, a 390 px</h2>
    <div class="con-telefono">
      <div class="telefono">
        <header class="app-cabecera">${marcaSvg(18)}<span>Buscar</span><span class="app-entrar">Entrar</span></header>
        <div class="app-cuerpo">
          <h3 class="app-h1">Barbería El Cangrejo</h3>
          <p class="app-dir">Calle 47 con Vía Argentina · El Cangrejo</p>
          <p class="app-nota"><span class="cifra">4,32</span> · 12 reseñas</p>
          <p class="rotulo">Servicios</p>
          <ul class="app-servicios">
            <li><span>Corte clásico</span><span class="cifra">45 min · $12.00</span></li>
            <li class="elegido"><span>Corte + barba</span><span class="cifra">60 min · $18.00</span></li>
          </ul>
          <p class="rotulo">Horas libres · martes 8</p>
          <div class="app-horas"><span>16:00</span><span>16:15</span><span class="sel">16:30</span><span>16:45</span><span>17:00</span><span>17:15</span></div>
          <button class="btn e0 ancho">Reservar 16:30</button>
        </div>
        <nav class="app-pestanas"><span class="on">Buscar</span><span>Mis citas</span><span>Yo</span></nav>
      </div>
      <div class="explica">
        <p><strong>Se enseña entera</strong>, con su cabecera y su barra de abajo, porque un recorte bonito esconde justo lo que suele estar mal: qué se ve al llegar y qué se ve al final.</p>
        <p>La hora elegida no lleva sombra ni redondeo: cambia de color y de peso. Es la misma regla del acento — el color solo marca lo que se toca.</p>
        <p>El precio y la hora van en cifra tabular: en una columna de seis horas, si no se alinean, se leen mal de un vistazo.</p>
      </div>
    </div>`,
    'Pantalla',
  )

const voz = () =>
  pagina(
    'voz',
    `${rotulo('10 · Voz y cierre')}
    <h2 class="titulo">Cómo habla ${marca.nombre}</h2>
    <div class="voz">
      ${marca.voz
        .map(
          ([q, f]) =>
            `<p class="${q === 'Se dice' ? 'si' : 'no'}"><span class="rotulo">${q}</span>${f}</p>`,
        )
        .join('')}
    </div>
    <div class="cierre">
      <div class="tarjeta">
        ${marcaSvg(28)}
        <p class="t-nombre">Barbería El Cangrejo</p>
        <p class="t-linea cifra">${marca.nombre.toLowerCase()}.com/barberia-el-cangrejo</p>
      </div>
      <p class="firma">Una dirección de marca para M2G Bookings. El nombre, el color y la letra se deciden aquí; lo demás ya está construido.</p>
    </div>`,
    'Cierre',
  )

/* ── Hoja de estilo ──────────────────────────────────────────────────────────────────────── */

const comun = `
@page { size: 297mm 210mm; margin: 0 }
* { box-sizing: border-box; margin: 0; padding: 0 }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact }
body { background: ${fondo}; color: ${texto}; font-family: ${marca.tipos.texto.css}; }
.pagina {
  width: 297mm; height: 210mm; overflow: hidden; position: relative;
  background: ${fondo}; padding: 16mm 18mm 17mm;
  display: flex; flex-direction: column; gap: 6mm;
}
.cifra { font-variant-numeric: tabular-nums; font-feature-settings: 'tnum' 1 }
.rotulo {
  font-family: ${marca.tipos.display.css}; font-size: 9pt; font-weight: 600;
  letter-spacing: .14em; text-transform: uppercase; color: ${apoyo};
}
.titulo { font-family: ${marca.tipos.display.css}; font-size: 26pt; line-height: 1.1; font-weight: 700; max-width: 22ch }
.folio {
  position: absolute; left: 18mm; right: 18mm; bottom: 8mm;
  display: flex; justify-content: space-between; font-family: ${marca.tipos.display.css};
  font-size: 8pt; letter-spacing: .1em; text-transform: uppercase; color: ${apoyo};
}
.regla { font-size: 10pt; line-height: 1.5; max-width: 78ch; color: ${apoyo} }
.regla strong { color: ${texto} }

/* Moodboard */
.mosaico { display: grid; grid-template-columns: repeat(3, 1fr); grid-auto-rows: 46mm; gap: 5mm; flex: 1 }
.pieza { position: relative; display: flex; align-items: flex-end; padding: 4mm; overflow: hidden }
.pieza span { font-family: ${marca.tipos.display.css}; font-size: 9pt; letter-spacing: .1em; text-transform: uppercase; position: relative }
.pieza--llena { background: ${acento}; color: ${fondo} }
.pieza--rayas { background: repeating-linear-gradient(90deg, ${texto} 0 1px, ${fondo} 1px 6px); color: ${texto} }
.pieza--rejilla { background:
  repeating-linear-gradient(90deg, ${apoyo} 0 .5px, transparent .5px 9mm),
  repeating-linear-gradient(0deg, ${apoyo} 0 .5px, transparent .5px 9mm), ${fondo}; color: ${texto} }
.pieza--arco { background: ${texto}; color: ${fondo} }
.pieza--arco::before { content: ''; position: absolute; inset: -30% -10% auto; height: 130%; border-radius: 50%; background: ${acento} }
.pieza--cifras { background: ${fondo}; border: 1.5px solid ${texto}; color: ${texto}; align-items: center; justify-content: center }
.pieza--cifras span { font-size: 30pt; letter-spacing: -.02em }
.pieza--puntos { background: radial-gradient(${texto} 22%, transparent 23%) 0 0/4mm 4mm, ${fondo}; color: ${texto} }

/* Logotipo e ícono */
.versiones { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6mm; flex: 1 }
.v { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6mm; padding: 8mm }
.v figcaption { font-size: 9pt; letter-spacing: .04em }
.v--principal { background: ${fondo}; border: 1px solid ${apoyo}; color: ${texto} }
.v--invertida { background: ${texto}; color: ${fondo} }
.v--tinta { background: ${acento}; color: ${fondo} }
.escalones { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8mm; flex: 1; align-items: start }
.caja-icono { display: grid; place-items: center; background: ${texto}; color: ${fondo}; margin-bottom: 4mm }
.i48 { width: 48px; height: 48px } .i32 { width: 32px; height: 32px } .i16 { width: 16px; height: 16px }
.escalones figcaption { font-size: 9.5pt; line-height: 1.5; color: ${apoyo} }
.escalones figcaption .cifra { color: ${texto}; font-family: ${marca.tipos.display.css}; font-weight: 700 }

/* Color */
.tabla-color { width: 100%; border-collapse: collapse; font-size: 9.5pt }
.tabla-color th { text-align: left; font-family: ${marca.tipos.display.css}; font-weight: 600 }
.tabla-color thead th { font-size: 8pt; letter-spacing: .1em; text-transform: uppercase; color: ${apoyo}; padding-bottom: 2mm }
.tabla-color td, .tabla-color tbody th { padding: 2.6mm 3mm 2.6mm 0; border-top: 1px solid ${apoyo}44; vertical-align: middle }
.tabla-color small { color: ${apoyo}; font-size: 7.5pt; margin-left: .4em }
.muestra { display: block; width: 13mm; height: 9mm; border: 1px solid ${texto}22 }
.uso { color: ${apoyo} }
.sello { font-family: ${marca.tipos.display.css}; font-size: 8pt; font-weight: 700; letter-spacing: .08em; padding: .8mm 2mm; background: ${texto}; color: ${fondo} }
.sello--mal { background: #B00020; color: #fff }
.proporcion { display: flex; height: 9mm; margin-top: 1mm; border: 1px solid ${texto}55 }
.proporcion span + span { border-left: 1px solid ${texto}55 }

/* Tipografía */
.tipos { display: grid; grid-template-columns: 1fr 1fr; gap: 8mm }
.espec-display { font-family: ${marca.tipos.display.css}; font-size: 44pt; line-height: 1; font-weight: 700; margin: 3mm 0 }
.espec-cifras { font-family: ${marca.tipos.display.css}; font-size: 16pt; font-weight: 600 }
.espec-texto { font-size: 15pt; line-height: 1.45; margin: 3mm 0 }
.nota { font-size: 9.5pt; color: ${apoyo}; line-height: 1.5; margin-top: 2mm }
.jerarquia { width: 100%; border-collapse: collapse; font-size: 9.5pt; margin-top: 2mm }
.jerarquia th { text-align: left; width: 22mm; font-family: ${marca.tipos.display.css}; font-size: 8pt; letter-spacing: .1em; text-transform: uppercase; color: ${apoyo} }
.jerarquia td { padding: 1.6mm 0; border-top: 1px solid ${apoyo}44 }
.jerarquia td:last-child { color: ${apoyo}; text-align: right }
.j-display { font-family: ${marca.tipos.display.css}; font-size: 20pt; font-weight: 700 }
.j-h1 { font-family: ${marca.tipos.display.css}; font-size: 15pt; font-weight: 700 }
.j-h2 { font-family: ${marca.tipos.display.css}; font-size: 12pt; font-weight: 600 }
.j-cuerpo { font-size: 11pt } .j-etiqueta { font-size: 8.5pt; letter-spacing: .06em; text-transform: uppercase }

/* Componentes */
.estados { display: grid; grid-template-columns: repeat(6, 1fr); gap: 4mm }
.estados figcaption { font-size: 8.5pt; color: ${apoyo}; margin-top: 2mm; text-align: center }
.btn {
  width: 100%; font-family: ${marca.tipos.display.css}; font-size: 10pt; font-weight: 700;
  padding: 3.4mm 3mm; border: 2px solid transparent; background: ${acento}; color: ${fondo};
  display: flex; align-items: center; justify-content: center; gap: 2mm; cursor: default;
}
.btn.ancho { width: 100%; margin-top: 3mm }
.e1 { filter: brightness(.88) }
.e2 { filter: brightness(.76); transform: translateY(1px) }
.e3 { opacity: .92 }
.e4 { background: ${apoyo}55; color: ${apoyo} }
.e5 { outline: 3px solid ${texto}; outline-offset: 2px }
.rueda { width: 3mm; height: 3mm; border: 1.6px solid ${fondo}; border-top-color: transparent; border-radius: 50% }
.otros { display: grid; grid-template-columns: 1fr 1.3fr 1fr; gap: 6mm; align-items: start }
.campo label { display: block; font-size: 9pt; color: ${apoyo}; margin: 2mm 0 1.4mm }
.entrada { border: 1.5px solid ${texto}; padding: 3mm; font-size: 11pt; background: ${P.blanco ?? P.cal ?? '#fff'} }
.horas { display: flex; flex-wrap: wrap; gap: 2mm; margin-top: 2mm }
.hora { font-family: ${marca.tipos.display.css}; font-size: 10pt; font-weight: 600; padding: 2.4mm 3mm; border: 1.5px solid ${texto}; background: ${P.blanco ?? P.cal ?? '#fff'} }
.hora--elegida { background: ${acento}; color: ${fondo}; border-color: ${acento} }
.hora--ida { color: ${apoyo}; border-color: ${apoyo}66; text-decoration: line-through }
.aviso { margin-top: 2mm; border-left: 3px solid ${acento}; padding: 2mm 0 2mm 3mm; font-size: 10pt; line-height: 1.45 }

/* Pantalla */
.con-telefono { display: grid; grid-template-columns: 390px 1fr; gap: 10mm; flex: 1; align-items: start }
.telefono { width: 390px; height: 132mm; background: ${P.blanco ?? P.cal ?? '#fff'}; border: 1.5px solid ${texto}; display: flex; flex-direction: column; overflow: hidden }
.app-cabecera { display: flex; align-items: center; gap: 3mm; padding: 3mm 4mm; border-bottom: 1px solid ${apoyo}44; font-size: 9pt; color: ${apoyo} }
.app-entrar { margin-left: auto; color: ${texto}; font-weight: 700 }
.app-cuerpo { padding: 4mm; flex: 1 }
.app-h1 { font-family: ${marca.tipos.display.css}; font-size: 17pt; font-weight: 700; line-height: 1.15 }
.app-dir, .app-nota { font-size: 9.5pt; color: ${apoyo}; margin-top: 1mm }
.app-cuerpo .rotulo { margin: 4mm 0 1.6mm }
.app-servicios { list-style: none; font-size: 10pt }
.app-servicios li { display: flex; justify-content: space-between; padding: 2.2mm 2mm; border-bottom: 1px solid ${apoyo}33 }
.app-servicios .elegido { background: ${acento}18; border-left: 3px solid ${acento}; font-weight: 700 }
.app-horas { display: flex; flex-wrap: wrap; gap: 1.6mm; font-family: ${marca.tipos.display.css}; font-size: 9.5pt; font-weight: 600 }
.app-horas span { padding: 2mm 2.6mm; border: 1.4px solid ${texto} }
.app-horas .sel { background: ${acento}; color: ${fondo}; border-color: ${acento} }
.app-pestanas { display: flex; border-top: 1px solid ${apoyo}44; font-size: 8.5pt; color: ${apoyo} }
.app-pestanas span { flex: 1; text-align: center; padding: 3mm 0 }
.app-pestanas .on { color: ${texto}; font-weight: 700; box-shadow: inset 0 2px 0 ${acento} }
.explica p { font-size: 10.5pt; line-height: 1.55; margin-bottom: 4mm; max-width: 52ch }

/* Voz y cierre */
.voz { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm 8mm }
.voz p { font-size: 12pt; line-height: 1.4; padding: 3mm 0; border-top: 1px solid ${apoyo}44 }
.voz .rotulo { display: block; margin-bottom: 1mm }
.voz .no { color: ${apoyo}; text-decoration: line-through ${apoyo} }
.cierre { display: grid; grid-template-columns: 90mm 1fr; gap: 10mm; align-items: end; flex: 1 }
.tarjeta { background: ${texto}; color: ${fondo}; padding: 8mm; height: 52mm; display: flex; flex-direction: column; justify-content: space-between }
.t-nombre { font-family: ${marca.tipos.display.css}; font-size: 15pt; font-weight: 700 }
.t-linea { font-size: 9pt; opacity: .75 }
.firma { font-size: 10.5pt; line-height: 1.55; color: ${apoyo}; max-width: 56ch }

/* Estrategia */
.nota-nombre { font-size: 11pt; line-height: 1.55; max-width: 80ch }
.verdades { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8mm; margin-top: 2mm }
.verdades h3 { font-family: ${marca.tipos.display.css}; font-size: 13pt; font-weight: 700; margin: 2mm 0 1.6mm }
.verdades p { font-size: 10.5pt; line-height: 1.55; color: ${apoyo} }
.ordinal { font-family: ${marca.tipos.display.css}; font-size: 30pt; font-weight: 700; color: ${acento}; line-height: 1 }
`

const editorial = `
.portada-editorial { display: flex; flex-direction: column; gap: 5mm; flex: 1 }
.filete { height: 2px; background: ${texto} }
.cabecera-portada { display: flex; align-items: center; justify-content: space-between }
.titulazo { font-family: ${marca.tipos.display.css}; font-size: 86pt; line-height: .92; font-weight: 800; font-stretch: 112%; letter-spacing: -.02em; margin-top: 6mm }
.promesa { font-size: 17pt; line-height: 1.3; max-width: 34ch; margin-bottom: 6mm }
.pie-portada { display: flex; align-items: flex-end; justify-content: space-between; gap: 10mm; flex: 1; padding-bottom: 4mm }
.entradilla { font-family: ${marca.tipos.texto.css}; font-size: 22pt; line-height: 1.32; max-width: 30ch; color: ${acento} }
.marca-fantasma { color: ${texto}12 }
.titulo { font-family: ${marca.tipos.texto.css}; font-weight: 600 }
.pieza--llena, .pieza--arco::before { background: ${acento} }
`

const sistema = `
.portada-sistema { display: flex; flex-direction: column; gap: 6mm; flex: 1 }
.barra { display: flex; justify-content: space-between; background: ${texto}; color: ${fondo}; padding: 2.6mm 4mm; font-family: ${marca.tipos.display.css}; font-size: 9pt; font-weight: 700; letter-spacing: .18em }
.centro { display: flex; align-items: center; gap: 10mm; flex: 1 }
.titulazo { font-family: ${marca.tipos.display.css}; font-size: 92pt; font-weight: 900; letter-spacing: -.045em; line-height: .9 }
.promesa { font-family: ${marca.tipos.texto.css}; font-size: 13pt; letter-spacing: -.01em }
.rejilla-cupos { display: grid; grid-template-columns: repeat(12, 1fr); gap: 2mm; height: 22mm }
.rejilla-cupos i { background: ${texto} }
.rejilla-cupos i.libre { background: ${acento} }
.titulo { letter-spacing: -.03em }
.rotulo { letter-spacing: .18em }
.pieza--arco::before { border-radius: 0; inset: auto -10% -40%; height: 90% }
`

const bloques = `
.portada-bloques { display: grid; grid-template-columns: 1fr 1.25fr; grid-template-rows: 1fr 1fr; gap: 4mm; flex: 1 }
.bloque { padding: 8mm; display: flex; flex-direction: column; justify-content: flex-end }
.bloque--cobalto { background: ${P.cobalto}; color: ${P.hueso}; align-items: center; justify-content: center }
.bloque--hueso { background: ${P.hueso}; grid-row: span 2; border: 1.5px solid ${texto} }
.bloque--fucsia { background: ${P.fucsia}; color: ${P.hueso} }
.bloque--amarillo { background: ${P.amarillo}; color: ${texto} }
.titulazo { font-family: ${marca.tipos.display.css}; font-size: 76pt; font-weight: 700; line-height: .95; letter-spacing: -.03em }
.promesa { font-size: 15pt; line-height: 1.35; margin-top: 4mm; max-width: 26ch }
.grito, .dato { font-family: ${marca.tipos.display.css}; font-size: 30pt; font-weight: 700; line-height: 1 }
.v--tinta { background: ${P.cobalto} }
.pieza--llena { background: ${P.cobalto}; color: ${P.hueso} }
.pieza--arco::before { background: ${P.amarillo} }
.pieza--cifras { color: ${P.cobalto} }
`

const propio = { editorial, sistema, bloques }[marca.layout] ?? ''

/* ── El archivo ──────────────────────────────────────────────────────────────────────────── */

const html = `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>${marca.nombre} · Manual de marca</title>
<link rel="stylesheet" href="./fuentes/fuentes.css">
<style>${comun}${propio}</style>
</head>
<body>
${[portada(), estrategia(), moodboard(), logotipo(), icono(), color(), tipografia(), componentes(), pantalla(), voz()].join('\n')}
</body>
</html>
`

writeFileSync(path.join(raiz, 'libro.html'), html)

const problemas = marca.paleta
  .map((c) => ({ c, r: Math.max(ratio(c.hex, fondo), ratio(c.hex, texto)) }))
  .filter(({ r }) => r < 4.5)
console.log(`${marca.nombre}: 10 páginas escritas en ${path.relative(process.cwd(), path.join(raiz, 'libro.html'))}`)
for (const { c, r } of problemas) {
  console.log(`  ⚠ ${c.nombre} (${c.hex}) queda en ${r.toFixed(2)}:1 — solo vale para bloque, no para texto`)
}
