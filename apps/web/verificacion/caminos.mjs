/**
 * Los cinco caminos del listón, recorridos a 390 px con toques de verdad.
 *
 * No comprueba que las pantallas compilen: comprueba que **se llega de punta a punta**. Cada
 * paso deja una captura en `verificacion/capturas/camino-*` y grita si algo no aparece.
 *
 *   node verificacion/caminos.mjs
 */

import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  abrirNavegador,
  animacionesEnMarcha,
  API,
  CUENTAS,
  esperarAQueSeQuede,
  medirAncho,
  medirContraste,
  nuevaPagina,
  sembrarSesion,
  WEB,
} from './comun.mjs';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const CAPTURAS = path.join(AQUI, 'capturas');
await mkdir(CAPTURAS, { recursive: true });

const navegador = await abrirNavegador();
let fallos = 0;

function decir(texto) {
  console.log(texto);
}

/** Una afirmación suelta, para lo que no es una pantalla sino un hecho del camino. */
function afirmar(bien, texto, extra = '') {
  if (!bien) fallos += 1;
  decir(`${bien ? '  ok ' : 'FALLA'} · ${texto}${extra ? ` · ${extra}` : ''}`);
}

/**
 * Cada paso del camino se mide entero: que lo que se esperaba está, que no desborda a 390 px y
 * que **ninguna combinación de texto baja de AA**. Esto último importa aquí y no solo en el
 * barrido de pantallas: el resumen de la reserva o el aviso de cancelar solo existen si alguien
 * toca, y son justo las pantallas donde se decide algo.
 */
async function comprobar(pagina, etiqueta, condicion) {
  const ancho = await medirAncho(pagina);
  const bien = await condicion();
  const contraste = await medirContraste(pagina);
  const flojos = contraste.filter((medida) => !medida.pasa);
  const animaciones = await animacionesEnMarcha(pagina);
  const todoBien = bien && ancho.scrollWidth <= 390 && flojos.length === 0;
  if (!todoBien) fallos += 1;
  decir(
    `${todoBien ? '  ok ' : 'FALLA'} · ${etiqueta.padEnd(52)} · ancho ${ancho.scrollWidth} · AA ${contraste.length - flojos.length}/${contraste.length} · anim ${animaciones.length}`,
  );
  flojos.forEach((medida) => decir(`        ${medida.razon}:1 (mín ${medida.minimo}) ${medida.selector} «${medida.texto}»`));
  if (ancho.scrollWidth > 390) decir(`        culpables: ${ancho.culpables.join(' | ')}`);
}

async function foto(pagina, nombre) {
  await pagina.screenshot({ path: path.join(CAPTURAS, `${nombre}.png`), fullPage: true });
}

/**
 * Recorre las fichas de día hasta dar con una que tenga huecos.
 *
 * Hace falta porque los datos son de verdad: si la agenda de esa persona se llena, «hoy» deja
 * de tener horas y una prueba que diera por hecho que hoy siempre hay algo estaría mintiendo.
 */
async function elegirDiaConHoras(pagina) {
  const dias = pagina.locator('.opciones button', { hasText: /./ });
  const cuantos = await pagina.locator('section[aria-label="Elegir día y hora"] .opciones button').count();
  for (let indice = 0; indice < cuantos; indice += 1) {
    await pagina.locator('section[aria-label="Elegir día y hora"] .opciones button').nth(indice).click();
    await pagina.waitForTimeout(400);
    await esperarAQueSeQuede(pagina);
    if ((await pagina.locator('.hora').count()) > 0) {
      return pagina.locator('section[aria-label="Elegir día y hora"] .opciones button').nth(indice).innerText();
    }
  }
  void dias;
  return null;
}

/* ═══ 1 · Descubrir: portada → buscar → resultados → ficha ═══════════════════════════════ */
{
  decir('\n1 · DESCUBRIR');
  const pagina = await nuevaPagina(navegador);
  await pagina.goto(`${WEB}/`, { waitUntil: 'networkidle' });
  await comprobar(pagina, 'la portada abre con la pregunta del cuándo', async () =>
    (await pagina.getByRole('heading', { level: 1 }).innerText()).includes('cuándo'),
  );
  await foto(pagina, 'camino-1a-portada');

  await pagina.fill('#texto', 'corte');
  await pagina.getByRole('button', { name: 'Buscar' }).click();
  await pagina.waitForURL('**/buscar?texto=corte', { timeout: 20_000 });
  await pagina.waitForLoadState('networkidle');
  await comprobar(pagina, 'la búsqueda por texto trae resultados de la API', async () =>
    (await pagina.locator('.fila--resultado').count()) > 0,
  );
  await foto(pagina, 'camino-1b-resultados');

  const primero = pagina.locator('.fila--resultado .fila__titulo').first();
  const nombre = await primero.innerText();
  await primero.click();
  await pagina.waitForURL('**/salon/**', { timeout: 20_000 });
  await pagina.waitForLoadState('networkidle');
  await comprobar(pagina, `la ficha de «${nombre}» carga con su carta`, async () =>
    (await pagina.getByRole('heading', { level: 1 }).innerText()).trim() === nombre.trim() &&
    (await pagina.getByRole('heading', { name: 'La carta' }).count()) === 1,
  );
  await foto(pagina, 'camino-1c-ficha');
  await pagina.context().close();
}

/* ═══ 2 · Elegir persona: ficha → equipo → perfil ════════════════════════════════════════ */
{
  decir('\n2 · ELEGIR PERSONA');
  const pagina = await nuevaPagina(navegador);
  await pagina.goto(`${WEB}/salon/barberia-el-cangrejo`, { waitUntil: 'networkidle' });
  await comprobar(pagina, 'la ficha pregunta primero con quién', async () =>
    (await pagina.getByRole('heading', { name: '¿Con quién quieres ir?' }).count()) === 1,
  );

  await pagina.getByRole('link', { name: 'Su perfil' }).first().click();
  await pagina.waitForURL('**/con/**', { timeout: 20_000 });
  await esperarAQueSeQuede(pagina);
  await comprobar(pagina, 'el perfil trae años, atendidos y reseñas', async () => {
    // En minúsculas a propósito: las etiquetas van en versalitas por CSS y `innerText`
    // devuelve lo que se ve, no lo que está escrito en el componente.
    const texto = (await pagina.locator('main').innerText()).toLowerCase();
    return (
      texto.includes('años detrás de la silla') &&
      texto.includes('citas atendidas') &&
      (await pagina.getByRole('heading', { name: 'Sus reseñas' }).count()) === 1 &&
      (await pagina.getByRole('heading', { name: 'Lo que hace' }).count()) === 1
    );
  });
  await comprobar(pagina, 'el perfil enseña horas libres de verdad', async () =>
    (await pagina.locator('.hora').count()) > 0,
  );
  await foto(pagina, 'camino-2-perfil');
  await pagina.context().close();
}

/* ═══ 3 · Reservar: servicio → persona → hora → entrar → confirmar → mis citas ═══════════ */
{
  decir('\n3 · RESERVAR (sin sesión, entrando por el camino)');
  const pagina = await nuevaPagina(navegador);
  await pagina.goto(`${WEB}/reservar/barberia-el-cangrejo`, { waitUntil: 'networkidle' });

  await pagina.getByRole('button', { name: /Corte clásico/ }).click();
  await comprobar(pagina, 'elegido el servicio, aparece el paso de la persona', async () =>
    (await pagina.getByRole('heading', { name: '2 · Con quién' }).count()) === 1,
  );

  await pagina.getByRole('button', { name: /^Con Kevin$/ }).click();
  const diaElegido = await elegirDiaConHoras(pagina);
  await comprobar(pagina, `elegida la persona, salen sus horas libres (${diaElegido})`, async () =>
    (await pagina.locator('.hora').count()) > 0,
  );
  await foto(pagina, 'camino-3a-horas');

  const laHora = pagina.locator('.hora').last();
  const rotuloHora = await laHora.innerText();
  await laHora.click();
  await comprobar(pagina, `elegida la hora ${rotuloHora}, sale el resumen`, async () =>
    (await pagina.getByRole('heading', { name: '4 · Confirmar' }).count()) === 1,
  );
  await foto(pagina, 'camino-3b-resumen');

  await pagina.getByRole('link', { name: 'Entrar y confirmar' }).click();
  await pagina.waitForURL('**/entrar**', { timeout: 20_000 });
  await pagina.fill('#correo', CUENTAS.clienta.correo);
  await pagina.fill('#contrasena', CUENTAS.clienta.contrasena);
  await pagina.getByRole('button', { name: 'Entrar' }).click();
  await pagina.waitForURL('**/reservar/**', { timeout: 30_000 });
  await pagina.waitForSelector('.hora[aria-pressed="true"]', { timeout: 30_000 });
  await comprobar(pagina, 'al volver de entrar, la hora elegida sigue puesta', async () =>
    (await pagina.locator('.hora[aria-pressed="true"]').count()) === 1,
  );

  // Se apunta **qué cita** se acaba de crear. Buscarla luego por su hora es lo que hacía esta
  // prueba y es una trampa: una cuenta de ejemplo tiene decenas de citas en el mismo salón, y
  // «las 6:15 p. m.» cae en varias de días distintos. El día que coincidían, la prueba fallaba
  // sin que hubiera nada roto — y eso es peor que no tenerla.
  let citaCreada = null;
  pagina.on('response', async (respuesta) => {
    if (respuesta.request().method() === 'POST' && respuesta.url().endsWith('/mi/reservas') && respuesta.status() === 201) {
      citaCreada = (await respuesta.json()).id;
    }
  });

  await pagina.getByRole('button', { name: /^Confirmar / }).click();
  await pagina.waitForSelector('text=Tu turno está cogido.', { timeout: 40_000 });
  await comprobar(pagina, 'la reserva se hace y la API la devuelve confirmada', async () =>
    (await pagina.locator('main').innerText()).includes('Tu turno está cogido.'),
  );
  await foto(pagina, 'camino-3c-confirmada');

  await pagina.getByRole('link', { name: 'Ver mis citas' }).click();
  await pagina.waitForURL('**/mis-citas', { timeout: 20_000 });
  await pagina.waitForSelector('text=Tu próximo turno', { timeout: 30_000 });
  // Su cita, por identificador y **esté donde esté**.
  //
  // No siempre es una fila: la más próxima se pinta arriba, grande y sola, en su propio bloque.
  // Buscarla solo como `li.fila` funcionaba mientras la cuenta de ejemplo tuviera algo más
  // cercano por delante, y fallaba el día que la cita recién hecha era la siguiente — acusando
  // a la pantalla de perder una cita que estaba en lo alto y en letra grande.
  const suya = pagina.locator(`[data-cita="${citaCreada}"]`);
  await comprobar(pagina, 'la cita recién hecha aparece en «mis citas»', async () =>
    citaCreada !== null && (await suya.count()) === 1,
  );
  await foto(pagina, 'camino-3d-mis-citas');

  // Y se cancela desde la pantalla: prueba el camino de vuelta y, de paso, deja la agenda del
  // salón como estaba. Una prueba que llena la agenda de ejemplo rompe la siguiente.
  // **Cancelar solo si el servidor deja.** Dentro de la ventana de cancelación no hay botón, y
  // eso es lo correcto: la pantalla no promete lo que la API va a rechazar. Exigirlo siempre
  // convertía la prueba en un sorteo con la hora del día.
  const sePuedeCancelar = (await suya.first().getByRole('button', { name: 'Cancelar' }).count()) > 0;
  if (!sePuedeCancelar) {
    decir('  --  · esa hora ya cae dentro de la ventana de cancelación: no se puede soltar, y así debe ser')
    await foto(pagina, 'camino-3e-sin-cancelar');
  } else {
    await suya.first().getByRole('button', { name: 'Cancelar' }).click();
    await suya.first().getByRole('button', { name: 'Sí, cancelar' }).click();
  // La fila cancelada NO se busca con el mismo localizador: ya no tiene botón de cancelar, que
  // es justo lo que se quiere comprobar. Y sigue en su sitio, sin caerse al pliegue de lo
  // pasado, para que quien cancela vea que le hicieron caso.
    const yaCancelada = suya.filter({ hasText: /cancelada por la clienta/i });
    await yaCancelada.waitFor({ timeout: 20_000 });
    await comprobar(pagina, 'se cancela desde la fila, sin salir de la pantalla', async () =>
      // La MISMA cita: sigue en su sitio —para que quien cancela vea que le hicieron caso— y ya
      // no ofrece cancelar. Contar filas parecidas no demostraba ninguna de las dos cosas.
      (await yaCancelada.count()) === 1 &&
      (await suya.getByRole('button', { name: 'Cancelar' }).count()) === 0,
    );
    await foto(pagina, 'camino-3e-cancelada');
  }
  await pagina.context().close();
}

/* ═══ 3 bis · La hora se ocupa mientras la estás mirando ════════════════════════════════ */
{
  decir('\n3 bis · LA HORA QUE SE OCUPA MIENTRAS ELIGES');
  const pagina = await nuevaPagina(navegador);
  await sembrarSesion(pagina, 'clienta');
  await pagina.goto(`${WEB}/reservar/barberia-el-cangrejo`, { waitUntil: 'networkidle' });
  await pagina.getByRole('button', { name: /Corte niño/ }).click();
  await pagina.getByRole('button', { name: /^Con Yaritza$/ }).click();
  await elegirDiaConHoras(pagina);

  const laHora = pagina.locator('.hora').last();
  await laHora.click();
  await pagina.waitForSelector('.hora[aria-pressed="true"]');
  // La URL la escribe un efecto: hay que esperar a que llegue, no leerla en el mismo latido.
  await pagina.waitForFunction(() => location.search.includes('inicio='), null, { timeout: 10_000 });
  const inicio = await pagina.evaluate(() => new URLSearchParams(location.search).get('inicio'));

  // Se la quita otra persona, de verdad y por la API, mientras la clienta mira el resumen.
  const ladron = await (await fetch(`${API}/api/v1/auth/entrar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...CUENTAS.dueno, superficie: 'web' }),
  })).json();
  // **El servicio y la persona se preguntan, no se escriben aquí.** Estaban puestos a mano
  // como dos UUID literales y funcionaron hasta que se recargaron los datos de ejemplo: a
  // partir de ahí el robo contestaba `422 SERVICIO_NO_DISPONIBLE` y la prueba acusaba a la web
  // de un fallo que era suyo. Un identificador copiado en una prueba se pudre en silencio.
  const perfil = await (await fetch(`${API}/api/v1/publico/negocios/barberia-el-cangrejo`)).json();
  const queRoba = perfil.servicios.find((servicio) => /Corte niño/i.test(servicio.nombre)) ?? perfil.servicios[0];
  const quienRoba = perfil.equipo.find((persona) => /Yaritza/i.test(persona.nombre)) ?? perfil.equipo[0];

  const robo = await fetch(`${API}/api/v1/mi/reservas`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${ladron.acceso}`,
      'Idempotency-Key': `robo-${Date.now()}`,
    },
    body: JSON.stringify({
      negocio_slug: 'barberia-el-cangrejo',
      servicios: [queRoba.id],
      inicio,
      profesional_id: quienRoba.id,
    }),
  });
  const cita = await robo.json();
  afirmar(robo.status === 201, 'otra persona coge esa misma hora por la API', `HTTP ${robo.status} · inicio ${inicio} · ${JSON.stringify(cita).slice(0, 160)}`);

  await pagina.getByRole('button', { name: /^Confirmar / }).click();
  // Se espera al TEXTO, no a que exista un `role="alert"`: la consola de Next inyecta uno
  // vacío y esperar al papel en vez de al contenido llegaba antes de tiempo.
  await pagina.waitForFunction(
    () =>
      Array.from(document.querySelectorAll('[role="alert"]')).some((aviso) =>
        aviso.textContent.toLowerCase().includes('se acaba de ocupar'),
      ),
    null,
    { timeout: 30_000 },
  );
  await esperarAQueSeQuede(pagina);
  await comprobar(pagina, 'la web enseña el mensaje de la API y devuelve las horas', async () => {
    const avisos = await pagina.locator('[role="alert"]').allInnerTexts();
    return (
      avisos.some((aviso) => aviso.toLowerCase().includes('se acaba de ocupar')) &&
      (await pagina.locator('.hora').count()) > 0
    );
  });
  await foto(pagina, 'camino-3bis-hora-ocupada');

  // Se deshace el robo para no dejar basura en los datos de ejemplo.
  if (cita?.id) {
    await fetch(`${API}/api/v1/mi/reservas/${cita.id}/cancelar`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${ladron.acceso}` },
    });
  }
  await pagina.context().close();
}

/* ═══ 4 · Entrar: contraseña mala y contraseña buena ═════════════════════════════════════ */
{
  decir('\n4 · ENTRAR');
  const pagina = await nuevaPagina(navegador);
  await pagina.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' });
  await comprobar(pagina, 'el botón arranca inhabilitado con los campos vacíos', async () =>
    await pagina.getByRole('button', { name: 'Entrar' }).isDisabled(),
  );

  await pagina.fill('#correo', CUENTAS.clienta.correo);
  await pagina.fill('#contrasena', 'esto-no-es-la-buena');
  await pagina.getByRole('button', { name: 'Entrar' }).click();
  await pagina.waitForSelector('#fallo-entrada', { timeout: 20_000 });
  await comprobar(pagina, 'la contraseña mala enseña el mensaje de la API', async () =>
    (await pagina.locator('#fallo-entrada').innerText()).includes('incorrect'),
  );
  await comprobar(pagina, 'el correo se conserva y el campo queda marcado', async () =>
    (await pagina.inputValue('#correo')) === CUENTAS.clienta.correo &&
    (await pagina.getAttribute('#contrasena', 'aria-invalid')) === 'true',
  );
  await foto(pagina, 'camino-4a-contrasena-mala');

  await pagina.fill('#contrasena', CUENTAS.clienta.contrasena);
  await pagina.getByRole('button', { name: 'Entrar' }).click();
  await pagina.waitForURL('**/mis-citas', { timeout: 30_000 });
  await comprobar(pagina, 'con la buena entra y va a sus citas', async () =>
    pagina.url().includes('/mis-citas'),
  );
  await foto(pagina, 'camino-4b-dentro');
  await pagina.context().close();
}

/* ═══ 5 · El salón: entrar como dueño y ver la agenda del día ═══════════════════════════ */
{
  decir('\n5 · EL SALÓN');
  const pagina = await nuevaPagina(navegador);
  await pagina.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' });
  await pagina.fill('#correo', CUENTAS.dueno.correo);
  await pagina.fill('#contrasena', CUENTAS.dueno.contrasena);
  await pagina.getByRole('button', { name: 'Entrar' }).click();
  await pagina.waitForSelector('text=¿A qué vienes hoy?', { timeout: 30_000 });
  await comprobar(pagina, 'al dueño se le pregunta si viene al salón o de clienta', async () =>
    (await pagina.locator('main').innerText()).includes('Trabajas en'),
  );

  await pagina.getByRole('link', { name: 'La agenda del salón' }).click();
  await pagina.waitForURL('**/local', { timeout: 20_000 });
  await pagina.waitForSelector('.riel', { timeout: 40_000 });
  await comprobar(pagina, 'la agenda del día carga en un solo riel de horas', async () =>
    (await pagina.locator('.riel .cita').count()) > 0,
  );
  await comprobar(pagina, 'cada cita dice cliente, persona, servicio y estado', async () => {
    const texto = await pagina.locator('.riel .cita').first().innerText();
    return texto.includes('con ') && /\$\d/.test(texto);
  });
  await foto(pagina, 'camino-5a-agenda');

  await pagina.getByRole('button', { name: 'Mañana' }).click();
  await pagina.waitForTimeout(500);
  await esperarAQueSeQuede(pagina);
  await comprobar(pagina, 'se puede cambiar de día sin salir de la pantalla', async () =>
    (await pagina.locator('main').innerText()).toLowerCase().includes('citas del día'),
  );
  await foto(pagina, 'camino-5b-otro-dia');
  await pagina.context().close();
}

/* ═══ 6 · Con el teclado, sin ratón ══════════════════════════════════════════════════════ */
{
  decir('\n6 · TECLADO');
  const pagina = await nuevaPagina(navegador);
  await pagina.goto(`${WEB}/salon/barberia-el-cangrejo`, { waitUntil: 'networkidle' });
  await esperarAQueSeQuede(pagina);

  await pagina.keyboard.press('Tab');
  await pagina.waitForTimeout(400); // el enlace baja con una transición de 120 ms
  const primero = await pagina.evaluate(() => {
    const activo = document.activeElement;
    const estilo = getComputedStyle(activo);
    return {
      texto: activo.textContent.trim(),
      contorno: `${estilo.outlineWidth} ${estilo.outlineStyle}`,
      visible: activo.getBoundingClientRect().top >= 0,
    };
  });
  afirmar(
    primero.texto === 'Saltar al contenido' && primero.contorno === '3px solid' && primero.visible,
    'el primer tabulador es «saltar al contenido» y se ve al recibir el foco',
    JSON.stringify(primero),
  );

  // Se recorre la pantalla entera con el tabulador y se comprueba que todo lo que recibe foco
  // lo enseña: un foco invisible es un foco que no existe.
  const sinContorno = await pagina.evaluate(async () => {
    const culpables = [];
    const focables = document.querySelectorAll('a[href], button:not(:disabled), input, textarea, summary, [tabindex]');
    for (const elemento of focables) {
      elemento.focus();
      const estilo = getComputedStyle(elemento);
      const tieneContorno = estilo.outlineStyle !== 'none' && parseFloat(estilo.outlineWidth) >= 2;
      if (!tieneContorno) culpables.push(elemento.tagName + '.' + String(elemento.className).slice(0, 40));
    }
    return culpables;
  });
  afirmar(sinContorno.length === 0, 'todo lo que recibe foco lo enseña con 3 px de tinta', sinContorno.join(' | '));
  await pagina.context().close();
}

await navegador.close();
decir(`\n${fallos === 0 ? 'Los cinco caminos se recorren enteros.' : `${fallos} comprobaciones fallaron.`}`);
process.exit(fallos === 0 ? 0 : 1);
