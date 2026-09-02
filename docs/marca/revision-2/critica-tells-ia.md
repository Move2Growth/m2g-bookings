# Crítica de dirección de arte: dónde se ve que esto lo hizo una máquina · Estado: completado

> Revisión adversarial encargada tras el rechazo de Luis («todo me parece IA, reutilizado, no hay
> botones personalizados, no hay nada que siga el brand book, todo muy mal, super IA, y trabajo
> muy perezoso»). El encargo era darle la razón con pruebas o quitársela con pruebas.
>
> **Resultado corto: tiene razón en lo esencial.** Nueve de las diez pantallas hay que rehacerlas.
> Lo que hay no es un producto con lenguaje propio: es la maqueta de `packages/tokens` aplicada
> con los componentes por defecto de cualquier hoja de estilos, con el brandbook contradicho en
> sus tres reglas duras (el color como estructura, el naranja que nunca es texto, y el canto vivo)
> **en la propia portada**.
>
> Rechaza por defecto. Lo que se salva está en la última sección y son cinco decisiones sueltas,
> ninguna de ellas un componente.

---

## 0 · Cómo se comprobó (para que otro lo repita)

Todo lo que aquí lleva un número está medido, no estimado. Método:

- **Navegador real**, Chromium por Playwright 1.49.1 (el que ya está en el repo), contra la web en
  `http://127.0.0.1:3100` y la API en `http://127.0.0.1:8000`, con el seed cargado.
- **Dos anchos**: 390 px (`isMobile`, `hasTouch`, escala 2) y 1440 px. Capturas de página completa
  y por franjas de 800 px.
- **Sesión de salón**: `/entrar` con `+50760000003` (Spa Costa del Este) y el código que enseña la
  propia pantalla. **Sesión de consola**: `consola@bukeo.local` con el código de
  `cd apps/api && ./.venv/bin/python -m agenda.consola_codigo`.
- **Medidas de layout** con `getBoundingClientRect()` y, para el ancho real de la tinta,
  `Range.getClientRects()` sobre los nodos de texto (así el `text-wrap: balance` de un titular no
  falsea el ancho ocupado).
- **Contrastes** con la fórmula WCAG 2.x aplicada a los colores **computados en pantalla**
  (`getComputedStyle`) y al fondo efectivo del primer ancestro con fondo opaco. No a los tokens:
  a lo que se ve.
- **Inventario de forma** contando, sobre todos los elementos visibles de cada página,
  `borderRadius`, `borderTopWidth`, `boxShadow`, `transition`, `fontFamily` y `letterSpacing`.

Lo que **no** se ha comprobado y por tanto aquí no se afirma: el modo oscuro (los tokens lo
declaran, el producto arranca en claro y no se abrió), el comportamiento con la fuente aún sin
cargar, la carga real en 3G, un teléfono físico con sol de frente (que es el argumento con el que
se eligió esta dirección en ADR-0016), y las pantallas `/panel/equipo`, `/panel/horario`,
`/panel/clientes`, `/panel/resenas`, `/mi/*` y `/reservar`, que quedaban fuera del encargo.

---

## 1 · Veredicto por pantalla

| Pantalla | Veredicto | En una frase |
|---|---|---|
| `/` | **Hay que rehacerla** | A 1440 px, cuatro de las ocho secciones dejan entre 464 y 560 px de ancho vacío (del 40 % al 48 % del contenedor de 1160), y los números 1-2-3 rompen a 2,34:1 la única regla de color que el proyecto declara innegociable. |
| `/buscar` | **Hay que rehacerla** | Diez salones, una sola foto en toda la página, y nueve fichas resueltas con un cuadrado de color y una letra cuyo color rota por posición en la lista, o sea con el color significando nada. |
| `/spa-costa-del-este` | **Hay que rehacerla** | La pantalla que Google indexa y por la que entra el cliente no tiene ni un bloque de color a sangre ni un solo filo: son 32 elementos con filete de 1 px sobre cal, que es exactamente lo que ADR-0016 descartó al rechazar la dirección A. |
| `/como-funciona` | **Hay que rehacerla** | 4.487 px de alto a 390 px y **cero imágenes**: cinco secciones que son cinco listas de texto con el mismo esqueleto, y los números en naranja sobre el bloque azul (3,38:1), dos saturados peleando en la misma línea. |
| `/para-negocios` | **Hay que rehacerla** | El mismo esqueleto que `/como-funciona` con la misma foto que ya se usó en la portada, y un bloque de cierre en tinta de 395 px de alto con 535 px de ancho vacíos a la derecha. |
| `/entrar` | **Hay que rehacerla** | Es el split-screen de acceso de cualquier SaaS de los últimos diez años; a 390 px el 50 % de la pantalla es cal vacía y el logotipo sale **azul por accidente**, heredado de la regla `a { color: acento }` del reset, no por decisión. |
| `/panel/agenda` | **Hay que rehacerla** | A 1440 px hay **484 px de franja blanca vacía** entre las pestañas y el contenido, y cada fila de cita deja el 83 % de su ancho sin usar; la agenda no tiene rejilla de horas, que es la referencia número 3 del propio moodboard. |
| `/panel/servicios` | **Hay que rehacerla** | Cuatro filas y **414 px de cal vacía** (el 49 % del alto de pantalla a 390 px), y es la misma maqueta exacta que `/consola/negocios`: cabecera, filete de 2 px, filas con filete de 1 px. |
| `/panel/ficha` | **Salvable** | Es la única con jerarquía propia (el bloque de estado manda sobre el título y eso resuelve una confusión real), pero arrastra un botón deshabilitado a 3,4:1 por `opacity: .55` y un botón blanco de 44 px que muerde la esquina de la foto. |
| `/consola` | **Hay que rehacerla** | **No cabe a 390 px**: el documento reclama 531 px en `/consola/negocios` y 889 px en `/consola/metricas`, y `body { overflow-x: hidden }` no lo arregla, lo esconde; además es la misma pantalla que el panel de un salón salvo 56 px de barra negra. |

---

## 2 · Los diez peores hallazgos

Ordenados por lo que más delata que esto lo escribió una máquina y no lo miró nadie. El criterio de
orden es: primero lo que escribe la regla y la rompe en la misma entrega, luego el componente por
defecto disfrazado, luego el relleno automático, y al final lo que solo demuestra que nadie abrió
la pantalla.

| # | Hallazgo | Prueba |
|---|---|---|
| 1 | **La regla que el proyecto llama innegociable está rota en la portada, y el verificador está escrito para no verla.** El brandbook §05 y ADR-0016 dicen «el naranja **nunca** es color de texto, sobre cal se queda en 2,4:1... es una consecuencia de la medida, no una preferencia». En pantalla, los números 1-2-3 de la portada son `#FF7A1F` sobre cal `#F2F3EF`: **2,34:1 medido** (mínimo AA para texto grande: 3). Y el guardián que debía impedirlo lleva escrito que **excluye esa combinación a propósito**. Escribir la regla, escribir el verificador que la protege, escribir el comentario que la explica y romperla en la primera pantalla del producto es la firma más clara de todo el repositorio. | `apps/web/app/globales.css:513` (`.pasos__numero { color: var(--color-abre) }`) · `packages/tokens/verificar-contraste.mjs:54-56` (el comentario «No se comprueba como color de texto sobre claro a propósito») · captura `t-portada-02.png` · el brandbook afirma en §05 que «las 41 combinaciones que el producto usa de verdad están medidas y todas cumplen AA»: es falso, esta no está en la lista y está en pantalla |
| 2 | **De las tres anchuras tipográficas, la de cifra (125 %) no se usa en ninguna hora, ninguna duración ni ningún precio.** El brandbook §06 lo pone en tabla: «Cifra · 125 % · Horas, duraciones y precios», y ADR-0016 lo repite como decisión. Medido en vivo: las horas de la agenda y los precios de los servicios salen a `font-stretch: 100%`. La clase `.cifra-grande` existe y se usa cinco veces: tres para el número decorativo de una lista de pasos, una para una métrica de la consola y una para la media de estrellas. **El eje que justifica toda la decisión tipográfica solo se aplica donde no hacía falta.** El eje funciona (mismo texto: 272,5 px a 100 %, 305,5 a 112 % y 341,3 a 125 %), o sea que no es una limitación de la fuente: es que no se aplicó. | `getComputedStyle` sobre `.fila__cifra` en `/panel/servicios` y `.agenda__hora > *` en `/panel/agenda`: `fontStretch: "100%"` en los diez casos · usos de `.cifra-grande`: `apps/web/app/page.tsx:215`, `como-funciona/page.tsx:120` y `:143`, `consola/metricas/page.tsx:106`, `[slug]/page.tsx:350` |
| 3 | **Los iconos son un set de librería con el grosor cambiado, y contradicen la única regla de forma que la marca declara suya.** `strokeWidth: 1.75`, `strokeLinecap: 'round'`, `strokeLinejoin: 'round'` sobre `viewBox 24`: es Feather/Lucide con 2 cambiado por 1,75. Los dibujos lo confirman: lupa = círculo r=7 más diagonal, reloj = círculo r=9 con las manecillas a las 10:10, calendario = rectángulo con dos patitas, lista = tres rayas. El comentario del fichero dice «no vienen de una librería». **Y el wordmark de la marca va con `strokeLinecap="square"`**, porque el brandbook §03 pide «remate a escuadra y esquinas en ángulo vivo» y §07 «nada de todo redondeado». Hay dos lenguajes de dibujo en el mismo producto y el que se ve en todas las pantallas con sesión es el genérico. | `apps/web/componentes/pestanas.tsx:69-71` frente a `apps/web/componentes/marca.tsx:22-23` · el `rect ... rx="1"` del icono de agenda en `pestanas.tsx:92` · capturas `panel-agenda-390.png` y `panel-agenda-1440.png` |
| 4 | **La ficha pública del salón no tiene ni un gramo de la dirección visual elegida.** Es la pantalla que Google indexa, la que se pega en la bio de Instagram y por la que entra el cliente. Inventario a 390 px: **0 secciones con fondo de color** (las seis salen `rgba(0,0,0,0)`), **0 filos de 6 px** y **32 elementos con filete de 1 px**. ADR-0016 dice en sus consecuencias: «Cierra la puerta a las tarjetas con sombra y a **los filetes finos como mecanismo de estructura**. Lo que separa es color, filo o aire». La dirección A se descartó por «23 reglas» de filete a 1,31:1. Aquí hay 31 apariciones de `1px solid` en la hoja y 32 elementos con filete en una sola pantalla: **la ganadora tiene más filetes que la que se rechazó por tenerlos.** | Inventario de `borderTopWidth` y `backgroundColor` de `/spa-costa-del-este` a 390 px · `grep -c "1px solid" apps/web/app/globales.css` = 31 · ADR-0016, sección «Alternativas consideradas» |
| 5 | **El sistema de imagen del producto es una letra sobre un rectángulo, y el color rota por posición en la lista.** En `/buscar` hay diez salones y **una sola foto**. Los otros nueve son un cuadrado de 104 px con la inicial, y el tono lo elige `nth-child(4n+1..4)`: azul, tinta, naranja, gris. Eso significa que **el mismo salón cambia de color si cambias el orden de la lista**, que es lo contrario exacto de «el color es la estructura». Y el naranja (que abre) y el azul (que cierra) aparecen uno debajo del otro en la misma lista, que es la única cosa que ADR-0016 prohíbe con la palabra «nunca». Todo el producto tiene **dos archivos de imagen** (`spa.webp` y `unas.webp`) y la portada usa el mismo dos veces en la misma pantalla. | `apps/web/app/globales.css:1138-1141` (la rotación) y `:1144-1154` (`.salon__inicial`) · `ls apps/web/public/fotos/` = 2 ficheros · captura `t-buscar-00.png` · en la portada, `unas.webp` sale a 356×222 en el hero y a 173×132 en la celda de categoría |
| 6 | **La llamada a la acción principal del negocio está a 2,34:1 por una colisión de especificidad que nadie miró.** «Crear mi salón», el botón que convierte un visitante en un negocio, sale con texto cal `rgb(242,243,239)` sobre naranja: **2,34:1** con un mínimo AA de 4,5. El mismo componente, el botón «Buscar» de la misma portada, sale correcto en tinta (6,99:1). La causa: `.seccion--tinta a` tiene especificidad 0-1-1 y machaca a `.boton--primario`, que tiene 0-1-0. Es decir: **el mismo botón es legible o ilegible según en qué bloque de color caiga**, en una dirección visual cuyo argumento de venta es que se usa con el sol de frente. | `apps/web/app/globales.css:126` frente a `:191` · medido con `getComputedStyle` sobre `.boton--primario` en `/`: `color: rgb(242,243,239)` dentro de `seccion seccion--holgada seccion--tinta` · captura `t-portada-04.png` |
| 7 | **A 1440 px el panel del salón tiene 484 px de franja blanca vacía y filas con el 83 % del ancho sin usar.** La barra de pestañas mide de `top=56` a `bottom=540` cuando debería medir 48 px de alto: en una ventana de 900 px, **el 54 % de la primera pantalla del panel es blanco**. Debajo, cada fila de cita mide 1.096 px de ancho y el texto acaba en `x=362` y `x=422`: 906 y 846 px de nada. Nadie abrió esta pantalla en un escritorio. | Medición con `getBoundingClientRect()` de `.pestanas`, `.app__cuerpo` y `.agenda__fila` en `/panel/agenda` a 1440×900 · captura `panel-agenda-1440.png` · la regla que lo provoca está en `apps/web/app/globales.css:906-912` |
| 8 | **La consola no cabe a 390 px y el desbordamiento está tapado, no resuelto.** `/consola/negocios` pide 531 px de ancho de documento y `/consola/metricas` pide 889 px, con un viewport de 390. El culpable de raíz es `.app__contexto`, que se estira a 372 px con el texto «Consola interna · Equipo M2G (demo) (superadmin)» y arrastra la barra a 531. Y `body { overflow-x: hidden }` (con el comentario «La página no se desplaza en horizontal nunca; lo que no cabe se desplaza dentro de su propio contenedor») hace que ese contenido **no se desplace dentro de nada: se pierde**. En la captura se ven cortados los filtros de periodo, la tercera cifra clave y la gráfica entera. Además, la rejilla `.cifras-clave` deja **una celda gris vacía** cuando el número de métricas no llena la última fila, y las 60 barras de «Reservas por día» miden **2 px de alto todas**, o sea que la gráfica no pinta nada dentro de una caja de 120 px. | `document.documentElement.scrollWidth` = 531 y 889 con `innerWidth` 390 · captura `consola-metricas-390.png`, que sale de 1778 px de ancho en vez de 780 · `apps/web/app/globales.css:32`, `:1592-1599` y `:1615-1618` |
| 9 | **Los cinco signos que más se repiten en el producto son caracteres de texto, no formas propias.** La valoración se compone con `'★'.repeat(n)` más `'★'.repeat(5-n)` en gris, a 14 px, en siete sitios distintos. Las flechas del navegador de día son `←` y `→` escritas en el JSX. El acordeón abre y cierra con `content: '+'` y `'−'`. El botón de quitar una foto es una `×`. El proyecto **tiene** un set de iconos SVG dibujados a mano y no incluye ni una flecha ni una estrella: se resolvió con la fuente del sistema, que además no controlamos. | `apps/web/app/[slug]/page.tsx:204`, `:375-376` y `:195` · `apps/web/componentes/ficha-salon.tsx:78` · `apps/web/app/panel/agenda/page.tsx:96` y `:110` · `apps/web/app/globales.css:531` y `:535` · `apps/web/app/mi/citas/page.tsx:233` |
| 10 | **197 estilos en línea reparten el ritmo vertical pantalla por pantalla, que es justo lo que el propio CSS dice que no puede pasar.** 75 `marginTop` puestos a mano y 30 `fontSize` elegidos a mano, 22 de ellos solo en la portada. El comentario de `globales.css:260` dice literalmente: «Un formulario es una columna de campos con el mismo aire entre ellos. **Sin esto cada pantalla inventa su propio margen y ninguna coincide con la de al lado**». Y luego cada página inventa su margen. En su descargo: todos usan tokens y no hay hexadecimales sueltos. Pero un sistema con 197 excepciones escritas a mano no es un sistema: es una hoja de estilos con parches, y así es como sale que todas las pantallas tengan el mismo ritmo aburrido y ninguna tenga el suyo. | `grep -rn "style={{" apps/web/app apps/web/componentes \| wc -l` = 197 · reparto: `page.tsx` 22, `reservar/page.tsx` 16, `panel/horario/page.tsx` 15, `como-funciona/page.tsx` 13 · los tres valores más repetidos son `marginTop: var(--espacio-4)` (23), `var(--espacio-3)` (17) y `var(--espacio-5)` (15) |

### Otros cuatro que no entran en los diez pero se arreglan el mismo día

- **El foco redondea los bloques.** `:focus-visible { border-radius: var(--radio-control) }` aplica
  el radio **al elemento**, no al anillo. Medido: una celda de categoría de la portada pasa de
  `border-radius: 0px` a `4px` al recibir el foco. En una dirección cuya única regla de forma es
  «bloques a canto vivo», navegar con el teclado va redondeando la portada.
  `apps/web/app/globales.css:98`.
- **El mismo botón cambia de naranja a azul debajo del dedo.** En `/entrar` y en `/reservar`, el
  botón principal es `boton--primario` en el primer paso y `boton--cierra` en el segundo, en el
  mismo sitio de la pantalla. Y «entrar en el producto» es naranja en `/entrar` y azul en
  `/consola`, que es literalmente el caso que ADR-0016 pone como prohibido («el mismo botón no
  puede salir naranja en `/entrar` y azul en `/reservar`»).
  `apps/web/app/entrar/page.tsx:254`, `apps/web/app/reservar/page.tsx:220`,
  `apps/web/app/consola/page.tsx:100`.
- **El botón deshabilitado se apaga con `opacity: .55`**, que es el recurso de plantilla por
  antonomasia y aquí deja «Añadir foto» a **3,4:1**, por debajo de AA.
  `apps/web/app/globales.css:185`, visible en `/panel/ficha`.
- **El dominio está escrito a fuego**: `bukeo.com/{ficha.slug}` en
  `apps/web/app/panel/ficha/page.tsx:179`, mientras el resto del producto lo saca de
  `NEXT_PUBLIC_NOMBRE_COMERCIAL` (`apps/web/lib/marca.ts:5`). Esto no es un tell de IA, es
  incumplimiento de D1 y de la tarea permanente QA-T007, pero sale en la misma pantalla y conviene
  cerrarlo a la vez. Igual que el `M2G` fijo de `apps/web/app/consola/layout.tsx:53`.

---

## 3 · Los cuatro puntos del encargo, contestados uno a uno

### 3.1 · Componentes que no se distinguirían de una plantilla de Tailwind

Estos seis no pasarían un test a ciegas contra el kit por defecto de cualquiera:

| Componente | Qué es exactamente | Dónde |
|---|---|---|
| `.boton` | Rectángulo con radio 4 px, borde de 1 px transparente, alto mínimo 44, padding lateral 1 rem, peso 500 y `translateY(1px)` al pulsar. No hay una sola decisión de forma. | `globales.css:166-185` |
| `.entrada` | El `input` del navegador con `border: 1px solid` y radio 4 px. Ni tratamiento del cursor, ni del estado enfocado propio, ni del relleno automático. | `globales.css:274-285` |
| `.panel` | Fondo blanco, borde de 1 px, padding 1 rem. La tarjeta genérica, solo que sin redondear. | `globales.css:227-232` |
| `.lista-filete` | `border-top: 1px solid` entre filas. El filete gris literal. | `globales.css:242` |
| `.aviso` | Fondo pastel más `border-left: 3px` de color. Es el bloque de alerta de Bootstrap desde 2013. | `globales.css:300-307` |
| `.esqueleto__fila` | El brillo que recorre un rectángulo gris cada 1,4 s. El esqueleto de carga por defecto, con `linear-gradient` a `rgba(255,255,255,.68)`. | `globales.css:935-951` |

Añado dos que son peores porque son piezas de producto, no primitivas: **la rejilla de horas**
(`.hora`, `globales.css:368-378`) son nueve rectángulos blancos idénticos con borde de 1 px, sin
franjas de mañana y tarde, sin peso distinto, sin nada, para lo que la marca llama «la hora que sí
existe»; y **la ficha de un salón en `/buscar`** (`.salon`, `globales.css:1104-1112`) es una tarjeta
con borde de 1 px, cuando el brandbook §07 dice literalmente «listas con filete entre filas **en vez
de una tarjeta por elemento**». Existe `.resultado` (`globales.css:611-623`), que sí hace lo que
manda el brandbook, y no se usa en `/buscar`. Hay dos componentes de lista de salones y el que está
en pantalla es el que el brandbook prohíbe.

### 3.2 · Dónde el código traiciona al brandbook

| Regla del brandbook / ADR-0016 | Qué pasa de verdad |
|---|---|
| «El color es la estructura» | En `/spa-costa-del-este` y en `/buscar` no hay ni un bloque de color ni un filo: son cal y filetes. En `/buscar` sí hay color, pero rotando por posición en la lista, o sea significando nada. |
| «El naranja nunca es color de texto» | `globales.css:513` lo pone como texto sobre cal (2,34:1) y `globales.css:1645` lo pone como color del glifo de las estrellas de puntuación. Y `globales.css:1060` lo pone sobre azul (3,38:1) en `/como-funciona`. |
| «El naranja abre, el azul cierra, nunca compiten» | Compiten en `/buscar` (fichas naranja y azul una debajo de otra), en `/panel/ficha` («Añadir foto» naranja y «Guardar ficha» azul en la misma pantalla, que por el propio ADR significa que una está mal clasificada) y entre `/entrar` (naranja) y `/consola` (azul) para la misma acción. |
| «Nada de todo redondeado, canto vivo» | Se cumple en reposo (solo salen radios de 0 y 4 px en todas las páginas medidas) y **se incumple al enfocar**: el bloque pasa de 0 a 4 px. Y los iconos van con remates y uniones redondeados. |
| «Sin sombras decorativas; la sombra se reserva para lo que flota» | El corazón de favorito lleva `box-shadow: 0 1px 2px` y no flota: está pegado a la ficha. `globales.css:1224`. |
| «Cifras tabulares, y esto no es un detalle» | `tabular-nums` sí está aplicado (comprobado en horas y precios). El ancho de cifra al 125 %, no. |
| «Lenguaje de rótulo de local, no de panel de control» | El panel del salón, la consola y `/buscar` son exactamente un panel de control: cabecera de 56 px, filete de 2 px, filas con filete de 1 px, badge de estado pastel con radio 4 px. |
| «Moodboard: papel y tinta, la materialidad de un negocio pequeño; la luz de Panamá, sombra dura» | Cero texturas, cero grano, cero tratamiento de superficie en 1.688 líneas de CSS. El único `filter` del producto es `brightness(0.94)` en un hover. La única sombra real es blanda: `0 1px 2px rgba(13,21,38,.08)`. |

### 3.3 · Vaguería

- **`/como-funciona`: 4.487 px de alto a 390 px y cero imágenes.** Cinco secciones, 15 nodos de
  texto en la más larga, ni un diagrama, ni una captura de la agenda, ni la rejilla de horas que la
  propia portada sí enseña.
- **Bloques de color donde debería haber imagen:** seis de las ocho celdas de categoría de la
  portada. Dos de ellas («Depilación» y «Estética») son, respectivamente, un rectángulo blanco con
  borde de 1 px y un rectángulo negro, cada uno con una palabra abajo a la izquierda. El brandbook
  §02 reconoce que faltan cuatro fotos por falta de crédito del generador; eso explica la deuda pero
  no explica que la solución sea un rectángulo vacío con una palabra en la esquina.
- **Rellenos de una sola letra:** `.salon__inicial` en `/buscar` (nueve de diez resultados),
  `.equipo__inicial` en la ficha (dos cuadrados negros de 56 px con «I» y «R»), y
  `.galeria--vacia span`, que pinta **una letra a tamaño cartel (4,25 rem) sobre un bloque azul** de
  hasta 260 px de alto cuando un salón no tiene fotos.
- **Huecos:** `/panel/servicios` a 390 px deja 414 px vacíos (49 % del alto), `/entrar` deja 420
  (50 %), `/panel/agenda` deja 268 (32 %). A 1440 px, la portada deja entre 464 y 560 px de ancho
  vacíos en cuatro secciones, y `/como-funciona` entre 339 y 561 px en las cinco.
- **La mitad oscura de `/entrar` a 1440** es un rectángulo de 720 px de ancho con un logotipo, tres
  líneas de texto y un pie: más del 75 % de esa mitad es tinta lisa sin nada.
- **Restos:** `apps/web/public/fuentes/` sigue sirviendo dos `woff2` de IBM Plex Sans más su
  licencia, la fuente que ADR-0016 descartó. Ya no la usa nadie: el layout importa
  `@fontsource-variable/archivo/wdth.css`.

### 3.4 · Uniformidad

El esqueleto es el mismo en las cinco pantallas públicas: sección transparente, filo, bloque de
color, sección transparente, bloque de tinta, pie de 856 px. Los altos de sección se mueven casi
siempre entre 360 y 730 px. El pie mide **856 px en todas las páginas**, lo que en `/buscar`
equivale al 28 % del documento entero.

En las pantallas con sesión es peor, porque el patrón se repite pieza a pieza: `/panel/servicios`,
`/panel/equipo`, `/consola/negocios` y `/consola/moderacion` comparten literalmente la misma
maqueta (`.cabeza-seccion` + `.filas` con borde superior de 2 px + `.fila` con borde inferior de
1 px + `.fila__cifra` a la derecha). La consola de M2G, donde se suspende el negocio de una persona
real, se distingue del panel de un salón **solo** en el color de 56 px de barra
(`globales.css:1561`), y el propio comentario de esa regla dice que «no puede parecer la misma
pantalla». Parece la misma pantalla.

### 3.5 · Detalles que un diseñador de verdad habría hecho

- **Estado de pulsación:** hay **cinco** reglas `:active` en 1.688 líneas, y son `translateY(1px)`
  dos veces y `scale()` tres. **No lo tienen** las entradas, las fichas de filtro, la rejilla de
  horas, las filas de la agenda, las filas del panel ni el acordeón. En un teléfono, donde el hover
  no existe, tocar una hora libre en la ficha de un salón no produce **ninguna** respuesta visual
  hasta que carga la página siguiente. Es la pieza que vende el producto.
- **Transiciones:** siete en total, todas con las mismas dos duraciones (140 y 220 ms) y la misma
  curva. La única con carácter es el `curva-empuje` del icono de pestaña.
- **Tipografía:** hay interletrado (-0,02 em en titulares, +0,08 em en cintillos) y hay
  `tabular-nums`. No hay ligaduras, ni `font-feature-settings`, ni versalitas, ni tratamiento de las
  fracciones, ni la anchura de cifra donde toca. La atención tipográfica está a medias.
- **Forma propia del icono:** no existe. Ver hallazgo 3.
- **Textura o grano:** no existe, y el moodboard la pide por escrito.
- **Foco:** aquí sí hay una decisión propia (ver la sección siguiente), estropeada por el
  `border-radius`.

---

## 4 · Lo que sí tiene carácter y hay que conservar

**Hay algo, pero es poco y ninguno de los elementos es un componente.** Son cinco decisiones
sueltas. No salvan el conjunto; sirven de semilla para rehacerlo.

1. **El filo naranja de 6 px** (`globales.css:140-141`). Es la única forma propia del producto que
   se ve a un metro de distancia, es coherente con la idea del canto de un rótulo, y funciona: en
   las capturas de la portada y de `/como-funciona` es lo que separa las secciones sin dibujar caja.
   Es genérico un borde de 1 px; no lo es uno de 6 px en un color que solo tiene ese trabajo.

2. **El anillo de foco en tinta y no en el color de marca**, con la inversión a cal dentro de los
   bloques oscuros (`globales.css:95-105`). Es contraintuitivo, está razonado con una medida (en
   azul se quedaba en 2:1 encima del bloque azul y del botón naranja, que son los dos sitios donde
   más se pulsa) y no lo hace nadie por defecto: los kits ponen el foco del color de marca. Conservar
   la decisión y quitarle el `border-radius`.

3. **El titular que interpola con el ancho en vez de saltar por puntos de ruptura**
   (`globales.css:71-77` y `:398`). Es una decisión de composición, no un valor por defecto: el
   `clamp` está calibrado para que a 390 px un titular a ancho de rótulo no se coma la pantalla y a
   1440 llegue al tamaño de cartel. Es la razón de que los titulares sean lo mejor de las capturas.

4. **La barra de estado como filete grueso a la izquierda de la fila de la agenda**
   (`globales.css:719-731`), en vez del punto de color que pone todo el mundo. Está justificado
   («se lee de reojo, cabe en una fila estrecha y no depende de distinguir dos tonos parecidos») y
   en la captura funciona: se distingue una cita confirmada de una cancelada sin leer la etiqueta.

5. **Dos gestos de artesanía menores** que demuestran que alguien sabía hacerlo y no tuvo tiempo o
   ganas de hacerlo en el resto: la flecha del `<select>` dibujada con dos gradientes lineales en
   vez de una imagen o un icono (`globales.css:1358-1366`), y la retícula de cifras clave dibujada
   con `gap: 1px` sobre un fondo del color de borde, de modo que la línea la dibuja el hueco
   (`globales.css:1592-1599`). Este último hay que arreglarlo antes de conservarlo, porque deja una
   celda gris vacía cuando las métricas no llenan la última fila.

**Lo que no hay:** ni un componente que no se pueda sustituir por su equivalente de plantilla sin
que nadie lo note. Ni un botón, ni un campo, ni una tarjeta, ni una lista, ni un icono. Si el
encargo era construir un lenguaje propio, lo que existe hoy es una paleta bien escogida, una fuente
bien escogida y una hoja de estilos que las aplica a los componentes de todo el mundo.
