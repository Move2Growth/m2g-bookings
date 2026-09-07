# Crítica · dirección C «Tanda» · Estado: completado

> Objeto juzgado: `/Users/luisgomez/Desktop/kraken/m2g-bookings/docs/marca/revision-4/salida/Tanda_BrandBook.pdf`,
> las diez páginas vistas una a una a 110 y 260 dpi, más `direcciones/c-tanda/libro.html` y `direcciones/c-tanda/logo/`
> después de mirarlas. No hay `NOTAS.md` ni `marca.json`; se juzga por el libro, como corresponde.
> Todos los ratios de este documento están recalculados con la fórmula de WCAG 2.1 a partir de los hex.

---

## 1 · Los descartes

### D1 · Claro por defecto — **pasa**
Las diez páginas están sobre papel `#FBF8F2`. Las tres pantallas de la página 09 son claras
(`.tel{background:var(--papel)}`), incluida la agenda del negocio. Lo oscuro aparece solo donde
tiene que aparecer: la versión invertida del logo (p04), una pieza del moodboard (p03), la
cabecera de un panel (p06) y la rotulación de calle (p10). No hay una sola pantalla de producto
en oscuro.

### D2 · Cero fuentes delatoras — **pasa**
`pdffonts` sobre el PDF: **Archivo** (Omnibus-Type) y **Alegreya Sans** (Huerta Tipográfica).
Ninguna de las siete vetadas. La variable de anchura de Archivo se usa de verdad —hay siete ejes
distintos incrustados, de `wdth 6A` a `wdth 7D`— y eso es lo que separa el rótulo de la celda de
la agenda; no es una fuente puesta por defecto.

*Reserva:* en las páginas 07, 09 y 10 aparece incrustada una tercera fuente, **HiraginoSans-W4/W6**,
que es del sistema operativo. Es el glifo ★ de «★ 4,9», que sale en el espécimen tipográfico, en las
cinco fichas de la pantalla A y en la tarjeta de la p10. La página 07 titula su primera regla
«La tipografía nunca cede… la letra es de la casa siempre», y el símbolo más repetido del producto
está puesto por macOS.

### D3 · Cero redondeo y cero degradado decorativo — **pasa**
`border-radius:0` declarado explícitamente en el botón base (línea 108 del HTML) y ni una esquina
redonda en todo el libro. Las sombras son macizas, sin blur: `box-shadow:4px 4px 0 var(--tinta)`.
Los `linear-gradient` del CSS son todos de paradas duras (`repeating-linear-gradient(45deg,var(--tt) 0 3px,transparent 3px 11px)`),
o sea tramas, no desvanecidos. Y la p10 resuelve bien el único redondeo inevitable: «El redondeo lo
pone el sistema operativo con su máscara: no es nuestro y no se dibuja».

*La única excepción real:* línea 402, un `linear-gradient(var(--linea),transparent)` de 6 px bajo el
doblez de la pieza 01 del moodboard. Es un desvanecido de verdad, y está en la misma página cuya
pieza 03 se titula «Sombra maciza, cero desenfoque». Seis píxeles, pero se contradice a sí misma.

### D4 · Contraste AA real, comprobado y escrito — **pasa** (con dos defectos serios, abajo)
Recalculé **diecisiete** de los ratios impresos. Los diecisiete salen exactos:

| Par | Impreso | Calculado |
|---|---|---|
| tinta `#17140F` / papel `#FBF8F2` | 17,33:1 | 17,33:1 |
| gris `#6E6559` / papel | 5,40:1 | 5,40:1 |
| rojo `#B31226` / papel | 6,54:1 | 6,54:1 |
| azul `#123C63` / papel | 10,70:1 | 10,70:1 |
| hueso `#EFE8DA` / papel | 1,15:1 | 1,15:1 |
| gris / hueso | 4,70:1 | 4,70:1 |
| tinta / hueso | 15,06:1 | 15,06:1 |
| verde a una tinta `#007A46` / papel | 5,12:1 | 5,12:1 |
| las seis tintas de local filtradas | 6,11 · 5,79 · 5,12 · 5,96 · 5,98 · 5,72 | idénticos a la centésima |

Y comprobé además la afirmación gorda de la p06, que es la que sostiene toda la dirección:
implementé `oklch(0.50, clamp(C,0.06,0.16), H)` y barrí los 360 tonos. Peor caso a C=0,16:
**4,70:1 en H=192**. Es exactamente el número impreso. Esa parte está hecha de verdad, no escrita
a ojo.

Lo doy por pasado porque no hay ningún texto activo por debajo de AA y porque los números impresos
son reales. Pero el descarte dice «cada color de texto sobre su fondo lleva su ratio impreso», y eso
no se cumple del todo: ver §4, puntos 7 y 8. Si la ronda aplica ese descarte a la letra, D4 cae.

### D5 · Logotipo generado, vectorial, tres versiones + 48/32/16 — **pasa**
`logo/` contiene los **seis intentos** en SVG (`intento-01…06`), y el pie de la p04 acredita
«Generado en vectorial con Recraft V4.1 (Higgsfield) · seis intentos · el quinto». Los archivos
son trazado real (`d="M 704.662 896.987 L 1341.89 897.211 …"`, coordenadas de tracing, no rects a mano).
Las tres versiones están en la página 04 y los tres tamaños en la 05.

Y la p05 no miente cuando dice que son tres dibujos distintos: comprobado en el SVG, el cuadro
interior del sello de 16 mide 173 unidades (`938→1111`) contra 113 del principal (`968→1081`), un
53 % mayor —la página dice «un 50 % mayor»— y el toldo de 16 es un trapecio liso sin los cinco picos.
No es un escalado disfrazado.

*Nit de entrega:* `principal.svg` y `sello-48.svg` son el mismo archivo byte a byte (md5
`63b137c0…`), y ninguno de los dos contiene la palabra TANDA: el lockup «principal» solo existe
compuesto en HTML. Coherente con lo que la p04 declara («el nombre no se genera, se compone con
Archivo»), pero entonces el archivo no debería llamarse «principal».

### D6 · Nada a medias — **pasa**
Cuatro tipos de botón × seis estados = 24 botones **dibujados**, no descritos. Los estados se
distinguen por materia y no por matiz: reposo lleva sombra maciza de 4 px, encima crece a 6 px y
la chapa se desplaza −2/−2, pulsado la pierde entera y recorre los 4 px, cargando sustituye la
etiqueta por tres cuadrados, inhabilitado pasa a hueso sin sombra, foco añade anillo azul de 2 px
con separación de papel. Campo de texto en cinco estados, selector abierto y cerrado, chip en tres.
Las tres pantallas son 390 × 844 completas.

*Reservas:* el pie de la p09 dice «de la barra de estado a la barra de pestañas», y la pantalla B no
tiene barra de pestañas (tiene barra de acción con el precio). Y hay tres defectos de esa página 08
en §4, puntos 9 y 10 —que importan porque es la página que se rechazó dos veces.

---

## 2 · Las diez páginas

| # | ¿Resuelve o menciona? |
|---|---|
| 01 Portada | **Resuelve.** Nombre, símbolo, y la frase que hacía falta: «Eliges a la persona, no al local. Y al salón no le cuesta nada». Además la portada ya es el argumento: seis locales con seis tintas dentro del mismo marco, y el sexto sin subir nada. |
| 02 Estrategia | **Resuelve.** Una idea («Tanda es el marco, el salón es el cuadro») y tres verdades que son las tres del encargo: gratis, la persona, Panamá a 390 px. El recuadro «lo que Tanda no es» y el de «cómo suena» sobran menos de lo que parecen: fijan el tono. |
| 03 Moodboard | **Resuelve a medias.** Seis piezas dibujadas y ninguna foto, correcto. Pero cuatro son piezas reales del sistema (festón, damero, sombra maciza, rótulo) y dos son relleno: la 01 es una caja gris de wireframe y la 05 es una rejilla de 24 muestras de color que es lo único del libro con aire de captura de herramienta. Es la página más floja. |
| 04 Logotipo | **Resuelve.** Principal, invertida, una tinta, construcción por altura de caja, y cinco «lo que nunca se le hace» dibujados uno a uno. |
| 05 Ícono | **Resuelve, y es de las mejores.** Los tres escalones con lo que se cae en cada uno, ampliados ×8 para verlo, más el reparto determinista de trama (`trama = hash(nombre) mód 6`). Eso último no lo tiene ninguna plantilla. |
| 06 Color | **Resuelve.** Hex, RGB, ratio, para qué sirve, proporción de uso medida sobre una pantalla concreta, y el hueco declarado de la séptima tinta con su fórmula. |
| 07 Tipografía | **Resuelve.** Dos familias con foundry y motivo, pesos, anchuras, jerarquía completa con px/interlineado/tracking y un espécimen que es un párrafo real del producto, no un pangrama. |
| 08 Botones | **Resuelve** lo que D6 pide, pero con las tres pifias del §4. |
| 09 Pantallas | **Resuelve.** Las tres pedidas, enteras, con anotaciones que explican la regla en vez de adornar. |
| 10 Aplicaciones | **Resuelve.** Ícono, perfil, tarjeta de dos dueños, y tres soportes de calle con una regla («cuanto más cerca del negocio, más pequeña la marca») que es una idea, no un mockup. |

Ninguna página rellena hueco salvo dos de las seis piezas de la 03.

---

## 3 · ¿Se puede confundir con una plantilla?

**No.** Y se nota en cosas que una plantilla no tiene:

- **Hay una materia, y es consistente.** Filete de 2 px y sombra maciza de 4 px sin desenfoque
  que *viaja* al pulsar. No es «card con sombrita»: es una chapa apoyada en papel, y el botón,
  el campo, el chip, el selector y la tarjeta de visita obedecen la misma física.
- **El sistema tiene una idea antes que un estilo.** «El marco es nuestro, el cuadro es del local»
  no es un eslogan: produce la regla del filtro de vitrina, el reparto de trama por hash del nombre,
  el 6 % de tope de superficie y la inversión de la regla en la calle. Todo eso se puede implementar.
- **Es de Panamá y no de Berlín.** Bella Vista, El Chorrillo, Obarrio, Vía Argentina, Casco Antiguo,
  B/. y no $, el damero del zaguán, el festón del toldo, y «tanda» como palabra que ya existe allí.
  Los nombres de las personas son panameños, no «Jane Doe».
- **Hay sitio para una persona.** El sello cuadrado con iniciales es una pieza del sistema, no un
  avatar redondo pegado: tiene su página, su tipografía, su comportamiento sin foto y su ratio.
- **Los botones están completos y son propios.** 24 estados dibujados con duraciones, curva y
  `prefers-reduced-motion`. Es lo contrario de lo que se rechazó dos veces.

Lo único que roza el «todo me parece IA»: la rejilla de 24 colores de la p03, que es una captura de
círculo cromático con marco.

---

## 4 · Lo que está mal y no se ve a primera vista

**1 · El rojo de reservar cabe dentro del rango que el libro le regala a los locales. Es el fallo de sistema.**
La p06 dice que el rojo `#B31226` es «la acción de la plataforma: reservar. **Nunca la usa un local**»,
y la p08 lo remata: «El botón de reservar no cede… si cambiara de color en cada ficha, dejaría de
reconocerse». Pero el filtro de vitrina es `oklch(0.50, clamp(C,0.06,0.16), H)` **sin ninguna
restricción de tono**, y el rojo marquesina está, en OKLCh, en `L=0.490 C=0.189 H=23.4`. Un local que
suba cualquier rojo obtiene `oklch(0.50, 0.16, 23)` = **`#AC3034`**, que al lado de `#B31226` es el
mismo rojo. Una barbería con rótulo rojo —en Panamá, unas cuantas— tendrá el filo de su ficha, el
fondo de su sello y el subrayado de su nombre exactamente del color del botón de reservar. La regla
que el libro repite dos veces se rompe sola el día que el sistema funcione.

**2 · El local que no sube color no queda «digno», queda desactivado.**
La p09, nota 2, promete: «Sin color y sin foto: trama 00 en el filo y en el sello… Digno, y distinto
del vecino, sin haber hecho nada». Lo que la pantalla dibuja es otra cosa. Comprobado en el HTML,
línea 1373: la tarjeta de Milagros Grajales es la única de las cinco **cuyo nombre no lleva subrayado**
—las otras cuatro llevan `box-shadow:inset 0 -3px 0 var(--lN)`, que es la tinta del local—. Y su filo
izquierdo es trama en `--linea` `#D9D0BE`, que contra papel da **1,44:1**: prácticamente invisible al
lado de los 6 px saturados del vecino. O sea: el subrayado es a la vez la afordancia de «esto es
pulsable» y la tinta del local, así que el local sin tinta pierde la afordancia. Es justo el caso que
la portada convierte en titular («Y el sexto no ha subido nada todavía»), y es el estado en el que
entra todo salón nuevo.

**3 · El azul canal tiene un significado declarado que ninguna pantalla cumple.**
La p06 asigna `#123C63` a «**La persona**: su nombre enlazado, y el anillo de foco de teclado».
Muestreado el PDF: en la pantalla A y en la ficha, los nombres de las personas son tinta `#17140F`
con subrayado en la tinta del local, no azul. El azul acaba en «Más cerca», «Otro día», «Ofrecerlo» y
«Ver el salón y su equipo» —enlaces genéricos, ninguno un nombre de persona—. La ficha de color
describe un sistema que el producto no usa.

**4 · Dentro de una sola pantalla ya conviven dos tintas de local. Ahí está el mercadillo.**
En la agenda de **Uñas Ávila** (pantalla C), la tanda de las 11:00 lleva el sello **DC en verde**.
En la pantalla A, DC es Dayra Castillo, del **Spa Ancón**, y el verde es la tinta de Spa Ancón.
O es un error de datos, o —lo que es peor— el sello es de la persona y arrastra su color a la
pantalla de otro negocio, con lo que «el color lo pone cada local» deja de ser cierto en el momento
en que alguien trabaja en dos sitios (que es medio sector). El libro no dice qué pasa con eso, y es
la pregunta que su propia apuesta obliga a contestar.

**5 · El chip mide 32 px y el libro dice dos veces que ningún control baja de 40.**
p02: «ningún control por debajo de 40 px». p08, cabecera: «Alto mínimo 40 px; en pantalla de móvil,
44 px». p08, tres centímetros más abajo: «**CHIP · ALTO 32 PX**». Y los chips no son decorativos: son
el filtro principal de la pantalla A (Uñas / Barbería / Pestañas / Cejas). El botón de ícono, además,
se declara 40×40, también por debajo del suelo móvil de 44 que fija esa misma cabecera.

**6 · Trece textos de producto por debajo del suelo tipográfico que fija el propio libro.**
p07, regla 3: «Nada por debajo de 12 px en pantalla… y el cuerpo base de la app es 15 px, no 14».
Los teléfonos están dibujados a tamaño real (`.tel{width:390px;height:844px}`; la reducción al 68 %
es solo de impresión), así que los px del HTML son los del producto. Dentro de las pantallas:
barra de pestañas a **10,5 px** en gris, días SÁB/DOM/LUN/MAR/MIÉ a **10,5 px**,
«312 reseñas / atendidas / en Panamá / tandas / ocupadas / del día» a **11 px**, la etiqueta
«NUEVA» a **9 px**, y la línea secundaria de cada ficha («Uñas Ávila · a 400 m») a 13 px cuando el
cuerpo base declarado es 15. La regla más rotunda de la página 07 se incumple en la página 09.

**7 · El 4,98:1 está calculado con blanco puro, y el producto no pinta blanco.**
La p06 fija la referencia: «Contraste medido siempre contra papel `#FBF8F2`». Pero el «4,98:1 con
papel encima» de las páginas 05 y 06 solo sale si el texto es `#FFFFFF`; con el papel real el peor
caso es **4,70:1**, el mismo número que la propia página da para el otro sentido. Y las iniciales del
sello se pintan en `color:var(--papel)` (HTML línea 101), no en blanco. Sigue por encima de AA, así
que no tumba nada, pero es un número impreso que no es el del producto —exactamente el tipo de cosa
que D4 existe para cazar—.

**8 · La casa tiene ocho colores y la tabla enseña seis; uno de los dos que faltan lleva texto a 3,74:1.**
En el `:root` del HTML, además de las seis tintas de la página 06, viven `--linea:#D9D0BE` y
`--rojo-2:#921021` (el rojo del botón pisado). Ninguno tiene ficha ni ratio impreso. Y `#D9D0BE` no
es solo filete: la banda «Almuerzo · cerrado» de la agenda es trama de `#D9D0BE` sobre hueso, con el
texto en gris `#6E6559` encima. Donde el glifo cruza una raya, el ratio es **3,74:1** —por debajo de
AA—. Es defendible como componente inactivo (WCAG lo exime), y por eso no tumbo D4; pero la p02
promete «ningún gris sobre gris» y esto es gris sobre gris.

**9 · En la página 08, el anillo de foco se monta encima de las filas vecinas.**
El foco se pinta como `box-shadow:…,0 0 0 5px var(--azul)`, que no ocupa layout. En la retícula de
estados, las filas están a menos distancia que el anillo, y a 260 dpi se ve claramente que el anillo
de RESERVAR invade la fila de VER PERFIL, el de VER PERFIL la de CANCELAR y el de CANCELAR la del
botón de ícono. En la página que se rechazó dos veces, la columna de foco es la que se ve sucia.

**10 · Dos cosas más de la 08, y una de la 10.**
(a) El estado *cargando* del botón de texto encoge el botón a un tercio de su ancho (los otros tres
mantienen la caja): en pantalla, pulsar «Cancelar» haría saltar el layout y mover el objetivo.
(b) El bloque se titula «CAMPO DE TEXTO · … ETIQUETA SIEMPRE FUERA» y no dibuja **ni una sola**
etiqueta fuera: los cinco campos van desnudos, el primero usa el placeholder como etiqueta
(«¿Qué te haces hoy?») y la pantalla A repite ese mismo patrón en el buscador. La regla se enuncia y
se incumple en el mismo centímetro cuadrado.
(c) En la p10, el pie del bloque «PERFIL PARA COMPARTIR» desborda su caja: la línea «no preside.»
queda impresa cruzando el filete inferior del recuadro.

**11 · El rojo significa tres cosas distintas.**
p06: «la acción de la plataforma: reservar», y nada más. p08: el campo con error lleva borde y
mensaje en ese mismo rojo. p09: la etiqueta «NUEVA» de la reserva pendiente, también. Tres
significados para el único acento del sistema, en un libro que dedica media página a explicar que
el rojo no cede.

---

## 5 · Veredicto

**Pasa.**

Cumple los seis descartes con pruebas que aguantan que las recalculen —los diecisiete ratios
impresos son exactos, incluido el peor caso del barrido de 360 tonos, y los tres tamaños del sello
son tres dibujos distintos y no un escalado—, y no se parece a una plantilla: tiene una materia
propia, una idea que genera reglas implementables y es de Panamá y no de un SaaS de agenda.

Lo digo sabiendo que llega con un agujero de sistema que no es cosmético: **el filtro de vitrina no
excluye la franja roja, así que el color de «reservar» está dentro del rango que el libro le regala a
cada local**, y el local que no sube color pierde el subrayado que marca su nombre como pulsable.
Ninguna de las dos cosas es un descarte del listón, así que no la tumbo; pero si esta dirección se
elige, esas dos y el suelo de 12 px son lo primero que hay que cerrar antes de implantar nada.
