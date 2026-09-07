# Crítica · Dirección A «Buenamano» · Estado: completado

Objeto: `docs/marca/revision-4/salida/Buenamano_BrandBook.pdf`, 10 páginas, A4 apaisado
(841,92 × 595,92 pt), numeradas 01–10. Miradas las diez, una por una, rasterizadas a 110 dpi
y las dudosas a 300–400 dpi. Los ratios los he recalculado yo con la fórmula de WCAG 2.1 a
partir de los hex impresos; los estados de botón y los tamaños de texto los he medido a
nivel de píxel sobre el PDF, no leído en el texto.

---

## 1 · Los descartes

### D1 · Claro por defecto — **pasa**
Las diez páginas van sobre `#F7F2E9`. Las tres pantallas de la 09 son claras de la barra de
estado a la de abajo. El oscuro aparece una sola vez, en un recuadro de 12 × 4 cm en la 06,
rotulado *«El tema oscuro existe. Pero no es el estado normal: la aplicación abre en papel»*.
Es exactamente lo contrario de lo que mató la ronda anterior.

### D2 · Cero fuentes delatoras — **pasa**
`pdffonts` sobre el PDF: **Alegreya** (Huerta Tipográfica) y **Archivo** (Omnibus-Type), con
sus ejes de peso y de ancho. Ninguna de la lista vetada. Hay tres fuentes más incrustadas y
las he perseguido hasta la página que las usa, porque es justo donde se cuela un descuido:

- `Georgia-Italic` → **solo página 04**, en la casilla con ✕ *«El nombre no se compone en otra
  letra ni con mayúscula inicial»*. Es el contraejemplo. Legítimo.
- `.SFNS-Regular` → **solo página 05**, en la maqueta de pestaña de navegador.
- `.SFNS-Bold` y `.SFNS-Regular_wdth_opsz…` → **solo página 09**, en las barras de estado
  `9:41 · 4G · 78 %` de los tres teléfonos.

Es decir: cada aparición de una fuente ajena está simulando cromo de sistema operativo o
sirviendo de ejemplo prohibido. Ninguna toca la marca.

### D3 · Cero redondeo y cero degradado decorativos — **pasa**
Radio 0 en botones, campos, chips, selector de hora, tarjetas y celdas de agenda; comprobado
en los recortes a 400 dpi. La única forma redonda es el círculo del retrato, y está declarada
como significado, no como estilo (03, pieza 05: *«un círculo quiere decir aquí hay alguien»*).
El único degradado del libro es el de la casilla con ✕ de la 04. El icono de aplicación de la
10 se entrega **cuadrado**, con la máscara redondeada dibujada aparte y rotulada *«el único
redondeo que existe en esta marca lo pone el sistema operativo, no nosotros»*.

### D4 · Contraste AA real, comprobado y escrito — **pasa**
He recalculado los **diez pares impresos** en la 06 y los **cinco estados de botón** de la 08
a partir de los hex, con la fórmula de WCAG:

| Par | Impreso | Recalculado |
|---|---|---|
| Tinta sobre papel | 16,97 | **16,97** |
| Tinta sobre bruma | 13,27 | **13,27** |
| Papel sobre añil | 7,88 | **7,88** |
| Añil sobre bruma | 6,16 | **6,16** |
| Papel sobre achiote | 5,56 | **5,56** |
| Ceniza sobre papel | 5,42 | **5,42** |
| Ceniza sobre bruma (prohibido) | 4,24 | **4,24** |
| Bruma sobre papel (prohibido) | 1,28 | **1,28** |
| Botón encima `#173397` | 9,62 | **9,62** |
| Botón pulsado `#14318C` | 10,19 | **10,19** |
| Urgente reposo / encima / pulsado | 5,56 / 6,75 / 8,80 | **5,56 / 6,75 / 8,80** |

Los seis RGB decimales impresos también corresponden a sus hex. **Ni un número inventado**, y
los dos pares que no llegan están escritos en rojo como prohibidos en vez de escondidos. Esto
es lo contrario del naranja de 2,3:1 de la ronda anterior. Paso el descarte — con dos manchas
que detallo en el punto 4 (el inhabilitado sobre trama y el azul del tema oscuro sin ratio),
porque ninguna de las dos produce texto ilegible, que es lo que D4 existe para impedir.

### D5 · Logotipo generado, no dibujado con CSS — **pasa, con prueba dura**
En `direcciones/a-buenamano/logo/` están los tres intentos. Cada `intento-*.svg` lleva un
manifiesto **C2PA** incrustado que dice literalmente `claim_generator_info: recraft.ai`,
`digitalsourcetype/trainedAlgorithmicMedia`, *«Created by Recraft AI»*. Y he comparado los
trazados: **los 6 paths de `principal.svg` son idénticos, carácter a carácter, a 6 de los 7 de
`intento-3.svg`** — solo cambia el color y el encuadre, como dice NOTAS. No hay ningún círculo
de CSS aquí: son béziers trazados con coordenadas irregulares.
En el libro: principal, invertida y una tinta en la 04; 48, 32 y 16 px en la 05 (y las tres
tallas están además incrustadas como PNG de 48×48, 32×32 y 16×16 reales dentro del PDF).

### D6 · Nada a medias — **pasa**
Página 08: **cuatro tipos × seis estados = 24 botones dibujados**, no descritos. Debajo, el
campo de texto en sus seis estados, el selector de hora con elegida/tomada y los chips.
Página 09: tres pantallas de la barra de estado al pie, no recortes.

---

## 2 · Las diez páginas

| # | ¿Resuelve o menciona? |
|---|---|
| 01 | **Resuelve.** Nombre, sello a sangre, frase (*«Reservas con la persona que te atiende, no con el local»*), y ya enseña los dos signos y una profesional con nombre. |
| 02 | **Resuelve.** Una idea y tres verdades, cada una con línea *«se ve en:»* que apunta a piezas que existen de verdad más adelante. Añade los tres casos difíciles (sin foto, equipo de seis, recién llegada) y los tres reaparecen usados en la 09. |
| 03 | **Resuelve.** Seis piezas dibujadas, cero fotografías. La única floja es la 04 (proporción de tinta), que repite tal cual la barra de la página 06: es la pieza que más se parece a relleno. |
| 04 | **Resuelve.** Tres versiones + construcción (aire ½ ø, separación ¼ ø) + seis prohibiciones dibujadas. |
| 05 | **Resuelve, y es la mejor del libro.** No enseña tres tamaños del mismo dibujo: enseña **tres dibujos distintos** y dice qué se cae en cada escalón (a 32 px se retira el anillo interior; a 16 px quedan un anillo y la barra) con el «sin reducir» al lado convertido en mancha. Además talla mínima 14 px y fondos admitidos. |
| 06 | **Resuelve.** Seis tintas con hex, RGB, ratio, papel y proporción medida. |
| 07 | **Resuelve.** Dos familias, pesos, jerarquía de cinco niveles con medidas reales y espécimen. La regla que las reparte es de producto, no de gusto: *si tiene nombre y apellido va en Alegreya, todo lo demás en Archivo* — y se cumple en la 09. |
| 08 | **Resuelve.** Es la página que se rechazó dos veces y aquí está dibujada entera, con anatomía propia. |
| 09 | **Resuelve**, con el defecto de tamaño que explico en el punto 4c. |
| 10 | **Resuelve.** Icono cuadrado + máscara, perfil, tarjeta por las dos caras, y calle: vinilo, placa de metacrilato y sello de goma. |

**Ninguna página rellena hueco.** La más prescindible es la pieza 04 del moodboard, por
duplicada.

---

## 3 · ¿Se puede confundir con una plantilla?

**No.** Y no lo digo por el aspecto, lo digo por lo que he podido medir:

- **El botón no sale de ninguna biblioteca.** Medí el canto sobre el PDF a 400 dpi: reposo
  **2 px** de añil más oscuro por debajo, encima **4 px**, pulsado **0 px y el botón entero
  bajado 2 px**. Está construido, no configurado. Una plantilla habría oscurecido el relleno
  al pasar por encima y ahí se habría acabado el «estado».
- **Hay un segundo signo que solo puede existir en este producto.** La cinta de horas
  (ocupado en tinta maciza, hueco en papel, próximo con aro de achiote) aparece en la portada,
  en el moodboard, en la ficha, en el perfil público y **en el reverso de la tarjeta de visita**.
  Eso no se descarga.
- **El caso feo está resuelto en vez de escondido.** «No ha subido foto» no da un monigote
  gris: da una huella calculada desde su nombre, y está usada en la 09 en tres personas
  distintas con tres dibujos distintos.
- **La tipografía tiene una regla semántica**, no un tamaño por nivel: el nombre propio en
  serifa y el sistema en palo seco, obedecido en las pantallas.
- **Panamá está en el sustrato, no en la bandera.** La trama sale del bordado de la pollera,
  el rojo es achiote, la moneda es `B/.`, el barrio es Bella Vista, el servicio es «trenzas
  box», y el nombre viene de una frase que en Berlín no se dice. La gratuidad no está en la
  letra pequeña: está en la portada y otra vez en el pie de la agenda del dueño
  (`TE COBRAMOS HOY 0,00 B/.`).

Lo poco que todavía huele a presentación: los numerales `01 02 03` de la 02 y la fila de
guiones de progreso al pie de cada página son mobiliario genérico de brandbook. Es
mobiliario, no es el diseño.

---

## 4 · Lo que está mal y no se ve a primera vista

**a) El estado inhabilitado imprime un ratio que no es el que tiene.**
La 08 dice *«inhabilitado 5,42:1 (ceniza sobre papel, no exento)»* y NOTAS presume de no
necesitar la excepción de WCAG. Pero el rótulo no está sobre papel liso: está sobre una trama
diagonal de **bruma**, y la trama **pasa por detrás de los glifos**. Medido sobre el recorte a
400 dpi del botón primario inhabilitado: de 3 127 píxeles de glifo, **1 068 (el 34 %) tienen
bruma a dos píxeles o menos**. En esas rayas el contraste real es **4,24:1** — exactamente el
par que la página 06 imprime en rojo como **«prohibido»** dos páginas antes. La misma trama
está bajo los horarios tachados `4:30` y `5:30` del selector y bajo el chip `3:00`, con la
misma nota de 5,42:1.

**b) La regla del achiote se rompe en su propia página de pantallas.**
La 03 dice *«el color señala, no decora: dos achiotes en pantalla es uno de más»* y la 06
*«el achiote es uno por pantalla»*. La pantalla C tiene **cuatro**: la huella de Abdiel S., el
aro de Dayra Q., la celda `hueco` y el `1 HUECO` del pie. Y no es un descuido de maqueta: es
estructural, porque según NOTAS la tinta de la huella sale de un *hash del nombre*, o sea que
el achiote se reparte entre personas **al azar y decorando**, que es literalmente lo que la
03 prohíbe. La regla y el sistema de huellas no pueden convivir tal como están escritos.

**c) La agenda de cuatro columnas no cabe a 390 px sin romper el mínimo del propio libro.**
La 07 imprime *«en el teléfono nunca baja de 15 px»*. Medí alturas de mayúscula sobre el
render a 300 dpi: la «T» del cuerpo de 15 px de la pantalla A mide 20 px de trama; la «C» de
«Corte» dentro de la agenda de la pantalla C mide **16 px**. Es decir, **~12 px CSS**, un 20 %
por debajo del suelo. Con columnas de ~85 px cada una en un teléfono de 390, ese texto no baja
de 12 px sin dejar de caber. Es la decisión que se ve bien en el libro y que en pantalla real
obliga a elegir entre romper la regla o rehacer la pantalla.

**d) El tema oscuro mete una séptima tinta que no está en ninguna paleta y no lleva ratio.**
Muestreé el botón «Reservar» de la tarjeta oscura de la 06: es `#7EA0FF`. No aparece entre las
seis tintas, no aparece en «pares comprobados» y no lleva ratio impreso en ninguna página
(sí está en `marca.json`, 7,53:1 con tinta, pero el libro no lo dice). Además obliga a una
regla tácita que el libro nunca escribe: papel sobre `#7EA0FF` da **2,25:1**, así que el
rótulo del botón primario tiene que cambiar de color entre temas.

**e) Dos de los seis estados son cromáticamente el mismo.**
Primario pulsado y primario cargando son ambos `#14318C`; urgente pulsado y urgente cargando
son ambos `#7E2316`. Se distinguen por el rótulo y por el canto segmentado, no por el color.
Están dibujados los seis, así que D6 se cumple, pero dos de ellos se apoyan en la palabra.

**f) La 10 usa fondos que la 05 no admite.** «Fondos admitidos: cuatro. Sobre foto o sobre
trama, nunca.» El vinilo de la calle pone el bloque completo sobre `#E8EDF7` con bandas de
`#EFEFEF` y `#EDEEF2` (el cristal), y la placa y el recibo usan `#EFE7D9`. Son planos, no
degradados —no rompen D3—, pero son un quinto y un sexto fondo contra una regla que dice
cuatro.

**g) Un dato menor que está al revés.** La 06 dice que la proporción se midió *«sobre la
pantalla de búsqueda, que es la más cargada»*. Contando píxeles: añil al **2,57 %** en la
búsqueda y al **5,65 %** en la ficha. El tope del 8 % se respeta en las tres, pero la frase
señala la pantalla equivocada.

**h) La cota de la anatomía miente.** El corchete de la 08 rotula «44» sobre un botón que en
el libro mide **58 px**, mientras los 24 botones de la rejilla de arriba miden **38 px**. Es
una hoja de especificación cuya línea de cota no cota nada.

**i) La pantalla B no tiene barra de pestañas** y A y C sí. La ficha sustituye la navegación
por la llamada a la acción; puede ser correcto, pero el libro no lo dice en ningún sitio y
las tres pantallas se presentan como el mismo sistema.

---

## 5 · Veredicto

**PASA.**

No falla ningún descarte: arranca en claro, no hay una sola fuente delatora tocando la marca,
no hay redondeo ni degradado decorativos, los quince ratios que imprime son exactos cuando se
recalculan, el sello es una generación vectorial firmada por C2PA y reutilizada trazo a trazo,
y los seis estados están dibujados de los cuatro botones y del campo de texto.

Lo que arrastra —la trama de bruma bajo el texto inhabilitado, el achiote que su propio
sistema de huellas reparte a discreción, y la agenda de cuatro columnas que a 390 px baja a
12 px— es deuda de sistema seria y hay que escribirla, pero es lo que se rompe **cuando este
libro se aplica**, no lo que impide enseñarlo.
