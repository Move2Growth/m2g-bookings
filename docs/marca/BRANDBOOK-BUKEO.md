# Bukeo · Brand Book — Estado: completado

> **Identidad de marca · Vol. 01 · 2026 · Ciudad de Panamá**
>
> Mismo formato que el brandbook de RŪTA, que es el estándar de la casa: estrategia, moodboard,
> logo, ícono, color con proporciones, tipografía y aplicaciones. Lo que aquí se decide se
> implementa en [`packages/tokens`](../../packages/tokens/tokens.json); si los dos divergen,
> **manda este documento** y se corrigen los tokens.

---

## 01 · Estrategia de marca

### La frase

**Tu agenda, gratis. Y el sitio donde te encuentran.**

No vendemos software de gestión. Le quitamos a una señora que corta el pelo el trabajo de
llevar su día en el WhatsApp, y le ponemos delante clientas que hoy no la conocen.

### Tres pilares

| Gratis de verdad | Horas que existen | El barrio primero |
|---|---|---|
| Sin tarjeta, sin mensualidad y sin comisión por cita. El plan Gratis no tiene letra pequeña. | Lo que se ve libre está libre. No es una solicitud que alguien contesta mañana. | Se busca por Bella Vista y por El Cangrejo, no por «área metropolitana». |

### Esencia

**la hora que sí existe**

### Cómo hablamos

Llano, directo y de aquí. Frases cortas. Nada de «potenciar», «solución integral» ni
«revolucionar». Si una frase no la diría la dueña del salón, no va. El vocabulario completo y
las palabras prohibidas están en [`COPIA.md`](COPIA.md).

### Qué NO es la marca

- No es una app de belleza aspiracional con modelos de agencia. Es el negocio de una persona.
- No es un dashboard corporativo. Se usa de pie, con una mano, entre clienta y clienta.
- No es lujo. Es oficio.

---

## 02 · Moodboard

Seis referencias, y ninguna es una app:

1. **La pizarra del salón** con las citas del día escritas a mano. Lo que Bukeo sustituye.
2. **El rótulo pintado** de un local de barrio en Ciudad de Panamá: color plano, letra grande, sin degradado.
3. **La rejilla de horas** de un horario impreso. Cifras alineadas, columnas que cuadran.
4. **Manos trabajando**: tijera, pincel de tinte, torno de uñas. Personas, no producto.
5. **Papel y tinta**: recibo, tarjeta de cita, sello. La materialidad de un negocio pequeño.
6. **La luz de Panamá**: alto contraste, sombra dura. Nada de neblina ni de degradado suave.

---

## 03 · Logo suite

**El wordmark es `BUKEO` en versales dibujadas a trazo**: cinco letras construidas con líneas
del mismo grosor, remate a escuadra y esquinas en ángulo vivo. No es una fuente rotulada, es un
trazado; por eso a 16 px sigue siendo el mismo dibujo y no se convierte en una mancha.

Versales y no minúsculas: el lenguaje de esta marca es el del **rótulo pintado de un local**,
no el de una aplicación. Un rótulo se lee desde la acera.

| Versión | Cuándo |
|---|---|
| **Principal** | Símbolo más wordmark, en tinta sobre papel |
| **Invertida** | El mismo archivo sobre fondo oscuro o sobre foto |
| **Solo símbolo** | Cuando el espacio no da: favicon, avatar, sello |

**El logotipo no tiene tres archivos.** Se dibuja con `currentColor`, así que hereda el color
del sitio donde está: sobre papel sale tinta y sobre una sección oscura sale papel. Una versión
invertida a mano es una versión que alguien acaba usando mal.

**Lo que no se hace nunca:** deformarlo, ponerle sombra, meterlo en una caja de color que no sea
del sistema, o separar el símbolo del wordmark con más aire del que trae.

## 04 · Ícono

El símbolo es **el hueco**: un bloque sólido con una muesca calada. Es literalmente lo que vende
el producto, la hora que sí está libre en una jornada llena.

Está dibujado con un solo trazado y regla par-impar, de modo que **la muesca es un calado y no
una forma pintada del color del fondo**. Por eso funciona igual sobre papel, sobre tinta y sobre
una fotografía, con un archivo y sin versiones.

**Escalas.** A 24 px y más, símbolo y wordmark juntos. A 16 px, solo el símbolo: dos formas
geométricas siguen leyéndose donde una ilustración ya no.

**Usos:** favicon y icono de aplicación, foto de perfil, sello en el recibo de una cita, marca
de agua discreta en material impreso.

## 05 · Color

**El color es la estructura.** Aquí no hay retícula dibujada ni tarjetas: lo que separa una
sección de otra es un bloque de color a sangre y un filo grueso. Cal, tinta, azul y naranja.

| Nombre | Hex | Para qué | Proporción |
|---|---|---|---|
| **Cal** | `#F2F3EF` | Fondo de toda la web | 44 % |
| **Lienzo** | `#FFFFFF` | Superficies: filas, formularios, rejilla de horas | 20 % |
| **Tinta noche** | `#0D1526` | Texto principal y bloques oscuros a sangre | 16 % |
| **Arena** | `#E7E9E2` | Secciones alternas | 8 % |
| **Azul chiva** | `#1636C7` | Bloque de sección y lo que **cierra** | 6 % |
| **Tinta suave** | `#4A5163` | Texto secundario | 4 % |
| **Naranja mango** | `#FF7A1F` | Lo que **abre** y el filo de bloque | 2 % |

### La regla que no se rompe

**Hay dos colores saturados y cada uno tiene un trabajo.**

- **El naranja abre.** Empieza algo: buscar, crear el salón, publicar. Y es el filo que corta
  la página entre bloques.
- **El azul cierra.** Remata: elegir la hora, confirmar la cita. Y es el bloque de sección.

**Nunca compiten en el mismo botón.** Si en una pantalla hay dos acciones saturadas, una de las
dos está mal clasificada.

**El naranja nunca es color de texto.** Sobre cal se queda en 2,4:1, muy por debajo de AA. Vive
siempre como fondo con tinta noche encima, y esa es la razón de la regla, no una preferencia.

**Estados de una reserva.** Cinco, con el mismo color en la web, el panel y la app: pendiente
(ámbar), confirmada (verde), completada (azul apagado), no vino (gris) y cancelada (rojo). Un
estado que se lee distinto en cada superficie es un estado que nadie aprende.

**Contraste.** Las 41 combinaciones que el producto usa de verdad están medidas con la fórmula
WCAG y **todas cumplen AA**, en claro y en oscuro. Lo comprueba un script que falla el proceso
si alguien retoca un color «solo un poco»:
[`packages/tokens/verificar-contraste.mjs`](../../packages/tokens/verificar-contraste.mjs).

## 06 · Tipografía

**Una sola familia, tres anchos.** Archivo Variable, con el eje de anchura (`wdth`) haciendo el
trabajo que en otros sistemas hacen dos o tres fuentes distintas:

| Ancho | Valor | Trabajo |
|---|---|---|
| **Rótulo** | 112 % | Titulares y wordmark. Ancho, plantado, de rótulo de local |
| **Texto** | 100 % | Interfaz y cuerpo |
| **Cifra** | 125 % | Horas, duraciones y precios, con tabulares |

Una familia y no dos porque **es una sola petición de red**, y porque el contraste entre un
titular y el cuerpo lo da aquí el ancho, no un salto de familia que a 390 px nadie percibe como
intencionado.

Va **autoalojada**. Enlazar a Google Fonts sería una dependencia de un tercero, un problema de
política de seguridad de contenido y una petición más en una red de 3G.

**Vetadas:** Inter, Fraunces, Bricolage y General Sans.

**Cifras tabulares, y esto no es un detalle.** Horas, duraciones y precios llevan `tabular-nums`
siempre. En una agenda las columnas tienen que cuadrar o no se leen de un vistazo, que es la
única forma en que se lee una agenda entre clienta y clienta.

**Escala:** de 0,75 rem a 4 rem, con el cuerpo en 1 rem. Los campos de formulario **nunca** bajan
de 16 px: por debajo, iOS hace zoom al enfocar y descuadra la pantalla sin que nadie la toque.

## 07 · UI y aplicaciones

> Este apartado era prosa —«canto vivo», «sin sombras decorativas», «listas con filete»— y por
> eso el código pudo alejarse durante semanas sin que saltara nada: **un párrafo no se puede
> contrastar con una pantalla**. Ahora dice piezas, medidas y números que se comprueban.

### La regla de la forma

**Con canto se toca. Sin canto se lee.** (ADR-0017)

| Pieza | Canto | Qué significa |
|---|---|---|
| Botón que abre o cierra | 4 px | La acción principal de la pantalla |
| Botón secundario, ficha de filtro, chapa de hora | 3 px | Se toca, no manda |
| Botón llano | 2 px, mordida de 10 px | Se toca y casi no pesa |
| Sello de estado, fila de lista, panel | 0 | **No se toca**: se lee |

El canto es un zócalo macizo **dentro** de la caja, dibujado con `currentColor` y al que le
faltan los últimos **14 px** por la derecha. Esa mordida es la muesca calada del icono, tumbada:
es lo que hace que un control de Bukeo se reconozca con el texto tapado.

Al pasar por encima el canto crece a 6 px, la chapa se levanta. Al pulsar se lo traga y el
contenido baja 2 px. **La altura total no cambia**: 48 px en reposo, al pulsar y apagado.

### Lo que separa

Color, filo o aire. **Nunca un filete que no llegue a 3:1.** El filete de `--color-borde` medía
1,29:1 y se retiró de toda la hoja de estilos: donde de verdad separa se usa
`--color-borde-fuerte` (3,88:1), y donde dibujaba una caja alrededor de algo, desaparece. Una
caja con filete es una tarjeta, y aquí no hay tarjetas.

El **filo** es la barra de 6 px que corta la página entre bloques y marca lo elegido. En naranja
cuando separa secciones; en tinta cuando marca una ficha o una pestaña.

### Las piezas, y dónde vive cada una

| Pieza | Dónde | Regla propia |
|---|---|---|
| **El rótulo** | Ficha de salón sin foto, celda de categoría, sello de la lista | Nombre entero a tamaño de cartel, trama del oficio como máscara y par de color. **El par vive en el elemento que lleva el texto**, no en el rótulo (ADR-0018) |
| **La fila de salón** | Buscador y guardados | Es una fila, no una tarjeta. Termina en la próxima hora libre, en chapa con canto |
| **La rejilla de horas** | Ficha de salón | Dentro de un bloque azul a sangre: elegir la hora es lo que cierra |
| **La barra del armazón** | Panel y consola | Tinta con filo naranja y el nombre en ancho de rótulo |
| **La barra de pestañas** | Panel, consola, área de la clienta | Abajo en el teléfono, donde llega el pulgar; fila bajo la cabecera en escritorio. La activa se marca con filo, no con relleno |
| **Los iconos** | Toda la navegación | Dibujados aquí, no de librería. Remate a escuadra y ángulo vivo como el wordmark, trazo de 2 sobre caja de 24 en coordenadas enteras |

### Los tres anchos, y dónde se gasta cada uno

- **Rótulo, 112 %:** titulares, nombre del salón, nombre de la categoría, contexto de la barra.
- **Texto, 100 %:** cuerpo e interfaz.
- **Cifra, 125 %:** **todas** las horas, duraciones y precios. Este producto es horas y precios:
  el ancho de cifra estaba declarado y sin gastar, y ese era el gesto propio que faltaba.
- **Estrecho, 87 %:** la segunda línea de una fila, las etiquetas en versalita y los datos que
  acompañan sin competir.

### Movimiento

Tres gestos y ninguno más: **entra** (lo nuevo sube dos píxeles), **escalonado** (una lista entra
fila a fila, cortado a las diez) y **hoja** (sube desde abajo, que es de donde viene el pulgar).
El canto es el cuarto y no cuenta: es el propio control respondiendo. La única animación en
bucle es el brillo del esqueleto, cuyo trabajo es justamente decir «esto sigue pasando». Todo se
apaga con `prefers-reduced-motion`.

### Cómo se comprueba que esto se cumple

Tres medidas, y las tres se pueden repetir:

1. **Contraste en las páginas de verdad**, con el color calculado y el fondo real:
   `node scripts/verificar-contraste-en-pantalla.mjs`. Recorre veintidós pantallas, **incluidas
   las que hay detrás del acceso**, y sale con error si algo baja de AA. Si no puede entrar, no
   da el visto bueno: lo cuenta como fallo.
2. **Reparto de color por superficie**, con el script de
   [`docs/marca/revision-2/medicion-del-color.md`](../marca/revision-2/medicion-del-color.md).
3. **Filetes por debajo de 3:1**: tienen que ser cero. `grep -c "var(--color-borde)"` sobre
   `globales.css`.

**Dónde vive esto en el código:** [`packages/tokens/tokens.json`](../../packages/tokens/tokens.json)
son los valores y `apps/web/app/globales.css` la capa de componentes. En esa capa no hay ni un
hexadecimal escrito a mano; si aparece uno, es un error.

## 08 · Cómo se elige y cómo se cambia

La identidad **no se eligió a ojo**. Tres direcciones independientes compitieron con prototipos
comparables y tres críticos intentaron tumbarlas contra la lista de vetos, el contraste y el
comportamiento a 390 px. El proceso y el porqué del ganador están en
[`DECISION-DE-MARCA.md`](DECISION-DE-MARCA.md).

Para cambiar algo de aquí: se cambia **este documento primero**, después los tokens, y solo
entonces las pantallas. Al revés es como una identidad se deshace en tres semanas.
