/**
 * Darse de baja desde la pantalla, y que signifique algo (Ley 81 · ADR-0025).
 *
 * La ley no da solo el derecho a que te borren: da el derecho a **ejercerlo**. Un derecho que
 * hay que pedir por correo y esperar no está ejercido, así que lo que se comprueba aquí es que
 * una persona entra, lo hace y **queda hecho** — mirando después, desde fuera, qué desapareció y
 * qué se quedó.
 *
 * Se usa una cuenta que se crea aquí mismo. Darle de baja a una de la semilla dejaría el
 * entorno de demostración roto para todo lo demás, y una prueba que estropea las siguientes es
 * peor que ninguna.
 */

import { abrirNavegador, nuevaPagina, esperarAQueSeQuede, medirAncho, API, WEB } from './comun.mjs';

const bien = [];
const mal = [];
const ok = (q, d = '') => { bien.push(q); console.log(`ok   ${q}${d ? ' · ' + d : ''}`); };
const nok = (q, d = '') => { mal.push(q); console.log(`MAL  ${q}${d ? ' · ' + d : ''}`); };
const j = async (r) => { const t = await r.text(); try { return JSON.parse(t) } catch { return t } };

const marca = Date.now().toString().slice(-9);
const correo = `baja-${marca}@ejemplo.pa`;
const contrasena = 'una-clave-de-prueba-2026';

/* Una cuenta recién hecha, con su nombre y su correo. */
const alta = await fetch(`${API}/api/v1/auth/registrar`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ correo, contrasena, nombre: 'Persona De Prueba', superficie: 'web' }),
});
if (!alta.ok) {
  console.log(`MAL  no se pudo crear la cuenta de prueba · HTTP ${alta.status} · ${(await alta.text()).slice(0, 160)}`);
  process.exit(1);
}
const credenciales = await j(alta);

const navegador = await abrirNavegador();
try {
  const pagina = await nuevaPagina(navegador);
  await pagina.addInitScript((datos) => {
    window.localStorage.setItem('agenda.sesion', JSON.stringify(datos));
  }, {
    acceso: credenciales.acceso,
    refresco: credenciales.refresco,
    usuarioId: credenciales.usuario_id,
    negocioActivo: credenciales.negocio_activo ?? null,
  });

  await pagina.goto(`${WEB}/mi-cuenta`, { waitUntil: 'domcontentloaded' });
  await esperarAQueSeQuede(pagina);

  const visto = await pagina.locator('main').innerText();
  if (visto.includes('Persona De Prueba')) ok('la cuenta enseña sus datos');
  else nok('no enseña los datos de la cuenta', visto.slice(0, 120));

  const ancho = await medirAncho(pagina);
  if (ancho.scrollWidth <= ancho.clientWidth) ok('no desborda a 390 px', `${ancho.scrollWidth} px`);
  else nok('se va de lado', `${ancho.scrollWidth} px · ${ancho.culpables.join(' | ')}`);

  await pagina.getByRole('button', { name: 'Quiero darme de baja' }).click();

  // **Lo que se enseña son números, no una advertencia genérica.**
  const aviso = await pagina.locator('.bloque--peligro').innerText();
  if (/citas? por venir|No tienes ninguna cita por venir/i.test(aviso)) ok('dice qué pasa con las citas');
  else nok('no dice qué pasa con las citas', aviso.slice(0, 140));
  if (/se queda sin tu nombre/i.test(aviso)) ok('y dice que las opiniones se quedan, sin nombre');
  else nok('no dice qué pasa con las opiniones', aviso.slice(0, 140));

  // Sin escribir la palabra, el botón no se puede pulsar. Esto no se toca sin querer.
  const antesDeEscribir = await pagina.getByRole('button', { name: 'Borrar mi cuenta' }).isEnabled();
  if (!antesDeEscribir) ok('sin escribir BORRAR no se puede pulsar');
  else nok('el botón de borrar está activo sin confirmar nada');

  await pagina.fill('#confirmar-baja', 'BORRAR');
  await pagina.getByRole('button', { name: 'Borrar mi cuenta' }).click();
  await pagina.waitForURL('**/?adios=1', { timeout: 30_000 }).catch(() => null);

  if (pagina.url().includes('adios')) ok('la baja se hace y saca a la calle');
  else nok('la baja no terminó', `${pagina.url()} · ${(await pagina.locator('.campo__fallo').allInnerTexts()).join(' | ')}`);

  // Y ahora, desde fuera: la comprobación que importa.
  const vuelta = await fetch(`${API}/api/v1/auth/entrar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ correo, contrasena, superficie: 'web' }),
  });
  if (vuelta.status >= 400) ok('con esa cuenta ya no se entra', `HTTP ${vuelta.status}`);
  else nok('la cuenta borrada sigue entrando', `HTTP ${vuelta.status}`);

  // **Y el refresco de antes tampoco vale.**
  //
  // Sin esto la prueba era teatro: comprobar solo que no se puede volver a entrar pasa igual
  // aunque las sesiones sigan vivas y la contraseña siga sirviendo, porque quien entra ya se
  // topa con el estado «eliminado». Lo demostró una rotura: se quitaron las dos cosas y la
  // prueba siguió en verde. El refresco es lo que de verdad mantiene a alguien dentro durante
  // días, así que es lo que hay que ver muerto.
  const refresco = await fetch(`${API}/api/v1/auth/refrescar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresco: credenciales.refresco, superficie: 'web' }),
  });
  if (refresco.status >= 400) ok('y la sesión que tenía abierta se murió', `HTTP ${refresco.status}`);
  else nok('la sesión de antes sigue viva: puede seguir dentro días', `HTTP ${refresco.status}`);

  const conElViejo = await fetch(`${API}/api/v1/mi/perfil`, {
    headers: { Authorization: `Bearer ${credenciales.acceso}` },
  });
  const perfil = await j(conElViejo);
  if (conElViejo.status >= 400 || perfil?.nombre !== 'Persona De Prueba') {
    ok('y su nombre ya no está', conElViejo.status >= 400 ? `HTTP ${conElViejo.status}` : `nombre «${perfil?.nombre}»`);
  } else {
    nok('el nombre sigue ahí después de la baja', JSON.stringify(perfil).slice(0, 120));
  }

  if (pagina.problemas.length === 0) ok('sin errores en la consola');
  else nok('la consola se queja', pagina.problemas.slice(0, 2).join(' | '));
} finally {
  await navegador.close();
}

console.log(`\n${bien.length} bien · ${mal.length} mal`);
if (mal.length > 0) process.exit(1);
console.log('Una persona se da de baja desde la pantalla, y queda hecho.');
