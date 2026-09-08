# Crítica de la DIRECCIÓN B · «El tablón» — Estado: completado

> Escrita por el agente **QA / Validador** el 8 de septiembre de 2026, en el papel de **crítico
> cruzado** de la ronda adversarial del listón del frontend.
> Solo he visto esta dirección. No he mirado las otras dos ni sé qué proponen.
>
> **Qué juzgo:** `/Users/luisgomez/Desktop/kraken/m2g-bookings/.claude/worktrees/agent-a09579b18212f1f38/apps/web`,
> navegado en `http://localhost:3300` contra la API local en `http://localhost:8000` con la semilla cargada.
> **Contra qué:** `/Users/luisgomez/Desktop/kraken/m2g-bookings/docs/producto/LISTON-FRONT.md`.
>
> **No he ejecutado ni uno de sus verificadores** (`verificacion/*.mjs`). Todo lo de abajo está
> medido con instrumentos míos, escritos aparte, con Playwright y Chromium a **390 px**.
> Los guiones están en
> `/private/tmp/claude-501/-Users-luisgomez-Desktop-kraken-m2g/1376160a-a936-466a-bcb6-7086a3fd95ea/scratchpad/qa/`
> y las capturas en su subcarpeta `shots/`.

---

## Veredicto en una línea

**No pasa el listón: falla D7.** El anillo de foco de teclado de la navegación principal se pinta
**#FBFBF9 sobre #FFFFFF — 1,04:1** en **las nueve pantallas**, contra el 3:1 que D7 exige para
elementos de interfaz. Los otros seis descartes los pasa, y varios los pasa con holgura. Los cinco
caminos se recorren enteros a base de clics.

---

## 1 · ¿Pasa los siete descartes?

| # | Descarte | Veredicto |
|---|---|---|
| D1 | Ni un hexadecimal ni una familia escrita a mano | **Pasa** |
| D2 | Nada a medias (seis estados, pantalla entera) | **Pasa** |
| D3 | Cero redondeo y cero degradado decorativos | **Pasa** |
| D4 | Se navega de verdad contra la API local | **Pasa** |
| D5 | 390 px primero, sin desbordar | **Pasa** |
| D6 | Movimiento con motivo, nada en bucle | **Pasa** |
| D7 | AA de verdad en la pantalla renderizada | **NO PASA** |

### D1 · Ni un hexadecimal, ni una familia tipográfica escrita a mano — **PASA**

El comando literal del listón, sobre **todo** el CSS de la propuesta:

```
$ cd .claude/worktrees/agent-a09579b18212f1f38/apps/web
$ find . -name "*.css" -not -path "./node_modules/*" -not -path "./.next/*" \
    | while read f; do echo "$f -> $(grep -cE '#[0-9a-fA-F]{3,6}' "$f")"; done
  ./app/globales.css      -> 0 coincidencias
  ./public/fuentes/fuentes.css -> 0 coincidencias
```

Y lo mismo sobre los `.tsx`/`.ts` de `app/`, `componentes/` y `lib/`: **cero**. Tampoco hay
`rgb(`, `rgba(`, `hsl(`, `color-mix(` ni `oklch(` en ninguno de los dos sitios.

Comprobé además **la trampa concreta que el listón nombra** —«importaba los tokens y acto seguido
los tapaba con cuarenta líneas de color a mano»—: `grep -nE "^\s*--[a-z0-9-]+\s*:" app/globales.css`
devuelve **cero**; la hoja no redefine ni una variable. Y las **86** variables `var(--…)` que usa
existen todas en `packages/tokens/variables.css` (`comm -23` entre usadas y definidas: vacío), así
que no hay ninguna que caiga a nada en silencio. Los tokens del worktree son **byte a byte** los de
`development` (`git diff --no-index`: sin salida), o sea que no ganó el descarte cambiándose la paleta.

En la pantalla renderizada, las familias computadas en 40 combinaciones de pantalla × ancho son
exactamente **dos**: `"Public Sans", …` y `"Familjen Grotesk", …`, ambas por `var(--tipografia-familia*)`.

**Dos matices que doy por escrito, y que no lo tumban:**
- `Times` aparece como familia computada en las 40, pero solo en `<html>`, `<head>` y sus `<meta>`;
  ningún nodo con texto propio la usa. Es la hereda del navegador, no algo pintado.
- En `/entrar` hay un `<code>demo-panama-2026</code>` que sale en **`monospace` del navegador** —una
  tercera letra en pantalla que no viene de los tokens—. No rompe la letra de D1 (nadie escribió una
  familia a mano) y está en el panel de cuentas de demostración, pero conviene que se sepa.

El nombre comercial tampoco está a fuego: sale de `lib/marca.ts` con `NEXT_PUBLIC_NOMBRE_COMERCIAL`,
y `grep -rn "Tanda" app componentes lib` fuera de ese archivo **no devuelve nada**.

### D2 · Nada a medias — **PASA**

**Los seis estados del botón, medidos por mí** con `CSS.forcePseudoState` de CDP (con 500 ms de
espera entre estado y estado, porque leer antes de que acabe la transición de 90 ms da lecturas
falsas), sobre el botón principal de `/entrar`:

| Estado | fondo | zócalo | transform | outline | otros |
|---|---|---|---|---|---|
| 1 reposo | `rgb(200,30,100)` | `0 4px 0 0` | `none` | — | |
| 2 encima | `rgb(163,24,79)` | `0 6px 0 0` | `translateY(-2)` | — | |
| 3 pulsado | `rgb(163,24,79)` | `0 0 0 0` | `translateY(4)` | — | |
| 4 foco teclado | `rgb(200,30,100)` | `0 4px 0 0` | `none` | `3px solid rgb(16,16,20)` | |
| 5 cargando | `rgb(200,30,100)` | `none` | `translateY(4)` | — | barra, `cursor:progress`, `disabled`, `aria-busy` |
| 6 inhabilitado | `rgb(237,237,233)` | `none` | `none` | — | `cursor:not-allowed`, `disabled` |

**Las seis huellas son distintas**; ninguna pareja coincide. Y no son un decorado de laboratorio: el
botón «Entrar» **nace `disabled=true`** con los campos vacíos, o sea que el estado 6 se alcanza usando
la aplicación.

**Pantalla entera:** de las **20 pantallas** que barrí (incluidas las de vacío, error, sin sesión, con
sesión de clienta donde no toca, y el 404), a **390 y a 1440**, las **40** tienen `<header>` y
`<footer>`. El 404 de `/ruta-que-no-existe-abc` no es el de Next: es una pantalla propia, con banda
de cobalto, dos salidas («Ver las horas de hoy», «Buscar un salón») y su pie.

**Los tres estados que casi nadie construye, comprobados uno a uno:**
- *Error*: cortando `http://localhost:8000/**` con `route(...).abort('failed')`, las **ocho**
  pantallas con datos dan un bloque de error propio y **con reintento** — y el texto es distinto en
  cada una («No se pudo abrir el salón», «No se pudo abrir el perfil», …), no un genérico.
- *Carga*: con la API retardada 6 s, salen textos de espera propios («Cargando el salón…»,
  «Cargando tus citas…»). Son de texto, no esqueletos con la forma de lo que llega.
- *Vacío*: `/buscar?texto=zzzzz` da «Nada con «zzzzz»» **con salida** (dos botones), y el día sin
  hueco del reservador dice «Ese día no queda nada · El primer hueco libre es el martes 8» con un
  botón «Ir al hoy».

Recorrí además **26 rutas internas siguiendo enlaces** (rastreo por clic de `a[href^="/"]`): ninguna
pantalla se queda vacía, y solo hay **una** respuesta ≥400 en todo el árbol (ver «lo peor», más abajo).

### D3 · Cero redondeo y cero degradado decorativos — **PASA**

En el código: `grep -niE "gradient"` sobre `app`, `componentes`, `lib` y `public/fuentes/fuentes.css`
solo encuentra la palabra **dentro de un comentario**. Ni un `linear-gradient`, ni un
`radial-gradient`, ni un `conic-`.

En la pantalla renderizada (`getComputedStyle` de **todos** los nodos visibles de las 40
combinaciones): **cero** `background-image` con `gradient`.

Radios: en la hoja hay **seis** declaraciones de `border-radius`, y las seis son
`var(--radio-control)`. En pantalla se pintan **164** nodos con radio y **todos valen 4px**, que es
`--radio-control`. Repartidos: `a.cabecera__cuenta`, `button.dia`, `button.boton--*`,
`input.campo__control`, `button.elegible`. **Ni una tarjeta, ni una superficie, ni un contenedor**
—que es exactamente lo que el listón rechaza—. `--radio-superficie` vale `0` y se respeta.

Las sombras que hay son `0 Npx 0 0 <color>`: **desenfoque cero y expansión cero**. Eso es un bloque
macizo, no una sombra decorativa.

### D4 · Se navega de verdad contra la API local — **PASA**

Registrando **cada petición `xhr`/`fetch` del navegador** en ocho pantallas: **todas** salen a
`http://localhost:8000/api/v1/…` y **ninguna** va a un tercero. Ni un dato inventado en un componente.

Contrasté el pintado con la respuesta cruda, a mano:

```
GET /api/v1/publico/buscar?con_proxima_hora=true&orden=relevancia
  Barbería El Cangrejo → rating 4.32 · numero_reviews 12 · servicios_desde_centavos 800
                         proxima_hora "2026-09-08T14:00:00Z"
```

La pantalla pinta «Barbería El Cangrejo · El Cangrejo · 4,3 (12) · desde $8.00 · **9:00 a. m.**».
14:00Z → 9:00 en Panamá: **la hora se convierte bien**. Repetí la cuenta con los diez salones:
13:00Z→8:00, 16:15Z→11:15, 17:15Z→12:15, 20:00Z→15:00, y `proxima_hora: null` de «Maquillaje por
Karla» cae en el bloque **«Sin hueco hoy»**, que existe de verdad y no lo esconde.

Y la escritura también es real: la reserva del camino 3 salió por `POST /mi/reservas` y la comprobé
por la API con otro cliente (`curl`), no en la pantalla.

### D5 · 390 px primero — **PASA, y comprobado contra su propia trampa**

`document.documentElement.scrollWidth` = **390** en las 20 pantallas a 390 px, y **1440** en las 20
a 1440 px. Cero excepciones.

**Pero ese número solo no vale**, porque la hoja pone `overflow-x: hidden` en el `body`, y eso
*fabrica* un `scrollWidth` bueno aunque se estuviera recortando contenido. Así que lo medí de dos
maneras más:

1. **Quitando el recorte en caliente** (`body.style.overflowX='visible'` y lo mismo en `html`) y
   volviendo a medir en once rutas: sigue dando **390 en las once**. No tapaba nada.
2. **Elemento a elemento**: busqué todo nodo con `right > 390,5` o `left < -0,5`. Los hay —el carril
   de días, los filtros del buscador, la rejilla del salón— pero **todos, sin excepción, cuelgan de
   un antepasado con `overflow-x: auto`**, es decir de un carril que se arrastra a propósito. Ninguno
   cuelga de un `overflow-x: hidden`, que sería recorte de verdad. Los carriles miden 735/358,
   1138/358, 461/358 y 400/356 (scrollWidth/clientWidth) y se arrastran.

Además estresé el caso peor a mano: la agenda de **Salón Obarrio**, con **cuatro** profesionales.
La rejilla pasa a 736 px dentro de 356 y el documento **sigue midiendo 390**. Pasa el descarte.

### D6 · Movimiento con motivo — **PASA**

Medido con `document.getAnimations()` en nueve pantallas, dos veces cada una (al terminar la carga y
2,5 s después), con y sin `prefers-reduced-motion`:

| | animaciones al cargar | iteraciones | duración | vivas a los 2,5 s |
|---|---|---|---|---|
| normal | 0 a 20 según pantalla | **`[1]` en todas** | `[240]` ms | **0 en las nueve** |
| reduced-motion | las mismas | `[1]` | **`[1]` ms** | **0** |

**Ni una animación en bucle** —`grep -c infinite` sobre la hoja: 0— y nada sigue moviéndose pasados
dos segundos y medio. Con `prefers-reduced-motion` las duraciones caen a 1 ms. Los tres motivos que
declara (zócalo al tocar, entrada escalonada de una lista, barra de espera) son los tres que aparecen
y no hay un cuarto.

### D7 · AA de verdad — **NO PASA**

**Lo que sí pasa.** Escribí mi propio medidor (resuelve el fondo real subiendo por los padres y
componiendo alfas, distingue texto grande de normal, y mide aparte relleno, borde, contorno y zócalo
de cada control). Sobre las **40** combinaciones de pantalla × ancho: **0 fallos de texto** y **0
fallos de elemento de interfaz**. Repetí la medida **en los estados que solo se alcanzan tocando**
—servicio elegido, persona elegida, día elegido, hora elegida, dos servicios encadenados, domingo sin
hueco, el error de contraseña puesto— y también da **0 y 0**. Marcadores de posición y contenido
generado en `::before`/`::after`: **0 fallos** en las nueve pantallas. Esa parte está muy bien hecha.

**Lo que no pasa.** El **anillo de foco de teclado** es un elemento de interfaz y D7 le exige 3:1.
Recorrí cada pantalla **con el tabulador** hasta dar la vuelta (24, 42, 42, 19, 18, 21, 6, 9 y 20
paradas) y medí el color del contorno contra el fondo real que tiene detrás:

```
/                       focos recorridos=24  malos=3
/buscar                 focos recorridos=42  malos=3
/personas               focos recorridos=42  malos=3
/salon/barberia-el-cangrejo            malos=3
/salon/barberia-el-cangrejo/kevin-ortega  malos=3
/salon/barberia-el-cangrejo/reservar      malos=3
/entrar                                   malos=3
/mis-citas                                malos=3
/local                                    malos=3
TOTAL DE FOCOS POR DEBAJO DE 3:1: 27
```

Son siempre **los mismos tres**: los enlaces de sección **Horas**, **Salones** y **Personas**, o sea
**la navegación principal del producto**, presentes en todas las pantallas.

```
A.seccion «Horas»     outline: solid 3px rgb(251,251,249)   fondo: rgb(255,255,255)   ratio = 1.04
A.seccion «Salones»   outline: solid 3px rgb(251,251,249)   fondo: rgb(255,255,255)   ratio = 1.04
A.seccion «Personas»  outline: solid 3px rgb(251,251,249)   fondo: rgb(255,255,255)   ratio = 1.04
```

**Prueba en píxeles, no en la paleta.** Puse el foco en «Salones» con el tabulador, hice una captura
del `<header>` a `deviceScaleFactor: 3` y barrí una fila de píxeles dentro de la banda blanca:

```
x=215..221  (255,255,255)      ← la barra de secciones
x=222..230  (251,251,249)      ← el anillo de foco, 9 px de imagen = 3 px CSS
x=231..244  (255,255,255)
```

`#FBFBF9` sobre `#FFFFFF` = **1,04:1**. El anillo solo se intuye en el borde superior, y únicamente
porque ahí asoma sobre la banda de cobalto de encima; los lados y el borde de abajo son invisibles.
Captura: `shots/foco-secciones-INVISIBLE.png`.

**De dónde sale.** `.cabecera` lleva la clase `sobre-bloque`, y la regla
`.sobre-bloque :where(a, button, input, select, [tabindex]):focus-visible { outline-color: var(--color-papel) }`
alcanza a **todo** descendiente del `<header>`. Eso es correcto en la fila de cobalto de arriba y es
donde se rompe abajo, porque `.secciones` tiene `background: var(--color-lienzo)`, que es blanco.

**Por qué su propia verificación no lo vio:** `grep -c "focus" verificacion/contraste.mjs` devuelve
**0**. Su medidor recorre texto y bordes, pero **no mide el indicador de foco**, que es justo el
elemento de interfaz que aquí se cae. Sus «446 medidas, todas pasan» son ciertas para lo que miden.

**Un descarte fallado es un rechazo**, y este lo es: 27 apariciones, en 9 de 9 pantallas, sobre la
navegación principal.

---

## 2 · ¿Se recorren enteros los cinco caminos?

Los recorrí **a base de clics**. Las únicas direcciones que escribí fueron el punto de partida de
cada sesión y las de comprobación de estados sueltos.

### Camino 1 · Descubrir — **completo**

Portada → escribo «barba» en el campo de la portada y pulso **Buscar** → `/buscar?texto=barba`
→ toco el primer resultado (`/salon/barberia-el-cangrejo`) → ficha. `scrollWidth` = 390 en los tres
pasos, cero errores de consola, cero respuestas ≥400. La ficha abre por «Quién atiende», después «La
carta» con los **cuatro** servicios, el horario de los siete días y las doce reseñas con la respuesta
del salón.

*Un aviso para que no se confunda a nadie:* en una captura de página completa parece que a «La carta»
le falta «Corte clásico». **No falta**: es el zócalo pegajoso de «Pedir hora» tapándolo mientras
pasas por encima. Lo comprobé con `elementFromPoint` sobre el centro de la fila y con un barrido de
oclusión al fondo del documento en las nueve pantallas: **ningún** texto queda tapado de forma
permanente por el zócalo. Es un artefacto de la captura, no un defecto.

### Camino 2 · Elegir persona — **completo**

Desde la ficha, el primer bloque es el equipo. Toco «Kevin Ortega» →
`/salon/barberia-el-cangrejo/kevin-ortega`. Trae lo que el encargo pide: **9 años detrás de la silla**,
**4,3 con 10 opiniones**, **18 citas atendidas**, **4 clientas distintas**, descripción, Instagram
enlazado, los servicios que hace con duración y precio, y sus cinco reseñas con la respuesta del salón.
La puerta paralela `/personas` también existe, con su vacío propio.

*Lo único que no pude verificar:* el bloque de «lo que **no** hace del local». El código está
(`app/salon/[slug]/[persona]/page.tsx:190`), pero **en la semilla todos los profesionales hacen todos
los servicios de su salón** —lo comprobé contra la API en cuatro salones—, así que ese bloque **nunca
se pinta con los datos de verdad** y no lo he visto funcionando.

### Camino 3 · Reservar — **completo**, con una condición que hay que conocer

Portada → toco la fila de la Barbería El Cangrejo → ficha → «Pedir hora» → elijo «Arreglo de barba»
→ elijo «Kevin Ortega» → el carril de días ya dice **cuánto queda en cada uno antes de tocarlo**
(`MAR 8 · 23 libres`, `MIÉ 9 · 27 libres`, …, `DOM 13 · sin hueco`) → toco mañana → 27 horas → toco
las 6:30 p. m. → el botón dice **«Entrar y confirmar»** → me manda a `/entrar` con la selección
entera en el `volver=` → entro → **vuelve a la reserva con servicio, persona, día y hora puestos** →
«Confirmar» → `/mis-citas?nueva=01a07ffb-992f-79a2-9d95-2c9c2f52013c`.

La cita es real: `GET /mi/reservas` con `curl` la devuelve
(`2026-09-09T23:30:00Z`, Arreglo de barba, 800 centavos, `confirmada`), sale **marcada con filete
fucsia `rgb(200,30,100)` y fondo rosa `rgb(252,231,239)`** y la etiqueta «Acabas de reservarla», y
**aparece en la agenda del dueño** de mañana, con el nombre «Abdiel Him», subiendo los números del
día de 4 citas / $48.00 a 5 citas / $56.00.

**La condición.** Repetí el camino reservando para el **sábado 12** y la cita **no aparece en la
lista**: `li.fila--elegida` = 0. Es el tope de 30 citas futuras de `GET /mi/reservas` y la cuenta de
demostración ya lo agota. **La pantalla no miente**: en ese caso el aviso cambia y dice *«Está
guardada, aunque no la veas en la lista: esta cuenta ya arrastra 30 citas por delante y la API
entrega como mucho esas 30. El salón sí la tiene.»* Es honesto y está declarado en su `DIRECCION.md`.
Dicho eso, el último paso del camino («verla en mis citas») **depende de la fecha que elijas**, y la
frase que lo explica le cuenta a una clienta cómo pagina la API.

De propina, probé el botón **«Cancelar esta cita»**: abre una confirmación **dentro de la fila**
(«¿Seguro? El salón se entera al momento. · Sí, cancelar · Dejarla»), y al confirmar dispara
`POST /mi/reservas/{id}/cancelar` + `GET /mi/reservas` y la fila pasa a «La cancelaste tú». No es un
botón muerto y no es un solo toque destructivo.

### Camino 4 · Entrar — **completo**

Toco «Entrar» en la cabecera → `/entrar?volver=%2F` → toco «Rellenar» de la clienta → le quito una
letra a la contraseña → «Entrar». Resultado medido:

- Bloque de error visible con `role="alert"`: **«Correo o contraseña incorrectos»** —sin decir cuál
  de los dos campos falló—, más el apunte al pie del campo «Revisa la contraseña y vuelve a intentarlo».
- El **foco vuelve al campo de contraseña** (`document.activeElement` = `INPUT[password]`).
- **No se crea sesión**: `localStorage['agenda.sesion.v1']` sigue vacío.
- La URL no cambia.

Con la contraseña buena entra, vuelve a `/` —de donde venía— y la cabecera pasa a decir «Abdiel».

### Camino 5 · El salón — **completo**

Salgo desde el pie → toco «Soy un salón» → `/local` **sin sesión** explica qué hace falta y da un
botón para entrar → entro con el dueño → **cae directo en su salón sin preguntar en cuál**
(«ZONA DEL SALÓN · DUEÑO · Barbería El Cangrejo»). Arriba, los cuatro números del día: **4 citas en
pie · 2.1 h de silla ocupada · $48.00 previsto · 2 personas trabajando**, y un apunte de que hay 2
citas caídas que no cuentan en el dinero. Debajo, la rejilla con una columna por persona y las citas
colocadas por duración; y debajo, la misma información en lista. Toco «MAÑANA 9» en el carril y la
agenda cambia de día. La zona del salón es de tinta y no de cobalto, como dice que hace.

**Con una cuenta de clienta**, `/local` dice que esa cuenta no trabaja en ningún local. Comprobado.

### Limpieza (la base es compartida)

Creé **tres** reservas durante las pruebas y las **tres** están canceladas y verificadas por la API:

| id | cuándo | cómo la cerré | estado comprobado |
|---|---|---|---|
| `01a07ffb-992f-79a2-9d95-2c9c2f52013c` | mié 9, 6:30 p. m. | `POST /mi/reservas/{id}/cancelar` | `cancelada_cliente` |
| `01a08007-8839-7ec1-835b-a2e57002c467` | sáb 12, 4:30 p. m. | `POST /mi/reservas/{id}/cancelar` | `cancelada_cliente` |
| `01a08009-0ac2-7340-a35f-397337ed913b` | mié 9, 6:30 p. m. | por pantalla, para probar el botón | `cancelada_cliente` |

Comparé la lista final con la instantánea que tomé **antes** de empezar: no queda **ninguna** reserva
viva que no estuviera ya en la semilla.

---

## 3 · Qué hace mejor que nadie y qué hace peor

### Lo mejor

**Es la única portada que contesta la pregunta de verdad —«¿a qué hora me pueden atender hoy?»— sin
que nadie escriba nada, y la contesta con la hora real calculada por el motor**: nueve salones
ordenados de las 8:00 a las 3:00 p. m., partidos en mañana y tarde, cada fila con su precio de
entrada y su nota, y el que hoy no tiene hueco **bajado a un bloque aparte que lo dice** en vez de
maquillarse como los demás.

### Lo peor

**La agenda del dueño se rompe como herramienta en cuanto el salón tiene más de dos personas:** con
cuatro profesionales la rejilla mide 736 px dentro de un carril de 356 —ves **una columna y media de
cuatro**— y las cabeceras con los nombres, aunque son `position: sticky; top: 0`, cuelgan de un
contenedor que **no** hace scroll vertical, así que al bajar 500 px por la página todas se van a
`top: -500` y **desaparecen**: de media mañana en adelante estás leyendo citas sin saber de quién es
la columna que miras. Medido en `/local` con `dueno.salon-obarrio@demo.pa`.

---

## Apéndice · Otras cosas que encontré y que no tumban ningún descarte

Van aquí porque son hechos comprobados, no opiniones, y porque tres de ellas **contradicen su propio
`DIRECCION.md`**.

1. **«En la semilla no existe ni una foto» es falso.** `GET /publico/buscar` devuelve
   `foto_portada: "/fotos/spa.webp"` para `spa-costa-del-este`, y la profesional `ivonne-saavedra`
   tiene un `trabajo` con esa misma URL. La justificación de diseñar alrededor de las iniciales sigue
   siendo defendible; el dato en el que se apoya no lo es.
2. **La única foto real del sistema se pinta rota.** En
   `/salon/spa-costa-del-este/ivonne-saavedra`, bajo el rótulo «FOTOS DE SU TRABAJO», sale el icono
   de imagen rota con el texto alternativo «Masaje relajante» al lado y un hueco vacío debajo
   (`naturalWidth = 0`). Es la **única** respuesta ≥400 de todo el rastreo de 26 rutas:
   `404 /fotos/spa.webp` —y el archivo tampoco existe en el 8000—. El origen del 404 es la semilla,
   no el frontend; lo que es del frontend es que no hay repliegue y el rótulo se imprime igual.
   Captura: `shots/foto-404.png`.
3. **El bloque «lo que no hace» del perfil no se puede ver con datos reales** (todos los
   profesionales de la semilla hacen todo el catálogo de su salón). Está listado como entregado y no
   he podido comprobarlo funcionando.
4. **En el buscador, los carriles de filtros no avisan de que se arrastran.** A 390 px la fila de
   «QUÉ» corta «Uñas» por la mitad contra el borde derecho, sin degradado, flecha ni sombra —lo cual
   es coherente con D3— pero tampoco hay ninguna otra señal. El carril funciona; el que exista no se
   ve.
5. **El aviso del tope de 30 citas habla de la API a la clienta** («la API entrega como mucho esas
   30»). Es honesto y es implementación colándose en el producto.
