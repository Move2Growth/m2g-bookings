# Crítica de tells: Bukeo, direcciones A, B y C

**Estado: completado.** Auditoría del 1 de septiembre de 2026, 22:49.

## Advertencia sobre el material auditado

Los tres HTML se estaban editando **mientras** se hacía esta revisión (marcas de tiempo 22:48, 22:49, 22:51, 22:52, 22:53). Las capturas `vista-*-movil.png` son de las 22:42 a las 22:45, así que **ya no corresponden al código**. Un defecto concreto (el de la portada de C, fila C-4) aparece en la captura y estaba parcheado en el archivo pocos minutos después. Todo lo demás que se señala aquí se ha comprobado contra una copia congelada a las 22:49 y sigue vivo en los archivos a las 22:53.

Además, **la captura de C está truncada**: mide 2363 px de alto frente a los 7562 de A y los 8553 de B, y se corta a media sección del salón. Más de la mitad de la dirección C (ficha, agenda, pie, anexo) no se ha visto nunca a 390 px. El propio `CLAUDE.md` del repositorio exige verificar la interfaz a 390 px. No se ha hecho con C.

## Criterio de gravedad

| Marca | Significado |
|---|---|
| **descalifica** | Está a la vista y es falso, o rompe un veto explícito del cliente. No se corrige, se retira. |
| **grave** | Un diseñador lo señala en la primera pasada y hay que rehacer la pieza. |
| **menor** | Se arregla en minutos y no compromete la dirección. |

## Lo que fallan las tres a la vez (esto es del encargo, no de las propuestas)

1. **No hay ni una fotografía real, y las tres lo disimulan.** Las tres tiran de `picsum.photos` con semillas descriptivas (`barberia-panama-corte-cliente`) que no producen nada de lo que nombran. A y B usan **la misma semilla**, así que **renderizan la misma imagen equivocada**: una estructura de acero de un puente. La segunda foto de A es una fachada de torre de oficinas. La portada de C es la **Estatua de la Libertad**. Cero salones, cero personas, cero Panamá en las tres propuestas. El encargo no dijo nada de imagen, y las tres taparon el hueco con un marcador de posición al que luego le pusieron un pie que afirma lo que no se ve. Eso ya no es un marcador de posición: es una afirmación falsa.
2. **Las tres rematan con un anexo de paleta con hexadecimales y porcentajes de uso que suman 100.** A: 58/22/12/4/2/2. B: 42/27/15/10/6. C: 58/20/7/3/6/4/2. Es el mismo reflejo tres veces, y el porcentaje de uso de un color es indemostrable: nadie lo va a medir nunca. Es decoración con aspecto de rigor.
3. **Las tres meten cuadrados de color decorativos.** A: el punto rojo del logotipo. B: cuatro cuadrados naranjas como viñetas. C: la celda roja del icono y el marcador de la fila elegida.
4. **Las tres dibujan el logotipo a mano en trazados SVG y ninguna de las tres está a nivel de salir.** Detalle en cada tabla.
5. **Dos de las tres usan 01 / 02 / 03** para los tres pasos. La tercera (C) usa el mismo dispositivo con palabras en versalita en vez de dígitos.

## Lo que las tres hacen bien (y conviene decirlo)

Los vetos escritos se han cumplido **al pie de la letra** en las tres: **cero rayas largas** (`grep -o "—"` da 0, 0, 0), **cero fuentes vetadas** (Jost + IBM Plex Sans; Archivo; IBM Plex Sans + Mono; ni rastro de Inter, Fraunces, Bricolage ni General Sans; las coincidencias de «inter» son «Interior», «interfaz» y `cursor:pointer`), **cero degradados**, **cero JavaScript** y por tanto cero scrollytelling, cero barra lateral de iconitos, cero tarjetas de funcionalidad a tres columnas, cero píldoras sobre fotos, cero indicaciones de «desliza» y cero sellos de versión. Ninguna cae en la familia beige/latón/espresso ni en el morado de IA con resplandores. Las tres declaran una regla de radio por escrito y la respetan.

Traducción: **lo que se nombró en el encargo se cumplió; todo lo que falla está en lo que el encargo no nombró** (fotografía, cifras, pies de foto y el propio logotipo).

---

## Dirección A, «Editorial de barrio»

| Defecto | Dónde | Gravedad | Arreglo |
|---|---|---|---|
| **A-1. «Contraste medido: tinta sobre papel 16,4:1» es falso.** El valor real de `#16211D` sobre `#F6F6F3` es **15,28:1**. Los otros dos sí cuadran (7,20 y 5,36). Es la única cifra de A que un revisor puede comprobar en diez segundos, dice «medido», y no está medida. Un anexo de especificación con una medición inventada no vale nada. | Línea 551 (anexo) | **descalifica** | Poner 15,3:1, o borrar la frase. Y comprobar las tres con una calculadora antes de volver a escribir «medido». |
| **A-2. Las dos fotos muestran otra cosa y el pie afirma lo que no se ve.** El hero es una celosía de acero de un puente con el pie «Vía Argentina, El Cangrejo. La silla de las 4:30 p. m.». La segunda es una fachada de oficinas con el pie «Una reserva de 40 segundos, con 3G y una sola mano». Los 40 segundos, además, son inventados. | Líneas 254-255 y 330-331; captura, franjas ~470-760 px y ~1750-1950 px | grave | Fotografía real o, si no la hay, retícula/color sin foto. El pie describe lo que se ve o no existe. Borrar «40 segundos». |
| **A-3. Separador decimal de España en un producto panameño.** «$12,00», «$18,00», «4,8 de 5». Panamá escribe 12.00 y 4.8. El propio pie de A presume de «Español de Panamá» tres líneas más abajo. B y C lo hacen bien. | Líneas 398, 408-412, 498 | grave | Punto decimal en todos los precios y valoraciones. |
| **A-4. Rejilla de horas de 12 h sin a.m./p.m.** Bajo «Tarde» se leen botones «1:30», «2:15», «3:00» junto a los «9:00» de la mañana. En una pantalla de reserva, ambigüedad de doce horas. | Líneas 428-435 | grave | 24 h como hace C, o marcar la franja dentro de cada botón. |
| **A-5. Numeritos de sección 01 / 02 / 03**, además en el color de acento, que así deja de estar reservado a lo accionable. | Líneas 314, 319, 324 | grave | Quitar los dígitos. «Busca por zona», «Elige la hora», «Reserva» ya van en orden. |
| **A-6. Cita sin autor.** «Aquí no se paga por trabajar. Se paga, si acaso, por salir arriba.» Compuesta como cita destacada, con filete de acento, y no la dice nadie. Es un aforismo sobre el modelo de negocio escrito por la casa y entrecomillado para que parezca testimonio. | Línea 357 | grave | Borrarla. Si hace falta explicar el modelo, se explica en prosa, sin comillas. |
| A-7. **Punto cuadrado rojo en el logotipo**, única forma cuadrada de una marca hecha entera de círculos y trazos monolineales. Ninguna regla del anexo lo sostiene. | SVG, línea 229 | menor | Quitarlo. |
| A-8. **Espaciado desigual del logotipo.** El hueco entre `k` y `e` es visiblemente mayor que el de `e` y `o`, que casi se tocan. Se ve al ampliar la barra. | SVG, líneas 223-228 | menor | Reespaciar a ojo, no por coordenadas redondas. |
| A-9. **Píldoras de filtro (radio 999 px) contra canto vivo en todo lo demás.** El anexo declara la excepción, pero declarar una excepción no la convierte en sistema. | Línea 130 frente a 60 | menor | Filtros a canto vivo y una sola forma en toda la página. |
| A-10. **Etiqueta «eyebrow»** «CIUDAD DE PANAMÁ · MARTES 2 DE SEPTIEMBRE», versalita a 11 px con 0,16 em de espaciado. | Línea 245 | menor | Es **una sola** en siete secciones: dentro de tolerancia. Se puede dejar. |
| A-11. **El contraste declarado mide un par que casi no ocurre.** «Gris plomo sobre blanco 7,2:1» es correcto, pero el plomo se usa sobre `--papel`, donde da 6,65:1. Se ha declarado la combinación favorable. | Línea 551 | menor | Declarar el par que de verdad se usa. |

**Veredicto A: rechazada.** El anexo es la pieza que justifica la dirección y contiene una medición falsa (A-1); mientras eso esté ahí, nada del resto del anexo es creíble. Vuelve a mirarse cuando: se corrija la cifra de contraste, se ponga fotografía real o se quiten las fotos con sus pies, se pase a punto decimal, se marquen las horas con a.m./p.m. y desaparezcan los 01/02/03 y la cita sin autor.

---

## Dirección B, «Bloque de color panameño»

| Defecto | Dónde | Gravedad | Arreglo |
|---|---|---|---|
| **B-1. La B del logotipo está mal dibujada.** Ampliada, la `B` es una astilla estrecha con una ranura clara en el centro donde chocan los remates cuadrados de los dos arcos, y su cuenco inferior baja por debajo de la línea base de `UKEO`. Las anchuras no guardan relación: la B mide unos 29 px de caja y la O unos 57, casi el doble. En una propuesta de **identidad**, el logotipo es la pieza. | SVG, líneas 332-345 (y repetido en el pie, 508-521) | **descalifica** | Redibujar el mark completo con anchuras coherentes y uniones reales, no trazados sueltos superpuestos. Es lo único que impide aprobar esta dirección. |
| **B-2. Numeritos 01 / 02 / 03 a tamaño de titular** (`clamp(2.25rem, 9vw, 3.75rem)`, peso 800, anchura 125). No es que estén: es que son lo más grande de la sección después del h2. | Líneas 155-158, 381, 386, 391 | grave | Quitarlos. El bloque naranja ya separa los tres pasos con filetes de 2 px. |
| **B-3. Dos colores saturados donde la regla pide uno.** Azul `#1636C7` y naranja `#FF7A1F`, ambos a plena saturación, ambos usados en superficie y en botón. B lo declara («dos colores saturados en tensión») pero declararlo no lo hace cumplir la regla de un solo acento. En la ficha conviven un botón azul de confirmar y un botón naranja de registrar sin una jerarquía escrita entre ellos. | Líneas 22-23, 137-142 | grave | Elegir uno como acento accionable y bajar el otro a superficie, o escribir la regla de cuándo manda cada uno. |
| **B-4. Misma foto equivocada que A** (idéntica semilla `barberia-panama-corte-cliente`: la celosía del puente), con `alt` que dice «Cliente en el sillón de una barbería mientras le terminan el corte». La segunda foto es un campo al atardecer con `alt` «Dueña de un salón revisando la agenda». El texto alternativo miente donde solo lo oye quien no puede comprobarlo. | Líneas 370 y 419; captura, franjas ~720-900 px y ~1900-2150 px | grave | Fotografía real, o franja de color sin foto (que es justo lo que esta dirección sabe hacer). Corregir el `alt`. |
| B-5. **Cuatro cuadrados naranjas como viñetas** en la lista de ventajas. Punto de color decorativo, y consume el acento en algo que no se toca. | Línea 178 | menor | Viñeta tipográfica o filete, no color. |
| B-6. **Horas de 12 h sin a.m./p.m.**, igual que A: «1:00», «2:30» junto a «9:00». | Líneas 484-489 | menor | La franja «Mañana»/«Tarde» ayuda, pero conviene marcarlo en el botón. |
| B-7. **Etiqueta «eyebrow»** «CIUDAD DE PANAMÁ» sobre el h1, más tres encabezados de columna del pie en versalita con 0,1 em. | Líneas 121-124, 257 | menor | Una ceja real en siete secciones: dentro de tolerancia. Los del pie son convención de pie, no cejas. |
| B-8. **Anexo de porcentajes de uso** (42/27/15/10/6). Indemostrable, igual que en A y C. | Líneas 567-575 | menor | O se mide de verdad sobre una pantalla concreta, o se cambia por la regla de uso en prosa, que B ya escribe bien. |

**Veredicto B: aceptable con condiciones.** Condición explícita y única para pasar: **redibujar el logotipo** (B-1) y quitar los 01/02/03 (B-2). Es la única de las tres cuyas cifras declaradas cuadran **todas** al decimal (siete ratios de contraste comprobados, siete exactos) y la única sin un solo número inventado sobre el negocio. Lo demás son restas, no rectificaciones.

---

## Dirección C, «Herramienta afilada»

| Defecto | Dónde | Gravedad | Arreglo |
|---|---|---|---|
| **C-1. Cifras inventadas en la portada, de un producto que no tiene ni un usuario.** «418 salones publicados», «2,146 horas libres hoy», «11 zonas de la ciudad», puestas en una cinta con aspecto de cuadro de mando. Y siguen: «Tres pasos · 40 segundos de media», «38 resultados en 0.4 s», «La pantalla que se abre 40 veces al día». Esto es mentir en la portada. | Líneas 624-629, 642, 655, 810 | **descalifica** | Borrar la cinta entera. Si hace falta algo ahí, que sea la única cifra verdadera que existe: B/. 0.00 de coste para el salón. |
| **C-2. Cuarenta y siete etiquetas en versalita con espaciado** en una sola página de ocho secciones (13 `.cota`, 8 `.estado`, 8 cabeceras de tabla, 4 `.rotulo`, 4 `h5` de pie, 4 rótulos de KPI, más ceja, leyenda, pie legal y rótulo de pantalla). El máximo tolerable es una por cada tres secciones, es decir dos o tres en toda la página. C va quince veces por encima. Cada bloque de contenido lleva su etiqueta minúscula encima o al lado, y el efecto es de plantilla, no de herramienta. | 13 declaraciones de `text-transform:uppercase` con `letter-spacing` de 0,06 a 0,14 em (líneas 100, 161, 201, 224, 287, 331, 357, 365, 379, 411, 465, 475, 487) | **descalifica** | Dejar tres, como mucho. Todo lo demás pasa a texto normal o desaparece: los estados ya se leen escritos, las cabeceras de tabla no necesitan versalita, los KPI tampoco. |
| **C-3. La foto de portada es la Estatua de la Libertad**, en Nueva York, con el pie «BARBERÍA EN EL CANGREJO · 08°59'N 79°32'O». Las coordenadas de Ciudad de Panamá bajo una foto de Manhattan. Además, poner coordenadas como pie de foto es el ejemplo de manual del pie pretencioso. | Línea 632-633; captura, franja ~565-790 px | **descalifica** | Foto real, y pie que diga qué se ve o ningún pie. Las coordenadas fuera en cualquier caso. |
| **C-4. La portada se dibujaba sin canal lateral.** En la captura, la ceja, el titular, la bajada, los dos botones, la cinta de cifras y la foto llegan a x=0 y x=389, pegados a los dos bordes del teléfono, mientras la barra de navegación conserva sus 16 px. La causa: `.portada` (línea 158) redefinía la abreviatura `padding` y anulaba la de `.marco` (línea 71), misma especificidad y definida después. **Ya está parcheado** en el archivo de las 22:49 (`padding:24px var(--canal) 28px`), pero es un defecto que la captura enseñaba y que nadie vio antes de entregarla. | Captura completa por debajo de y=57 px; CSS líneas 71 y 158 | grave | Corregido. La lección es la otra: la captura de C está truncada a 2363 px y más de la mitad de la página no se ha mirado nunca a 390 px. Volver a capturar entera. |
| **C-5. Toda la interfaz en monoespaciada.** `--mono` se invoca 33 veces frente a 1 de `--sans`: horas, precios, duraciones, estados, cabeceras, leyendas, KPI, pie legal, coordenadas y el rótulo «390 px». Las cifras tabulares se justifican; el resto es estética de terminal. Un salón de belleza no es una consola. | Líneas 32-33 y sus 33 usos | grave | Mono solo en cifras que forman columna. Todo rótulo y estado, a la Sans. |
| **C-6. El número 40 hace tres trabajos distintos.** «40 segundos de media» (duración de una reserva), «40 veces al día» (frecuencia de apertura, repetido en dos sitios), «40 min» (duración del corte). Un número elegido por cómo suena, no por lo que mide. | Líneas 642, 810, 932, 665, 756 | grave | Fuera los dos primeros. El tercero es dato de la ficha simulada y puede quedarse. |
| C-7. **«Bukeo, S.A.»** en el pie legal. Sociedad inventada. | Línea 1000 | menor | «Bukeo» a secas hasta que exista la sociedad. |
| C-8. **El `aria-label` de la barra de proporciones describe otro gráfico.** Dice «grafito 6 %, tinta 4 %, cota 3 %» y la barra dibuja cota (3 %) antes que grafito (6 %). Quien no ve la barra recibe un orden distinto del que se pinta. | Líneas 1071-1078 | menor | Igualar el orden. |
| C-9. **La escala tipográfica documenta solo el escritorio.** «Titular de portada · 56 px» cuando a 390 px, que es donde vive esto, el h1 mide 30 px. | Líneas 1097-1102 | menor | Documentar los dos extremos del `clamp`. |
| C-10. **El icono es una rejilla de 3×3 con una celda roja.** Lee «hoja de cálculo» o «calendario», no belleza, y podría ser de cualquier SaaS. Es además el tercer cuadrado de color decorativo del conjunto. | SVG, líneas 587-591 | menor | O se dibuja algo que signifique algo, o se va y queda solo la palabra, que está mejor dibujada que en A y B. |

**Veredicto C: rechazada.** No con condiciones: la portada hay que borrarla y rehacerla. C es la que mejor dibuja las letras del logotipo y la única con una rejilla de horas de verdad usable (24 h, ocupadas tachadas, «9 de 22» que además cuadra: hay exactamente 22 botones y 9 libres), y ese rigor con lo comprobable hace más grave, no menos, que se invente todo lo que nadie puede comprobar.

---

## Recuento comparado

| | A, Editorial de barrio | B, Bloque de color | C, Herramienta afilada |
|---|---|---|---|
| **descalifica** | 1 | 1 | 3 |
| **grave** | 5 | 3 | 3 |
| **menor** | 5 | 4 | 4 |
| **Total** | **11** | **8** | **10** |
| Rayas largas (`—`) | 0 | 0 | 0 |
| Fuentes vetadas | 0 | 0 | 0 |
| Degradados / scrollytelling / iconitos / tarjetas a tres columnas | 0 | 0 | 0 |
| Cejas en versalita (tolerancia: 2-3) | 1 | 1 (+3 de pie) | **47** |
| Numeritos de sección | 3 | 3 | 0 |
| Cifras inventadas sobre el negocio | 2 | **0** | 6 |
| Ratios de contraste declarados que no cuadran | **1 de 3** | 0 de 7 | 0 de 6 |
| Acentos saturados (regla: 1) | 1 | **2** | 1 |
| Fotos que muestran lo que dicen | 0 de 2 | 0 de 2 | 0 de 4 |
| Veredicto | **rechazada** | **aceptable con condiciones** | **rechazada** |

---

**B es la que mejor aguanta que la mire un diseñador de verdad, porque es la única cuyas cifras declaradas cuadran todas al decimal y no inventa un solo dato sobre el negocio, y porque sus dos defectos serios son una resta (quitar los 01/02/03 y elegir un solo acento) y un redibujo del logotipo, mientras que A tiene que retractarse de una medición que dice haber medido y C tiene que borrar su portada entera.**
