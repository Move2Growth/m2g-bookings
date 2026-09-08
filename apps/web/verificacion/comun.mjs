/**
 * Lo que comparten los verificadores: el navegador, la sesión de demostración y los cálculos
 * de contraste. Nada de esto entra en el paquete de la web: es la prueba de que lo que se
 * entrega cumple, no parte del producto.
 */

import { chromium } from 'playwright';

export const WEB = process.env.WEB ?? 'http://localhost:3400';
export const API = process.env.API ?? 'http://localhost:8000';
export const MOVIL = { width: 390, height: 844 };

export const CUENTAS = {
  clienta: { correo: 'abdiel@demo.pa', contrasena: 'demo-panama-2026' },
  dueno: { correo: 'dueno.barberia-el-cangrejo@demo.pa', contrasena: 'demo-panama-2026' },
};

export async function abrirNavegador() {
  return chromium.launch();
}

export async function nuevaPagina(navegador, { reducirMovimiento = false } = {}) {
  const contexto = await navegador.newContext({
    viewport: MOVIL,
    deviceScaleFactor: 2,
    locale: 'es-PA',
    timezoneId: 'America/Panama',
    reducedMotion: reducirMovimiento ? 'reduce' : 'no-preference',
  });
  const pagina = await contexto.newPage();
  const problemas = [];
  pagina.on('console', (mensaje) => {
    if (mensaje.type() === 'error') problemas.push(mensaje.text());
  });
  pagina.on('pageerror', (error) => problemas.push(`pageerror: ${error.message}`));
  pagina.problemas = problemas;
  return pagina;
}

/** Mete la sesión en el navegador sin pasar por la pantalla: para probar lo de dentro. */
export async function sembrarSesion(pagina, cuenta) {
  const respuesta = await fetch(`${API}/api/v1/auth/entrar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...CUENTAS[cuenta], superficie: 'web' }),
  });
  if (!respuesta.ok) throw new Error(`No se pudo entrar como ${cuenta}: ${respuesta.status}`);
  const credenciales = await respuesta.json();
  await pagina.addInitScript((datos) => {
    window.localStorage.setItem('agenda.sesion', JSON.stringify(datos));
  }, {
    acceso: credenciales.acceso,
    refresco: credenciales.refresco,
    usuarioId: credenciales.usuario_id,
    negocioActivo: credenciales.negocio_activo ?? null,
  });
}

/**
 * Espera a que la pantalla se quede quieta: que no quede ningún estado de carga a la vista.
 * Sin esto se mide una pantalla a medio pintar y la medida no vale para nada.
 */
export async function esperarAQueSeQuede(pagina, milisegundos = 25_000) {
  await pagina.waitForFunction(() => document.querySelectorAll('.cargando').length === 0, null, {
    timeout: milisegundos,
  });
  await pagina.waitForTimeout(600);
}

export async function medirAncho(pagina) {
  return pagina.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    culpables: Array.from(document.querySelectorAll('body *'))
      .filter((elemento) => elemento.getBoundingClientRect().right > 391)
      .slice(0, 5)
      .map((elemento) => `${elemento.tagName.toLowerCase()}.${elemento.className}`.slice(0, 90)),
  }));
}

export async function animacionesEnMarcha(pagina) {
  return pagina.evaluate(() =>
    document
      .getAnimations()
      .filter((animacion) => animacion.playState === 'running')
      .map((animacion) => animacion.animationName ?? 'sin-nombre'),
  );
}

/* ── Contraste medido sobre lo que se pintó, no sobre la paleta ──────────────────────────── */

export const MEDIDOR = `(() => {
  const aCanal = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const luminancia = ([r, g, b]) => 0.2126 * aCanal(r) + 0.7152 * aCanal(g) + 0.0722 * aCanal(b);
  const razon = (a, b) => { const la = luminancia(a), lb = luminancia(b); const [x, y] = la > lb ? [la, lb] : [lb, la]; return (x + 0.05) / (y + 0.05); };
  const leerColor = (texto) => {
    const n = texto.match(/[\\d.]+/g);
    if (!n) return null;
    return { rgb: [Number(n[0]), Number(n[1]), Number(n[2])], alfa: n[3] === undefined ? 1 : Number(n[3]) };
  };
  const mezclar = (frente, fondo, alfa) => frente.map((c, i) => c * alfa + fondo[i] * (1 - alfa));
  const fondoDe = (elemento) => {
    let actual = elemento;
    let acumulado = null;
    const pila = [];
    while (actual) {
      const color = leerColor(getComputedStyle(actual).backgroundColor);
      if (color && color.alfa > 0) pila.push(color);
      if (color && color.alfa === 1) break;
      actual = actual.parentElement;
    }
    if (pila.length === 0) return [255, 255, 255];
    acumulado = pila[pila.length - 1].rgb;
    for (let i = pila.length - 2; i >= 0; i -= 1) acumulado = mezclar(pila[i].rgb, acumulado, pila[i].alfa);
    return acumulado;
  };
  const resultados = [];
  const conTexto = Array.from(document.querySelectorAll('body *')).filter((elemento) =>
    Array.from(elemento.childNodes).some((hijo) => hijo.nodeType === 3 && hijo.textContent.trim().length > 0),
  );
  for (const elemento of conTexto) {
    const caja = elemento.getBoundingClientRect();
    if (caja.width === 0 || caja.height === 0) continue;
    const estilo = getComputedStyle(elemento);
    if (estilo.visibility === 'hidden' || estilo.opacity === '0') continue;
    if (elemento.closest('.solo-lectores')) continue;
    const frente = leerColor(estilo.color);
    if (!frente) continue;
    const fondo = fondoDe(elemento);
    const color = frente.alfa === 1 ? frente.rgb : mezclar(frente.rgb, fondo, frente.alfa);
    const tamano = parseFloat(estilo.fontSize);
    const peso = Number(estilo.fontWeight) || 400;
    const grande = tamano >= 24 || (tamano >= 18.66 && peso >= 700);
    const minimo = grande ? 3 : 4.5;
    const valor = razon(color, fondo);
    resultados.push({
      texto: (elemento.textContent || '').trim().slice(0, 44),
      selector: elemento.tagName.toLowerCase() + (elemento.className ? '.' + String(elemento.className).split(' ').join('.') : ''),
      razon: Math.round(valor * 100) / 100,
      minimo,
      pasa: valor >= minimo - 0.005,
      tamano,
      peso,
    });
  }
  return resultados;
})()`;

export async function medirContraste(pagina) {
  return pagina.evaluate(MEDIDOR);
}
