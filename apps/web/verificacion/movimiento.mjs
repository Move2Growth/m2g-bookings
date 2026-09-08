/**
 * El movimiento, comprobado en el navegador.
 *
 *   1 · En una pantalla quieta no hay NI UNA animación en marcha.
 *   2 · La única que repite es la barra que tapa una espera, y solo mientras hay una petición
 *       en vuelo: en cuanto llega la respuesta, desaparece.
 *   3 · Con `prefers-reduced-motion: reduce` no queda movimiento: ni animaciones ni
 *       transiciones. Se mide la duración calculada, no se confía en la regla escrita.
 */

import { abrirNavegador, API, CUENTAS, esperarAQueSeQuede, nuevaPagina, WEB } from './comun.mjs';

const navegador = await abrirNavegador();
let fallos = 0;

function decir(bien, texto, extra = '') {
  if (!bien) fallos += 1;
  console.log(`${bien ? '  ok ' : 'FALLA'} · ${texto}${extra ? ` · ${extra}` : ''}`);
}

const enMarcha = (pagina) =>
  pagina.evaluate(() =>
    document
      .getAnimations()
      .filter((animacion) => animacion.playState === 'running')
      .map((animacion) => ({
        nombre: animacion.animationName ?? 'sin-nombre',
        repeticiones: animacion.effect?.getTiming().iterations ?? 1,
      })),
  );

/* 1 · Pantalla quieta */
{
  const pagina = await nuevaPagina(navegador);
  await pagina.goto(`${WEB}/salon/barberia-el-cangrejo`, { waitUntil: 'networkidle' });
  await esperarAQueSeQuede(pagina);
  const vivas = await enMarcha(pagina);
  decir(vivas.length === 0, 'la ficha quieta no tiene ninguna animación en marcha', `${vivas.length} vivas`);
  await pagina.context().close();
}

/* 2 · Mientras se espera */
{
  const pagina = await nuevaPagina(navegador);
  await pagina.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' });
  await pagina.route(`${API}/api/v1/auth/entrar`, async (ruta) => {
    await new Promise((seguir) => setTimeout(seguir, 3000));
    await ruta.continue();
  });
  await pagina.fill('#correo', CUENTAS.clienta.correo);
  await pagina.fill('#contrasena', CUENTAS.clienta.contrasena);
  await pagina.locator('form button.boton').click();
  await pagina.waitForTimeout(500);
  const durante = await enMarcha(pagina);
  decir(
    durante.length === 1 && durante[0].nombre === 'barrido' && durante[0].repeticiones === Infinity,
    'mientras se espera solo corre la barra que tapa la espera',
    JSON.stringify(durante),
  );
  await pagina.waitForURL('**/mis-citas', { timeout: 30_000 });
  await esperarAQueSeQuede(pagina);
  const despues = await enMarcha(pagina);
  decir(despues.length === 0, 'terminada la espera, no queda nada moviéndose', `${despues.length} vivas`);
  await pagina.context().close();
}

/* 3 · Con el movimiento reducido */
{
  const pagina = await nuevaPagina(navegador, { reducirMovimiento: true });
  await pagina.goto(`${WEB}/entrar`, { waitUntil: 'networkidle' });
  await pagina.route(`${API}/api/v1/auth/entrar`, async (ruta) => {
    await new Promise((seguir) => setTimeout(seguir, 3000));
    await ruta.continue();
  });
  await pagina.fill('#correo', CUENTAS.clienta.correo);
  await pagina.fill('#contrasena', CUENTAS.clienta.contrasena);
  await pagina.locator('form button.boton').click();
  await pagina.waitForTimeout(500);

  const medidas = await pagina.evaluate(() => {
    const barra = document.querySelector('.boton__espera');
    const estiloBarra = barra ? getComputedStyle(barra, '::after') : null;
    const boton = document.querySelector('form button.boton');
    return {
      duracionAnimacion: estiloBarra?.animationDuration ?? 'no hay barra',
      duracionTransicion: boton ? getComputedStyle(boton).transitionDuration : 'no hay botón',
      rotulo: boton?.innerText.trim() ?? '',
      corriendo: document.getAnimations().filter((a) => a.playState === 'running').length,
    };
  });

  decir(
    medidas.duracionAnimacion === '0.001s',
    'con movimiento reducido la animación se apaga',
    `duración ${medidas.duracionAnimacion}`,
  );
  decir(
    medidas.duracionTransicion.split(',').every((valor) => valor.trim() === '0.001s'),
    'con movimiento reducido las transiciones se apagan',
    `duración ${medidas.duracionTransicion}`,
  );
  decir(
    medidas.rotulo.toLowerCase().includes('comprobando'),
    'sin movimiento, quien informa de la espera es el texto',
    `rótulo «${medidas.rotulo}»`,
  );
  await pagina.context().close();
}

await navegador.close();
console.log(`\n${fallos === 0 ? 'El movimiento cumple: con motivo, sin bucles ociosos y apagable.' : `${fallos} comprobaciones fallaron.`}`);
process.exit(fallos === 0 ? 0 : 1);
