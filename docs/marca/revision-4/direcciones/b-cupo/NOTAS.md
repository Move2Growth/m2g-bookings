# cupo · por qué cada decisión · Estado: completado

## El nombre

**cupo.** Es la palabra que ya se usa en Panamá para esto: «¿hay cupo?», «no hay cupo», «me
guardas un cupo». No es una metáfora de reserva, es la unidad de venta dicha en voz alta. Cuatro
letras, sin hache muda, sin ll, sin acento: por teléfono se dice una vez y se entiende.

Se escribe siempre en minúscula y en redonda. No lleva artículo: no es «el cupo», es **cupo**.

Lo que descarté y por qué:
- **Turno** — es argentino y venezolano; en Panamá se dice *cita*.
- **Ahorita** — en Panamá «ahorita» significa *luego*. El chiste se lo hacen solos.
- **Hueco** — es exactamente el concepto, pero en Centroamérica es un insulto homófobo.
- Cualquier cosa acabada en **-ly**, **-ify** o **book**: eso es Berlín, no Calidonia.

## La semilla: lo que se vende es la hora

El sistema entero está construido sobre un solo objeto gráfico, **la regla del día**: doce horas
de 8:00 a 20:00 en veinticuatro medias horas. Lo vendido se apaga en piedra y baja de altura; lo
libre sube y es lo único con tinta viva. Un salón lleno se apaga solo, sin que nadie tenga que
escribir «completo».

De ahí salen las cuatro respuestas que pedía el encargo, y ninguna es un texto:
- **Cerrado ahora** — la regla se raya en diagonal, el nombre baja a piedra y no queda ni una
  hora que se pueda tocar. Página 09, tercera ficha.
- **El último hueco del día** — es el único sitio donde aparece el guayacán. Una agenda vacía es
  una regla llena de achiote; el último hueco es una sola marca amarilla.
- **Un día entero de un vistazo** — la agenda del dueño son tres reglas en paralelo con lo
  vendido apagado: lo único que resalta son los cuatro huecos, que es lo que él tiene que mirar.
- **Te quitaron el hueco mientras reservabas** — el chip pasa a filete discontinuo y tachado, y
  debajo aparecen las dos horas vecinas ya pulsables. Página 08, abajo a la derecha.

**No hay semáforo.** Nada es verde por estar disponible. Es una decisión, no un descuido: si lo
libre y lo ocupado compiten en color, la pantalla se vuelve un tablero. Aquí solo hay tinta donde
hay algo que vender.

## El símbolo

Salió de Higgsfield en vectorial (`recraft_v4_1`, `model_type vector`), cinco intentos, 12,5
créditos. Los cuatro descartados están en `logo/intentos/`.

Es un bloque con dos marcos encajados y **un canal que lo atraviesa y sale por el borde inferior**.
La masa es el tiempo vendido; el canal es el cupo. La construcción —quitar capas para que aparezca
el dibujo— es la de la mola guna y la del calado de la pollera: en Panamá el oficio es sustractivo,
el dibujo es el agujero. Ese mismo canal, reducido a un escalón de 13 × 7 px, es el corte que
lleva cada botón en la esquina inferior izquierda.

Descarté el reloj sin dibujarlo. Y descarté una versión más literal de mola (`intento-a`) porque a
16 px era una mancha.

A 16 px el filete interior desaparecería, así que **hay un segundo dibujo**, `icono-16.svg`, con el
marco interior quitado a propósito. Es el único que se usa por debajo de 24 px.

## Las tintas

Seis, con su ratio impreso en la página 06 y medido contra el fondo con el que se usa de verdad:

| Tinta | Hex | Ratio | Para qué |
|---|---|---|---|
| Cal | `#F4EFE6` | carbón encima 15,94:1 | el fondo de todo |
| Carbón | `#17150F` | 15,94:1 sobre cal | todo el texto |
| Achiote | `#A82F18` | 5,94:1 sobre cal · cal encima 5,94:1 | **el cupo libre** |
| Guayacán | `#F2B705` | 1,59:1 sobre cal · 10,04:1 sobre carbón | solo el último cupo del día |
| Caribe | `#0E6156` | 6,40:1 sobre cal | confirmado y foco de teclado |
| Piedra | `#645F57` | 5,53:1 sobre cal | lo vendido y el texto de apoyo |

Proporción: cal 68 · carbón 17 · piedra 8 · achiote 5 · caribe 1,5 · guayacán 0,5. Si el achiote
pasa del 5 % es que se está pintando de rojo lo que ya está vendido.

**El guayacán da 1,59:1 sobre cal y 10,04:1 sobre carbón.** La prohibición está acotada al fondo,
que es lo único honesto: sobre claro no es texto ni filete nunca; sobre carbón sí, y ahí es donde
vive el rótulo de calle y el perfil que se comparte. Un amarillo bonito usado como texto sobre
papel es exactamente el error que ya coló una vez, y por eso la prohibición se dibuja tachada en
la página 04.

El achiote es la única tinta del sistema que aguanta en los dos sentidos (texto sobre cal 5,94 y
cal sobre relleno 5,94). Por eso puede ser a la vez la marca de un hueco y el fondo de un botón.

## Las tipografías

**Chivo** y **Chivo Mono** (Omnibus-Type, Buenos Aires) y **Petrona** (Huerta Tipográfica, La
Plata). No es folclore: son letras dibujadas para el español, con eñe y acentos de verdad y no
parcheados sobre un diseño inglés. Ninguna está en la lista de vetadas y ninguna es la que trae la
plantilla.

La regla que sostiene el sistema: **en el producto, toda hora va en Chivo Mono, y nada más.** Ni
precios, ni nombres, ni distancias, ni cuentas: «31 cupos hoy», «4,9» y «1.240 atendidas» van en
Chivo con cifras tabulares. Este manual es la excepción declarada, porque aquí Chivo Mono hace
además de voz técnica para hex, ratios y cotas: eso es documentación y no producto. Se ve en la página 07 con el ejemplo de lo que pasa cuando se
hace al revés. La consecuencia práctica es que en cualquier pantalla se distingue una hora del
resto sin llegar a leerla, y que dos columnas de horas nunca bailan.

Petrona solo aparece en frases de marca y en citas de clientas. En la interfaz no hay serif: a
390 px estorba.

## Interfaz

Radio de esquina **0** en todo, escrito y aplicado. Un cupo es un corte, no una pastilla.

**44 px de alto en todo control tocable**, con 8 px de separación: iOS pide 44 pt y Android 48 dp,
y esto se toca de pie entre cliente y cliente. El chip informativo —el que no se pulsa— se queda en
28 px y está declarado como tal.

**Al pulsar, el corte se cierra:** el botón pasa a rectángulo pleno. Esa es la señal principal del
estado, no el matiz de color. En un teléfono el dedo tapa medio botón y dos rojos vecinos no se
distinguen; un cambio de silueta sí. Y «encima» solo existe con ratón, cosa que el libro dice.

El foco de teclado no se pinta en el botón sino en un envoltorio, porque el `clip-path` del corte
recorta el propio contorno. Es un detalle feo de implementación y por eso está dicho en la página,
no escondido: quien lo construya se va a topar con ello el primer día.

## Lo que cambió después de la crítica

Seis defectos objetivos, todos reparados sin tocar nombre, paleta, sello ni regla del día:

1. **Dos estados que no eran estados.** «Encima» y «pulsado» del secundario estaban a 1,15:1, y en
   el de texto compartían hex. Ahora el pulsado cierra el corte y cambia de tinta (secundario y de
   texto pasan a fondo achiote), así que se distinguen por silueta y por color, no por 1 px.
2. **La regla del guayacán, acotada.** El libro decía «nunca como texto ni como filete» y usaba
   guayacán como texto trece veces, siempre sobre carbón. La regla del libro ahora dice lo mismo
   que decía el `marca.json`: prohibido sobre cal, permitido sobre carbón, con los dos ratios.
3. **La regla de Chivo Mono, acotada al producto y cumplida.** «31 cupos hoy», «4 cupos», «4,9»,
   «1.240», los contadores de la agenda, «Panamá · 4G» y el teléfono de la tarjeta salieron de
   Chivo Mono y pasaron a Chivo con cifras tabulares.
4. **La palabra `CUPO` ya no se parte.** Los bloques de hueco de la agenda detectan su duración: por
   debajo de una hora se componen en una línea con una marca cuadrada en vez de dos líneas apretadas.
5. **La jerarquía llega al suelo.** Se añadieron Cuerpo menor (11,5/16) y Micro (9,5/13), y no queda
   ni un texto por debajo de 9,5 px en ninguna de las tres pantallas.
6. **Alto de toque a 44 px** en los treinta y tantos controles de las páginas 08 y 09.

Y dos cosas más que el crítico señaló sin contarlas como fallo: los **siete tonos de estado** que
faltaban están ahora en la página 06 con su ratio impreso (el texto inhabilitado subió de 2,38:1 a
3,57:1 aunque WCAG lo exima por ser control inactivo), y las **estrellas de valoración** —el único
widget prestado que quedaba— se redibujaron con la gramática de la regla del día: bloques llenos y
bloques vacíos.

**Lo que decidí dejar como está.** La retícula interna se repite en las páginas 03, 04, 05, 06 y
10 —tres cajas arriba, tira de tres bloques abajo—. Es cierto y se nota al pasar páginas seguidas,
pero cambiarla es rediseñar el libro, no reparar un defecto, y una retícula constante en un manual
de marca es una decisión defendible. Tampoco toqué el hueco de la mitad de la portada: ese aire es
intencionado.

## Lo que no me convence de mi propia propuesta

1. **El símbolo tiene una segunda lectura que no controlo.** Bloque con pie: a algunos les va a
   parecer un espejo de barbería con su pedestal, y a otros un enchufe. Lo primero me viene bien;
   lo segundo no lo puedo evitar y no lo he escondido.
2. **«cupo» es una palabra del diccionario.** Se dice muy bien y significa exactamente lo que
   vendemos, pero es de registrar difícil y de posicionar en buscadores peor. Esa pelea es real y
   no la resuelve el diseño.
3. **La tercera pantalla vive de la retícula.** La agenda del dueño con tres columnas cabe en un
   teléfono porque el ejemplo tiene tres profesionales. Con siete hay que inventar otra cosa, y
   ese caso no está resuelto en este libro.
4. **El moodboard tiene una pieza floja.** «Cal de Casco Viejo» es la única de las seis que
   ilustra un ambiente en vez de resolver un mecanismo. Las otras cinco se ganan el sitio.
5. **El achiote al 5 % es una disciplina, no una garantía.** El día que alguien decida que las
   promociones también van en achiote, el sistema se cae entero y el libro no tiene forma de
   impedirlo más que diciéndolo.
6. **Subir todo a 44 px apretó las pantallas.** Caben, pero con menos aire del que tenían: en la
   ficha, la rejilla de horas se come ahora media pantalla. Es el precio correcto —se paga en
   composición y se cobra en pulsaciones acertadas—, pero es un precio.
