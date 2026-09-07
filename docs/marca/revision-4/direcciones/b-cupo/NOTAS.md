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
| Guayacán | `#F2B705` | carbón encima 10,04:1 | solo el último cupo del día |
| Caribe | `#0E6156` | 6,40:1 sobre cal | confirmado y foco de teclado |
| Piedra | `#645F57` | 5,53:1 sobre cal | lo vendido y el texto de apoyo |

Proporción: cal 68 · carbón 17 · piedra 8 · achiote 5 · caribe 1,5 · guayacán 0,5. Si el achiote
pasa del 5 % es que se está pintando de rojo lo que ya está vendido.

**El guayacán da 1,59:1 sobre cal.** Está escrito en el libro como prohibición, no como matiz: no
es texto ni filete nunca, solo fondo con carbón encima. Un amarillo bonito usado como texto es
exactamente el error que ya coló una vez.

El achiote es la única tinta del sistema que aguanta en los dos sentidos (texto sobre cal 5,94 y
cal sobre relleno 5,94). Por eso puede ser a la vez la marca de un hueco y el fondo de un botón.

## Las tipografías

**Chivo** y **Chivo Mono** (Omnibus-Type, Buenos Aires) y **Petrona** (Huerta Tipográfica, La
Plata). No es folclore: son letras dibujadas para el español, con eñe y acentos de verdad y no
parcheados sobre un diseño inglés. Ninguna está en la lista de vetadas y ninguna es la que trae la
plantilla.

La regla que sostiene el sistema: **toda hora va en Chivo Mono, y nada más va en Chivo Mono.** Ni
precios, ni nombres, ni distancias. Se ve en la página 07 con el ejemplo de lo que pasa cuando se
hace al revés. La consecuencia práctica es que en cualquier pantalla se distingue una hora del
resto sin llegar a leerla, y que dos columnas de horas nunca bailan.

Petrona solo aparece en frases de marca y en citas de clientas. En la interfaz no hay serif: a
390 px estorba.

## Interfaz

Radio de esquina **0** en todo, escrito y aplicado. Un cupo es un corte, no una pastilla.

El foco de teclado no se pinta en el botón sino en un envoltorio, porque el `clip-path` del corte
recorta el propio contorno. Es un detalle feo de implementación y por eso está dicho en la página,
no escondido: quien lo construya se va a topar con ello el primer día.

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
