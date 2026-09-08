# 0002 · Crítica adversarial de la Dirección C del frontend

- **Agente:** QA / Validador · **Tarea:** crítica de ronda adversarial (encargo del director, sin ID de `TAREAS.md`) · **Fecha:** 2026-09-08
- **Estado al cerrar:** hecha

## Qué hice

Juzgué **una sola dirección de frontend, la C («La hora primero»)**, contra
`docs/producto/LISTON-FRONT.md`: sus siete descartes y sus cinco caminos. No vi ni busqué las
otras dos direcciones ni las otras críticas, y no propuse ni una mejora — proponerlas invalida la
ronda.

Lo medí todo yo, con guiones propios de Playwright a 390 px contra
`http://localhost:3400` y la API local en `http://localhost:8000` con el seed cargado. **No usé
como prueba nada de `apps/web/verificacion/`**; lo leí solo al final para decir qué es lo que ese
verificador no mira.

Cobertura de la medición: **13 pantallas** en barrido más **22 pasos** de los cinco caminos, con
esta sonda en cada una: `scrollWidth` (y otra vez neutralizando el `overflow-x: hidden` del
`body`), cajas que se salen del *viewport*, todos los `border-radius` y `background-image`
calculados, `document.getAnimations()`, contraste del color y el fondo **efectivos** de cada nodo
con texto propio (**752 combinaciones** solo en el barrido), colores usados contra
`packages/tokens/tokens.json`, y presencia de cabecera y pie. Aparte: **hover sobre ~250 enlaces y
botones** en 10 pantallas, **179 paradas de tabulador** en 7 pantallas midiendo el anillo de foco,
los **seis estados** del botón provocados uno a uno, y comprobaciones a 768 y 1440 px.

## Veredicto

**NO PASA.** Seis descartes limpios (D1, D2, D3, D4, D5, D6) y **D7 roto en tres sitios**:

1. `app/globales.css:98` — `a:hover { color: var(--color-acento-hover) }` gana por especificidad
   (0,1,1 contra 0,1,0) a `.boton--cierra` y `.boton--abre`. Todo botón pintado sobre un `<a>`
   pierde su color de texto al pasar por encima: **1,54:1** en las seis llamadas fucsias a
   reservar y **1,00:1** —texto invisible, con captura— en «IR A LA BÚSQUEDA» de la página 404.
2. `.pie` usa `background-color: var(--color-tinta)` y `--color-foco` es el mismo `#101014`; la
   regla que salva los bloques saturados (`globales.css:111`) solo cubre `.bloque--cobalto` y
   `.bloque--fucsia`. El **anillo de foco de los cinco enlaces del pie es 1,00:1 en todas las
   pantallas del producto**.
3. Esa misma regla no cubre `input`: el anillo del campo de la portada es **2,11:1** contra el
   cobalto (el más leve de los tres; a la vista se distingue por el borde blanco del campo).

Los cinco caminos se recorren enteros **a clics**, con una excepción medida: en el camino 3, una
reserva confirmada para el **lunes 14** no aparece en «Mis citas», porque
`apps/api/agenda/api/cliente.py:120` devuelve **30 próximas + 30 pasadas sin ningún parámetro** y
el seed llena esa ventana hasta el 10 de septiembre. **La causa es de la API, no de esta
dirección**; con una fecha dentro de la ventana el camino se cierra bien.

## Decisiones tomadas

- **Di D6 por pasado** aunque hay dos animaciones `infinite` (`globales.css:644` y `:1344`):
  las dos son barras de espera, mueren con la respuesta (0 animaciones en pantalla quieta,
  comprobado) y `prefers-reduced-motion` las deja en 1 ms. El descarte permite explícitamente lo
  que «tapa una espera». Dejé el número de línea escrito por si el director quiere ser más
  literal con «nada en bucle».
- **No conté como fallo de D7** los bordes y rellenos que mi heurística marcó por debajo de 3:1:
  son falsos positivos, porque `.boton--secundario` dibuja su contorno con `box-shadow: inset`
  y no con `border`. Lo verifiqué antes de descartarlos.
- **No conté como fallo de descarte** el objetivo de toque de 19 px del nombre del salón ni la
  falta de alineación por hora de las columnas de 1280 px: no están en los siete descartes. Van en
  el apéndice de la crítica, porque el primero **contradice una afirmación literal** de su hoja.

## Archivos / recursos creados o tocados

- `/Users/luisgomez/Desktop/kraken/m2g-bookings/docs/producto/criticas-front/critica-c.md` — la crítica (carpeta creada por mí).
- Esta entrada de bitácora.
- `ESTADO-GLOBAL.md` — fila del QA y aviso de la marca de conflicto (ver abajo).
- **No toqué ni una línea** de la dirección C, ni de `apps/api`, `packages/` o `scripts/`.
- Guiones y capturas de la medición, fuera del repositorio, en
  `/private/tmp/claude-501/-Users-luisgomez-Desktop-kraken-m2g/1376160a-a936-466a-bcb6-7086a3fd95ea/scratchpad/qa-c/`
  (70 capturas, `salida/barrido.json`). Son de usar y tirar: lo que vale está en la crítica.

## Cómo verificar que funciona

Con la web en `http://localhost:3400` y la API en `http://localhost:8000`:

```js
// D7 · fallo 1, el peor: el texto del botón desaparece
await p.goto('http://localhost:3400/esto-no-existe');
await p.locator('a.boton--abre').first().hover();
// reposo: rgb(255,255,255) sobre rgb(27,52,196)
// encima: rgb(20,40,156)   sobre rgb(20,40,156)   ← 1,00:1

// D7 · fallo 2: el anillo de foco del pie
await p.goto('http://localhost:3400/entrar');
// tabulando hasta un enlace del pie:
// outline 3px solid rgb(16,16,20) sobre un pie rgb(16,16,20) → 1,00:1
```

```bash
# camino 3 · la reserva existe y «Mis citas» no la enseña
curl -s "http://localhost:8000/api/v1/negocio/agenda?desde=2026-09-14&hasta=2026-09-15" \
  -H "Authorization: Bearer <token en modo negocio>"
# y en /mis-citas la última fila es «jue, 10 sept»
```

## Pendiente o bloqueado

- **Limpieza hecha:** creé dos reservas por la interfaz; una la cancelé desde la propia pantalla y
  la otra (`01a07ff8-69cb-7740-9efe-fdf540366114`, lunes 14 a las 5:15 p. m.) por la API. Al cerrar
  **no queda ninguna reserva mía en estado `confirmada`**. En la agenda del 14 hay otras cuatro
  creadas y canceladas esa madrugada que **no son mías**: servicios y horas que no elegí. La base
  es compartida y hubo otro agente trabajando a la vez.
- **`ESTADO-GLOBAL.md` tiene una marca de conflicto de git sin resolver**, en la línea 56:
  `>>>>>>> worktree-agent-abb50ac3d35f2882e`, dentro de la tabla «Estado de los agentes». **No la
  he quitado**: es el resto de un merge de otro agente y borrarla podría tapar una fila perdida.
  Queda avisada en el propio tablero.
- **Deuda que sale de esta crítica y que hay que rastrear pase lo que pase con la ronda:**
  `GET /api/v1/mi/reservas` devuelve 30 + 30 sin paginar ni admitir parámetros, así que **una
  clienta con la agenda llena no puede ver su propia reserva**. Es de la API y sobrevive a
  cualquier dirección de frontend que se elija.

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **La crítica de la C está escrita y cerrada.** El veredicto es NO PASA por D7, con captura y con
  la línea de CSS que lo causa. No hay que repetir la medición: está toda reproducida en el
  documento.
- **Lo que NO hay que hacer:** arreglar el `a:hover`. Un crítico que propone o aplica mejoras
  invalida la ronda entera (`LISTON-FRONT.md`, «Cómo se juzga»). Si la C gana, se implanta tal
  cual y **entonces** eso se critica como producto.
- **Lo que sí sobrevive a la ronda:** los tres fallos de D7 son de CSS de la propuesta, pero el
  tope de `/mi/reservas` es de la API y afecta a las tres direcciones.
- **Para repetir cualquier medida:** los guiones están en el scratchpad de la sesión (ruta arriba).
  El patrón es siempre el mismo: `chromium.launch()`, contexto de 390×844 con
  `locale es-PA` y `timezoneId America/Panama`, y `getComputedStyle` sobre lo renderizado. Ojo con
  `overflow-x: hidden` en el `body`: hay que neutralizarlo antes de creerse un `scrollWidth`.
