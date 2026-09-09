/**
 * Que el salón pueda apuntar una cita de teléfono, que es como entran casi todas (AGD-2).
 *
 * No se comprueba que el formulario exista: se comprueba **la consecuencia**. Una cita apuntada
 * tiene que aparecer en el día que se está mirando, y el contador de citas del día tiene que
 * subir. Un formulario que se envía y no cambia nada es exactamente el fallo que esto busca.
 *
 * La hora se pide **al motor**, no se elige a ojo. Ya me he engañado tres veces escribiendo
 * pruebas con una hora inventada que resultó estar ocupada, y el resultado es una prueba que
 * falla por el motivo equivocado o, peor, que pasa sin probar nada.
 */

import { abrirNavegador, nuevaPagina, sembrarSesion, esperarAQueSeQuede, medirAncho, API, WEB } from './comun.mjs';

const bien = [];
const mal = [];
const ok = (que, detalle = '') => { bien.push(que); console.log(`ok   ${que}${detalle ? ' · ' + detalle : ''}`); };
const nok = (que, detalle = '') => { mal.push(que); console.log(`MAL  ${que}${detalle ? ' · ' + detalle : ''}`); };

const j = async (r) => { const t = await r.text(); try { return JSON.parse(t) } catch { return t } };

/**
 * Un ISO a lo que espera un `datetime-local`, **pasando por la zona del salón**.
 *
 * Aquí me engañé yo: la primera versión cortaba el ISO por posiciones (`slice(11, 16)`) y
 * daba por hecho que ahí había hora de Panamá. La API es libre de contestar `…T23:15:00Z` o
 * `…T18:15:00-05:00` —las dos llevan desplazamiento explícito, que es lo que pide ADR-0003, y
 * la respuesta trae además la zona—, así que cortar por posiciones **acierta o miente según
 * cuál toque**. Salió a la luz porque la prueba anunció una barbería cerrando a las once y
 * cuarto de la noche.
 */
function paraElCampo(iso) {
  const partes = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'America/Panama', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date(iso));
  return partes.replace(' ', 'T');
}

/**
 * Un acceso **con el salón fijado**, que es lo que pide la API del negocio.
 *
 * Con el acceso a secas de `/auth/entrar` la agenda del día contesta vacía en vez de negarse, y
 * la primera versión de esta prueba se lo tragó: contaba `0 → 0` y cantaba un fallo que no
 * existía mientras la pantalla funcionaba perfectamente. Un token sin negocio no es un token
 * inválido, y esa diferencia es justo la que engaña.
 */
async function entrarComoDueno() {
  const r = await fetch(`${API}/api/v1/auth/entrar`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ correo: 'dueno.barberia-el-cangrejo@demo.pa', contrasena: 'demo-panama-2026', superficie: 'web' }),
  });
  const suelto = await j(r);
  const suyos = await j(await fetch(`${API}/api/v1/mi/negocios`, { headers: { Authorization: `Bearer ${suelto.acceso}` } }));
  const enModo = await j(await fetch(`${API}/api/v1/auth/modo-negocio`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${suelto.acceso}` },
    body: JSON.stringify({ negocio_id: suyos[0].id, superficie: 'web' }),
  }));
  return enModo.acceso;
}

/**
 * Una hora que **el motor** dice que está libre, y **dentro de los días que la agenda enseña**.
 *
 * Las dos condiciones importan. La hora sale del motor porque elegirla a ojo ya me ha salido
 * mal tres veces: se cae encima de una cita existente y la prueba falla por un motivo que no
 * es el suyo. Y el día tiene que estar entre los cuatro que ofrece la pantalla —de ayer a
 * pasado— o la cita se apuntaría en un día que nadie está mirando, y comprobar que «aparece
 * sin recargar» sería imposible por construcción.
 */
async function huecoDeVerdad() {
  const ficha = await j(await fetch(`${API}/api/v1/publico/negocios/barberia-el-cangrejo`));
  const servicio = ficha.servicios[0];
  const d = (n) => new Date(Date.now() + n * 86400000).toISOString().slice(0, 10);
  const disp = await j(await fetch(
    `${API}/api/v1/publico/negocios/barberia-el-cangrejo/disponibilidad?servicios=${servicio.id}&desde=${d(0)}&hasta=${d(3)}`,
  ));
  const dias = [d(-1), d(0), d(1), d(2)];  // los mismos cuatro botones de la pantalla
  const libres = disp.slots.filter((s) => s.profesional_id && dias.includes(s.inicio.slice(0, 10)));
  if (libres.length === 0) throw new Error('El motor no ofrece ni un hueco en los días que la agenda enseña.');
  const hueco = libres[libres.length - 1];
  return { hueco, servicio, salto: dias.indexOf(hueco.inicio.slice(0, 10)) };
}

const navegador = await abrirNavegador();
try {
  const acceso = await entrarComoDueno();
  const { hueco, salto, servicio } = await huecoDeVerdad();
  const equipo = await j(await fetch(`${API}/api/v1/negocio/profesionales`, { headers: { Authorization: `Bearer ${acceso}` } }));
  const quienAtiende = equipo.find((persona) => persona.id === hueco.profesional_id)?.nombre;
  if (!quienAtiende) throw new Error('El hueco nombra a alguien que no está en el equipo del salón.');
  const dia = hueco.inicio.slice(0, 10);
  let respuestaAlApuntar = null;

  const pagina = await nuevaPagina(navegador);
  pagina.on('response', async (respuesta) => {
    if (respuesta.request().method() === 'POST' && respuesta.url().includes('/negocio/reservas')) {
      respuestaAlApuntar = { estado: respuesta.status(), cuerpo: await respuesta.text() };
    }
  });
  await sembrarSesion(pagina, 'dueno');
  await pagina.goto(`${WEB}/local`, { waitUntil: 'domcontentloaded' });
  await esperarAQueSeQuede(pagina);

  // Primero se lleva la agenda al día del hueco: se apunta en el día que se está mirando.
  await pagina.locator('.seccion--corta .opciones').last().locator('button').nth(salto).click();
  await esperarAQueSeQuede(pagina);

  const abrir = pagina.getByRole('button', { name: 'Apuntar una cita' });
  if (await abrir.count() === 0) { nok('la agenda ofrece apuntar una cita'); throw new Error('sin botón'); }
  ok('la agenda ofrece apuntar una cita');

  await abrir.first().click();
  await pagina.waitForSelector('.apuntar form', { timeout: 15000 });

  // A 390 px, con el panel abierto y su fila de servicios dentro.
  const ancho = await medirAncho(pagina);
  if (ancho.scrollWidth <= ancho.clientWidth) ok('con el panel abierto la página no se va de lado', `${ancho.scrollWidth} px`);
  else nok('con el panel abierto la página se va de lado', `${ancho.scrollWidth} px · ${ancho.culpables.join(' | ')}`);

  // Antes de apuntar: cuántas citas dice el día.
  const contarCitas = async () => {
    const antes = await j(await fetch(`${API}/api/v1/negocio/agenda/columnas?dia=${dia}`, { headers: { Authorization: `Bearer ${acceso}` } }));
    return (antes.columnas ?? []).reduce((n, c) => n + c.citas.filter((x) => !x.estado.startsWith('cancelada')).length, 0);
  };

  // El día que la pantalla mira tiene que ser el del hueco: se navega con el selector si hace falta.
  await pagina.evaluate(() => window.scrollTo(0, 0));
  const antesDeTodo = await contarCitas();
  // El día que se apunta **es el que la pantalla enseña**, y por eso la cita tiene que verse
  // sin recargar. Se pone la hora del hueco dentro de ese mismo día.

  const persona = 'Prueba Teléfono ' + Date.now().toString().slice(-5);

  // **Se elige a quien ofrece el hueco y el servicio con el que se calculó**, no el primer
  // botón de cada fila. Con el primero la prueba pasaba o fallaba según a quién le tocara
  // estar arriba: la hora estaba libre para una persona y ocupada para otra, y el 409 que
  // salía no decía nada del código. Es la cuarta vez que me engaño igual — dar por buena una
  // hora que el motor nunca dijo que estuviera libre **para esa persona**.
  await pagina.locator('.apuntar .opciones button', { hasText: quienAtiende }).first().click();
  await pagina.locator('.apuntar .opciones button', { hasText: servicio.nombre }).first().click();
  await pagina.fill('#apuntar-cuando', paraElCampo(hueco.inicio));
  await pagina.fill('#apuntar-nombre', persona);
  await pagina.fill('#apuntar-telefono', '+50760001234');

  const total = await pagina.locator('.apuntar [role="status"]').first().textContent().catch(() => null);
  if (total && /termina a las/.test(total)) ok('dice a qué hora termina antes de apuntar', total.trim());
  else nok('no dice a qué hora termina', String(total));

  await pagina.getByRole('button', { name: 'Apuntar la cita' }).click();
  await pagina.waitForSelector('.bloque--exito, .campo__fallo', { timeout: 20000 }).catch(() => null);

  if (respuestaAlApuntar?.estado === 201) ok('la API acepta la cita del mostrador');
  else nok('la API no aceptó la cita', JSON.stringify(respuestaAlApuntar).slice(0, 180));

  const despues = await contarCitas();
  if (despues === antesDeTodo + 1) ok('la cita apuntada existe de verdad', `${antesDeTodo} → ${despues} citas el ${dia}`);
  else nok('la cita no llegó a la agenda', `${antesDeTodo} → ${despues}`);

  // Y se ve **dentro del día**, no solo en la base ni en el aviso de «apuntada».
  //
  // Buscar el nombre en toda la página no valía para nada, y lo demostró la rotura: con el
  // refresco de la agenda desconectado a propósito, la prueba seguía en verde porque
  // encontraba el nombre en el propio aviso de éxito. Lo que hay que mirar es el riel del día,
  // que es donde el salón busca a quién le toca ahora.
  const enElDia = await pagina.locator('.riel').getByText(persona).count();
  if (enElDia > 0) ok('y se ve en el día sin recargar');
  else nok('no aparece en el día: la agenda no se refrescó tras apuntar');

  if (pagina.problemas.length > 0) nok('la consola del navegador se queja', pagina.problemas.slice(0, 2).join(' | '));
  else ok('sin errores en la consola');
} finally {
  await navegador.close();
}

console.log(`\n${bien.length} bien · ${mal.length} mal`);
if (mal.length > 0) process.exit(1);
console.log('El salón puede apuntar una cita de teléfono y aparece en el día.');
