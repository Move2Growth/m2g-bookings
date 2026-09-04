# Dirección 2 · «Revista de oficio» · Estado: propuesta, sin validar

**Prototipo:** [`direccion-2.html`](direccion-2.html). Se abre en el navegador, no necesita servidor
ni conexión salvo para las fuentes. Navega entre cinco pantallas sin recargar (`#/portada`,
`#/buscar`, `#/salon`, `#/agenda`, `#/consola`).

---

## 1. La idea en una frase

Bukeo no es una app de tecnología: es el **catálogo impreso del oficio de la belleza en Panamá**.
Papel con cuerpo, filetes finos, folios en las esquinas, una tipografía de portada de revista y la
información puesta como se pone en una publicación seria: jerarquía por tamaño y por aire, no por
cajitas de colores. La clienta lee un reportaje sobre salones; el salón lee su cuaderno de citas.

Por qué esta dirección y no otra: el producto vende **verdad** (horas reales, patrocinados
marcados, precio a la vista). La estética de plantilla SaaS, con tarjetas redondeadas y degradados,
promete lo contrario: promete «experiencia». Una revista de oficio promete **datos comprobables**,
que es exactamente lo que el brief dice en la copia («Horas reales, no una solicitud»).

## 2. Paleta

Familia elegida: **verde profundo con hueso**, con lápiz rojo de corrector y marcador amarillo.
Ni beige con latón ni naranja con azul.

| Nombre | Hex | Para qué |
|---|---|---|
| Verde tinta | `#0F2A20` | Texto principal, planchas oscuras, filetes, sellos |
| Verde monte | `#1E5140` | Sombra dura de los botones, segundo plano oscuro |
| Verde claro | `#8FBFA6` | Texto de apoyo **solo sobre verde tinta** |
| Gris verde | `#3F5148` | Texto secundario sobre papel |
| Hueso | `#F1EBDD` | Papel base de toda la aplicación |
| Hueso claro | `#FAF7F0` | Papel montado encima: fichas, boletas, cabecera |
| Rojo lápiz | `#A32E1E` | Marca de corrección: patrocinado, avisos, «falta para publicar» |
| Amarillo marcador | `#E8B93F` | La hora elegida. **Nunca es color de texto** |

El verde no es decorativo: sale de las dos únicas fotos que existen (las plantas y el bambú del
spa, el esmalte oscuro del bote de uñas). El papel hueso lleva un grano de ruido SVG al 5,5 %, que
es textura de imprenta, no un degradado.

### Contraste, medido con la fórmula WCAG

Pares que se usan de verdad en las cinco pantallas:

| Texto sobre fondo | Ratio | Mínimo AA |
|---|---|---|
| Verde tinta sobre hueso claro | **14,30:1** | 4,5 |
| Verde tinta sobre hueso | **12,87:1** | 4,5 |
| Hueso claro sobre verde tinta | **14,30:1** | 4,5 |
| Verde tinta sobre amarillo marcador | **8,34:1** | 4,5 |
| Hueso claro sobre verde monte | **8,51:1** | 4,5 |
| Gris verde sobre hueso claro | **7,91:1** | 4,5 |
| Verde claro sobre verde tinta | **7,41:1** | 4,5 |
| Gris verde sobre hueso | **7,12:1** | 4,5 |
| Hueso claro sobre rojo lápiz | **6,62:1** | 4,5 |
| Rojo lápiz sobre hueso claro | **6,62:1** | 4,5 |
| Rojo lápiz sobre hueso | **5,95:1** | 4,5 |

**El peor caso real es 5,95:1**, el rojo del lápiz sobre papel. No hay un solo texto por debajo de
AA. Está medido en pantalla, no en la paleta: `scripts/revision-3-direccion-2.mjs` recorre las
cinco pantallas a 390 y a 1440, mira el color ya calculado de cada nodo de texto y el fondo real
del primer antepasado que tenga uno, y sale con error si algo baja de 4,5 (o de 3 en texto grande).
Última pasada: **666 textos medidos, cero fallos**.

Dos combinaciones quedan prohibidas por escrito: **verde claro sobre verde monte** (4,41:1) y
**gris verde sobre amarillo** (3,93:1). No aparecen en el prototipo.

## 3. Tipografía

Tres familias, como una revista: una para la portada, una para leer, una para los datos.

| Papel | Familia | Por qué |
|---|---|---|
| Display | **Bodoni Moda** | Una didone de verdad, con el contraste grueso y fino que hace las cabeceras de revista. Tiene cursiva con carácter y eje óptico variable, así que a 90 px afina y a 24 px no se rompe. Da personalidad sin disfraz: no es una geométrica más. |
| Texto | **Newsreader** | Serif de lectura pensada para pantalla, con eje óptico. Casa con la Bodoni sin competir y sostiene párrafos largos a 390 px, que es donde vive esto. |
| Dato | **Courier Prime** | Mecanografiada. Las horas, los precios y los rótulos son **datos de un formulario**, y se ven como tales: `$28.00`, `10:30`, `OCUPADO`. Además alinea en columna sin esfuerzo en la agenda y en la consola. |

Ninguna de las tres está en la lista vetada. Las tres se cargan de Google Fonts con pila de
respaldo (Didot, Georgia, Courier New), así que el documento no se cae sin conexión.

Escala: el titular es `clamp(2,5rem, 7,2vw, 5,6rem)`, el cuerpo 17 px en escritorio y 16 px en
móvil, y los rótulos mecanografiados 0,68 a 0,82 rem con `letter-spacing` abierto. El salto entre
display y cuerpo es deliberadamente brutal: eso es lo que hace que parezca una página maquetada y
no una interfaz.

## 4. Retícula y papel

- Doce columnas con reparto **asimétrico**: 8/4 en las portadas, 5/7 en la ficha del salón, 7/5 en
  la consola. Nunca dos mitades iguales.
- Márgenes generosos (`clamp(18px, 5vw, 72px)`) y aire vertical grande entre bloques.
- Cada pantalla abre con un **rótulo de sección con filete** («TRES · FICHA DEL SALÓN ____ OBARRIO»)
  y cierra con un **pie de revista** con el número de página. Eso es lo que da la sensación de
  cuaderno, y de paso orienta.
- Las fotos van con **filete de dos píxeles, número de figura y pie**, como en una publicación. Solo
  existen dos fotos reales y se usan dos veces cada una. Donde no hay foto se resuelve con
  tipografía grande, filetes y planchas de tinta: ni un placeholder gris.
- Nada tiene radio: `border-radius: 0` está puesto en el `*`. Las profundidades son **desplazamientos
  duros** (5 px, sin desenfoque), que son registros de impresión, no sombras.
- A 390 px la retícula colapsa a una columna, la tabla de la consola se convierte en fichas con su
  rótulo delante de cada dato, y la agenda pasa de tres columnas de profesional a una, con un
  selector arriba. Comprobado: `scrollWidth` es exactamente 390 en las cinco pantallas, no hay
  desbordamiento horizontal.

## 5. Movimiento

Regla única: **cada animación dice de dónde viene algo, que se ha tocado, o que hay que esperar.
Nada se repite, nada se mueve solo.** No hay ni un `infinite` en el archivo.

| Gesto | Qué hace | Qué dice |
|---|---|---|
| Paso de página | Al cambiar de pantalla, un canto de papel de 120 px cruza el ancho en 420 ms y la sección nueva entra desplazada 26 px | «Has pasado de página», que es literalmente la metáfora del producto |
| Titular en dos tiempos | Las líneas suben desde su propia caja recortada: primero el enunciado (con 70 ms entre líneas), y tras una pausa el remate en cursiva, a 280 ms | Ordena la lectura: primero qué es, luego dónde |
| Entrada de apoyo | Bajada, botones y columna lateral aparecen a 340 ms, después del titular | Jerarquía: lo importante llega antes |
| Horas libres | Cada hueco aparece con 28 ms de retardo entre sí y **su raya se dibuja después**, de izquierda a derecha | Es un formulario que alguien rellena a mano. Dice «esto se acaba de consultar» y que las horas son de ahora |
| Botones | Al pulsar se desplazan 5 px y la sombra dura se cierra bajo ellos | Gesto físico: la tecla baja. Se nota que se ha tocado |
| Chips y horas | 1 px de desplazamiento al pulsar | Lo mismo, en pequeño |
| Subrayado del sumario | El trazo rojo se dibuja de izquierda a derecha, 260 ms | «Estás aquí», y de dónde vienes |
| Carga | Las rayas del formulario se rellenan una vez, con retardo entre ellas, y el contenido las sustituye | Hay que esperar, y esto tarda lo que tarda una consulta, no un bucle infinito |
| Confirmación | La plancha verde entra desde abajo, una sola vez | Ha pasado algo nuevo y es el resultado de lo que acabas de pulsar |

Duraciones entre 90 ms (pulsación) y 500 ms (titular), todas con la misma curva
`cubic-bezier(.2,.7,.2,1)`.

**`prefers-reduced-motion: reduce`** apaga todo: las animaciones y transiciones caen a 0,001 ms, el
canto de página desaparece, los titulares nacen en su sitio y el rellenado de horas se salta desde
el JavaScript, que consulta la media query. Los estados de carga siguen apareciendo, porque son
información, pero se resuelven al instante. Comprobado con `reducedMotion: 'reduce'` en Playwright:
titular con `transform: matrix(1,0,0,1,0,0)` y las once horas del día pintadas.

## 6. Estados, pantalla por pantalla

Ninguna pantalla enseña solo el caso bonito:

| Pantalla | Estados que se ven |
|---|---|
| Portada | Zona sin salones todavía (Juan Díaz, sin inventar cifras) |
| Buscar | **Carga** al entrar (rayas rellenándose) y **vacío** real: el filtro «Antes de las 8:00» deja la búsqueda sin resultados, con salida para quitar el filtro |
| Salón | Huecos **ocupados** tachados; al pulsar uno salta «Ese horario se acaba de ocupar»; el domingo es un **día sin huecos**; el botón inactivo es una casilla sin rellenar, no un botón desvaído; y la **confirmación** con su número de reserva |
| Agenda | Cita **pendiente de confirmar** (filete discontinuo), cita **no vino** (roja), aviso de **sin cobertura** con agenda guardada, **día sin citas** el domingo, y «falta una foto para publicar» |
| Consola | **Carga** de la lista, **vacío** en «Suspendidos», y dos borradores con lo que les falta en rojo |

Todos los textos salen de `docs/marca/COPIA.md` palabra por palabra donde existía copia.

## 7. Lo que no hay, a propósito

Cero radios, cero degradados, cero cristal, cero sombras difusas, cero scrollytelling, cero foto de
banco, cero iconos genéricos y cero cifras de escala inventadas. Las fuentes vetadas no aparecen.
Los datos son de Panamá: El Cangrejo, Obarrio, Costa del Este, Marbella, San Francisco, Bella Vista,
Juan Díaz; Yaritza Moreno, Dayana Sánchez, Anayansi Pérez, Maricel Quintero, Nitzia Barría; precios
en dólares con dos decimales.

## 8. Cómo se comprueba

```
node scripts/revision-3-direccion-2.mjs
```

Abre Chromium a 390 y a 1440, recorre las cinco pantallas, mide el contraste real de cada texto,
guarda una captura por pantalla y ancho, y monta las dos hojas de contacto:

- `capturas/direccion-2-movil.png` (las cinco pantallas a 390 px)
- `capturas/direccion-2-escritorio.png` (las cinco pantallas a 1440 px)
- `capturas/direccion-2-{movil,escritorio}-0X-*.png` (cada pantalla suelta)
- `capturas/direccion-2-estado-{carga,confirmada}.png` (dos estados en marcha)

Sale con código de error si un texto baja de AA o si el prototipo lanza un error de JavaScript.

## 9. Si se elige esta dirección

Lo que habría que decidir después, y que **no** está decidido aquí: el logotipo definitivo (en el
prototipo la marca es la palabra compuesta en Bodoni, que sirve de provisional), el tratamiento de
las fotos que suban los salones (hay que forzar el filete y el pie para que no rompan la página), y
si el amarillo marcador entra también en el panel del salón o se queda solo en la reserva.
