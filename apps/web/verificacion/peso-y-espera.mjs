/**
 * Cuánto pesa y cuánto se espera, **en gama media con 3G** (requisito no funcional del brief).
 *
 * Es el hueco que dejaba «Lighthouse sin medir». No se ejecuta Lighthouse: se miden las tres
 * cosas por las que Lighthouse puntúa y que aquí importan de verdad, contra el mismo navegador
 * y con la red y el procesador frenados a lo que tiene un teléfono de 120 dólares en Panamá.
 *
 * **Contra el build de producción, no contra el de desarrollo.** El de desarrollo sirve los
 * módulos sin empaquetar ni minimizar: medir ahí y llamarlo rendimiento es medir otra cosa y
 * dar un número que no le pasa a nadie. Por eso esta comprobación levanta su propio servidor.
 *
 *   BASE=http://localhost:3101 node verificacion/peso-y-espera.mjs
 *
 * Qué se mide:
 *
 * · **LCP** — cuándo aparece lo grande de la pantalla. Es lo que la persona llama «ha cargado».
 * · **CLS** — cuánto se mueve lo ya pintado. Un botón que salta bajo el dedo hace tocar otra
 *   cosa, y en una pantalla de reservar eso es reservar otra hora.
 * · **Los bytes que viajan** — en un plan prepago de Panamá los megas se pagan, y el peso es lo
 *   único de esta lista que no mejora con un teléfono mejor.
 *
 * El peso se cuenta **comprimido, que es lo que viaja**, y no descomprimido. La primera versión
 * de esto contaba el cuerpo ya descomprimido y daba 433 kB de JavaScript en la portada; lo que
 * de verdad sale por el cable son 135. Un número tres veces peor que el real no es prudencia:
 * es un número falso, y con él se «arreglan» cosas que no estaban rotas. Se enseñan los dos,
 * porque el descomprimido también cuenta para algo distinto —es lo que el procesador tiene que
 * leer— y en un teléfono lento eso se nota.
 *
 * Los topes son los de Google para «bueno»/«aceptable», con una excepción escrita: **LCP a 4 s**
 * y no a 2,5, porque 2,5 es el listón de una conexión normal y aquí se mide con 3G frenado
 * a propósito. Fingir que se cumple el de escritorio en una red de móvil sería trampa.
 */

import { chromium } from 'playwright';

const BASE = process.env.BASE ?? 'http://localhost:3101';

/** «Slow 3G» tal y como lo define Chrome, y un procesador cuatro veces más lento. */
const RED_3G = { latency: 400, downloadThroughput: (400 * 1024) / 8, uploadThroughput: (400 * 1024) / 8 };
const CPU_LENTA = 4;

//: Topes sobre lo que **viaja**. LCP a 4 s y no a 2,5 porque 2,5 es el listón de una conexión
//: normal y aquí se mide con 3G frenado a propósito; fingir el de escritorio en una red de
//: móvil sería trampa. Los de peso salen de lo que hoy se mide, con holgura: están para que un
//: descuido se note, no para aprobar por los pelos.
const TOPES = { lcp: 4000, cls: 0.1, viaja: 300 * 1024, jsViaja: 200 * 1024 };

/**
 * Las cinco que decide la gente. Si estas van, el resto va.
 *
 * La tercera columna es **la señal**: qué tiene que estar en pantalla para que la persona pueda
 * seguir. Solo la lleva el mapa, y por un motivo que hay que decir en vez de esconder: **lo más
 * grande de esa pantalla es una baldosa de OpenStreetMap**, que ni es nuestra ni la servimos, y
 * a 3G tarda diez segundos. Medir el LCP ahí y llamarlo nuestro rendimiento es medir la red de
 * otro. Lo que sí es nuestro —y lo único que de verdad hace falta para elegir salón— es la
 * lista de debajo, que además es la que se puede leer con un lector de pantalla. Esa se mide y
 * esa manda; el LCP se sigue enseñando al lado, para que la lentitud de las baldosas no
 * desaparezca del informe.
 */
const PANTALLAS = [
  ['/', 'La portada'],
  ['/buscar', 'Buscar'],
  ['/salon/barberia-el-cangrejo', 'La ficha de un salón'],
  ['/reservar/barberia-el-cangrejo', 'Reservar'],
  ['/mapa', 'El mapa', '.fila-mapa'],
];

const bien = [];
const mal = [];

const navegador = await chromium.launch();
try {
  for (const [ruta, nombre, senal] of PANTALLAS) {
    const contexto = await navegador.newContext({ viewport: { width: 390, height: 844 } });
    const pagina = await contexto.newPage();

    const cdp = await contexto.newCDPSession(pagina);
    await cdp.send('Network.emulateNetworkConditions', { offline: false, ...RED_3G });
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: CPU_LENTA });

    // La señal se empieza a esperar **antes** de navegar, para cronometrarla desde el principio
    // y no desde que `load` termina.
    const arranque = Date.now();
    const esperaSenal = senal
      ? pagina.waitForSelector(senal, { timeout: 120_000 }).then(() => Date.now() - arranque).catch(() => null)
      : Promise.resolve(null);

    await pagina.goto(`${BASE}${ruta}`, { waitUntil: 'load', timeout: 120_000 });
    // Se deja respirar: el LCP puede llegar después de `load` —una imagen, un dato de la API— y
    // medir justo en `load` da un número bonito que nadie vive.
    await pagina.waitForTimeout(6000);

    const medidas = await pagina.evaluate(
      () =>
        new Promise((listo) => {
          let lcp = 0;
          let cls = 0;
          new PerformanceObserver((lista) => {
            for (const entrada of lista.getEntries()) lcp = Math.max(lcp, entrada.startTime);
          }).observe({ type: 'largest-contentful-paint', buffered: true });
          new PerformanceObserver((lista) => {
            for (const entrada of lista.getEntries()) if (!entrada.hadRecentInput) cls += entrada.value;
          }).observe({ type: 'layout-shift', buffered: true });

          setTimeout(() => {
            // `transferSize` es lo que salió por el cable, con su compresión y sus cabeceras;
            // `decodedBodySize`, lo que el navegador acaba teniendo en memoria. El documento
            // entra aparte: no aparece en la lista de recursos.
            const documento = performance.getEntriesByType('navigation')[0] ?? {};
            let viaja = documento.transferSize ?? 0;
            let pesa = documento.decodedBodySize ?? 0;
            let jsViaja = 0;
            let jsPesa = 0;
            let deFuera = 0;
            for (const recurso of performance.getEntriesByType('resource')) {
              // Un recurso de otro dominio sin `Timing-Allow-Origin` reporta 0 y **no se
              // cuenta como si fuera gratis**: se dice cuántos hay. En el mapa son las
              // baldosas de OpenStreetMap.
              if (recurso.transferSize === 0 && recurso.decodedBodySize === 0) {
                deFuera += 1;
                continue;
              }
              viaja += recurso.transferSize;
              pesa += recurso.decodedBodySize;
              if (recurso.initiatorType === 'script' || /\.js(\?|$)/.test(recurso.name)) {
                jsViaja += recurso.transferSize;
                jsPesa += recurso.decodedBodySize;
              }
            }
            listo({
              lcp: Math.round(lcp),
              cls: Math.round(cls * 1000) / 1000,
              viaja,
              pesa,
              jsViaja,
              jsPesa,
              deFuera,
            });
          }, 500);
        }),
    );

    const tiempoSenal = await esperaSenal;

    const kb = (n) => `${Math.round(n / 1024)} kB`;
    const fallos = [];
    if (senal) {
      if (tiempoSenal === null) fallos.push(`«${senal}» no llegó a aparecer`);
      else if (tiempoSenal > TOPES.lcp) fallos.push(`«${senal}» tardó ${tiempoSenal} ms > ${TOPES.lcp}`);
    } else if (medidas.lcp > TOPES.lcp) {
      fallos.push(`LCP ${medidas.lcp} ms > ${TOPES.lcp}`);
    }
    if (medidas.cls > TOPES.cls) fallos.push(`CLS ${medidas.cls} > ${TOPES.cls}`);
    if (medidas.viaja > TOPES.viaja) fallos.push(`viajan ${kb(medidas.viaja)} > ${kb(TOPES.viaja)}`);
    if (medidas.jsViaja > TOPES.jsViaja) fallos.push(`JS ${kb(medidas.jsViaja)} > ${kb(TOPES.jsViaja)}`);

    const detalle =
      (senal ? `lista en ${tiempoSenal} ms · LCP ${medidas.lcp} ms (baldosas de fuera)` : `LCP ${medidas.lcp} ms`) +
      ` · CLS ${medidas.cls} · ` +
      `viajan ${kb(medidas.viaja)} (${kb(medidas.jsViaja)} de JS) · ` +
      `en memoria ${kb(medidas.pesa)}` +
      (medidas.deFuera > 0 ? ` · ${medidas.deFuera} recursos de fuera sin medir` : '');
    if (fallos.length === 0) {
      bien.push(ruta);
      console.log(`ok   ${nombre.padEnd(22)} ${detalle}`);
    } else {
      mal.push(ruta);
      console.log(`MAL  ${nombre.padEnd(22)} ${detalle} · ${fallos.join(' · ')}`);
    }
    await contexto.close();
  }
} finally {
  await navegador.close();
}

console.log(`\n${bien.length} bien · ${mal.length} mal · red 3G lenta y procesador 4× más lento`);
if (mal.length > 0) process.exit(1);
console.log('Las cinco pantallas que decide la gente cargan y no bailan en un teléfono de gama media.');
