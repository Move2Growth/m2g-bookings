# Crítica de la Dirección C · «La hora primero» — Estado: completado

> **Quién:** QA / Validador, como crítico de la ronda adversarial.
> **Cuándo:** 8 de septiembre de 2026.
> **Contra qué:** `docs/producto/LISTON-FRONT.md` — siete descartes y cinco caminos.
> **Qué se juzgó:** `/Users/luisgomez/Desktop/kraken/m2g-bookings/.claude/worktrees/agent-ac64aedc6a80f0a09/apps/web`, navegable en `http://localhost:3400`, contra la API local en `http://localhost:8000` con el seed cargado.
>
> **Todo lo de aquí está vuelto a medir por mí**, con mis propios guiones de Playwright a 390 px
> (Chromium, `locale es-PA`, `timezoneId America/Panama`). **No se ha aceptado como prueba nada
> de `apps/web/verificacion/`**; al contrario, al final se dice qué es lo que ese verificador no
> mira y por eso no vio.
>
> **Veredicto: NO PASA.** Falla **D7** en tres sitios distintos, dos de ellos reproducibles con
> una captura en la que el texto de un botón sencillamente no se ve. Los otros seis descartes
> los pasa, y los pasa bien.

---

## 1 · Los siete descartes, uno a uno

### D1 · Ni un hexadecimal, ni una familia tipográfica a mano — **PASA**

**Cómo lo comprobé.** Primero el `grep` literal del listón sobre el CSS de la propuesta, y luego
lo que el navegador acaba pintando, contrastado contra `packages/tokens/tokens.json`.

```bash
cd .../agent-ac64aedc6a80f0a09/apps/web
grep -rE "#[0-9a-fA-F]{3,6}" --include="*.css" .        # → 0 líneas
grep -rnE "rgba?\(|hsla?\(|oklch\(" app componentes lib # → 0 líneas
grep -rn "font-family" app componentes lib              # → 13 líneas, TODAS var(--tipografia-familia*)
```

Solo hay un fichero de estilo, `app/globales.css`, y **no declara ni una variable propia**
(`grep -E "^\s*--" app/globales.css` → 0). Importa `@agenda/tokens/css` en la línea 20 y no lo
tapa después: eso es exactamente lo que se rompió la vez anterior y aquí no pasa.

**Medido en la pantalla, no en la paleta.** Recogí `color`, `background-color`, los cuatro
`border-*-color`, `outline`, `text-decoration`, `caret`, `fill`, `stroke` y los `rgba()` de
`box-shadow` de **todos** los nodos de **13 pantallas**. Fuera de la paleta de tokens aparecen
exactamente **dos valores, y ninguno pinta nada**:

| Valor | Qué es |
|---|---|
| `rgb(0,0,0)` | el `fill` inicial del navegador, heredado por todo elemento. El único `<svg>` de la web (el sello de la cabecera) lleva `fill="currentColor"` en sus cinco `path`, así que ese negro no se usa. Comprobado leyendo el `outerHTML` renderizado. |
| `rgb(117,117,117)` | el elemento `<nextjs-portal>` del *overlay* de desarrollo de Next. No es del producto. |

**Familias efectivas sobre texto:** dos y solo dos —`"Public Sans"` y `"Familjen Grotesk"`—
autoalojadas con `@fontsource-variable`. Ninguna de las vetadas.

**Y no hizo trampa por el otro lado:** `packages/tokens` está **intacto** en su worktree
(`git status` limpio, `md5` de `variables.css` idéntico al de `development`). No se ha ampliado
la paleta para que le cuadre.

---

### D2 · Nada a medias — **PASA**

**Los seis estados, provocados por mí** sobre el botón real de `/entrar`
(`<button class="boton boton--cierra boton--bloque">`), leyendo `getComputedStyle` en cada uno:

| # | Estado | Cómo lo provoqué | Lo que midió mi guion |
|---|---|---|---|
| 1 | inhabilitado | campos vacíos | `bg rgb(241,241,238)` · `color rgb(92,92,102)` · `cursor not-allowed` · `disabled=true` |
| 2 | reposo | campos llenos | `bg rgb(200,30,100)` · `color rgb(255,255,255)` · canto de 4 px |
| 3 | encima | `hover()` | `bg rgb(163,24,79)` · canto de 6 px · `translateY(-2px)` |
| 4 | foco de teclado | tabulador | `outline: 3px solid rgb(16,16,20)`, offset 2 px |
| 5 | pulsado | `mouse.down()` | `translateY(+2px)` · el canto se lo traga (`box-shadow` a cero) |
| 6 | cargando | interceptando `POST /auth/entrar` con 6 s de retardo | el rótulo cambia a **«COMPROBANDO»**, `aria-busy="true"`, `disabled`, `cursor: progress` |

Los seis se pintan **distintos**. El 6 además es honesto: no es un icono decorativo, cambia la
palabra.

**Pantallas enteras:** cabecera y pie en **las 13 pantallas del barrido y en los 22 pasos** de los
cinco caminos, sin una sola excepción. Estados de vacío, de carga y de error existen y son de
verdad (ver D4).

*Dos peros que no llegan a tumbar el descarte pero se anotan:*
- `/salon/no-existe-este-salon` y `/local` sin sesión **no tienen `<h1>`**; el rótulo es un nivel
  inferior. La pantalla está completa a la vista, pero el esqueleto semántico no.
- De las **siete variantes** de botón que hay en el producto (`--abre`, `--cierra`,
  `--secundario`, `--texto`, `--riesgo`, `--riesgo-suave`, `--bloque`), su propio verificador
  prueba **una**. Lo que se les escapó por ahí es lo de D7.

---

### D3 · Cero redondeo y cero degradado decorativos — **PASA, y con holgura**

**En el CSS:** los once `border-radius` del fichero usan solo `var(--radio-superficie)` (0) y
`var(--radio-control)` (4 px). `--radio-pildora` **existe en los tokens y no se usa ni una vez**.
`grep -E "gradient|radial-|conic-" app/globales.css` → **cero**.

**En la pantalla:** recorrí todos los nodos de las 13 pantallas leyendo las cuatro esquinas
calculadas y el `background-image` (y también el `mask-image`, por si el degradado entraba por
ahí):

```
radios distintos vistos en las 13 pantallas: ['4px']   (más el 0, que no se cuenta)
degradados: 0
```

Los avatares son **cuadrados de color con la inicial** —`S`, `B`, `K`, `Y`—, no círculos. Es la
dirección que más lejos está de lo rechazado.

---

### D4 · Se navega de verdad contra la API — **PASA**

No me fié del pie que dice «no hay ni un dato escrito a mano». Cuatro pruebas:

1. **El dato pintado coincide con el JSON, campo a campo.** `GET /api/v1/publico/buscar?texto=corte&con_proxima_hora=true`
   devuelve `2026-09-08T14:00:00Z` para Salón Obarrio y `2026-09-08T17:15:00Z` para Barbería San
   Francisco. La pantalla pinta `hoy · 9:00 a. m.` y `hoy · 12:15 p. m.` — la conversión a
   `America/Panama` es correcta.
2. **La hora es la del salón, no la del navegador.** Abrí la misma búsqueda con el navegador en
   `America/Panama`, `Europe/Madrid` y `Asia/Tokyo`: **las tres pintan lo mismo**. La afirmación
   de su hoja se sostiene.
3. **Escribir cambia la pantalla.** Creé una reserva por la interfaz y apareció en la agenda del
   negocio (`GET /negocio/agenda`); la cancelé por la interfaz y la agenda pasó a decir «Ver las
   2 canceladas» incluyendo la mía. No es un JSON congelado: es la base de datos.
4. **Los errores son los de la API, literales.** Intercepté `**/disponibilidad**` y devolví
   `{"error":{"codigo":"REVENTON","mensaje":"La base de datos se cayó, prueba en un rato."}}`:
   la pantalla enseña **ese mensaje exacto** bajo «NO SE PUDO · Esto no cargó», con «VOLVER A
   INTENTARLO». Con la red abortada del todo dice «No se pudo hablar con el servidor. Comprueba
   que la API está levantada en el puerto 8000.». Y `?simular=error` es de verdad: `buscar/page.tsx:179`
   pide `/api/v1/publico/negocios/esta-ruta-no-existe-a-proposito` y pinta lo que conteste.

**Lo público se pinta en el servidor.** `curl` sin ejecutar JavaScript trae ya «Barbería El
Cangrejo», «Kevin Ortega» y «Corte clásico» en el HTML de `/salon/barberia-el-cangrejo`.

*Un pero:* el mensaje que sale en el error de búsqueda es «Este negocio todavía no está
publicado», que es la respuesta honesta de la API a una ruta que no existe, pero para quien mira
la pantalla es un error que habla de otra cosa. Es el precio de no inventar errores; lo apunto,
no lo cuento como fallo.

---

### D5 · 390 px primero — **PASA**

`document.documentElement.scrollWidth` = **390 en las 13 pantallas del barrido y en los 22 pasos**
de los cinco caminos. Cero.

**Y no vale con eso, porque `app/globales.css:54` pone `overflow-x: hidden` en el `body`,** que
se propaga al *viewport* y podría estar tapando un desbordamiento y falseando la medida —que es
justo el número que su hoja presenta como prueba. Así que medí de dos maneras más:

1. **Neutralizando el recorte**: `html.style.overflowX='visible'; body.style.overflowX='visible'`
   y volviendo a leer `scrollWidth`. **Sigue dando 390 en las 13 pantallas.** No hay nada
   escondido.
2. **Contando cajas**: recorrí todos los elementos visibles y conté los que tienen el borde
   derecho más allá de `window.innerWidth`. **Cero**, en todas.

Comprobado también a **768 y 1440 px**: `scrollWidth` exacto y **0** desbordes en las seis
pantallas principales.

---

### D6 · Movimiento con motivo — **PASA**

- **En una pantalla quieta, `document.getAnimations().length` = 0** en las siete pantallas que
  probé, con y sin `prefers-reduced-motion`.
- Solo hay **tres** `@keyframes` en toda la hoja: `entrar-desde-abajo` (dice de dónde sale la
  pantalla, `1` iteración), `latir-una-vez` (confirma el toque, `1` iteración) y `barrido`.
- **`barrido` es la única `infinite`** y aparece en dos sitios (`globales.css:644` y `:1344`), los
  dos son barras de espera: `.boton__espera::after` y `.cargando__barra::after`. La cacé en vivo:
  navegando en frío a `/buscar`, a ≈80 ms hay **1** animación y el rótulo dice «BUSCANDO Y
  CALCULANDO LA PRIMERA HORA LIBRE DE CADA SALÓN»; a 200 ms hay **0**. En el botón de entrar,
  reteniendo la respuesta 6 s, hay 1 animación durante la espera y **0** en cuanto contesta.
- `prefers-reduced-motion: reduce` deja `.aparece` en `0.001s` y `animation-iteration-count: 1`
  para todo (`globales.css:165-174`). Comprobado con el contexto de Playwright en `reducedMotion:'reduce'`.

*El único punto donde se tensa la letra de «nada en bucle» es ese `barrido`.* Como el propio
descarte permite lo que «tapa una espera» y ese bucle no sobrevive a la respuesta ni a
`prefers-reduced-motion`, lo doy por pasado — pero queda escrito con número de línea para que el
director juzgue si quiere ser más literal.

---

### D7 · AA de verdad — ❌ **NO PASA**

**En reposo, impecable.** Calculé el contraste del color y el fondo **efectivos** (mezclando alfa
y subiendo por los ancestros hasta el primer fondo opaco) de cada nodo con texto propio:
**752 combinaciones en 13 pantallas, más las de los 22 pasos de los caminos: ninguna por debajo
de 4,5:1 (o 3:1 si el texto es grande).** Su cifra de reposo es cierta.

**El problema es que el reposo no es la pantalla renderizada: es una de sus pantallas.** El
descarte dice «medida en la pantalla renderizada», y las pantallas también tienen estado
«encima» y estado «con el foco puesto». Ahí falla, y falla de forma sistemática.

#### Fallo 1 · El texto de los botones-enlace se rompe al pasar por encima

**Causa exacta**, en `apps/web/app/globales.css:98`:

```css
a:hover {
  color: var(--color-acento-hover);
}
```

Esa regla vale `0,1,1` de especificidad y `.boton--cierra { color: … }` vale `0,1,0`. **Gana la
regla del enlace.** Resultado: cualquier botón pintado sobre un `<a>` pierde su color de texto en
cuanto el puntero se le pone encima, mientras el fondo sí cambia al de la variante.

Reproducción en tres líneas (navegador a 390 px, `(hover:hover)` = `true`):

```js
await p.goto('http://localhost:3400/salon/barberia-el-cangrejo');
await p.locator('a.boton--cierra').first().hover();
// reposo: rgb(255,255,255) sobre rgb(200,30,100)   → 5,0:1  ✔
// encima: rgb(20,40,156)   sobre rgb(163,24,79)    → 1,54:1 ✘
```

Barrí **las diez pantallas principales pasando el puntero por cada uno de sus enlaces y botones**
(≈250 elementos). Ocho casos distintos, todos por debajo del mínimo:

| Pantalla | Botón | Encima |
|---|---|---|
| `/salon/barberia-el-cangrejo` | **RESERVAR UNA HORA** (la acción principal de la ficha) | **1,54:1** |
| `/salon/barberia-el-cangrejo` | VER SUS HORAS | 1,54:1 |
| `/salon/barberia-el-cangrejo` | ELEGIR HORA (cada línea de la carta) | 1,54:1 |
| `/salon/…/con/kevin-ortega` | RESERVAR CON KEVIN | 1,54:1 |
| `/salon/…/con/kevin-ortega` | ELEGIR HORA | 1,54:1 |
| `/mis-citas` (sin sesión) | ENTRAR | 1,54:1 |
| `/local` (sin sesión) | ENTRAR | 1,54:1 |
| `/esto-no-existe` | **IR A LA BÚSQUEDA** | **1,00:1** |

El último es el que no admite discusión. `a.boton--abre` en reposo es
`rgb(255,255,255)` sobre `rgb(27,52,196)`; al pasar por encima, el fondo va a
`--color-acento-hover` y el texto **también** va a `--color-acento-hover`:

```
404 · reposo : rgb(255, 255, 255) sobre rgb(27, 52, 196)
404 · encima : rgb(20, 40, 156)  sobre rgb(20, 40, 156)   ← el mismo color
```

La captura del botón en ese estado es un rectángulo azul liso: **la palabra desaparece**.
Está en `capturas/PRUEBA-404-boton-hover.png` de mi carpeta de trabajo.

Y hay una ironía que conviene dejar escrita: la hoja de la dirección presume de haber
descubierto, «solo por medir en la pantalla», dos casos de 1:1 y 2,48:1 en transiciones de color,
y de haber sacado de ahí la regla «se anima el movimiento, nunca el color». **La regla es buena y
el caso más grave se les quedó dentro**, porque `verificacion/botones.mjs` mide un `<button>` de
`/entrar` —al que `a:hover` no le aplica— y `verificacion/recorrer.mjs` no hace `hover()` ni
`focus()` en ningún sitio.

#### Fallo 2 · El anillo de foco de teclado es invisible en el pie, en todas las pantallas

`--color-foco` es `#101014` (tinta) y `.pie` tiene `background-color: var(--color-tinta)`
(`globales.css:293-297`), o sea **el mismo color**. La regla que salva los bloques saturados solo
cubre `.bloque--cobalto` y `.bloque--fucsia` (`globales.css:111-114`); el pie no está en la lista.

Tabulando de verdad hasta un enlace del pie:

```
{"txt":"Portada","outline":"3px solid rgb(16, 16, 20)","dentroPie":true}
fondo del pie: rgb(16, 16, 20)   → 1,00:1
```

Son **cinco enlaces por pie, y el pie está en todas las pantallas del producto**. Con la captura
delante (`capturas/PRUEBA-foco-en-el-pie.png`) no se puede decir cuál de los cinco tiene el foco.
Un indicador de foco es «elemento de interfaz» y el descarte le pide 3:1; aquí tiene 1,00:1.

#### Fallo 3 · El anillo de foco del campo de la portada, 2,11:1 contra el bloque cobalto

La misma regla de `globales.css:111` cubre `a, button, [tabindex]` dentro de un bloque saturado
pero **no `input`**. El campo «Qué necesitas» de la portada vive dentro de `.bloque--cobalto`
(`rgb(27,52,196)`) y su anillo es tinta: **2,11:1** contra el cobalto.

Este es el más benigno de los tres —el anillo va con 2 px de separación y por dentro linda con el
blanco del campo, así que a la vista se distingue—, y lo dejo anotado como tercer punto del mismo
descuido, no como el fallo que lo tumba. Los que lo tumban son el 1 y el 2.

---

## 2 · Los cinco caminos, recorridos a clics

Los recorrí **pulsando**, nunca escribiendo una URL, en Chromium a 390 px. La única URL que tecleé
fue `http://localhost:3400/` para empezar.

### Camino 1 · Descubrir — **entero**

Portada → escribo `corte` en «Qué necesitas» y pulso **BUSCAR** → `/buscar?texto=corte`, cuatro
salones, cada uno con su primera hora libre → pulso «Salón Obarrio» → ficha con dirección,
valoración, equipo, carta (`Balayage · 3 h · $120.00`, `Keratina · 2 h 30 min · $90.00`), horario
semanal y reseñas con la respuesta del salón. Ni un error de consola.
**Los tres estados existen y son reales:** carga («BUSCANDO Y CALCULANDO LA PRIMERA HORA LIBRE DE
CADA SALÓN», cazado a ≈80 ms), vacío y error (D4).

### Camino 2 · Elegir persona — **entero**

Cabecera → «Buscar» → pulso «Barbería El Cangrejo» → en la ficha, «¿Con quién quieres ir?» está en
`y=550` y «La carta» en `y=1072`: **la persona va encima del precio, como afirman** → pulso «SU
PERFIL» → perfil de Kevin Ortega con **9 años detrás de la silla, 18 citas atendidas, 4 clientas
distintas**, bio, Instagram, lo que hace con precios, sus reseñas con la respuesta del salón y
**sus horas libres de verdad de los próximos siete días**, agrupadas por día y con el número de
huecos.

Esta pantalla es la mejor del lote y es la que más se aparta de lo que hace todo el mundo.

### Camino 3 · Reservar — **completo salvo el último paso, y ese último paso falla**

Ficha → **RESERVAR UNA HORA** → `1 · Qué` (pulso `Corte clásico`) → `2 · Con quién` (pulso `Con
Kevin`) → `3 · Cuándo` (pulso `Lun, 14 sept`, luego `5:15 p. m.`) → `4 · Confirmar` con el resumen
(qué, con quién, cuándo, cuánto dura, total) → **CONFIRMAR 5:15 P. M.** → «**Tu turno está
cogido.**», etiqueta CONFIRMADA, y los botones «VER MIS CITAS» y «VOLVER AL SALÓN».

La URL lleva `servicio`, `profesional`, `dia` e `inicio`; recargué en el paso 4 y **el resumen
seguía puesto**; el botón atrás vuelve a la ficha. Eso funciona.

**El choque funciona, y funciona bien.** Puse dos navegadores en el paso 4 sobre la misma hora.
El segundo confirmó primero; el primero, al confirmar, se quedó en la misma pantalla, borró
`inicio` de la URL, recargó los huecos del día y enseñó **«Ese horario se acaba de ocupar. Elige
otro y lo confirmamos enseguida.»** donde estaba la hora. Sin diálogo, sin perder el camino. Es
exactamente lo que promete su hoja.

**Lo que no funciona: «verla en mis citas».** Pulsé «VER MIS CITAS» y **mi reserva del lunes 14 no
está**. Comprobado tres veces:

- La reserva **existe**: `GET /api/v1/negocio/agenda?desde=2026-09-14` la devuelve
  (`01a07ff8-69cb-…`, `2026-09-14T22:15:00Z`, `confirmada`, «Abdiel Him», «Corte clásico»).
- La pantalla `/mis-citas` enseña **59 filas y ninguna pasa del `jue, 10 sept`**. Busqué «14 de
  septiembre» en el texto de la página: **no aparece**.
- **La causa está en la API, no en esta dirección**: `apps/api/agenda/api/cliente.py:120`
  devuelve las **30 próximas + 30 pasadas** y **no acepta ningún parámetro** (lo confirma el
  `openapi.json`: `GET /mi/reservas` no tiene ni uno). El seed le da a Abdiel 30 citas futuras que
  llenan la ventana hasta el 10 de septiembre, así que todo lo que se reserve más allá es
  invisible para siempre.

Repetí el camino con un hueco dentro de la ventana —`Arreglo de barba`, «Me da igual quién ·
quiero la hora más pronta», última hora de hoy— y ahí **sí** aparece en Mis citas con su
«CONFIRMADA» y su «CANCELAR». Así que: **el camino se recorre entero, pero el último paso solo
llega si la fecha cae dentro de las 30 próximas de esa cuenta.** La dirección no puede pintar lo
que la API no le da; lo que sí es suyo es que no hay nada en pantalla que avise de que la lista
está cortada.

**De propina, la cancelación en línea es como dicen y es buena:** pulsé «CANCELAR» en la fila y
**hay 0 elementos `<dialog>` o `role=dialog` en el DOM**; la propia fila se convierte en la
pregunta —«¿Seguro que sueltas esta hora? Se la queda quien la pida después.»— con «SÍ, CANCELAR»
y «NO, DEJARLA» encima del dato. Confirmé y la fila pasó a «CANCELADA POR LA CLIENTA».

### Camino 4 · Entrar — **entero**

Cabecera → «Entrar». Con los campos vacíos el botón está **inhabilitado** (`isDisabled() = true`).
Con `abdiel@demo.pa` y una contraseña mala: sale **«Correo o contraseña incorrectos.»** —el
mensaje de la API—, la contraseña queda con `aria-invalid="true"`, **el foco vuelve al campo de la
contraseña** (`activeElement = INPUT#contrasena`), **el correo se conserva** y la contraseña se
borra. Con la buena, entra y va a `/mis-citas`. Con la cuenta del dueño, en vez de entrar a secas
pregunta **«¿A qué vienes hoy?»** con «LA AGENDA DEL SALÓN» y «MIS CITAS COMO CLIENTA»: el cambio
de contexto es explícito, que es lo que pide el proyecto.

### Camino 5 · El salón — **entero**

Portada → «ENTRAR A MI SALÓN» → `/local` sin sesión enseña su propia pantalla («Esto es la
trastienda del salón») con su puerta → «ENTRAR» → credenciales del dueño → «LA AGENDA DEL SALÓN».

El día es un **riel de horas de 09 a 17** con las horas libres marcadas «Libre» y, dentro de cada
bloque, el tramo, el estado, **el nombre de la clienta y con quién va**, el servicio y el precio.
Arriba, tres cifras: `4 citas del día`, `2 personas trabajando`, `$48.00 se factura hoy`.
Comprobado con medida, no a ojo: **a 390 px `.riel` es `grid` y `.columnas` es `display:none`; a
1280 px al revés, con dos columnas, una por persona.** A 768 px sigue el riel.

«Ver las 2 canceladas» funciona y el botón cambia a «Esconder las 2 canceladas»; con las
canceladas encendidas aparece mi propia reserva cancelada. Los días Ayer / Hoy / Mañana / Jue
cambian el contenido.

---

**Limpieza.** Creé **una** reserva que quedó viva (`01a07ff8-69cb-7740-9efe-fdf540366114`, lunes
14 a las 5:15 p. m.) y la **cancelé por la API** al terminar
(`POST /api/v1/mi/reservas/{id}/cancelar` → `200`, `estado: cancelada_cliente`). La otra que hice
—`Arreglo de barba`, hoy a las 6:30 p. m.— la cancelé desde la propia interfaz mientras probaba el
camino 3. Comprobado al cierre: **no queda ninguna reserva mía en estado `confirmada`**. (En la
agenda del 14 hay otras cuatro creadas y canceladas esta madrugada que **no son mías** —servicios
y horas que nunca elegí—; las dejo como están.)

---

## 3 · Lo mejor y lo peor

**Lo que hace mejor que nadie:** convierte la agenda del salón en algo que un dueño puede leer con
el pulgar —un riel de horas de una sola columna, con el nombre de la clienta y el de quien la
atiende **dentro** del bloque— y lo demuestra con la medida, no con la promesa: a 390 px el riel
es `grid` y las columnas son `display:none`; a 1280 px, al revés.

**Lo que hace peor:** deja el color del texto colgando de una regla genérica de enlace
(`globales.css:98`), y por eso al pasar por encima **el botón «IR A LA BÚSQUEDA» de la página de
error queda azul sobre azul, 1,00:1, con la palabra literalmente invisible**, y las seis llamadas
fucsias a reservar caen a 1,54:1 — el único descarte que se ha roto, roto justo donde su propio
verificador no mira.

---

## Apéndice · Cosas medidas que no deciden el veredicto, pero que el director debe saber

1. **La afirmación de los dos objetivos de 44 px es falsa.** Su hoja dice: «Cada fila tiene dos
   objetivos distintos y **los dos miden 44 px**». Medido: la hora fucsia mide `124×44` con
   `padding: 0 12px`; **el nombre del salón mide `156×19`, con `padding: 0px` y sin ningún
   `::before`/`::after` que le agrande el área de toque**. El objetivo que lleva a la ficha es
   menos de la mitad de alto de lo que dice ser.
2. **Las columnas de 1280 px no están alineadas por hora.** Son dos listas apiladas: la cita de
   Kevin de las 11:00 y la de Yaritza de las 10:00 están **las dos en `y=601`**; la de las 16:00 y
   la de las 15:00, **las dos en `y=724`**. Con esa forma no se puede leer de un vistazo quién
   está ocupado a las tres, que es la única razón de poner columnas.
3. **El pie dice «Entrar» con la sesión iniciada**, en todas las pantallas, mientras la cabecera
   dice «Salir». El pie no mira la sesión.
4. **El día de la agenda del salón no vive en la URL**, y su decisión número 3 dice que sí («el
   servicio, la persona, **el día** y la hora … están en la barra de direcciones»). Pulsé «Jue, 10
   sept», recargué y **volvió al martes 8**; el botón atrás no retrocede un día, se sale a
   `/entrar`. En el asistente de reserva la promesa **sí** se cumple; en la pantalla donde vive el
   dueño, no.
5. **La agenda del salón es solo de lectura.** Los únicos controles son los cuatro días y el
   interruptor de canceladas: no se puede tocar una cita. Para el camino 5 tal como está escrito
   («ver su agenda del día») es suficiente; para operar un salón, no.
6. **El `<title>` de la ficha de un salón es el genérico del sitio** («Tanda · reserva tu turno en
   Panamá») y no hay `application/ld+json`. Fuera de los siete descartes, pero relevante para la
   Fase 2.
7. **El nombre comercial no está escrito a fuego** (QA-T007): `grep -rn "Tanda" app componentes lib`
   → **0 coincidencias** fuera de `lib/marca.ts`, donde sale de `NEXT_PUBLIC_NOMBRE_COMERCIAL`.
