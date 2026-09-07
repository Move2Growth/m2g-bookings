# Crítica · Dirección B — «cupo» · Estado: completado

Objeto juzgado: `docs/marca/revision-4/salida/Cupo_BrandBook.pdf` (10 pág., A4 apaisado, 841,92 × 595,92 pt).
Método: las diez páginas convertidas a imagen y miradas una a una; ampliaciones a 300 dpi de las
páginas 06, 08 y 09; once ratios recalculados con la fórmula de WCAG 2.1 a partir de los hex;
`pdffonts` para las fuentes embebidas; y el CSS del libro para lo que el render no enseña.
El `NOTAS.md` y el `marca.json` se leyeron **después** de mirar.

---

## 1 · Los descartes

### D1 · Claro por defecto — **pasa**
Las diez páginas van sobre cal `#F4EFE6`. Las tres pantallas de la p.09 son claras, incluida la
agenda. El carbón aparece solo donde tiene función: el panel de la versión invertida (p.04), una
pieza del moodboard (p.03), el rótulo de calle y la tarjeta de perfil (p.10). No hay tema oscuro
presentado como principal en ningún sitio.

### D2 · Cero fuentes delatoras — **pasa**
`pdffonts` solo devuelve tres familias: **Chivo**, **Chivo Mono** (Omnibus-Type) y **Petrona**
(Huerta Tipográfica), todas embebidas y subseteadas. Ninguna de las siete vetadas. Reserva honesta:
Chivo está en Google Fonts y no es una rareza, pero no es una fuente-plantilla ni tiene el tell de
Inter/Poppins, y el Chivo Black del logotipo tiene carácter propio.

### D3 · Cero redondeo y cero degradado decorativos — **pasa**
En el CSS del libro hay exactamente **un** `border-radius`: `border-radius:0` global. El único `50%`
del documento es el círculo de la p.05 que está **tachado** («metido en un círculo» → prohibido).
Cero `box-shadow` en todo el archivo. Los siete `linear-gradient` son todos de parada dura
(`0 16px, 16px 38px`): son tramas — cal encalada, azulejo, rayado de «cerrado» —, no degradados.
La p.05 declara además que la esquina del ícono de app no se dibuja: la redondea el sistema.

### D4 · Contraste AA comprobado y escrito — **pasa, con un agujero**
Recalculé **once** ratios impresos y **los once son exactos al segundo decimal**:

| Pareja | Impreso | Calculado |
|---|---|---|
| carbón `#17150F` / cal `#F4EFE6` | 15,94 | **15,94** |
| carbón / papel `#FFFFFF` | 18,25 | **18,25** |
| achiote `#A82F18` / cal | 5,94 | **5,94** |
| achiote / papel | 6,81 | **6,81** |
| guayacán `#F2B705` / carbón | 10,04 | **10,04** |
| guayacán / cal (prohibido) | 1,59 | **1,59** |
| caribe `#0E6156` / cal | 6,40 | **6,40** |
| piedra `#645F57` / cal | 5,53 | **5,53** |
| piedra / papel | 6,33 | **6,33** |
| carbón / piedra 15 `#E3DED3` | 13,61 | **13,61** |
| piedra / piedra 15 | 4,72 | **4,72** |

Ninguno inflado. El pie de la p.06 («Ninguna pareja de las de abajo baja de 4,5:1») también es cierto.

**El agujero:** la p.08 pinta estados con **ocho colores que no existen en la p.06 ni en el
`marca.json`** y que por tanto no llevan ratio impreso en ninguna parte del libro:
`#8E2712`, `#741F0D`, `#EBD3CB`, `#E9D9D2`, `#A29C91`, `#C9C3B6`, `#CFC8BA`, `#B9B2A5`.
Los calculé yo. Los activos aguantan (texto cargando 6,26 · «Cambiar hora» pulsado 9,43 · chip
encima 6,01 · etiqueta clara sobre carbón 8,67). Pero el texto **inhabilitado** `#A29C91` da
**2,38:1** sobre cal y **2,03:1** sobre piedra 15. El listón cita «un naranja de 2,3:1 usado como
texto» como el fallo que no vuelve a colar, y aquí hay dos valores de ese rango sin imprimir.

No lo cuento como fallo del descarte porque WCAG 2.1 exime explícitamente el texto de un control
inactivo (1.4.3, «incidental»), y ningún texto **activo** del sistema baja de 4,5:1. Pero D4 dice
«cada color de texto sobre su fondo» y ocho tonos de interfaz se quedaron fuera del libro.

### D5 · Logotipo generado, vectorial, tres versiones + tres tamaños — **pasa**
`logo/intento-e.svg` lleva manifiesto **C2PA** incrustado (prueba de generación) y el `marca.json`
declara `Higgsfield · recraft_v4_1 · model_type vector`, 12,5 créditos. Los `path` son curvas Bézier
con coordenadas irregulares (`519.502`, `590.588`…): vectorización de un original generado, no CSS.
En el libro están las tres versiones (p.04: principal carbón/cal, invertida cal/carbón, una tinta
achiote) y los tres tamaños (p.05: 48, 32 y 16 px, cada uno con su ×2,5/×3,75/×7,5 al lado).
Verifiqué que `icono-16.svg` es realmente **otro dibujo**: comparte el contorno exterior con
`principal.svg` pero le falta el segundo `path` (el filete interior), justo lo que la p.05 afirma.

### D6 · Nada a medias — **pasa (formalmente)**
Los seis estados están, etiquetados en cabecera de columna, para **cuatro** tipos de botón —
primario, secundario, de texto y «de hora» — más campo de texto (cinco estados), selector (cuatro,
con el vacío «Sin equipo aún») y chip (seis). Las tres pantallas de la p.09 están **enteras**: barra
de estado 9:41/Panamá/4G, cabecera, contenido y barra de pestañas inferior, las tres. No hay recorte
bonito. Verifiqué en el CSS que están maquetadas a `width:390px` con `zoom:.68`, o sea que la
afirmación «tres pantallas enteras, a 390 px» es literalmente cierta y no un dibujo a otra escala.

Reserva grave, que desarrollo en el punto 4: dos de esos seis estados no son estados.

---

## 2 · Las diez páginas

| # | ¿Resuelve o menciona? |
|---|---|
| 01 | **Resuelve.** Nombre, logo, frase («no es un salón, es una hora con una persona») y una línea que dice qué es, dónde y quién no paga. La regla del día vertical ya trabaja de portada. |
| 02 | **Resuelve.** Idea en una frase («un directorio enseña sitios, cupo enseña horas») y tres verdades con su prueba gráfica al pie de cada columna. |
| 03 | **Resuelve.** Seis piezas, las seis dibujadas, cero fotos: regla del día, calado de mola, cal de Casco Viejo, guayacán, la hora en Chivo Mono, el escalón acotado en px. |
| 04 | **Resuelve y se pasa.** Además de las tres versiones: aire mínimo acotado en unidades del propio símbolo, cuatro prohibiciones dibujadas, mínimos (92 px / 16 px), convivencia con el nombre del salón y cómo se escribe en texto corrido. |
| 05 | **Resuelve.** Los tres escalones con qué se cae en cada uno, y los tres a tamaño real dentro de su contexto (pestaña, aviso, lista). El «el sello no es un avatar» es una regla de producto, no de relleno. |
| 06 | **Resuelve.** Seis tintas con hex, RGB, ratios, uso y proporción (68/17/8/5/1,5/0,5), más dos superficies derivadas y cuatro parejas puestas a trabajar. |
| 07 | **Resuelve a medias.** La jerarquía está completa como tabla, pero **no gobierna la p.09** (ver punto 4). Es la única página que describe un sistema que su propia demostración no usa. |
| 08 | **Resuelve.** 24 casillas de botón + campo + selector + chip, y explica por qué el foco va en envoltorio externo (el escalón se come el contorno). |
| 09 | **Resuelve**, con un defecto de render (ver punto 4). |
| 10 | **Resuelve.** Ícono de app en tres tamaños, perfil que la profesional manda por WhatsApp, tarjeta 85×55 con su jornada al dorso, rótulo de calle y cómo se dice el nombre por teléfono. |

Ninguna página rellena hueco. Ninguna es una rejilla de cajas con texto genérico dentro.

---

## 3 · ¿Se puede confundir con una plantilla?

**No.** Y no por adjetivos, por cosas contables:

- **Hay un elemento gráfico propio que no es el logo.** La regla del día — doce horas en bloques,
  gris lo vendido, achiote lo libre, guayacán lo último, rayado lo cerrado — aparece en el pie de las
  diez páginas, en cada tarjeta de profesional (p.09), en la tarjeta impresa (p.10) y como pieza de
  moodboard (p.03). La p.02 lo dice explícitamente: «el elemento gráfico principal de la marca no es
  el logotipo». Eso es un sistema, no un tema.
- **Hay una firma dibujada en el control.** El escalón de 13 × 7 px quitado a la esquina inferior
  izquierda de **todo** botón, acotado en px en la p.03 y derivado del hueco del símbolo. Y tiene
  consecuencia técnica razonada: como el recorte se come el contorno, el foco de teclado va en un
  envoltorio externo de 2 px en caribe con 3 px de aire. Una plantilla no razona eso.
- **El libro tiene estructura propia:** el número de página lleva una hora que avanza de `08:00`
  (p.01) a `20:00` (p.10). La jornada es la paginación.
- **Es Panamá concreto, no «LatAm».** Calidonia, Casco Viejo, la mola guna, el guayacán que florece
  cuatro días, `B/.`, `+507 6104-2288`, el rótulo que se lee desde el semáforo de noche y con lluvia,
  cómo se deletrea el nombre por teléfono. Esto no se recicla a Berlín.
- **Las tintas se llaman cal, carbón, achiote, guayacán, caribe y piedra.** No `primary`/`secondary`.
- **La persona manda sobre el local**, que es el encargo: avatar de iniciales en carbón, tres agendas
  en paralelo en la p.09, «el sello no es un avatar», el salón siempre detrás de un filete vertical
  y nunca por encima de la palabra (p.04).
- **Cero border-radius, cero sombra, cero degradado suave**, verificado en el CSS, no de vista.

Lo que sí es reutilizado, para ser justo: la **retícula del libro** se repite casi idéntica en las
páginas 03, 04, 05, 06 y 10 — tres cajas de filete de 1 px arriba, tira de tres bloques abajo. Es
una plantilla interna y se nota al pasar páginas seguidas. Y las estrellas `★★★★★` de la p.09 son
el widget de reseñas de siempre, sin pasar por el sistema.

---

## 4 · Lo que está mal y no se ve a primera vista

**a) Dos de los seis estados no son estados.** En el CSS:
- `.btn-2.encima{background:var(--carbon)}` y `.btn-2.pulsa{background:#000}`. Entre `#17150F` y
  `#000000` hay **1,15:1**. La única diferencia real entre «encima» y «pulsado» del botón secundario
  es `translateY(1px)`.
- `.btn-3.encima{color:#741F0D}` y `.btn-3.pulsa{color:#741F0D}` — **el mismo hex**, otra vez con la
  única diferencia de 1 px de desplazamiento.

Esto vive a 390 px en un teléfono, donde **no existe el estado «encima»**: el usuario toca y la
respuesta visual es 1 px de movimiento. Dos de los cuatro controles no dan acuse de pulsación. La
página que se rechazó dos veces sigue teniendo dos casillas rellenadas en lugar de resueltas.

**b) La regla del guayacán se contradice consigo misma en tres páginas.** La p.06 dice, sin acotar:
«Nunca como texto ni como filete». `color:var(--guayacan)` aparece **13 veces** en el libro:
- p.03, la pieza «la hora en su propia voz»: el `PM` de `6:45` va en guayacán;
- p.07, el espécimen estrella de Chivo Mono: **`10:30` entero en guayacán**;
- p.10, el rótulo de calle («RESERVA AQUÍ CON TU BARBERA»), los tres chips del perfil
  (`border-color` **y** `color` guayacán: filete y texto a la vez) y el `6:30 PM` de «HOY QUEDA».

Todos van sobre carbón y dan 10,04:1, así que no hay problema de lectura. El problema es la regla:
el `marca.json` la acota bien («como texto o como filete **sobre cal**»), pero **lo que se imprimió
en el libro es la versión absoluta**, y el libro es lo que se entrega. Quien lo aplique al pie de la
letra tiene que tachar tres páginas del propio libro.

**c) La única regla marcada como «LA REGLA QUE NO SE SALTA» se salta cuatro veces, en la página
siguiente.** La p.07: «Toda hora va en Chivo Mono. Y nada más va en Chivo Mono. Ni los precios, ni
los nombres, ni las distancias.» En la p.09, con `class="mono"` y sin ser horas:
- `31 cupos hoy` — la frase entera, palabras incluidas;
- `4 cupos` (ficha) y `4` / `21` de los contadores de la agenda;
- `4,9` de valoración, `312` reseñas y `1.240` personas atendidas.

Curiosamente las dos cosas que la regla nombra — `400 m` y `B/. 18` — sí van en Chivo proporcional.
O sea: la regla se cumple donde se enuncia y se rompe donde no.

**d) Texto cortado en la agenda, a 390 px reales.** En la p.09, pantalla 3, los bloques de hueco
libre se generan con `overflow:hidden` y dos líneas (hora a 9 px + `CUPO` a 7,5 px) dentro de una
caja cuya altura la fija la duración. En los huecos de 30 min **no cabe**: a 300 dpi se ve la palabra
`CUPO` **seccionada por la mitad** por el borde inferior en los bloques de 8:00, 11:00 y 3:00 PM de
la columna Yaritza y el de 12:00 de la columna Rubén. No es una elección de composición, es overflow.
Y es justo el elemento que el pie de la página declara como lo único que el dueño tiene que mirar.

**e) La jerarquía «completa» de la p.07 no gobierna la p.09.** La tabla se detiene en Etiqueta a
10,5 px y define Cuerpo a 13/19,5. Dentro de los tres contenedores de 390 px hay **17 usos de texto
por debajo de 9 px** (7 · 7,5 · 8 · 8,5) y otros 27 entre 9,5 y 10 px, y el cuerpo real de las
tarjetas es 9,5–12 px. Ninguno de esos tamaños existe en la jerarquía. Una jerarquía que la propia
demostración no usa está incompleta aunque la tabla parezca completa.

**f) El alto de toque está por debajo del estándar y lo dice el libro.** La p.08 fija «38 px el botón
de hora, 34 el resto», y el `marca.json` lo confirma. iOS pide 44 pt y Android 48 dp. Los chips del
perfil de la p.10 bajan a `height:26px` y los de la p.08 a 32 px. En un producto cuyo gesto central
es tocar una hora en un teléfono, eso se paga en pulsaciones fallidas.

**g) Menor, pero es incoherencia:** la p.06 impone «ahí no se baja de 12 px» para piedra sobre
piedra 15 (4,72:1), y la única etiqueta que la jerarquía ofrece es de 10,5 px. La regla obliga a un
tamaño que el sistema tipográfico no tiene. Y en el eje de la portada, el primer `8:00` (mañana) y el
último `8:00` (noche) se escriben exactamente igual, sin AM/PM, en la pieza que se presenta como el
elemento gráfico principal de la marca; en el pie de página sí se distinguen.

---

## 5 · Veredicto

**pasa.**

No falla ningún descarte: el libro es claro, no usa ninguna fuente vetada, tiene radio 0 y ni una
sombra, imprime once ratios que resultan ser exactos hasta el segundo decimal, el logotipo es
vectorial generado con trazabilidad C2PA en sus tres versiones y tres tamaños, y las pantallas y los
estados están enteros. Es una propuesta con una idea gráfica propia — el hueco como mercancía y la
regla del día como sistema — que no se puede confundir con una plantilla ni trasladar a otro país.

Lo que arrastra no son descartes sino incoherencias de sistema: dos estados de botón que no se
distinguen (1,15:1 y hex idéntico), una regla de color que su propio libro rompe en tres páginas, la
regla tipográfica marcada como intocable rota en la página siguiente, ocho colores de interfaz fuera
de la paleta y sin ratio impreso, y una palabra literalmente cortada en la pantalla de la agenda.
