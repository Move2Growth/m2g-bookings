# Bukeo · Brand Book — Estado: en proceso

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

**El wordmark es `bukeo` en minúsculas**, en Outfit con peso de display y el interletrado
cerrado. Minúsculas porque la marca no grita: es la herramienta de trabajo de alguien, no una
promesa de lujo.

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

Tinta cálida sobre papel frío y **un solo acento**, que aparece poco y manda cuando aparece.

| Nombre | Hex | Para qué | Proporción |
|---|---|---|---|
| **Papel** | `#F7F6F4` | Fondo de toda la web | 46 % |
| **Lienzo** | `#FFFFFF` | Superficies: fichas, filas, formularios | 26 % |
| **Tinta** | `#171310` | Texto principal y bloque de marca | 14 % |
| **Arena** | `#EFEDE9` | Secciones alternas, estados apagados | 8 % |
| **Tinta suave** | `#585149` | Texto secundario | 4 % |
| **Fucsia Bukeo** | `#B5124F` | **Solo lo accionable**: acción principal, hora reservable, enlace | 2 % |

**La regla del acento:** si algo va en fucsia, se puede tocar. Un titular en fucsia enseña a la
gente que el color no significa nada, y a partir de ahí el botón deja de verse.

**Estados de una reserva.** Cinco, con el mismo color en la web, el panel y la app: pendiente
(ámbar), confirmada (verde), completada (azul apagado), no vino (gris) y cancelada (rojo). Un
estado que se lee distinto en cada superficie es un estado que nadie aprende.

**Contraste.** Las 35 combinaciones que el producto usa de verdad están medidas con la fórmula
WCAG y **todas cumplen AA**, en claro y en oscuro. Lo comprueba un script que falla el proceso
si alguien retoca un color «solo un poco»:
[`packages/tokens/verificar-contraste.mjs`](../../packages/tokens/verificar-contraste.mjs).

## 06 · Tipografía

**Dos voces y ninguna más.**

| | Familia | Trabajo |
|---|---|---|
| **Display** | Outfit Variable | Titulares y wordmark. Geométrica, de carácter a tamaño grande |
| **Texto** | Geist | Interfaz, cuerpo y **todas las cifras**, con tabulares de verdad |

Las dos van **autoalojadas**. Enlazar a Google Fonts sería una dependencia de un tercero, un
problema de política de seguridad de contenido y una petición más en una red de 3G.

**Vetadas:** Inter, Fraunces, Bricolage y General Sans.

**Cifras tabulares, y esto no es un detalle.** Horas, duraciones y precios llevan `tabular-nums`
siempre. En una agenda las columnas tienen que cuadrar o no se leen de un vistazo, que es la
única forma en que se lee una agenda entre clienta y clienta.

**Escala:** de 0,75 rem a 4 rem, con el cuerpo en 1 rem. Los campos de formulario **nunca** bajan
de 16 px: por debajo, iOS hace zoom al enfocar y descuadra la pantalla sin que nadie la toque.

## 07 · UI y aplicaciones

**La regla de forma, y se cumple entera:** superficies a canto vivo con filete de 1 px,
controles a 4 px, y píldora solo en fichas de filtro y avatares. Nada de todo redondeado.

**Sin sombras decorativas.** La sombra se reserva para lo que de verdad flota: un menú, una hoja
modal. Lo demás se separa con filete o con aire.

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
