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

**La regla de forma, y se cumple entera:** superficies y bloques de color a canto vivo,
controles a 4 px, y **nada con forma de píldora**. Nada de todo redondeado.

**El filo.** La línea de 6 px en naranja que corta la página entre bloques. Es lo que en un
rótulo es el canto de la chapa: separa sin dibujar una caja alrededor de nada.

**Sin sombras decorativas.** La sombra se reserva para lo que de verdad flota: un menú, una hoja
modal. Lo demás se separa con bloque de color, filo o aire.

**El foco no es del color de marca.** El anillo va en tinta noche sobre fondo claro y en cal
dentro de los bloques oscuros. En azul se quedaba en 2:1 justo encima del bloque azul y del
botón naranja, que son los dos sitios donde más se pulsa.

**Densidad.** Listas con filete entre filas en vez de una tarjeta por elemento: en un teléfono
caben tres salones más por pantalla, y lo que se compara en una lista son los nombres.

**Movimiento.** Contenido a propósito, porque esto se usa en 3G: transiciones de 140 a 220 ms en
lo que se toca y nada que se mueva solo. Todo se apaga con `prefers-reduced-motion`.

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
