# Crítica de accesibilidad y rendimiento — Bukeo, direcciones A, B y C

**Estado: completado**

Auditoría adversarial de las tres propuestas de identidad. El criterio no es «¿se ve bonito en el portátil?», sino **¿sobrevive en un teléfono de gama media, con 3G, a mediodía en Panamá, sostenido con una mano?**. Todo lo que sigue está medido, no estimado.

---

## Instantánea auditada

Los tres archivos se estaban editando durante la auditoría. Se esperó a una ventana de 100 s sin cambios y se midió con verificación de huella **antes y después** de la pasada (idénticas, así que el conjunto de números es coherente).

| Archivo | Bytes | MD5 |
|---|---|---|
| `/Users/luisgomez/Desktop/kraken/m2g-bookings/docs/marca/propuestas/direccion-a.html` | 28 565 | `8fc20f572e20a5680974a90a5a6791d7` |
| `/Users/luisgomez/Desktop/kraken/m2g-bookings/docs/marca/propuestas/direccion-b.html` | 33 663 | `6b1f0041f9f2ac5866e9d0f728c6a4f0` |
| `/Users/luisgomez/Desktop/kraken/m2g-bookings/docs/marca/propuestas/direccion-c.html` | 57 425 | `31343e004bc74d5869987c1d3d567b5e` |

**Método.** Contraste: script propio en Node con luminancia relativa sRGB de WCAG 2.1 (`(L1+0.05)/(L2+0.05)`), 156 combinaciones extraídas del CSS real, no del anexo de paleta. Geometría, tipografía renderizada, peso y red: Chromium headless vía Playwright 1.49.1 a **390 × 844 px, DPR 3**, con captura de todas las respuestas de red. Umbrales aplicados: **4,5:1** texto normal, **3:1** texto grande (≥ 24 px, o ≥ 18,66 px en negrita) y elementos de interfaz o bordes de control.

---

## 1. Lo que fallan las tres. Sin excepción

Antes de separarlas, lo que comparten. Estos cuatro puntos no los arregla elegir una u otra.

### 1.1 Ninguna tiene un solo campo de formulario. Cero. En las tres

```
campos de formulario:  A = 0   B = 0   C = 0
<input> + <label> + <select> + <textarea>:  A = 0   B = 0   C = 0
```

El requisito de «16 px en campos de formulario para que iOS no haga zoom» **es inauditable en las tres, porque ninguna ha dibujado un campo**. Y eso no es un descuido de maqueta: las dos pantallas donde el producto realmente toma datos —el buscador («escribes barbería o tu zona», que las tres describen en prosa) y la confirmación con número de teléfono— **no existen en ninguna propuesta**. Se ha diseñado la parte de leer y se ha dejado sin diseñar la parte de escribir, que es justo donde una mano ocupada, un teclado que tapa media pantalla y un zoom de iOS deciden si la reserva se completa o se abandona.

**Gravedad: grave, compartida.** No descalifica a ninguna porque no descalifica a ninguna en particular, pero **la dirección que se elija tiene que entregar el campo de búsqueda y el de teléfono antes de aprobarse**, con `font-size` ≥ 16 px, `<label>` visible (no marcador de posición como única etiqueta), `inputmode="tel"` y `autocomplete="tel"`.

### 1.2 Las tres suspenden el objetivo táctil, y por el mismo sitio

| | Pulsables totales | Por debajo de 44 px | % | El peor |
|---|---|---|---|---|
| A | 33 | **15** | 45 % | enlaces del pie a **19 px** de alto |
| B | 44 | **17** | 39 % | enlaces del pie a **16 px** de alto |
| C | 59 | **23** | 39 % | enlaces del pie a **18 px** de alto |

El patrón es idéntico en las tres: **los botones grandes están bien y las listas de enlaces del pie están rotas**. `.btn` mide 49,6 px en A, 52 px en B y 46 px en C; las celdas de hora miden 46 px en las tres. Y luego el pie apila catorce a dieciocho enlaces de 16–19 px de alto separados por 5–10 px, que con el pulgar es una lotería. Los tres logotipos también fallan (25,5 / 26 / 22 px de alto).

**Arreglo para las tres:** `padding-block` de 13 px en los `<a>` del pie (o `min-height:44px;display:flex;align-items:center`) y `padding` en el enlace del logotipo hasta 44 px de caja.

### 1.3 Ninguna sirve imágenes adaptadas, y solo una las difiere

```
srcset / <picture> / sizes:   A = 0   B = 0   C = 0
loading="lazy":               A = 0/6  B = 0/3  C = 3/3
```

Las tres piden a `picsum.photos` una imagen de tamaño fijo y la pintan a otro. En 3G, cada foto que entra por encima de lo que la pantalla puede mostrar es tiempo en el que la clienta mira un hueco gris.

### 1.4 El texto informativo más débil de las tres se queda por debajo de 7:1

WCAG AA (4,5:1) es un suelo pensado para una pantalla en interior. Bajo sol directo, el reflejo de la pantalla levanta el negro y aplasta el rango; el criterio práctico para exteriores es **AAA, 7:1**, para el texto que hay que poder leer de pie en la calle.

| | Texto informativo más débil | Ratio | ¿≥ 7:1? |
|---|---|---|---|
| A | `#4E5A55` sobre `#F6F6F3` (11–17 px) | 6,65:1 | **no** |
| B | `#CBD5F8` sobre `#1636C7` (12–19 px) | 6,04:1 | **no** |
| C | `#4E555C` sobre `#F4F5F6` (9–14 px) | 6,93:1 | **no** |

Las tres pasan AA y ninguna llega al listón de la calle. Ninguna queda descalificada por esto sola, pero es la diferencia entre «cumple la norma» y «se lee en Vía Argentina».

---

## 2. Contraste medido, combinación por combinación

### 2.1 Dirección A — «Editorial de barrio»

Paleta: papel `#F6F6F3`, ficha `#FFFFFF`, tinta `#16211D`, plomo `#4E5A55`, filete `#D7D9D3`, achiote `#C6350A`, achiote fuerte `#A72C08`, claro suave `#B9C0BC`, filete oscuro `#33403B`.

| Combinación | px / peso | Frente | Fondo | Ratio | Mínimo | ¿Pasa? |
|---|---|---|---|---|---|---|
| Texto corrido, tinta sobre papel | 16 / 400 | `#16211D` | `#F6F6F3` | 15,28:1 | 4,5 | sí |
| Titular h1 sobre papel | 37,6 / 600 | `#16211D` | `#F6F6F3` | 15,28:1 | 3,0 | sí |
| Enlaces de la barra | 15 / 400 | `#16211D` | `#F6F6F3` | 15,28:1 | 4,5 | sí |
| Antetítulo `.fecha` | 11 / 600 | `#4E5A55` | `#F6F6F3` | 6,65:1 | 4,5 | sí |
| Entradilla `.entrada` | 17 / 400 | `#4E5A55` | `#F6F6F3` | 6,65:1 | 4,5 | sí |
| Sumario de sección | 16 / 400 | `#4E5A55` | `#F6F6F3` | 6,65:1 | 4,5 | sí |
| Pie de foto | 13 / 400 | `#4E5A55` | `#F6F6F3` | 6,65:1 | 4,5 | sí |
| Número de paso `.num` | 22 / 600 | `#C6350A` | `#F6F6F3` | 4,95:1 | 4,5 | sí |
| Botón principal, texto | 16 / 600 | `#FFFFFF` | `#C6350A` | 5,36:1 | 4,5 | sí |
| Botón principal en `hover` | 16 / 600 | `#FFFFFF` | `#A72C08` | 6,98:1 | 4,5 | sí |
| Botón secundario, texto | 16 / 600 | `#16211D` | `#F6F6F3` | 15,28:1 | 4,5 | sí |
| Botón secundario, **borde** | 1 px | `#16211D` | `#F6F6F3` | 15,28:1 | 3,0 | sí |
| Bloque oscuro, texto | 16 / 400 | `#F6F6F3` | `#16211D` | 15,28:1 | 4,5 | sí |
| Bloque oscuro, sumario y apoyo | 14–16 / 400 | `#B9C0BC` | `#16211D` | 8,92:1 | 4,5 | sí |
| Bloque oscuro, pie de foto | 13 / 400 | `#B9C0BC` | `#16211D` | 8,92:1 | 4,5 | sí |
| **Bloque oscuro, filete de lista** | 1 px | `#33403B` | `#16211D` | **1,53:1** | 3,0 | **NO** |
| Bloque oscuro, filete de la cita | 4 px | `#C6350A` | `#16211D` | 3,08:1 | 3,0 | sí (por 0,08) |
| Precio `$0` | 78 / 600 | `#F6F6F3` | `#16211D` | 15,28:1 | 3,0 | sí |
| Ficha de filtro, texto | 14 / 400 | `#4E5A55` | `#FFFFFF` | 7,20:1 | 4,5 | sí |
| **Ficha de filtro, borde de control** | 1 px | `#D7D9D3` | `#F6F6F3` | **1,31:1** | 3,0 | **NO** |
| Ficha de filtro activa | 14 / 500 | `#F6F6F3` | `#16211D` | 15,28:1 | 4,5 | sí |
| **Tarjeta de salón, borde** | 1 px | `#D7D9D3` | `#F6F6F3` | **1,31:1** | 3,0 | **NO** |
| Ficha, zona | 15 / 400 | `#4E5A55` | `#FFFFFF` | 7,20:1 | 4,5 | sí |
| Ficha, nota | 13 / 400 | `#4E5A55` | `#FFFFFF` | 7,20:1 | 4,5 | sí |
| Ficha, duración del servicio | 13 / 400 | `#4E5A55` | `#FFFFFF` | 7,20:1 | 4,5 | sí |
| Botón de hora libre, texto | 15 / 400 | `#16211D` | `#FFFFFF` | 16,54:1 | 4,5 | sí |
| **Botón de hora libre, BORDE** | 1 px | `#D7D9D3` | `#FFFFFF` | **1,42:1** | 3,0 | **NO** |
| Hora ocupada (control desactivado) | 15 / 400 | `#4E5A55` | `#F6F6F3` | 6,65:1 | 4,5 | sí |
| Hora elegida, texto | 15 / 600 | `#FFFFFF` | `#C6350A` | 5,36:1 | 4,5 | sí |
| Hora elegida, borde | 1 px | `#C6350A` | `#FFFFFF` | 5,36:1 | 3,0 | sí |
| Leyenda y franja horaria | 13 / 400 | `#4E5A55` | `#FFFFFF` | 7,20:1 | 4,5 | sí |
| Pie, lema | 15 / 400 | `#4E5A55` | `#F6F6F3` | 6,65:1 | 4,5 | sí |
| Pie, enlaces de columna | 15 / 400 | `#4E5A55` | `#F6F6F3` | 6,65:1 | 4,5 | sí |
| Pie, letra legal | 13 / 400 | `#4E5A55` | `#F6F6F3` | 6,65:1 | 4,5 | sí |
| Anexo, dato de muestra | 13 / 400 | `#4E5A55` | `#FFFFFF` | 7,20:1 | 4,5 | sí |
| **Anexo, borde de muestra de color** | 1 px | `#D7D9D3` | `#FFFFFF` | **1,42:1** | 3,0 | **NO** |
| Foco: anillo sobre papel | 2 px | `#C6350A` | `#F6F6F3` | 4,95:1 | 3,0 | sí |
| Foco: anillo dentro del bloque oscuro | 2 px | `#C6350A` | `#16211D` | 3,08:1 | 3,0 | sí (por 0,08) |
| **Foco: anillo contra su propio botón acento** | 2 px | `#C6350A` | `#C6350A` | **1,00:1** | 3,0 | **NO** |

**A: 6 fallos de 39 combinaciones.** Cinco de ellos son el mismo color, `#D7D9D3`, usado en **23 reglas de borde** del documento.

### 2.2 Dirección B — «Bloque de color panameño»

Paleta: cal `#F2F3EF`, blanco `#FFFFFF`, azul `#1636C7`, naranja `#FF7A1F`, tinta `#0D1526`, sobre azul suave `#CBD5F8`, sobre tinta suave `#A8B3C9`, texto suave `#4A5163`, borde tenue `#8A8E85`.

| Combinación | px / peso | Frente | Fondo | Ratio | Mínimo | ¿Pasa? |
|---|---|---|---|---|---|---|
| Texto corrido, tinta sobre cal | 16 / 400 | `#0D1526` | `#F2F3EF` | 16,35:1 | 4,5 | sí |
| Enlaces de la barra | 15 / 500 | `#0D1526` | `#F2F3EF` | 16,35:1 | 4,5 | sí |
| Botón «Entrar» | 15 / 600 | `#F2F3EF` | `#0D1526` | 16,35:1 | 4,5 | sí |
| **Filete naranja de 6 px sobre cal** | 6 px | `#FF7A1F` | `#F2F3EF` | **2,34:1** | 3,0 | **NO** |
| Hero, h1 sobre azul | 32 / 800 | `#F2F3EF` | `#1636C7` | 7,90:1 | 3,0 | sí |
| Hero, antetítulo | 12 / 600 | `#CBD5F8` | `#1636C7` | 6,04:1 | 4,5 | sí |
| Hero, subtítulo | 16 / 400 | `#CBD5F8` | `#1636C7` | 6,04:1 | 4,5 | sí |
| Botón naranja, texto | 16 / 700 | `#0D1526` | `#FF7A1F` | 6,99:1 | 4,5 | sí |
| Botón naranja en `hover` | 16 / 700 | `#FF7A1F` | `#0D1526` | 6,99:1 | 4,5 | sí |
| Botón de línea sobre azul, texto | 16 / 700 | `#F2F3EF` | `#1636C7` | 7,90:1 | 4,5 | sí |
| Botón de línea sobre azul, borde | 2 px | `#F2F3EF` | `#1636C7` | 7,90:1 | 3,0 | sí |
| Botón azul de confirmar | 16 / 700 | `#F2F3EF` | `#1636C7` | 7,90:1 | 4,5 | sí |
| **Sección naranja**, texto de paso | 16 / 400 | `#0D1526` | `#FF7A1F` | 6,99:1 | 4,5 | sí |
| Sección naranja, h2 | 28 / 800 | `#0D1526` | `#FF7A1F` | 6,99:1 | 3,0 | sí |
| Sección naranja, número de paso | 36 / 800 | `#0D1526` | `#FF7A1F` | 6,99:1 | 3,0 | sí |
| Sección naranja, filete de 2 px | 2 px | `#0D1526` | `#FF7A1F` | 6,99:1 | 3,0 | sí |
| Salón, texto sobre azul | 16 / 400 | `#F2F3EF` | `#1636C7` | 7,90:1 | 4,5 | sí |
| Salón, cifra del precio (naranja sobre azul) | 74 / 800 | `#FF7A1F` | `#1636C7` | 3,38:1 | 3,0 | sí |
| Salón, viñeta naranja sobre azul | 14 px | `#FF7A1F` | `#1636C7` | 3,38:1 | 3,0 | sí |
| Salón, nota | 15 / 400 | `#CBD5F8` | `#1636C7` | 6,04:1 | 4,5 | sí |
| Salón, borde de la nota | 2 px | `#CBD5F8` | `#1636C7` | 6,04:1 | 3,0 | sí |
| Mercado, introducción | 16 / 400 | `#4A5163` | `#F2F3EF` | 7,11:1 | 4,5 | sí |
| Ficha, borde de 2 px | 2 px | `#0D1526` | `#F2F3EF` | 16,35:1 | 3,0 | sí |
| Etiqueta «Patrocinado» | 12 / 700 | `#0D1526` | `#FF7A1F` | 6,99:1 | 4,5 | sí |
| Ficha, metadatos | 15 / 400 | `#4A5163` | `#FFFFFF` | 7,93:1 | 4,5 | sí |
| Botón de servicio, borde de control | 2 px | `#8A8E85` | `#FFFFFF` | 3,34:1 | 3,0 | sí |
| Botón de servicio, duración | 14 / 400 | `#4A5163` | `#FFFFFF` | 7,93:1 | 4,5 | sí |
| Servicio elegido, borde azul | 8 px | `#1636C7` | `#FFFFFF` | 8,80:1 | 3,0 | sí |
| Selector de día, borde de control | 2 px | `#8A8E85` | `#FFFFFF` | 3,34:1 | 3,0 | sí |
| Selector de día, etiqueta pequeña | 12 / 600 | `#4A5163` | `#FFFFFF` | 7,93:1 | 4,5 | sí |
| Día elegido, texto | 15 / 700 | `#F2F3EF` | `#1636C7` | 7,90:1 | 4,5 | sí |
| Día elegido, etiqueta | 12 / 600 | `#CBD5F8` | `#1636C7` | 6,04:1 | 4,5 | sí |
| Hora libre, texto | 16 / 700 | `#1636C7` | `#FFFFFF` | 8,80:1 | 4,5 | sí |
| Hora libre, borde de 2 px | 2 px | `#0D1526` | `#FFFFFF` | 18,22:1 | 3,0 | sí |
| Hora elegida | 16 / 700 | `#F2F3EF` | `#1636C7` | 7,90:1 | 4,5 | sí |
| Hora ocupada, texto | 16 / 700 | `#4A5163` | `#F2F3EF` | 7,11:1 | 4,5 | sí |
| **Hora ocupada, borde sobre cal** | 2 px | `#8A8E85` | `#F2F3EF` | **2,996:1** | 3,0 | **NO** (por 0,004) |
| Franja horaria | 13 / 700 | `#4A5163` | `#FFFFFF` | 7,93:1 | 4,5 | sí |
| Pie, texto | 16 / 400 | `#F2F3EF` | `#0D1526` | 16,35:1 | 4,5 | sí |
| Pie, rótulo de columna | 13 / 700 | `#A8B3C9` | `#0D1526` | 8,64:1 | 4,5 | sí |
| Pie, lema | 16 / 400 | `#A8B3C9` | `#0D1526` | 8,64:1 | 4,5 | sí |
| Pie, base legal | 14 / 400 | `#A8B3C9` | `#0D1526` | 8,64:1 | 4,5 | sí |
| Anexo, cifras del specimen | 20 / 700 | `#FF7A1F` | `#0D1526` | 6,99:1 | 3,0 | sí |
| Anexo, pesos | 14 / 400 | `#A8B3C9` | `#0D1526` | 8,64:1 | 4,5 | sí |
| Foco: `currentColor` tinta sobre cal | 3 px | `#0D1526` | `#F2F3EF` | 16,35:1 | 3,0 | sí |
| Foco: `currentColor` cal sobre azul | 3 px | `#F2F3EF` | `#1636C7` | 7,90:1 | 3,0 | sí |
| Foco: `currentColor` tinta sobre naranja | 3 px | `#0D1526` | `#FF7A1F` | 6,99:1 | 3,0 | sí |
| Foco: en botón de hora | 3 px | `#1636C7` | `#FFFFFF` | 8,80:1 | 3,0 | sí |
| Foco: en hora ocupada | 3 px | `#4A5163` | `#F2F3EF` | 7,11:1 | 3,0 | sí |
| **Foco: botón naranja dentro del bloque azul** | 3 px | `#0D1526` | `#1636C7` | **2,07:1** | 3,0 | **NO** |

**B: 3 fallos de 50 combinaciones.** Y con un detalle que conviene decir en voz alta: **B declara en su propio CSS «3.00:1» para `--borde-tenue` sobre cal. El valor real es 2,9963:1.** Redondear un fallo hasta convertirlo en aprobado es exactamente la clase de número que esta auditoría existe para cazar. Es minúsculo, pero está mal escrito.

### 2.3 Dirección C — «Herramienta afilada»

Paleta: papel `#FFFFFF`, retícula `#F4F5F6`, filete `#DDE0E3`, cota `#878E95`, grafito `#4E555C`, tinta `#101418`, bermellón `#CE300A`, tinta suave `#C7CCD1`.

| Combinación | px / peso | Frente | Fondo | Ratio | Mínimo | ¿Pasa? |
|---|---|---|---|---|---|---|
| Texto corrido | 16 / 400 | `#101418` | `#FFFFFF` | 18,50:1 | 4,5 | sí |
| Titular h1 | 30 / 600 | `#101418` | `#FFFFFF` | 18,50:1 | 3,0 | sí |
| Párrafo secundario | 15 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Cota mono en versalitas | 11 / 500 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Ceja de portada | 11 / 500 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Bajada de portada | 16 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Botón secundario, texto | 15 / 600 | `#101418` | `#FFFFFF` | 18,50:1 | 4,5 | sí |
| Botón secundario, borde | 1 px | `#101418` | `#FFFFFF` | 18,50:1 | 3,0 | sí |
| Botón principal, texto | 15 / 600 | `#FFFFFF` | `#CE300A` | 5,18:1 | 4,5 | sí |
| Botón principal en `hover` | 15 / 600 | `#FFFFFF` | `#B32808` | 6,51:1 | 4,5 | sí |
| Cinta de cifras, rótulo | 12 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| **Cinta de cifras, filetes** | 1 px | `#DDE0E3` | `#FFFFFF` | **1,33:1** | 3,0 | **NO** |
| Pie de foto | 11 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Ledger, descripción | 14,5 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Pieza, rótulo | 10 / 400 | `#4E555C` | `#F4F5F6` | 6,93:1 | 4,5 | sí |
| Pieza, cifra | 13 / 400 | `#101418` | `#F4F5F6` | 16,95:1 | 4,5 | sí |
| Minihoras ocupadas | 12,5 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Minihoras, borde cota sobre retícula | 1 px | `#878E95` | `#F4F5F6` | 3,04:1 | 3,0 | sí |
| Minihoras libres | 12,5 / 500 | `#CE300A` | `#FFFFFF` | 5,18:1 | 4,5 | sí |
| Tabla de cifras, encabezado | 14,5 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Tabla de cifras, valor | 16 / 500 | `#101418` | `#FFFFFF` | 18,50:1 | 4,5 | sí |
| Datos de ficha | 13 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Tabla de servicios, encabezado mono | 10 / 500 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Tabla de servicios, duración | 14 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Servicio elegido, texto | 15 / 400 | `#101418` | `#F4F5F6` | 16,95:1 | 4,5 | sí |
| Servicio elegido, marca bermellón | 7 px | `#CE300A` | `#F4F5F6` | 4,75:1 | 3,0 | sí |
| Hora libre, texto | 14 / 500 | `#CE300A` | `#FFFFFF` | 5,18:1 | 4,5 | sí |
| Hora libre, borde de control | 1 px | `#CE300A` | `#FFFFFF` | 5,18:1 | 3,0 | sí |
| Hora libre, borde contra el filete de la rejilla | 1 px | `#CE300A` | `#DDE0E3` | 3,91:1 | 3,0 | sí |
| Hora elegida | 14 / 500 | `#FFFFFF` | `#CE300A` | 5,18:1 | 4,5 | sí |
| Hora ocupada (desactivada) | 14 / 400 | `#4E555C` | `#F4F5F6` | 6,93:1 | 4,5 | sí |
| Leyenda, texto | 11 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| **Leyenda, muestra «OCUPADA», borde** | 9 px | `#DDE0E3` | `#FFFFFF` | **1,33:1** | 3,0 | **NO** |
| **Leyenda, muestra «OCUPADA», relleno** | 9 px | `#F4F5F6` | `#FFFFFF` | **1,09:1** | 3,0 | **NO** |
| Leyenda, muestra «LIBRE» | 9 px | `#CE300A` | `#FFFFFF` | 5,18:1 | 3,0 | sí |
| Resumen de reserva | 14 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Agenda, subtítulo del día | 10 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Agenda, flechas ‹ › texto | 14 / 400 | `#101418` | `#FFFFFF` | 18,50:1 | 4,5 | sí |
| **Agenda, BORDE de las flechas** | 1 px | `#DDE0E3` | `#FFFFFF` | **1,33:1** | 3,0 | **NO** |
| Agenda, KPI valor | 14 / 500 | `#101418` | `#F4F5F6` | 16,95:1 | 4,5 | sí |
| Agenda, KPI rótulo | 9 / 400 | `#4E555C` | `#F4F5F6` | 6,93:1 | 4,5 | sí |
| Agenda, servicio de la cita | 12,5 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Agenda, importe de la cita | 12,5 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Agenda, estado neutro, texto | 9,5 / 500 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| **Agenda, estado neutro, BORDE** | 1 px | `#DDE0E3` | `#FFFFFF` | **1,33:1** | 3,0 | **NO** |
| Agenda, estado firme | 9,5 / 500 | `#101418` | `#FFFFFF` | 18,50:1 | 4,5 | sí |
| Agenda, hueco libre, cifra | 14 / 500 | `#CE300A` | `#FFFFFF` | 5,18:1 | 4,5 | sí |
| Agenda, hueco libre, texto | 12,5 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Agenda, botón «Ofrecer esta hora» | 12,5 / 600 | `#FFFFFF` | `#CE300A` | 5,18:1 | 4,5 | sí |
| Agenda, bloqueo de almuerzo | 13 / 400 | `#4E555C` | `#F4F5F6` | 6,93:1 | 4,5 | sí |
| Mapa de ocupación, barra ocupada | 17 px | `#101418` | `#FFFFFF` | 18,50:1 | 3,0 | sí |
| Mapa de ocupación, regla horaria | 9 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Mapa de ocupación, nombre | 11,5 / 400 | `#101418` | `#FFFFFF` | 18,50:1 | 4,5 | sí |
| **Mapa de ocupación, filetes internos** | 1 px | `#DDE0E3` | `#FFFFFF` | **1,33:1** | 3,0 | **NO** |
| Mapa de ocupación, pie | 10 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Notas de diseño | 14 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Pie, enlaces | 14 / 400 | `#C7CCD1` | `#101418` | 11,44:1 | 4,5 | sí |
| Pie, rótulo de columna | 10 / 500 | `#FFFFFF` | `#101418` | 18,50:1 | 4,5 | sí |
| **Pie, filete divisor** | 1 px | `#3A4048` | `#101418` | **1,77:1** | 3,0 | **NO** |
| Pie, línea legal | 10,5 / 400 | `#9AA1A8` | `#101418` | 7,08:1 | 4,5 | sí |
| Anexo, uso de paleta | 13 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Anexo, borde de muestra | 1 px | `#878E95` | `#FFFFFF` | 3,32:1 | 3,0 | sí |
| Anexo, escala tipográfica | 12 / 400 | `#4E555C` | `#FFFFFF` | 7,56:1 | 4,5 | sí |
| Foco: anillo sobre papel | 2 px | `#CE300A` | `#FFFFFF` | 5,18:1 | 3,0 | sí |
| Foco: anillo sobre el pie | 2 px | `#CE300A` | `#101418` | 3,57:1 | 3,0 | sí |
| Foco: anillo sobre retícula | 2 px | `#CE300A` | `#F4F5F6` | 4,75:1 | 3,0 | sí |
| **Foco: anillo contra su propio botón principal** | 2 px | `#CE300A` | `#CE300A` | **1,00:1** | 3,0 | **NO** |

**C: 8 fallos de 67 combinaciones.** Siete de ellos son el mismo color, `#DDE0E3`, usado en **32 reglas de borde** más **4 como relleno de rejilla**.

---

## 3. El resto de hallazgos, por propuesta

### 3.1 Dirección A — «Editorial de barrio»

| Hallazgo | Medida | Gravedad | Arreglo |
|---|---|---|---|
| Toda la estructura se dibuja con un filete que no llega ni a la mitad del mínimo | `#D7D9D3` sobre papel **1,31:1** y sobre blanco **1,42:1**, en **23 reglas de borde**; el mínimo para un borde de control es 3:1 | **descalifica** | Partir la variable en dos: `--filete-deco:#D7D9D3` para separadores puramente ornamentales y `--filete-control:#878F8B` (3,06:1 sobre papel, 3,32:1 sobre blanco) para los bordes de los botones de hora, las fichas de filtro y la tarjeta |
| No hay landmark principal | `<main>` = **0**. Un lector de pantalla no puede saltar al contenido | grave | Envolver de `<section class="hero">` a la ficha en un `<main id="contenido">` |
| No hay enlace de salto | `a[href^="#"]` en `body` = **0**. Con teclado hay que recorrer 33 destinos antes del contenido | grave | Copiar el `.saltar` de B, que ya está resuelto |
| El anillo de foco desaparece sobre el botón que más importa | anillo `#C6350A` sobre botón `#C6350A` = **1,00:1** (el `outline-offset:3px` lo separa 3 px, pero el ojo ve rojo junto a rojo) | grave | `.btn-acento:focus-visible{outline-color:var(--tinta)}` → 15,28:1 contra el papel y 3,08:1 contra el propio achiote |
| El anillo de foco en el bloque oscuro pasa por 0,08 | `#C6350A` sobre `#16211D` = **3,08:1** frente a un mínimo de 3,00 | menor | Usar `--papel` como color de anillo dentro de `.oscuro`: 15,28:1 |
| Salto en la jerarquía de encabezados | secuencia `1 2 3 3 3 2 2 3 4 4 4 4 4 **2 → 4**`: del h2 «Anexo. Paleta y tipografía» se cae directamente a h4 | menor | Los nombres de las muestras de color a `h3`, o a `<p>` con `<b>` si no son secciones |
| Objetivos táctiles del pie y de la barra | **15 de 33** pulsables por debajo de 44 px; enlaces del pie a **19 px**, logotipo a **25,5 px**, «Entrar» a **37 × 43,4 px** | grave | Ver 1.2 |
| Seis fotos, ninguna diferida | 6 imágenes, `loading="lazy"` en **0**, `srcset` en **0**; **493 651 B** medidos, el mayor número de peticiones de imagen de las tres | grave | `loading="lazy"` en las cinco que no están en el primer pliegue y `srcset` con anchos de 350, 700 y 1050 px |
| El propio anexo declara un número que no es | dice «tinta sobre papel **16,4:1**»; el valor real es **15,28:1**, un 7,3 % inflado | menor | Corregir el texto. Los otros dos números que declara (7,2:1 y 5,4:1) sí son exactos |
| La navegación pierde dos destinos en móvil | `.solo-ancho{display:none}` esconde «Categorías» y «Para tu salón» a 390 px, y no hay menú que los sustituya | menor | Están duplicados en el pie, así que es tolerable; aun así, conviene un menú o llevarlos a la barra |
| Filete de la lista del bloque oscuro | `#33403B` sobre `#16211D` = **1,53:1**; las seis ventajas del salón quedan sin separación visible | menor | Subir a `#4A5A54` o suprimir el filete y separar con espacio |
| Movimiento | **0 transiciones, 0 animaciones, 0 `scroll-behavior`**. No hay `prefers-reduced-motion`, pero tampoco hace falta | — | Sin acción |
| Estado «ocupada» de la hora | `disabled` + tachado. El tachado es una segunda señal además del color, correcto, pero no hay texto alternativo explícito | menor | Añadir `<span class="oculto">, ocupada</span>` como hace B |

### 3.2 Dirección B — «Bloque de color panameño»

| Hallazgo | Medida | Gravedad | Arreglo |
|---|---|---|---|
| El anillo de foco se apaga en los dos botones más importantes | los `.btn--naranja` («Buscar salón cerca», «Registrar mi salón») viven sobre el bloque azul; su `currentColor` es tinta, y el anillo cae sobre el azul: `#0D1526` sobre `#1636C7` = **2,07:1** | grave | `.btn--naranja:focus-visible{outline-offset:0}` para que el anillo tinta se dibuje sobre el propio naranja (6,99:1), o `outline-color:var(--cal)` (7,90:1 sobre azul) |
| El borde de control se queda a cuatro milésimas | `--borde-tenue:#8A8E85` sobre cal = **2,9963:1**. El CSS lo documenta como «3.00:1» | menor | `--borde-tenue:#888C83` → 3,08:1 sobre cal y 3,43:1 sobre blanco, sin cambio visible |
| El filete naranja de 6 px sobre cal | `#FF7A1F` sobre `#F2F3EF` = **2,34:1** | menor | Es decorativo (canto de bloque, no separa información), así que no bloquea; si se quiere que también funcione como separador, subir a 8 px o rematar con 1 px de tinta |
| Objetivos táctiles del pie y de la barra | **17 de 44** por debajo de 44 px; enlaces del pie a **16 px**, el peor de los tres; logotipo a **26 px** | grave | Ver 1.2 |
| Carrusel de días recortado | `button.dia` del quinto día se sale a **399 px** dentro de `.dias{overflow-x:auto}`. No provoca scroll de página, pero el día queda cortado sin señal de que hay más | menor | Está mitigado con `scroll-snap-type`; añadir un degradado o un `padding-inline-end` que deje asomar media ficha ya lo hace evidente |
| Un solo archivo de fuente, pero el más pesado de los tres | Archivo variable, **1 fichero de 90 096 B** (frente a 66 828 B en 2 de A y 70 472 B en 4 de C) | menor | Es un intercambio razonable: 2 peticiones de fuente frente a 3 y 5. Si se quiere bajar, subsetear a latín y a los dos ejes usados |
| Reserva tipográfica que descuadra al cargar | pila `'Archivo','Helvetica Neue',Helvetica,Arial`. Con `font-stretch:112–125%` y `font-synthesis-weight:none`, mientras Archivo no llega los titulares se pintan en Arial 700 y saltan al aterrizar | menor | Añadir `size-adjust` en una `@font-face` de reserva, o aceptar el salto (`display=swap` ya está puesto) |
| Tres fotos, ninguna diferida | 3 imágenes, `lazy` en **0**, `srcset` en **0**; la de portada se sirve a 1200 × 1500 y se pinta a 390 × 239 CSS px (**2,1× los píxeles necesarios** a DPR 3) | grave | `loading="lazy"` en las dos que no son portada y `srcset` |
| Textos alternativos que dicen «marcador de posición» | los 3 `alt` empiezan por «Marcador de posición…». Correcto para una maqueta, inválido para producción | menor | Dejar la descripción sola al pasar a producto |
| Lo que hace bien y hay que copiar | único con `<main>`, único con enlace de salto (48 px de alto), único con `@media (prefers-reduced-motion:reduce)`, único que da texto alternativo al estado ocupado (`<span class="oculto">, ocupado</span>`), jerarquía de encabezados **sin un solo salto** (`1 2 3 3 3 2 2 3 4 4 4 2`), y **cero texto por debajo de 12 px** | — | — |

### 3.3 Dirección C — «Herramienta afilada»

| Hallazgo | Medida | Gravedad | Arreglo |
|---|---|---|---|
| Nueve botones falsos en la agenda del salón | **9** `<div class="cita" tabindex="0" role="button">` y **0** `<script>` en todo el archivo. Se anuncian como botón, reciben el foco y **no hacen nada con Enter ni con Espacio** | **descalifica** | `<button type="button" class="cita">` de verdad, o quitar `role`/`tabindex` mientras sea maqueta. Un botón que anuncia que es botón y no responde es peor que un div |
| Tipografía por debajo del umbral de lectura de calle | **169** nodos de texto por debajo de 14 px, de ellos **16 a 9 px** (regla horaria del mapa), **9 a 9,5 px** (estados de la cita) y **28 entre 10 y 10,5 px**. Comparación: A tiene 35 nodos, mínimo 11 px; B tiene 14, mínimo 12 px | **descalifica** | Suelo de 12 px para cualquier texto informativo y de 14 px para lo que se lee de pie. Los estados («Confirmada», «No vino») a 12 px como mínimo: son la información que se busca al abrir la pantalla |
| La misma enfermedad estructural que A, más extendida | `#DDE0E3` a **1,33:1**, en **32 reglas de borde** más **4 como relleno de rejilla**. Toda la «retícula visible» de la dirección es invisible bajo reflejo | **descalifica** | Ya tiene el color correcto en la paleta: `--cota:#878E95` da 3,32:1 sobre papel y 3,04:1 sobre retícula. Usarlo en todo borde que separe información y dejar `#DDE0E3` solo para lo ornamental |
| La clave de la leyenda no se ve | la muestra «OCUPADA» es relleno `#F4F5F6` (**1,09:1**) con borde `#DDE0E3` (**1,33:1**) sobre blanco. Es una **leyenda**: su único trabajo es distinguirse | grave | Darle el mismo tachado que llevan las celdas ocupadas, y borde `--cota` |
| Controles de producto por debajo de 44 px | flechas de día **34 × 34 px** (×2) y «Ofrecer esta hora» **38,8 px** de alto. No son enlaces de pie: son los dos gestos que el salón repite «40 veces al día» según su propio texto | grave | 44 px de caja en las flechas y 44 px en el botón del hueco |
| Objetivos táctiles en total | **23 de 59** por debajo de 44 px; enlaces del pie a **18 px**, logotipo a **22 px**, «Entrar» a **35 px** | grave | Ver 1.2 |
| Dos saltos en la jerarquía de encabezados | secuencia `1 2 3 3 3 2 2 3 4 4 **2 → 4** 5 5 5 5 **2 → 4**` | menor | «Por qué está dibujada así» y «Tipografía» a `h3` |
| Sin enlace de salto | `a[href^="#"]` en `body` = **0**, con **59** destinos enfocables y una barra fija | grave | Añadirlo |
| El anillo de foco desaparece sobre el botón principal | anillo `#CE300A` sobre botón `#CE300A` = **1,00:1** | grave | `.boton--principal:focus-visible{outline-color:var(--tinta)}` → 18,50:1 sobre papel |
| Filete divisor del pie | `#3A4048` sobre `#101418` = **1,77:1** | menor | Subir a `#4E555C` (2,55) o mejor a `#6C737A` |
| Desplazamiento suave sobre 7 944 px | `scroll-behavior:smooth` en `html`, con barra fija y un documento de 7 944 px. Sí está protegido por `@media (prefers-reduced-motion:reduce)` | menor | Bien protegido. En gama media, una animación de scroll de 7 944 px suelta fotogramas; considerar quitarla del todo |
| Lo que hace bien y hay que copiar | **la más ligera con diferencia** (211 374 B de red frente a 545 069 y 571 393), **única con `loading="lazy"` en las 3 imágenes**, y **única con reserva tipográfica de métrica segura**: `system-ui` y `ui-monospace`, es decir, la única cuya columna de horas sigue alineada mientras la fuente viaja por 3G | — | — |

---

## 4. Comparativa final

| | **A · Editorial de barrio** | **B · Bloque de color** | **C · Herramienta afilada** |
|---|---|---|---|
| **Fallos de contraste** | **6** de 39 | **3** de 50 | **8** de 67 |
| — de los cuales, bordes de control | 4 (todos `#D7D9D3`) | 1 (por 0,004) | 5 (todos `#DDE0E3`) |
| Reglas de borde por debajo de 3:1 | **23** | **0** (3 reglas a 3,0–3,3 y 16 a 16,35) | **32** + 4 rellenos |
| **Desplazamiento horizontal a 390 px** | **no** (`scrollWidth` = 390) | **no** (390; un `.dia` asoma a 399 dentro de un carrusel con `overflow-x:auto`) | **no** (390) |
| **Peticiones de fuente** | **3** (1 CSS + 2 archivos) | **2** (1 CSS + 1 archivo) | **5** (1 CSS + 4 archivos) |
| Familias / pesos declarados | **2 familias**, 6 pesos | **1 familia** variable, 2 ejes | **2 familias**, 6 pesos |
| Bytes de fuente | 66 828 B | **90 096 B** | 70 472 B |
| **Bytes de HTML** | **28 565** | **33 663** | **57 425** |
| Peticiones totales | 16 | **9** | 12 |
| Imágenes | 6, 0 diferidas | 3, 0 diferidas | **3, las 3 diferidas** |
| Bytes de red medidos | 571 393 | 545 069 | **211 374** |
| **Total con HTML** | 599 958 B | 578 732 B | **268 799 B** |
| Tiempo de transferencia, 3G lento (400 kbit/s) | **11,7 s** | **11,3 s** | **5,2 s** |
| Tiempo de transferencia, 3G rápido (1,6 Mbit/s) | 2,9 s | 2,8 s | **1,3 s** |
| **Foco visible** | sí, 2 px `#C6350A` (falla sobre su propio botón) | **sí, 3 px `currentColor`, el mejor** (falla en el botón naranja sobre azul) | sí, 2 px `#CE300A` (falla sobre su propio botón) |
| `<main>` | **no** | sí | sí |
| Enlace de salto | **no** | **sí** | **no** |
| Saltos de encabezado | 1 | **0** | 2 |
| Texto por debajo de 14 px | 35 nodos (mín. 11 px) | **14 nodos (mín. 12 px)** | **169 nodos (mín. 9 px)** |
| Campos de formulario | 0 | 0 | 0 |
| Texto sobre foto | 0 | 0 | 0 |
| `alt` en imágenes | 6/6 descriptivos | 3/3 (dicen «marcador de posición») | 3/3 descriptivos |
| SVG sin etiqueta accesible | 0 | 0 | 0 |
| Animaciones | 0 | 1 transición, **protegida** | 1 desplazamiento suave, **protegido** |
| `prefers-reduced-motion` | no (no hace falta) | **sí** | **sí** |
| Controles < 44 px | 15/33 (45 %) | 17/44 (39 %) | 23/59 (39 %), **3 de ellos de producto** |

---

## 5. Veredicto

### A · Editorial de barrio — **rechazada**

No por una lista de defectos sueltos, sino porque **su idea central es el defecto**. El anexo lo dice con todas las letras: «filetes de 1 px en vez de sombras». Ese filete es `#D7D9D3`, mide **1,31:1** sobre el papel y **1,42:1** sobre la ficha, y sostiene **23 reglas de borde**: los bordes de las doce celdas de hora, el contorno de la tarjeta del salón, las fichas de filtro, la separación de los servicios. Un borde de control necesita 3:1. Este se queda en menos de la mitad, y en la calle no se queda corto: desaparece. La clienta no verá dónde termina una hora y empieza la siguiente; verá una columna de números flotando.

A eso se suma que es la única sin `<main>` y sin enlace de salto, que su anillo de foco se anula sobre el botón que reserva (1,00:1), y que declara un contraste de 16,4:1 donde el real es 15,28:1. Arreglar el filete es un cambio de una línea; asumir que la dirección se llama «filetes de 1 px» y que esos filetes tienen que ser tres veces más oscuros de lo que están, es un cambio de dirección.

### B · Bloque de color panameño — **aceptable con condiciones**

Es la única de las tres cuya estructura no depende de que la pantalla se vea bien. El bloque de color **es** la estructura: azul, naranja, cal y tinta, con filetes de 2 px en tinta a **16,35:1**. Cuando el sol borre las diferencias sutiles, aquí no hay diferencias sutiles que borrar. Tiene la jerarquía de encabezados sin un solo salto, el único enlace de salto, `<main>` correctamente puesto, el único texto alternativo para el estado «ocupado», el mejor sistema de foco de las tres (`currentColor` a 3 px, que se adapta solo a cada bloque de color) y **ningún texto por debajo de 12 px**. Tres fallos de contraste en 50 combinaciones, y dos de ellos son ornamentales.

**Condiciones para aprobarla, todas de una línea:**

1. `.btn--naranja:focus-visible{outline-offset:0}` — hoy el anillo cae sobre el azul a **2,07:1** en los dos botones que más se pulsan.
2. `--borde-tenue:#888C83` — de 2,9963:1 a 3,08:1 sobre cal. Y corregir el comentario del CSS, que redondea un fallo a «3.00:1».
3. `padding-block:13px` en los `<a>` del pie y del logotipo — 17 de 44 pulsables están por debajo de 44 px, y los del pie a 16 px son los peores de las tres propuestas.
4. `loading="lazy"` y `srcset` en las tres fotos — la de portada se sirve al doble de píxeles de los que se pintan, y es lo que la lleva a 11,3 s en 3G lento.
5. Entregar el campo de búsqueda y el de teléfono con `font-size:16px` y `<label>` visible antes de dar la dirección por cerrada.

### C · Herramienta afilada — **rechazada**

Duele, porque es la mejor construida en todo lo que se mide con un cronómetro: **268 799 B contra 578 732 y 599 958**, la única que difiere las tres imágenes, la única cuya reserva tipográfica (`system-ui` y `ui-monospace`) mantiene recta la columna de horas mientras la fuente viaja. En 3G lento carga en **5,2 s** frente a los 11 s largos de las otras dos. Su rejilla de horas es, medida, la más informativa de las tres.

Y aun así se cae por tres cosas que no son de opinión:

1. **Nueve `<div role="button" tabindex="0">` sin una sola línea de JavaScript.** Nueve elementos que se anuncian como botón, se enfocan como botón y no responden ni a Enter ni a Espacio. Es la agenda del salón, la pantalla que su propio texto dice que se abre 40 veces al día.
2. **169 nodos de texto por debajo de 14 px, 16 de ellos a 9 px y 9 a 9,5 px.** Los estados de la cita —«Confirmada», «Pendiente», «No vino»— están a 9,5 px en mayúsculas con tracking. Es literalmente la información que se va a buscar, dibujada al tamaño más pequeño de la página. Doce veces más texto diminuto que B.
3. **La misma retícula invisible que A, pero peor: 32 reglas de borde a 1,33:1.** Y con una vuelta de tuerca: la propia leyenda que explica qué es una hora ocupada usa una muestra de **1,09:1**. Es un elemento cuyo único trabajo es distinguirse y no se distingue.

Lo tercero se arregla con `--cota`, que ya está en su paleta. Lo primero, con `<button>`. Lo segundo obliga a rehacer la escala tipográfica entera, que es la dirección misma. **Su perfil de carga, en cambio, es el que hay que trasplantar a la ganadora.**

---

## 6. Mediodía en Vía Argentina

**Solo B aguanta**, y por una razón que no es de gusto: cuando el reflejo del sol levanta el negro de la pantalla y aplasta el rango de contraste, lo primero que se va son las diferencias pequeñas. **A dibuja su estructura con 23 líneas a 1,31:1 y C con 32 líneas a 1,33:1; B la dibuja con 16 líneas de 2 px a 16,35:1 y con bloques de color a sangre.** A y C se quedarán con los números flotando sin caja alrededor; B seguirá teniendo un rectángulo azul, un rectángulo naranja y una cuadrícula de bordes negros de 2 px, que es exactamente lo que se necesita para tocar la hora correcta a la primera, de pie, con una mano y el sol de frente.
