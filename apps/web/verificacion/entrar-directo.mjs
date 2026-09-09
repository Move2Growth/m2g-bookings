/**
 * Entrar **directo** a cada pantalla del salón, como quien tiene un marcador.
 *
 * Esta verificación existe porque las demás no podían encontrar lo que encontró: todas
 * recorrían el producto **por dentro**, entrando por la agenda del día y navegando desde ahí.
 * Y la agenda es justo la pantalla que pone la sesión en modo negocio. Así que el camino por
 * el que entra media plantilla —un marcador a «El dinero», una recarga, un enlace pegado en el
 * grupo de WhatsApp del salón— no lo pisaba nadie.
 *
 * Por ahí, todas las pantallas del portal contestaban `403` y «El equipo» decía «esto no
 * cargó». Todas las mañanas.
 *
 * Lo que se comprueba es lo mínimo y lo que importa: **ninguna llamada a la API falla y ninguna
 * pantalla enseña su estado de error**. Sin clics, sin navegar: se abre la URL y ya.
 */

import { abrirNavegador, nuevaPagina, sembrarSesion, esperarAQueSeQuede, WEB } from './comun.mjs';

/** Cada puerta del salón, y quién tiene que poder abrirla. */
const PUERTAS = [
  ['/local', 'dueno'],
  ['/local/equipo', 'dueno'],
  ['/local/horario', 'dueno'],
  ['/local/finanzas', 'dueno'],
  ['/local/mejor-del-mes', 'dueno'],
  ['/local/publicidad', 'dueno'],
  //: **Las del profesional también**, y no por simetría: su día es la pantalla que abre cada
  //: mañana, la más marcada de todo el producto. Se quedaron fuera del primer arreglo —que solo
  //: tocó la puerta del dueño— y siguieron rotas dos horas más, hasta que el barrido de
  //: pantallas las pilló diciendo «Cambia a modo negocio para hacer eso».
  ['/mi-agenda', 'profesional'],
  ['/mi-ficha', 'profesional'],
  ['/mis-citas', 'clienta'],
];

const bien = [];
const mal = [];

const navegador = await abrirNavegador();
try {
  for (const [ruta, cuenta] of PUERTAS) {
    const pagina = await nuevaPagina(navegador);
    // **Sesión de plataforma a secas.** Es la que deja `/entrar`, y es la que tiene alguien que
    // cierra el navegador y vuelve al día siguiente por su marcador.
    await sembrarSesion(pagina, cuenta);

    const rechazos = [];
    pagina.on('response', (respuesta) => {
      if (respuesta.status() >= 400 && respuesta.url().includes('/api/v1/')) {
        rechazos.push(`${respuesta.status()} ${respuesta.url().split('/api/v1')[1].split('?')[0]}`);
      }
    });

    await pagina.goto(`${WEB}${ruta}`, { waitUntil: 'domcontentloaded' });
    await esperarAQueSeQuede(pagina).catch(() => {});
    // Un latido más: los estados de error llegan después de que se apague lo de «cargando».
    await pagina.waitForTimeout(1500);

    const texto = (await pagina.locator('main').innerText()).replace(/\s+/g, ' ');
    const roto = /no cargó|no se pudo|vuelve a intentarlo/i.test(texto);

    if (rechazos.length === 0 && !roto) {
      bien.push(ruta);
      console.log(`ok   ${ruta.padEnd(22)} abre entrando directo`);
    } else {
      mal.push(ruta);
      console.log(`MAL  ${ruta.padEnd(22)} ${rechazos.length ? 'rechazos: ' + [...new Set(rechazos)].join(', ') : ''}${roto ? ' · la pantalla enseña su estado de error' : ''}`);
    }
    await pagina.context().close();
  }
} finally {
  await navegador.close();
}

console.log(`\n${bien.length} bien · ${mal.length} mal`);
if (mal.length > 0) process.exit(1);
console.log('Todas las puertas del salón abren entrando directo, sin pasar antes por la agenda.');
