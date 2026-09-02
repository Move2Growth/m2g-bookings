# 0001 · Auditoría del brandbook contra el código, y decisión sobre las imágenes

- **Agente:** Arquitecto / Coordinador · **Tarea:** encargo directo del director (revisión 2 de marca) · **Fecha:** 2026-09-02
- **Estado al cerrar:** hecha

## Qué hice

Dos cosas, ninguna de código.

**Uno.** Comprobé, promesa por promesa, si el código cumple los apartados 01 a 08 de
`docs/marca/BRANDBOOK-BUKEO.md` y el ADR-0016. Salieron 31 promesas comprobables: 12 cumplen,
9 cumplen de boquilla, 9 no cumplen y 1 no la puedo comprobar. Todo medido, no opinado: 19
pantallas en Chromium a 390 px (8 públicas, las 7 del panel con sesión de dueño real y 4 de la
consola con su segundo factor), superficie contada píxel a píxel en un canvas, filetes y
anchuras leídos de `getComputedStyle` sobre el DOM vivo, y contrastes con la fórmula WCAG.

**Dos.** Decidí qué se pinta donde no hay fotografía, porque no se pueden generar más (la
cuenta de generación está sin crédito) y solo hay dos fotos en el repositorio. La decisión va
con el CSS y el SVG de cuatro ejemplos probados en el navegador, no con adjetivos.

## Decisiones tomadas

**Sobre las imágenes: donde no hay foto va un rótulo, no un parche.** El rótulo no sustituye a
la foto, es la forma por defecto de presentar un salón: el nombre entero a tamaño de cartel en
versales y ancho de rótulo, una trama de oficio dibujada a trazo detrás y un par de colores de
la paleta. Sale del apartado 03 (el lenguaje es el del rótulo pintado de un local), del
moodboard 2, 3 y 4, y del apartado 06, que tiene la tipografía a tamaño de cartel y no la usa.

Pesa **1.369 bytes comprimidos** todo el sistema con sus seis tramas, frente a los 57.120 bytes
de una sola foto servida a 640 px, y no añade ni una petición de red. Verificado con los once
nombres del seed a 390 px: ninguno desborda su caja ni parte una palabra.

**Esto necesita un ADR-0017 que complete la parte de imágenes del 0016.** No lo escribí porque
el encargo acotaba la entrega a un archivo, y porque un ADR aceptado no se edita.

**Lo que escalo y no toco:** ADR-0016 descartó la dirección A por dibujar su estructura con 23
filetes a 1,31:1, y la dirección que ganó tiene 30 reglas de filete cuyo color mide 1,29:1
sobre papel, con 79 bordes visibles contados en una sola pantalla. Es un choque directo con una
decisión aceptada: va a la deuda viva del tablero, no lo cambio por mi cuenta.

## Archivos / recursos creados o tocados

- `docs/marca/revision-2/auditoria-brandbook.md` (nuevo, la entrega).
- `docs/ai-development/arquitecto/BITACORA/0001-auditoria-brandbook-y-decision-de-imagenes.md` (este).
- `docs/ai-development/ESTADO-GLOBAL.md`: seis filas nuevas de deuda viva y un bloqueo.
- **Nada más.** Ni una línea de `apps/`, `packages/` o `infra/`. Los scripts de medición se
  escribieron y se borraron: `git status` queda sin rastro de ellos.

## Cómo verificar que funciona

Cada número de la auditoría se puede repetir. Los caminos más cortos:

1. `node packages/tokens/verificar-contraste.mjs` imprime «41 combinaciones, todas cumplen AA»,
   y `grep -rn "verificar-contraste" .` demuestra que no lo llama ningún proceso.
2. `grep -c "1px solid" apps/web/app/globales.css` da 31.
3. `grep -rn --include='*.tsx' "seccion--\|filo" apps/web` demuestra que los bloques de color
   solo existen en `app/page.tsx`, `app/como-funciona/page.tsx` y `app/para-negocios/page.tsx`.
4. `grep -rn --include='*.tsx' "cifra-grande" apps/web` da 5 usos y ninguno es una hora, una
   duración ni un precio.
5. `grep -rn "Icono" apps/web --include='*.tsx'` demuestra que el símbolo del brandbook está
   exportado y no se importa nunca.
6. En el navegador a 390 px, el logotipo de la cabecera sale en `rgb(22, 54, 199)`, que es el
   azul, no la tinta que promete el apartado 03.

## Pendiente o bloqueado

- **Bloqueo:** la contradicción entre ADR-0016 y los 30 filetes de 1 px a 1,29:1. Solo se
  resuelve de dos formas y las dos son decisión de Luis: o el brandbook admite el filete fino
  como mecanismo de estructura, o `--color-borde` sube a 3:1 y hay que revisar cada superficie.
- **Pendiente:** el ADR-0017 de imágenes, cuando Luis apruebe la decisión de la parte 2.
- Los seis incumplimientos de código (logotipo azul, favicon inexistente, naranja como texto,
  ancho de cifra sin usar, CSS muerto de filas con filete, restos de IBM Plex) son trabajo de
  Frontend, no mío. Están en la deuda viva con dueño.

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **La entrega es `docs/marca/revision-2/auditoria-brandbook.md`.** No hay más.
- **Había otros dos agentes trabajando en paralelo** sobre la misma revisión de marca: uno
  cazando lo que delata la máquina y otro con el lenguaje de componentes (dejó
  `docs/marca/revision-2/lenguaje-de-componentes.html`). **No pisar su trabajo.**
- **La web estaba levantada en `http://127.0.0.1:3100` y no se reinició.** La API responde en
  `http://127.0.0.1:8000`. Las credenciales de la demo están en `docs/CREDENCIALES-DEMO.md`; el
  código de la consola sale de `apps/api/.venv/bin/python -m agenda.consola_codigo`.
- **Qué NO hacer:** no aplicar el CSS de la parte 2 sin que Luis apruebe la decisión, y no
  editar ADR-0016 para resolver lo del filete. Se supera con un ADR nuevo o no se toca.
- **Ojo al medir con Playwright:** una página de prueba sin `<meta name="viewport">` hace que
  Chromium infle los tamaños de fuente en modo móvil, y las medidas salen falsas. Me pasó y me
  costó tres iteraciones.
