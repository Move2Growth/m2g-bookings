# Auditoría del brandbook contra el código, y la decisión sobre las imágenes · Estado: completado

> **Qué es esto.** Dos cosas y ninguna más. La primera, comprobar promesa por promesa si el
> código cumple lo que prometen los apartados 01 a 08 de
> [`../BRANDBOOK-BUKEO.md`](../BRANDBOOK-BUKEO.md) y el
> [ADR-0016](../../arquitectura/adr/0016-la-direccion-visual-es-el-bloque-de-color.md), con
> fichero y línea. La segunda, decidir qué se pinta donde hoy no hay fotografía, con el código
> concreto de la decisión.
>
> **Qué NO es esto.** No es la caza de lo que delata que esto lo hizo una máquina, ni el
> lenguaje de componentes: los lleva otro agente cada uno. Aquí no se toca ni una línea de
> producto; este documento describe lo que hay y lo que debería haber.

---

## 0 · Cómo he medido

Cualquiera puede repetir esto. Todo sale de la web levantada en `http://127.0.0.1:3100` con el
seed de los once salones cargado, y de leer el CSS y las pantallas.

| Qué mido | Con qué | Cómo exactamente |
|---|---|---|
| **Superficie de color** | Chromium por Playwright, contexto `devices['iPhone 13']` (390 px CSS, factor de escala 3), `locale: es-PA` | Captura de **página completa** de cada pantalla, volcada a un `canvas` y contada píxel a píxel. Clasificación por HSL: luminosidad menor de 0,22 es **tinta**; saturación menor de 0,16 es **acromático** (blanco por encima de 0,93, gris claro por encima de 0,75, el resto gris medio); lo demás por matiz, de 200 a 265 grados **azul** y de 10 a 45 grados **naranja** |
| **Pantallas medidas** | Las mismas sesiones que usa la demo | **19 pantallas**: 8 públicas, las 7 pestañas del panel entrando con el dueño real `+50760000003`, y 4 de la consola con su correo, contraseña y segundo factor |
| **Filetes, sombras y anchura tipográfica** | `getComputedStyle` sobre el DOM vivo | Se cuenta cada uno de los cuatro bordes de cada nodo. Solo cuenta si tiene grosor, si su estilo no es `none` y si su color no es transparente. La anchura se lee de `fontStretch`, no del CSS fuente |
| **Contrastes** | La fórmula WCAG 2.x, la misma de `packages/tokens/verificar-contraste.mjs` | Luminancia relativa sRGB y cociente `(L1 + 0,05) / (L2 + 0,05)` |
| **Pesos de archivo** | `wc -c` y `gzip` sobre el fichero, y `curl` contra el servidor para lo que sirve `next/image` | Los bytes que da `curl` son los que viajan de verdad |

**Dos avisos de honestidad.**

1. La tabla de proporciones del apartado 05 del brandbook (cal 44 %, lienzo 20 %, tinta 16 %…)
   **no dice si se mide en superficie de pantalla o en frecuencia de uso**, y además mezcla
   colores de fondo con colores de texto («Tinta noche: texto principal **y** bloques oscuros»).
   Mi medida es de superficie. Comparo con ella porque es lo único escrito, pero digo aquí que
   la comparación no es exacta y que el brandbook debería precisarlo.
2. La medida de superficie es sobre **página completa**, no sobre la primera pantalla. Es la
   medida más favorable al brandbook, porque las secciones de color de la portada están abajo y
   una medida de primera pantalla las dejaría fuera.
3. **El código se movió mientras auditaba.** Todo lo de aquí está medido sobre el árbol de
   trabajo a partir del commit `25b9d87`, con otros dos agentes tocando `apps/web` en paralelo.
   Donde una línea ya haya cambiado, lo digo en la fila correspondiente. Los números de línea
   son los del momento de medir, no una garantía de que sigan ahí.

---

## 1 · Auditoría, apartado por apartado

Leyenda de veredicto:

- **cumple**: lo que dice el documento es lo que hace el código.
- **cumple de boquilla**: la pieza existe, está escrita, tiene su comentario justificándola, y
  **su efecto en la pantalla es marginal o nulo**. Un mecanismo que existe y no se usa no es una
  decisión de diseño: es una coartada.
- **no cumple**: el código hace lo contrario de lo que dice el documento.

---

### 01 · Estrategia de marca

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| «Tu agenda, gratis. Y el sitio donde te encuentran.» como frase de marca | `apps/web/lib/marca.ts` exporta `NOMBRE` y `PROMESA`, y `app/layout.tsx:9` compone el título con las dos. El nombre no está escrito a fuego en ninguna pantalla | **cumple** |
| «**No es un dashboard corporativo.** Se usa de pie, con una mano, entre clienta y clienta» | Las 7 pestañas del panel miden entre **78,9 % y 95,0 % de blanco** de superficie, con **0,1 % a 2,7 % de azul** y **0,0 % a 2,9 % de naranja**. `/panel/agenda` es blanco sobre gris con filetes y una barra de estado de 3 px. Visto en el navegador a 390 px, es un panel de control | **no cumple** |
| «No es lujo. **Es oficio**» | En todo el producto no hay **ni una sola representación de un oficio**: ni una herramienta, ni una trama, ni un icono de barbería o de uñas. Los iconos de la barra de pestañas son de repertorio genérico (calendario, líneas, personas, tarjeta). Donde falta una foto se pinta un rectángulo de color con una letra | **no cumple** |

---

### 02 · Moodboard

El moodboard son seis referencias, y su función es que las pantallas se parezcan a algo. Esta es
la comprobación de cuánto de cada una llegó al código.

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| 1 · **La pizarra del salón** con las citas escritas a mano | Nada. `/panel/agenda` es una lista de filas blancas | **no cumple** |
| 2 · **El rótulo pintado** de un local: color plano, letra grande, sin degradado | La letra grande existe solo en las tres páginas de marketing (ver 06). En las 16 pantallas restantes no hay un solo rótulo | **cumple de boquilla** |
| 3 · **La rejilla de horas** de un horario impreso, cifras alineadas y columnas que cuadran | `.horas` (`globales.css:359-383`) es una rejilla de botones, no un horario. Y las horas **no llevan la anchura de cifra**: ver 06 | **cumple de boquilla** |
| 4 · **Manos trabajando**: tijera, pincel de tinte, torno de uñas | Dos fotografías en todo el repositorio: `apps/web/public/fotos/unas.webp` y `spa.webp`. Ni un dibujo, ni un trazo, ni una trama de oficio | **no cumple** |
| 5 · **Papel y tinta**: recibo, tarjeta de cita, sello | No hay recibo, ni tarjeta de cita, ni sello. El apartado 04 promete «sello en el recibo de una cita» y el símbolo que lo haría no se usa en ningún sitio (ver 04) | **no cumple** |
| 6 · **La luz de Panamá**: alto contraste, sombra dura | Al revés: la estructura se dibuja con **30 filetes de 1 px a 1,29:1**, que es exactamente lo que desaparece con el sol de frente. Ver 07 | **no cumple** |

**Dato de contexto, no reproche:** cuatro de las seis fotos no existen porque el generador se
quedó sin crédito, y eso está anotado en la deuda viva del tablero. Lo que sí es reproche es que
**la ausencia se resolvió con un cuadrado de color y una letra** en vez de con dibujo, teniendo
seis referencias de moodboard que se pueden dibujar con CSS. Eso lo resuelve la parte 2 de este
documento.

---

### 03 · Logo suite

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| «El wordmark es `BUKEO` en versales dibujadas a trazo, cinco letras con líneas del mismo grosor, remate a escuadra» | `apps/web/componentes/marca.tsx:12-40`. Cinco letras, `strokeWidth={13}` uniforme, `strokeLinecap="square"` y `strokeLinejoin="miter"`. Es un trazado, no una fuente rotulada | **cumple** |
| «Se dibuja con `currentColor`, así que hereda el color del sitio donde está: **sobre papel sale tinta**» | Medido en vivo en `/`, `/buscar`, `/entrar` y `/spa-costa-del-este`: el logotipo de la **cabecera** sale en `rgb(22, 54, 199)`, que es el azul chiva `#1636C7`, no la tinta. En el pie sí sale en `rgb(13, 21, 38)`. La causa: el enlace de `componentes/cabecera.tsx:28` no lleva clase y hereda `a { color: var(--color-acento) }` de `globales.css:83-87` | **no cumple** |
| Tres versiones: **principal** (símbolo más wordmark), **invertida** y **solo símbolo** | En el producto se usa **una cuarta que no está en la tabla**: el wordmark solo. El símbolo no acompaña al wordmark en ningún sitio, y la versión «solo símbolo» no se usa nunca | **no cumple** |
| «Lo que no se hace nunca: … meterlo en una caja de color que no sea del sistema» | No pasa. El logotipo va siempre suelto | **cumple** |

**Consecuencia que conviene ver junta con el apartado 05.** Si el logotipo es azul, el azul deja
de significar «cierra» y pasa a significar también «esto es Bukeo». Es el mismo color haciendo
dos trabajos, que es justo lo que ADR-0016 quiso evitar con la regla de los dos saturados.

---

### 04 · Ícono

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| «El símbolo es **el hueco**: un bloque sólido con una muesca calada», con regla par‑impar | `componentes/marca.tsx:48-59`. Existe, está bien dibujado y usa `fillRule="evenodd"` | **cumple**, como pieza |
| «**Usos:** favicon e icono de aplicación, foto de perfil, sello en el recibo de una cita, marca de agua» | `Icono` está exportado y **no se importa en ningún fichero del repositorio**. No existe `apps/web/app/icon.*`, ni `public/favicon.ico`, ni `icons` en la metadata de `app/layout.tsx`. La carpeta `apps/web/public/marca/` está **vacía** | **no cumple** |
| «A 24 px y más, símbolo y wordmark juntos. A 16 px, solo el símbolo» | Nunca ocurre ninguna de las dos. El wordmark se pinta a 20, 22, 24 y 26 px según el sitio, siempre solo | **no cumple** |

**El símbolo del producto no aparece en el producto.** Ni en la pestaña del navegador. Es el
hallazgo más barato de arreglar de toda esta auditoría y el que más se nota.

---

### 05 · Color

Esta es la promesa central: «**el color es la estructura**». Va con los números delante.

#### 5.1 · Cuánta pantalla es de color y cuánta es blanco y gris

Superficie medida sobre página completa a 390 px, ponderada por área de captura:

| Conjunto | Blanco y gris | Tinta | Azul | Naranja |
|---|---|---|---|---|
| **Las 19 pantallas** | **84,3 %** | 7,0 % | 5,5 % | 2,7 % |
| Las 8 públicas | 79,2 % | 9,0 % | 7,9 % | 3,7 % |
| **Las 11 con sesión** (panel y consola) | **93,4 %** | 3,4 % | **1,1 %** | **1,0 %** |

Y el desglose por pantalla, en porcentaje de superficie:

| Pantalla | Blanco y gris | Azul | Naranja | Bloques de color |
|---|---|---|---|---|
| `/` | 64,9 | 10,9 | 4,9 | sí |
| `/como-funciona` | 63,3 | 25,4 | 2,3 | sí |
| `/para-negocios` | 81,0 | 0,4 | 5,9 | sí |
| `/buscar` | 89,6 | 3,5 | 2,7 | **no** |
| `/spa-costa-del-este` | 88,8 | 2,0 | 4,4 | **no** |
| `/entrar` | 92,5 | 0,6 | 5,9 | **no** |
| `/legal/privacidad` | 95,6 | 0,6 | 0,0 | **no** |
| `/panel/agenda` | 94,7 | 0,2 | **0,0** | **no** |
| `/panel/servicios` | 95,1 | 0,2 | 2,3 | **no** |
| `/panel/equipo` | 95,8 | 0,2 | 2,4 | **no** |
| `/panel/horario` | 93,5 | 2,3 | 0,7 | **no** |
| `/panel/clientes` | 97,7 | 0,2 | 0,4 | **no** |
| `/panel/resenas` | 93,4 | 0,1 | 2,9 | **no** |
| `/panel/ficha` | 86,9 | 2,7 | 2,1 | **no** |
| `/consola/negocios` | 91,3 | **0,0** | 0,2 | **no** |
| `/consola/moderacion` | 93,1 | **0,0** | **0,0** | **no** |
| `/consola/metricas` | 97,2 | 0,2 | **0,0** | **no** |
| `/consola/ranking` | 93,9 | 2,6 | **0,0** | **no** |

La columna «bloques de color» no es una apreciación: las clases `seccion--azul`,
`seccion--tinta`, `seccion--arena` y `filo` **solo aparecen en tres ficheros de veintiséis**:
`app/page.tsx`, `app/como-funciona/page.tsx` y `app/para-negocios/page.tsx`. Las tres son
páginas de marketing. En las otras veintitrés no hay ni un bloque ni un filo.

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| «**El color es la estructura.** Aquí no hay retícula dibujada ni tarjetas: lo que separa una sección de otra es un bloque de color a sangre y un filo grueso» | El bloque de color existe solo en la portada y en las dos páginas que explican el producto. **En el producto de verdad**, el que usa un salón todos los días, la estructura la dibujan filetes de 1 px: 93,4 % de superficie acromática y 2,1 % de saturado. Y en la portada hay **2 filos naranjas de 6 px contra 76 filetes de 1 px** | **cumple de boquilla** |
| Proporción declarada: cal 44 %, lienzo 20 %, tinta 16 %, arena 8 %, azul 6 %, naranja 2 % | Los dos saturados salen razonablemente cerca (azul 5,5 % frente a 6 %, naranja 2,7 % frente a 2 %). Lo que se desploma es la **tinta**: 7,0 % medido frente a 16 % prometido, y 3,4 % en las pantallas con sesión. Es decir, **los bloques oscuros a sangre casi no existen** | **cumple de boquilla** |
| «`.seccion--naranja`: la sección que pide dar el paso» (`globales.css:135-137`) | Definida y **no usada ni una vez** en todo el repositorio | **no cumple** |

#### 5.2 · «El naranja abre y el azul cierra»

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| «Hay dos colores saturados y cada uno tiene un trabajo» | `.boton--primario` (naranja) aparece 18 veces y `.boton--cierra` (azul) 15. Repasadas una a una, la clasificación es correcta y coherente: buscar, crear, añadir y publicar en naranja; guardar, confirmar, elegir hora y publicar respuesta en azul. `.hora:hover` pinta azul (`globales.css:379-383`), que es lo correcto: elegir la hora cierra | **cumple** |
| «El color lo decide **la fase del flujo, no la pantalla**» (ADR-0016) | Se respeta. El caso que más se le acerca es el botón único de `/entrar` y `/reservar`, que es naranja en el paso del teléfono y azul en el de verificar (`app/entrar/page.tsx:254`, `app/reservar/page.tsx:220`): eso es la fase del flujo mandando sobre la pantalla, que es justo lo pedido | **cumple** |
| «Si en una pantalla hay dos acciones saturadas, una de las dos está mal clasificada» | En `/panel/ficha` conviven «Añadir foto» en naranja (`app/panel/ficha/page.tsx:475`) y «Guardar ficha» en azul (`:340`). Medido: 2,7 % de azul y 2,1 % de naranja en la misma pantalla. Es defendible en la regla estricta del ADR («nunca en el mismo botón») y choca con esta frase del brandbook | **cumple de boquilla** |
| «**El naranja nunca es color de texto.** Sobre cal se queda en 2,4:1» | Se rompía en dos sitios. El primero, `.pasos__numero`, medía **2,34:1** sobre papel y **otro agente lo ha arreglado mientras yo auditaba**: ahora es bloque naranja con tinta encima, que es lo correcto. Queda un resto de la regla vieja en `globales.css:1073`. El segundo **sigue roto**: `globales.css:1658` `.estrella { color: var(--color-abre) }` mide **2,61:1** sobre lienzo. Las estrellas de valorar una cita son texto naranja sobre blanco | **no cumple**, ya a medias |

#### 5.3 · El verificador de contraste

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| «Las **41 combinaciones** que el producto usa de verdad están medidas y todas cumplen AA» | Cierto: `node packages/tokens/verificar-contraste.mjs` imprime «41 combinaciones, todas cumplen AA» | **cumple**, en lo que mide |
| «Lo comprueba un script **que falla el proceso** si alguien retoca un color solo un poco» | El script sí termina con `process.exit(1)` si falla, pero **no está enganchado a ningún proceso**. Aparece una sola vez en el repositorio, como script `contraste` en `packages/tokens/package.json:14`. No lo llama `pnpm lint`, no hay `.github/workflows`, y el `Makefile` no lo menciona. Nadie lo ejecuta nunca | **cumple de boquilla** |
| Que las 41 sean «las que el producto usa de verdad» | **No incluyen `--color-borde` `#D5D8D0`**, que es el color de los treinta filetes que dibujan la estructura, y que mide 1,29:1 sobre papel. **Y excluyen a propósito el naranja como texto**: el comentario de `verificar-contraste.mjs:54-56` lo dice literalmente, «no se comprueba como color de texto sobre claro a propósito». El código lo usa como texto en dos sitios. El verificador está construido para no encontrar lo que hay | **no cumple** |

#### 5.4 · Los estados de una reserva

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| Cinco estados, mismo color en web, panel y app, y ninguno usa el azul ni el naranja de marca | `tokens.json:70-97` los define con fondo, texto y borde propios, y `globales.css:350-355` y `:723-731` los aplican igual en la etiqueta y en la barra de la fila de agenda. Los cinco cumplen AA en el verificador. Ninguno reutiliza los saturados de marca | **cumple** |

---

### 06 · Tipografía

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| «Una sola familia, **Archivo Variable**, autoalojada» | `app/layout.tsx:5` importa `@fontsource-variable/archivo/wdth.css`. Una familia, autoalojada, una petición | **cumple** |
| «Vetadas: Inter, Fraunces, Bricolage y General Sans» | Ninguna aparece en el código | **cumple** |
| «**Tres anchos.** Rótulo 112 % para titulares. Texto 100 %. **Cifra 125 % para horas, duraciones y precios**» | El ancho de cifra vive en una sola clase, `.cifra-grande` (`globales.css:59-64`), y esa clase se usa **cinco veces en todo el producto**: los números 1, 2 y 3 de las listas de pasos de dos páginas de marketing (`app/page.tsx:215`, `app/como-funciona/page.tsx:120` y `:143`), la nota media del perfil (`app/[slug]/page.tsx:350`) y una cifra clave de la consola (`app/consola/metricas/page.tsx:106`). **Ni una sola hora, ni una duración, ni un precio la lleva.** Medido en vivo: 0 elementos con `font-stretch: 125%` en las siete pestañas del panel y en tres de las cuatro de la consola | **no cumple** |
| «El contraste entre un titular y el cuerpo lo da aquí **el ancho**» | En la portada hay 30 elementos a 112 %; en `/como-funciona`, 15. En el panel, entre 1 y 4 por pantalla. Y en `/panel/agenda`, que es la pantalla que más se abre del producto, **el único elemento con ancho de rótulo es un titular invisible**: `app/panel/agenda/page.tsx:90` es un `<h1 className="oculto-visualmente">`. El ancho de rótulo, en la pantalla principal del producto, no se ve nunca | **no cumple** |
| «**Cifras tabulares, y esto no es un detalle.** Horas, duraciones y precios llevan `tabular-nums` siempre» | La clase `.cifras` (que activa `tabular-nums` pero **no** el ancho de 125 %) se usa en 18 ficheros. Las horas de la agenda la llevan. Esta mitad de la promesa sí se cumple | **cumple** |
| «Los campos de formulario **nunca** bajan de 16 px» | Medido en vivo en cuatro pantallas: **0 campos por debajo de 16 px** y **0 nodos de texto por debajo de 14 px** | **cumple** |
| «Escala: **de 0,75 rem a 4 rem**» | `tokens.json:121` dice `"cartel": "4.25rem"`. El brandbook dice que si divergen manda el brandbook, así que o el documento dice 4,25 rem o el token baja a 4 rem | **no cumple**, en un detalle |

---

### 07 · UI y aplicaciones

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| «Superficies y bloques a canto vivo, controles a 4 px, y **nada con forma de píldora**» | Medido en vivo: **0 elementos con radio mayor o igual a 100 px** en las pantallas revisadas. El token `radio.pildora: 999px` sigue existiendo sin usarse (`tokens.json:153`, `tokens.ts:155`, `variables.css:83`), que es una invitación a que vuelva | **cumple** |
| «**El filo.** La línea de 6 px en naranja que corta la página entre bloques» | `.filo` (`globales.css:140`) existe y se usa **9 veces, todas en las tres páginas de marketing**. En la portada hay **2 filos** de 6 px contra **76 filetes** de 1 px, contados sobre el DOM vivo. Proporción de 1 a 38 | **cumple de boquilla** |
| «**Sin sombras decorativas.** La sombra se reserva para lo que de verdad flota» | 4 declaraciones de `box-shadow` en `globales.css`. Dos son legítimas (`.hoja`, y `.servicio--elegido` que es una barra `inset`, no una sombra). `.panel--elevado` (`:238`) está definida y no se usa. Y `.salon__guardar` (`:1224`) lleva sombra: son los **10 corazones de guardar** que salen en `/buscar`, cada uno con su cajita blanca elevada sobre la ficha. No flotan: están pegados | **cumple de boquilla** |
| «**Lo que separa es color, filo o aire**», y ADR-0016 «cierra la puerta a los filetes finos como mecanismo de estructura» | `globales.css` tiene **31 reglas con `1px solid`**, de las que 30 pintan un filete visible (la de `:173` es transparente). En vivo: `/buscar` tiene **79 bordes visibles**, de ellos **43 en `#D5D8D0`**; `/spa-costa-del-este` tiene **110**, de ellos 21; la portada **82**, de ellos 20. Y `#D5D8D0` mide **1,29:1 sobre papel** y **1,44:1 sobre lienzo**. **ADR-0016 tumbó la dirección A por «23 filetes a 1,31:1».** La dirección que ganó tiene más filetes y con menos contraste que la que perdió por tenerlos | **no cumple** |
| «**Densidad.** Listas con filete entre filas **en vez de una tarjeta por elemento**: en un teléfono caben tres salones más por pantalla» | El marketplace hace lo contrario. `.salon` (`globales.css:1104-1110`) es una caja con `border: 1px solid` **por elemento**, y en `/buscar` hay 10. La pieza que sí es filas con filete, `.resultados` y `.resultado` (`globales.css:607-623`), es **CSS muerto**: no hay ni un `className="resultado"` en ningún `.tsx`. Está escrita la regla correcta y se usa la contraria | **no cumple** |
| «**El foco no es del color de marca.** El anillo va en tinta noche sobre fondo claro y en cal dentro de los bloques oscuros» | `globales.css:95-105`. Exactamente eso, y con la inversión dentro de los bloques | **cumple** |
| «**Movimiento.** Transiciones de 140 a 220 ms y **nada que se mueva solo**. Todo se apaga con `prefers-reduced-motion`» | Las transiciones usan `--movimiento-rapido` (140 ms) y `--movimiento-normal` (220 ms). Hay una animación en bucle, `.esqueleto__fila` (`:946`), declarada como excepción en el propio comentario y con motivo. El apagado global está en `:405-411` | **cumple** |
| «**En esa capa no hay ni un hexadecimal escrito a mano; si aparece uno, es un error**» | En `globales.css` no hay ni uno. Pero sí hay **dos `rgba()` escritos a mano** (`:942` y `:1053`), y en `app/layout.tsx:22` hay un hexadecimal a mano: `themeColor: '#F2F3EF'`, que es el papel de la paleta duplicado fuera de los tokens. Si cambia el papel, la barra del navegador se queda con el viejo | **cumple de boquilla** |

---

### 08 · Cómo se elige y cómo se cambia

| Qué promete | Qué hace el código | Veredicto |
|---|---|---|
| «La identidad no se eligió a ojo»: tres direcciones, prototipos comparables, tres críticos | Los prototipos están en `docs/marca/propuestas/` y la decisión razonada en `DECISION-DE-MARCA.md`. El proceso ocurrió y está documentado | **cumple** |
| Las **cinco condiciones** de la auditoría de accesibilidad, aplicadas | Cuatro se cumplen. **La segunda no**: «lo que se toca no se delimita con un filete de 1,15:1» se aplicó a los controles (`.ficha`, `.entrada`, `.hora` usan `--color-borde-fuerte`, que mide 3,88:1 sobre lienzo) pero **no a la estructura**, que quedó en `--color-borde` a 1,29:1 y con treinta reglas. La condición se cumplió al pie de la letra y se incumplió en su motivo | **cumple de boquilla** |
| «Para cambiar algo de aquí: se cambia **este documento primero**, después los tokens, y solo entonces las pantallas» | No lo puedo comprobar: haría falta reconstruir el orden de los commits de marca y de código, y el repositorio tiene el trabajo de varios agentes mezclado en la rama. **Lo dejo sin veredicto** en vez de suponerlo | **sin comprobar** |

---

### Resumen de veredictos

De las 31 promesas comprobables:

| Veredicto | Cuántas |
|---|---|
| **cumple** | 12 |
| **cumple de boquilla** | 9 |
| **no cumple** | 9 |
| sin comprobar | 1 |

> Contadas sobre el árbol a partir del commit `25b9d87`. Uno de los «no cumple» (el naranja
> como color de texto) está ya arreglado a medias por otro agente mientras se escribía esto.

**Y las tres que más pesan están todas en el lado malo:**

1. **«El color es la estructura»** es cierto en la portada y falso en el producto. En las once
   pantallas que un salón usa a diario, el 93,4 % de la superficie es blanco o gris y el 2,1 %
   es color de marca.
2. **La dirección ganó por rechazar los filetes finos y está construida con filetes finos.**
   ADR-0016 descartó la dirección A por «23 filetes a 1,31:1». Esta tiene 30 reglas de filete,
   79 bordes visibles en una sola pantalla, y su color de filete mide 1,29:1. Es peor que
   aquello por lo que se descartó a la otra.
3. **De los tres anchos tipográficos, el de cifra no se usa nunca donde el brandbook dice.** Se
   usa en cinco sitios y ninguno es una hora, una duración ni un precio.

---

## 2 · La decisión sobre las imágenes

### 2.1 · El problema, con los números

- Hay **dos fotografías en todo el repositorio**: `apps/web/public/fotos/unas.webp` (52.718
  bytes) y `spa.webp` (130.830 bytes).
- **No se pueden generar más.** La cuenta de Higgsfield está sin créditos este periodo,
  comprobado intentando una generación real.
- Consultada la API con el seed cargado: hay **10 salones publicados y uno solo tiene foto de
  portada**.
- Medido en el navegador: en `/buscar` salen **10 fichas, 1 con foto y 9 con `.salon__inicial`**,
  que es un rectángulo de color plano con la primera letra del nombre. En la portada hay **8
  celdas de categoría y 2 llevan foto** (y el comentario de `app/page.tsx:151-152` dice «cuatro
  llevan foto y cuatro no», que no es verdad). En el perfil de un salón sin foto se pinta
  `.galeria--vacia`, un bloque azul de proporción 3:1 con la inicial a tamaño de cartel. En la
  sección de equipo hay **0 fotos de profesional** y todo son `.equipo__inicial`.

**El diagnóstico.** El problema no es que falten fotos. El problema es que **el producto trata la
falta de foto como una avería y pinta un parche**. Una inicial dentro de un cuadrado es el
recurso por defecto de cualquier aplicación del mundo: es exactamente lo que hace Gmail, Slack y
Notion. Es el sitio donde más se nota que esto lo montó una máquina eligiendo el camino corto.

### 2.2 · La decisión

**Donde no hay fotografía va un rótulo, no un parche.** Y el rótulo no es un sustituto de la
foto: es **la forma por defecto de presentar un salón**. Cuando hay foto, la foto manda; cuando
no la hay, el rótulo es la pieza normal del sistema, no un hueco tapado.

Sale del brandbook, no de mi gusto, y de tres sitios concretos:

- **Del apartado 03**, que dice que el lenguaje de esta marca es «el del **rótulo pintado de un
  local**, no el de una aplicación», y que «un rótulo se lee desde la acera».
- **Del moodboard 2, 3 y 4**: el rótulo pintado con color plano y letra grande; la rejilla de
  horas de un horario impreso; y las manos trabajando, que aquí se resuelven **dibujadas a
  trazo**, que es lo que se puede hacer sin crédito de generación y sin banco de imágenes.
- **Del apartado 06**, que ya tiene la tipografía a tamaño de cartel y no la usa en ninguna
  parte. El rótulo le da por fin trabajo al ancho de 112 % fuera de la portada.

El rótulo tiene **tres ingredientes** y ninguno pesa:

| Ingrediente | Qué es | De dónde sale |
|---|---|---|
| **El nombre a tamaño de cartel** | El nombre del salón entero, en versales, ancho de rótulo, con el filo naranja arriba. No la inicial: **el nombre**. Una inicial es un avatar; un nombre grande es un rótulo | Apartados 03 y 06 |
| **La trama del oficio** | Un patrón que se repite, dibujado **a trazo**, distinto por familia de servicio: el peine, la uña, el agua, la ceja, la brocha. No un icono centrado: una trama, como el toldo de un local | Moodboard 4, sin fotografía |
| **El par de colores** | Uno de los cuatro pares de la paleta (tinta, azul, naranja, y lienzo con filete) elegido por la posición en la lista, con la trama encima al 24 % de la propia tinta del bloque | Apartado 05 |

**Por qué aguanta once salones sin repetirse ni parecer relleno.** Lo que distingue a un salón de
otro **es su nombre**, que es único por definición y ocupa la pieza entera. La trama distingue el
**oficio**, no el negocio, y eso está bien: dos barberías del barrio comparten el poste
rojiblanco y nadie las confunde. Con 6 tramas y 4 pares de color hay 24 combinaciones para 11
salones, y aun con la trama repetida el rótulo nunca lo está.

**Qué se descarta explícitamente y por qué:**

- **Fotografía de banco:** prohibida por el encargo y ya rechazada en `DECISION-DE-MARCA.md`.
  Además miente sobre cómo es el sitio, y este producto vende que la hora que se ve es la hora
  que existe.
- **Imágenes generadas:** no se pueden hacer, comprobado.
- **Ilustración a color:** dos o tres ilustraciones se ven bien y once se ven repetidas, y cada
  una son kilobytes que en 3G se notan.
- **Seguir con la inicial:** es el parche que hay que quitar.

### 2.3 · Lo que pesa

Medido sobre el fichero que he escrito y probado:

| Qué | Bytes |
|---|---|
| El CSS completo, con sus comentarios | 8.785 |
| El mismo CSS sin comentarios | 5.497 |
| **Comprimido con gzip, que es lo que viaja** | **1.369** |
| Cada trama, como `data:` dentro del CSS | entre 203 y 256 |
| Para comparar: `spa.webp` servida por `next/image` a 640 px | **57.120** |

**Todo el sistema, las seis tramas incluidas, pesa el 2,4 % de una sola fotografía y no añade ni
una petición de red.** Se puede pegar en `globales.css` tal cual.

---

### 2.4 · Ejemplo 1 · El rótulo, en sus dos tallas

Sustituye a `.salon__inicial` (`globales.css:1144-1154`) en las listas y a `.galeria--vacia`
(`globales.css:1438-1454`) en la cabecera del perfil. Verificado en Chromium a 390 px.

```css
/* ── El rótulo: lo que se pinta donde no hay foto ──────────────────────────────
   No es un hueco tapado: es la forma por defecto de presentar un salón. El nombre hace de
   imagen, la trama dice el oficio y el color pone el ritmo. */

.rotulo {
  position: relative;
  display: grid;
  align-content: end;
  overflow: hidden;
  background: var(--rotulo-fondo, var(--color-acento));
  color: var(--rotulo-tinta, var(--color-acento-texto));
  /* El filo del brandbook, aquí haciendo de canto de chapa del rótulo. */
  border-top: 6px solid var(--color-abre);
}

/* La trama va detrás, en la propia tinta del bloque. Se pinta como máscara y no como imagen
   de fondo: así un mismo archivo sirve sobre azul, sobre tinta y sobre naranja, que es la
   misma idea del logotipo con `currentColor`. */
.rotulo::before {
  content: '';
  position: absolute;
  inset: 0;
  background-color: currentColor;
  opacity: var(--rotulo-trama-fuerza, 0.24);
  -webkit-mask-image: var(--rotulo-trama);
  mask-image: var(--rotulo-trama);
  -webkit-mask-size: var(--rotulo-trama-talla, 44px);
  mask-size: var(--rotulo-trama-talla, 44px);
  -webkit-mask-repeat: repeat;
  mask-repeat: repeat;
}

.rotulo__texto {
  position: relative;
  padding: var(--espacio-3);
  font-family: var(--tipografia-familia-display);
  font-weight: var(--tipografia-pesos-display);
  font-stretch: var(--tipografia-ancho-rotulo);
  line-height: var(--tipografia-interlineado-apretado);
  letter-spacing: var(--tipografia-espaciado-titular);
  text-transform: uppercase;
  /* Rompe solo si una palabra sola no cabe. Un rótulo pintado no parte «peluquería» por la
     mitad: si no entra, se pinta más pequeño. */
  overflow-wrap: break-word;
  text-wrap: balance;
}

/* Talla grande: la cabecera del perfil. No lleva proporción fija, porque un rótulo que
   recorta el nombre del local no es un rótulo. */
.rotulo--cartel { min-height: 34vw; --rotulo-trama-talla: 64px; }
.rotulo--cartel .rotulo__texto {
  padding: var(--espacio-5) var(--espacio-4) var(--espacio-4);
  font-size: var(--rotulo-talla, var(--tipografia-tamano-titulo-2));
}

/* Las tres tallas, por letras de la palabra más larga del nombre. Así estrecha el letrero un
   rotulista: manda el nombre, no el punto de ruptura. El servidor cuenta las letras en una
   línea y pone la clase; no se calcula con `cqw` porque el ancho del rótulo depende del texto
   y el cálculo se muerde la cola.
   Los topes están medidos con Archivo a peso 800 y anchura 112 %, donde un glifo ocupa
   0,81 em: la palabra más larga tiene que caber en 358 px, que es un teléfono de 390 menos
   el aire. */
.rotulo--larga { --rotulo-talla: clamp(1.375rem, 0.7rem + 3.4vw, 2.5rem); }   /* 10 letras o más */
.rotulo--media { --rotulo-talla: clamp(1.625rem, 0.8rem + 4.2vw, var(--tipografia-tamano-titulo-1)); } /* 7 a 9 */
.rotulo--corta { --rotulo-talla: clamp(2.25rem, 1rem + 6.4vw, var(--tipografia-tamano-cartel)); }      /* 6 o menos */

@media (min-width: 900px) { .rotulo--cartel { min-height: 220px; } }

/* Talla chica: la miniatura de una lista, 104 px. Ahí no cabe un nombre, caben las iniciales
   de las dos primeras palabras. Es la misma regla del apartado 04 del brandbook: a 24 px el
   wordmark, a 16 px solo el símbolo. */
.rotulo--sello {
  aspect-ratio: 1;
  align-content: center;
  justify-items: center;
  --rotulo-trama-talla: 52px;
}
.rotulo--sello .rotulo__texto {
  padding: 0;
  font-size: var(--tipografia-tamano-titulo-2);
  letter-spacing: 0.02em;
}
```

**Lo que hay que cambiar en el componente**, que son tres líneas en
`apps/web/componentes/ficha-salon.tsx:58-64`:

```tsx
// La talla la decide la palabra más larga del nombre, que es lo que de verdad limita.
const masLarga = Math.max(...salon.nombre.split(/\s+/).map((p) => p.length))
const talla = masLarga >= 10 ? 'rotulo--larga' : masLarga >= 7 ? 'rotulo--media' : 'rotulo--corta'
// Las iniciales de las dos primeras palabras, no una letra suelta: «BE», no «B».
const iniciales = salon.nombre.split(/\s+/).slice(0, 2).map((p) => p[0]).join('').toUpperCase()

<span className={`rotulo rotulo--sello oficio--${oficioDe(salon.categorias)}`}>
  <span className="rotulo__texto">{iniciales}</span>
</span>
```

**Verificado en Chromium a 390 px con los once nombres del seed:** ningún nombre desborda su
caja y ninguno parte una palabra. `Peluquería Doña Elvia` sale a 24,46 px, `Estética Integral
Obarrio` a 29,18 px y `Spa Costa del Este` a 40,96 px, y los tres miden exactamente el ancho
disponible de 358 px.

---

### 2.5 · Ejemplo 2 · Las seis tramas de oficio

Dibujadas a trazo, con `viewBox` de 40 y trazo de 2, y **sin color propio**: el color lo pone el
bloque, porque van como máscara. Cada una es un `data:` de entre 203 y 256 bytes. No hay
peticiones de red.

```css
/* Van a trazo y no a relleno porque el brandbook manda «dibujado a trazo» en el logotipo y en
   el símbolo, y porque a esta escala un relleno se convierte en mancha. */

.oficio--barberia {   /* el peine */
  --rotulo-trama: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40' fill='none' stroke='%23000' stroke-width='2'%3E%3Cpath d='M2 12h36M9 12v10M20 12v10M31 12v10'/%3E%3Cpath d='M2 32h36M14 22v10M26 22v10'/%3E%3C/svg%3E");
}
.oficio--unas {       /* la uña con su lúnula */
  --rotulo-trama: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40' fill='none' stroke='%23000' stroke-width='2'%3E%3Cpath d='M12 32V16a8 8 0 0 1 16 0v16z'/%3E%3Cpath d='M13 21a7 5 0 0 1 14 0'/%3E%3C/svg%3E");
}
.oficio--spa {        /* el agua */
  --rotulo-trama: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40' fill='none' stroke='%23000' stroke-width='2'%3E%3Cpath d='M0 13c5-6 10 6 15 0s10-6 15 0 10 6 15 0'/%3E%3Cpath d='M-5 27c5-6 10 6 15 0s10-6 15 0 10 6 15 0'/%3E%3C/svg%3E");
}
.oficio--cejas {      /* el arco con sus pelos */
  --rotulo-trama: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40' fill='none' stroke='%23000' stroke-width='2'%3E%3Cpath d='M4 26a16 16 0 0 1 32 0'/%3E%3Cpath d='M8 22l-4-5M16 15l-2-6M24 15l2-6M32 22l4-5'/%3E%3C/svg%3E");
}
.oficio--maquillaje { /* la brocha */
  --rotulo-trama: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40' fill='none' stroke='%23000' stroke-width='2'%3E%3Cpath d='M20 2v18M13 20h14l-7 18z'/%3E%3Cpath d='M13 26h14'/%3E%3C/svg%3E");
}
.oficio--horas {      /* la retícula del horario: el oficio por defecto, y el símbolo dentro */
  --rotulo-trama: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40' fill='none' stroke='%23000' stroke-width='2'%3E%3Cpath d='M0 10h40M0 20h40M0 30h40M10 0v40M30 0v40'/%3E%3Crect x='10' y='20' width='20' height='10' fill='%23000'/%3E%3C/svg%3E");
}
```

**Reparto sobre las categorías que trae el seed**, consultadas a la API:

| Categoría del seed | Trama | Cuántos salones |
|---|---|---|
| Barbería | `oficio--barberia` | 2 |
| Peluquería y salón | `oficio--barberia` | 2 |
| Uñas | `oficio--unas` | 1 |
| Spa y masajes | `oficio--spa` | 2, uno con foto |
| Pestañas y cejas | `oficio--cejas` | 1 |
| Maquillaje | `oficio--maquillaje` | 1 |
| Estética facial y corporal | `oficio--horas` | 1 |
| Depilación y cualquiera que llegue | `oficio--horas` | por defecto |

`oficio--horas` es el que se lleva lo que no encaja, y no es un comodín gris: es la retícula de
horas del moodboard 3 con el hueco del apartado 04 dentro. Una categoría nueva mañana entra sin
que nadie dibuje nada.

---

### 2.6 · Ejemplo 3 · La retícula de horas

La pieza que no dibuja un oficio: dibuja **el producto**. Es el horario impreso del moodboard 3
con las casillas ocupadas en tinta y **una casilla calada en el naranja que abre**, que es
literalmente el símbolo del apartado 04, la hora que sí existe. Todo con gradientes: **cero
bytes de imagen y cero peticiones**.

Va en las seis celdas de categoría de la portada que hoy son color liso, en los estados vacíos
(`.vacio`, `globales.css:953-968`) y en la cabecera de cualquier pantalla que necesite fondo.

```css
.reticula {
  position: relative;
  background-color: var(--retic-fondo, var(--color-arena));
  background-image:
    repeating-linear-gradient(to right,
      var(--retic-linea, var(--color-tinta)) 0 1px, transparent 1px var(--retic-col, 34px)),
    repeating-linear-gradient(to bottom,
      var(--retic-linea, var(--color-tinta)) 0 1px, transparent 1px var(--retic-fila, 22px));
}

/* Las casillas ocupadas: un día con cuatro citas puestas. Que se corten por el canto es lo
   que hace un horario impreso de verdad, no un fallo de maquetación. */
.reticula::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(var(--retic-ocupado, var(--color-tinta)) 0 0)  34px 22px / 33px 21px no-repeat,
    linear-gradient(var(--retic-ocupado, var(--color-tinta)) 0 0) 102px 22px / 33px 21px no-repeat,
    linear-gradient(var(--retic-ocupado, var(--color-tinta)) 0 0)  68px 66px / 33px 21px no-repeat,
    linear-gradient(var(--retic-ocupado, var(--color-tinta)) 0 0) 170px 44px / 33px 21px no-repeat;
  opacity: 0.9;
}

/* El hueco. Es el único rectángulo del color que abre en toda la pieza, y es el argumento de
   venta del producto dibujado sin una palabra. */
.reticula::after {
  content: '';
  position: absolute;
  top: 44px;
  inset-inline-start: 34px;
  width: 33px;
  height: 21px;
  background: var(--color-abre);
}
```

Uso, con el color puesto desde fuera para que la misma pieza sirva sobre claro y sobre bloque:

```html
<!-- celda de categoría sobre lienzo -->
<li class="categoria reticula"
    style="--retic-fondo: var(--color-lienzo);
           --retic-linea: var(--color-borde-fuerte);
           --retic-ocupado: var(--color-tinta)">
  <a href="/buscar?categoria=barberia"><span>Barbería</span></a>
</li>

<!-- la misma pieza dentro de un bloque azul -->
<li class="categoria reticula"
    style="--retic-fondo: var(--color-acento);
           --retic-linea: rgb(255 255 255 / 0.45);
           --retic-ocupado: rgb(255 255 255 / 0.85)">
  <a href="/buscar?categoria=spa-masajes"><span>Spa y masajes</span></a>
</li>
```

**Y de paso arregla un incumplimiento de la auditoría de arriba:** las celdas de categoría dejan
de ser color plano y pasan a tener dibujo, y el estado vacío deja de ser una caja de arena con un
icono gris.

---

### 2.7 · Ejemplo 4 · El sello del profesional

Sustituye a `.equipo__inicial` (`globales.css:1501-1511`), que hoy es un cuadrado de tinta con
una letra dentro. Mismo lenguaje que el rótulo del salón, a 56 px: filo naranja arriba, trama de
su oficio y la inicial en ancho de rótulo.

```css
.sello-persona {
  position: relative;
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: var(--rotulo-fondo, var(--color-tinta));
  color: var(--rotulo-tinta, var(--color-papel));
  border-top: 3px solid var(--color-abre);
  font-family: var(--tipografia-familia-display);
  font-weight: var(--tipografia-pesos-display);
  font-stretch: var(--tipografia-ancho-rotulo);
  font-size: var(--tipografia-tamano-titulo-4);
}
.sello-persona::before {
  content: '';
  position: absolute;
  inset: 0;
  background-color: currentColor;
  opacity: 0.26;
  -webkit-mask-image: var(--rotulo-trama);
  mask-image: var(--rotulo-trama);
  -webkit-mask-size: 28px;
  mask-size: 28px;
}
.sello-persona span { position: relative; }
```

Y es, además, el sitio donde por fin cabe el símbolo del apartado 04 cuando un profesional no
tiene ni foto ni oficio asignado: `<Icono alto={24} />` dentro del sello, que es exactamente el
uso «foto de perfil» que el brandbook promete y que hoy no existe.

---

### 2.8 · Qué habría que cambiar para aplicar esto

No lo hago yo, que este encargo era auditar y decidir. Queda la lista, corta a propósito:

1. Pegar los cuatro bloques de CSS de arriba en `apps/web/app/globales.css`, y borrar
   `.salon__inicial`, `.galeria--vacia` y `.equipo__inicial`.
2. Tres líneas en `apps/web/componentes/ficha-salon.tsx` (talla, iniciales y trama por
   categoría), y las equivalentes en `app/[slug]/page.tsx` para la cabecera del perfil y el
   equipo.
3. Una función `oficioDe(categorias)` de siete líneas con la tabla de la sección 2.5.
4. Quitar de la portada el `tono: 'cal'` y los tonos lisos, y pasar las seis celdas sin foto a
   `.reticula`.

**Esto es una decisión de identidad y le corresponde un ADR-0017 que supere la parte de
imágenes.** No lo escribo aquí porque el encargo acota la entrega a este archivo, y porque
**los ADR aceptados no se editan**: el 0016 se queda como está y el 0017 lo completa.

---

## 3 · Lo que queda abierto

Todo esto va a la tabla de deuda viva de `ESTADO-GLOBAL.md`, no en prosa.

| Qué | Dónde | Por qué no lo he resuelto |
|---|---|---|
| **La contradicción de fondo:** ADR-0016 descartó una dirección por 23 filetes a 1,31:1 y la ganadora tiene 30 reglas de filete a 1,29:1 | `globales.css`, `--color-borde` | **Es un choque con un ADR aceptado y no lo cambio por mi cuenta.** O el brandbook admite el filete fino como mecanismo de estructura, o `--color-borde` sube a 3:1 y hay que revisar cada superficie. Lo escalo |
| El brandbook dice escala «de 0,75 rem a 4 rem» y `tokens.json:121` dice 4,25 rem | `BRANDBOOK-BUKEO.md` §06 y `tokens.json` | El brandbook manda sobre los tokens por su propia regla, pero cambiarlo es cambiar el documento de otro agente. Lo escalo |
| El verificador de contraste no lo ejecuta nadie y no mide ni el filete ni el naranja como texto | `packages/tokens/verificar-contraste.mjs`, `package.json:14` | Es trabajo de código, no mío. Otro agente ha dejado `scripts/verificar-contraste-en-pantalla.mjs`, que va en la dirección correcta: mide lo que se ve, no lo que dicen los tokens |
| El símbolo, el favicon y el icono de aplicación no existen | `componentes/marca.tsx:48`, `app/layout.tsx` | Es trabajo de Frontend |
| El logotipo sale azul en la cabecera | `componentes/cabecera.tsx:28` | Es trabajo de Frontend, y es una línea |
| Restos de la dirección anterior en el repositorio: `public/fuentes/` tiene 76.676 bytes de IBM Plex que ya no usa nadie, y `public/marca/` está vacía | `apps/web/public/` | Es limpieza, no diseño |
| Si el orden «documento, tokens, pantallas» se respetó de verdad | `docs/marca/` | **No lo he podido comprobar** y no lo supongo |
