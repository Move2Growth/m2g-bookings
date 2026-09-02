# 0001 · El lenguaje de componentes (revisión 2)

- **Agente:** Mockuper · **Tarea:** MCK-T008 · **Fecha:** 2026-09-02
- **Estado al cerrar:** hecha (solo QA la pasa a validada)

## Qué hice

Luis rechazó el diseño entero: «no hay botones personalizados, no hay nada que siga el brand book,
todo super IA, trabajo muy perezoso». El encargo no era criticar sino **diseñar el lenguaje de
componentes propio que el brandbook implica y que nadie había construido**, con CSS que funcione.

Entregué dos archivos y ninguno más:

- `docs/marca/revision-2/lenguaje-de-componentes.html`, una página que se abre en el navegador y
  enseña **cada pieza en sus cinco estados**, con las variables de `packages/tokens/variables.css`
  copiadas dentro y quince líneas de JavaScript para poder tocar los grupos de selección.
- `docs/marca/revision-2/lenguaje-de-componentes.md`, el porqué de cada decisión y **el CSS listo
  para pegar** en la capa de componentes.

El sistema se reduce a **tres mecanismos** y una consecuencia:

1. **El canto.** Todo lo que se toca lleva un zócalo macizo dentro de su propia caja, dibujado con
   `currentColor`. Al pasar por encima crece de 4 a 6 px y al pulsar se lo traga y el contenido baja.
2. **La mordida.** Al canto le faltan los últimos 14 px: es la muesca calada del icono de Bukeo,
   tumbada. Es la firma que hace reconocible un control sin leer el texto.
3. **La forma manda.** Radio 4 px y canto: se toca. Canto vivo y sin canto: se lee.
4. Consecuencia: **la jerarquía de una acción se mide en píxeles de canto** (4, 3, 2, 0), en vez de
   en seis grises que hay que recordar.

Cubre las ocho piezas pedidas: botón en sus tres papeles, campo de texto, ficha de salón en lista,
hora reservable, ficha de filtro y pestaña, indicador de estado de la cita, dos tramas dibujadas con
CSS y el uso del eje de anchura de Archivo. Y además un «antes y después» con el CSS de hoy copiado
tal cual al lado, para que la diferencia se vea sin explicaciones.

## Decisiones tomadas

- **El canto se dibuja con `background-image` dentro de la caja, no con `box-shadow` fuera.** Así no
  se solapa con el vecino, la altura total no cambia al pulsar (44 px de objetivo táctil más el
  canto) y la misma declaración vale para un `<button>` y para un `<input>`, que no admite
  pseudoelementos. Esa es la razón técnica de que el campo y el botón se reconozcan como familia.
- **El canto es `currentColor`.** En el naranja sale tinta (6,99:1) y en el azul sale cal (7,90:1).
  Si hubiera sido siempre tinta, en el azul se quedaba en **2,07:1** y desaparecía justo en el botón
  que más se pulsa del producto. Medido, no estimado.
- **El anillo de foco NO usa `currentColor`**, porque se dibuja fuera del control y en el botón azul
  saldría cal sobre papel cal. Va con la variable `--foco-anillo`, que es la regla del ADR-0016
  convertida en variable en vez de en una lista de selectores que alguien olvidará ampliar.
- **El filo que marca lo elegido va en tinta y no en naranja.** El filo naranja de 6 px ya tiene un
  trabajo (cortar la página entre bloques); si el naranja significara además «seleccionado»,
  dejaría de significar «abre», que es la regla innegociable del ADR-0016.
- **El apagado pierde el canto en vez de bajar la opacidad.** `opacity: .55` deja el texto en 2,9:1;
  sin canto ya dice que no se pulsa y el texto se queda en **6,48:1**.
- **La banda de estado de la agenda pasa a usar el color de `texto` del estado, no el de `borde`.**
  El token de borde se queda entre 2,14:1 y 3,52:1 sobre lienzo. **No cambia la paleta, cambia qué
  token se consume.** Es un hallazgo medido durante este trabajo.
- **Se proponen cinco tokens nuevos y ni un color:** `canto` (principal, secundario, menor, alzado,
  mordida), `filo.grosor`, `foco.grosor` y `foco.separacion`, y `tipografia.ancho-estrecho: 87%`.
  **No los he escrito:** `packages/tokens` es zona serializada y esto es una propuesta pendiente de
  aprobación.
- **Se mantienen los nombres de clase actuales** (`.boton--primario`, `.entrada`, `.hora`, `.ficha`,
  `.estado`, `.resultado`), de modo que aplicarlo sea **solo CSS y ni un componente de React**.
- **Roza la arquitectura:** si esto se aprueba, merece un ADR propio, porque «el canto» es una
  decisión de forma con la misma vida que la regla de los dos saturados. **No he tocado ningún ADR.**

## Archivos / recursos creados o tocados

Creados (los dos únicos del encargo):

- `/Users/luisgomez/Desktop/kraken/m2g-bookings/docs/marca/revision-2/lenguaje-de-componentes.html`
- `/Users/luisgomez/Desktop/kraken/m2g-bookings/docs/marca/revision-2/lenguaje-de-componentes.md`

De sistema (obligación de este agente): esta bitácora, la fila de `MCK-T008` en
`docs/ai-development/mockuper/TAREAS.md` y la fila de deuda en `docs/ai-development/ESTADO-GLOBAL.md`.

**No he tocado `apps/web` ni `packages/`**, que era una regla dura del encargo. Nota: en el momento
de escribir esto, `apps/web/app/globales.css` aparece modificado en el árbol de trabajo **por otro
agente**, no por mí.

## Cómo verificar que funciona

Verificado en vivo con Chromium (Playwright 1.49.1, el que ya está en el repo), no con «build verde»:

1. Abrir `docs/marca/revision-2/lenguaje-de-componentes.html` en el navegador. La fuente carga desde
   `apps/web/node_modules/@fontsource-variable/archivo` y, si el navegador la bloquea por `file://`,
   cae a Google Fonts. Comprobado: la familia activa es `Archivo Variable`, cargada.
2. **Tres anchos comprobados:** a 390, 768 y 1440 px. `scrollWidth == clientWidth` en los tres:
   **cero desplazamiento horizontal**. Cero errores de consola y cero errores de página.
3. **Tocar de verdad:** pulsar un botón hunde el canto y baja el rótulo sin que la caja cambie de
   altura (medido: 48 px en reposo y 48 px apagado). Elegir una hora la pinta de azul y le quita el
   canto sin descuadrar la rejilla.
4. **El CSS del `.md` se probó pegado tal cual:** se extraen sus diez bloques `css`, se aplican sobre
   `packages/tokens/variables.css` y un marcado mínimo, y los estilos computados coinciden con los
   del HTML de muestra. O sea, lo que se entrega para pegar **funciona pegado**.
5. **Contrastes:** las 23 combinaciones que se proponen cumplen AA, calculadas con el mismo código de
   `packages/tokens/verificar-contraste.mjs`. Las tres que no cumplen están en el documento a
   propósito, porque son las opciones **descartadas** y conviene que quede escrito por qué.

Las capturas a 390, 768 y 1440 px se reproducen con Playwright contra ese archivo. **No se versionan
imágenes** porque el encargo pedía dos archivos y ninguno más.

## Pendiente o bloqueado

- **Falta que Luis lo mire y decida.** Mientras no lo apruebe, esto no se aplica a nada.
- Si lo aprueba, el orden está escrito en el §7 del documento: tokens, ADR, capa de componentes de
  `globales.css`, `data-texto` en las pestañas, y repaso del back-office.
- Queda anotado en la deuda viva del tablero.

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **Lo que hay que abrir primero es el HTML**, no el `.md`. El `.md` es el porqué y el CSS.
- **No apliques el CSS a `apps/web` sin el visto bueno de Luis.** Y cuando se aplique, hay que
  mirar **cada pantalla a 390 px en el navegador**: el cambio es de forma, y la forma no sale en un
  build verde.
- **Dos trampas de CSS que ya cuestan tiempo si se repiten:**
  `.hora--pasada` tiene que escribirse `.hora.hora--pasada` o pierde contra
  `.hora[aria-disabled="true"]` y la hora pasada sale rayada como si estuviera ocupada; y un hijo de
  rejilla con un ancho fijo dentro necesita `min-width: 0` o desborda la página en un teléfono.
- **Lo que NO hay que hacer:** meter el canto en cosas que no se tocan. El canto significa «esto se
  pulsa»; si se le pone a un sello de estado o a una cabecera, el sistema deja de significar nada,
  que es exactamente el problema del que se venía.
- El documento resuelve, de paso, tres deudas del tablero: el ancho de cifra sin usar, las tarjetas
  del marketplace donde el brandbook pide filas, y el botón apagado por opacidad. La deuda del
  **filete de 1,44:1** (que es un bloqueo abierto para Luis) se mitiga aquí pasando la estructura a
  `--color-borde-fuerte` (3,88:1), pero **la decisión sigue siendo de Luis**: yo no la he cerrado.
