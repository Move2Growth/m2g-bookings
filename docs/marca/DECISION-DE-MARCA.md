# Cómo se eligió la identidad de Bukeo — Estado: completado

> **La marca no se eligió a ojo.** Tres direcciones independientes compitieron con prototipos
> comparables y tres críticos con lentes distintas intentaron tumbarlas. Este documento cuenta
> qué pasó, qué se llevó cada una y por qué se construyó la **dirección B**.

---

## 1. El método

**Ronda 1, tres direcciones a ciegas.** Cada una recibió el mismo encargo, el mismo contenido y
las mismas prohibiciones, y una dirección artística distinta y obligatoria para que no
convergieran:

| | Dirección | Encargo |
|---|---|---|
| **A** | Editorial de barrio | Papel y tinta, retícula editorial asimétrica, canto vivo, un acento cálido que aparece poco |
| **B** | Bloque de color panameño | El color como estructura, secciones a sangre, dos saturados en tensión, lenguaje de rótulo |
| **C** | Herramienta afilada | Casi monocroma, retícula visible, densidad alta, cifras tabulares, un solo color para lo accionable |

Los tres prototipos están en [`propuestas/`](propuestas/) y se abren en el navegador.

**Ronda 2, tres críticos adversariales.** Con el encargo explícito de **rechazar por defecto**:

- **Tells y vetos**: rayas largas, fuentes vetadas, paletas prohibidas, etiquetas en versalita,
  numeritos de sección, datos con falsa precisión, copia de relleno.
- **Accesibilidad y 3G**: contraste medido con la fórmula WCAG, objetivos táctiles, tamaño de
  letra en formularios, desbordamiento a 390 px, peso de página y peticiones de fuente.
- **Negocio y verdad**: si se entiende en cinco segundos, si el gratis se sostiene, si hay datos
  inventados, si aguanta el marketplace vacío y si suena a Panamá.

## 2. Qué dijeron

**Ninguna dirección salió aprobada por los tres.** Ese es el resultado y no un fracaso del
proceso: es la señal de que la primera versión de cualquiera de las tres habría salido con
defectos que nadie mira cuando solo hay una propuesta.

| | Tells y vetos | Accesibilidad y 3G | Negocio y verdad |
|---|---|---|---|
| **A** | Rechazada: declaró un contraste de 16,4:1 que en realidad era 15,28:1 | Rechazada: dibuja su estructura con 23 filetes a 1,31:1 | Aceptable con condiciones: la única que sigue siendo verdad con cero salones |
| **B** | Aceptable con condiciones: la única sin un solo número inventado | **Aceptable con condiciones**: 3 fallos en 50, y dos ornamentales | Rechazada: el único salón que enseñaba iba etiquetado como patrocinado |
| **C** | Rechazada: cifras inventadas en portada y 47 etiquetas en versalita | Rechazada: 9 `div role="button"` sin JavaScript y 169 nodos por debajo de 14 px | Rechazada: «418 salones publicados» en un producto con cero usuarios |

**El hallazgo estructural lo dio el crítico de tells, y no era de ninguna dirección: era del
encargo.** Las tres cumplieron al pie de la letra todo lo que se les prohibió por escrito, y las
tres fallaron en lo que no se nombró: **ninguna tenía una sola fotografía real**. Las tres
tiraron de imágenes de relleno con semillas descriptivas que no producen lo que nombran, así que
A y B renderizaban la misma celosía de puente y la portada de C era la Estatua de la Libertad
rotulada «Barbería en El Cangrejo».

## 3. Qué se construyó

**La dirección B, «bloque de color panameño». La eligió Luis**, y coincide con la única de las
tres que el crítico de accesibilidad dio por aceptable. Esa coincidencia no es casualidad: la
razón por la que gusta y la razón por la que pasa la auditoría son la misma. **El color es la
estructura.** No hay filetes finos que distinguir ni retícula que adivinar; hay un rectángulo
azul, un rectángulo naranja y bordes negros de 2 px. Cuando el sol de mediodía aplasta el rango
de contraste de un teléfono, lo primero que desaparece son las diferencias pequeñas, y aquí no
hay ninguna que perder.

Su lenguaje es el del **rótulo de un local**, no el de un panel de control: tipografía ancha
haciendo de imagen y secciones planas a sangre.

**De la B se toma también la frase que desmonta el escepticismo** y que ninguna otra encontró:
*«Sin comisión por reserva. Ni ahora, ni cuando tengas la agenda llena.»* El miedo de la dueña
de un salón no es pagar hoy, es que le cobren cuando funcione.

**De la A se toma su honestidad con el marketplace vacío**, que era su mejor argumento y el
fallo por el que a B la rechazó el crítico de negocio: en el producto **no hay ni una cifra de
escala inventada, y el único salón que se enseña no va etiquetado como patrocinado**. Con tres
salones publicados la página sigue siendo verdad palabra por palabra.

**De la C se toma su mejor argumento de venta, que no era una sección sino una pantalla**: la
agenda del salón. En vez de contarla, el producto la enseña; es lo primero que ve un dueño al
entrar y lo que decide si se queda.

**Y se corrige lo que las tres compartían.** Las fotos del producto son **generadas y reales**,
no de banco: manos trabajando, luz de mediodía, oficio. Solo dos categorías llevan foto porque
solo hay dos fotos buenas; las otras seis son celdas tipográficas, que es más honesto que una
imagen genérica y además pesa cero en 3G.

## 4. Las cinco condiciones de la auditoría, aplicadas

La accesibilidad no aprobó la B a secas: la aprobó con cinco condiciones. Están las cinco en el
producto, no en el prototipo:

1. **El anillo de foco ya no es azul.** Va en tinta noche sobre claro y en cal dentro de los
   bloques oscuros. En azul se quedaba en 2,07:1 encima del bloque azul y del botón naranja.
2. **Lo que se toca no se delimita con un filete de 1,15:1.** Fichas de filtro y controles pasan
   a borde fuerte, que es el mínimo de 3:1 que pide AA para un elemento de interfaz.
3. **44 px de alto en todo lo pulsable**, enlaces del pie y logotipo incluidos. Lo único que
   queda por debajo son los enlaces dentro de un párrafo, que es la excepción que la propia
   norma contempla.
4. **Las fotos se sirven con `srcset` y carga diferida**, que lo resuelve `next/image` sin
   escribir una línea. Solo la de portada se carga con prioridad, porque es la que mide el LCP.
5. **El buscador lleva etiqueta visible** y todos los campos van a 16 px. Un marcador de
   posición desaparece al escribir y deja el campo sin nombre justo cuando hay que corregir.

## 5. Un desvío deliberado: la tipografía

La B llegó con dos familias. El producto va con **una sola, Archivo Variable, y tres anchos**:
112 % para rótulo, 100 % para texto y 125 % para cifras. El contraste que en la propuesta daba
el salto de familia lo da aquí el eje de anchura, y sale **una petición de red en vez de dos**,
que en 3G es la diferencia que el propio crítico midió entre 5 s y 11 s de carga.

## 6. Lo que queda anotado

- El proceso adversarial **funcionó y hay que repetirlo** cuando toque la app: dos de los tres
  autores corrigieron su propia propuesta después de leer la crítica del otro.
- **Los prototipos se quedan en el repositorio.** No son basura: son el registro de qué se
  descartó y por qué, y la próxima discusión de identidad empieza ahí y no de cero.
- **El crítico de accesibilidad y el director coincidieron sin hablarse.** Cuando la lente
  estética y la medida técnica apuntan a la misma propuesta, la decisión está más asentada que
  cuando solo apunta una.
- **De C queda pendiente su perfil de carga**, que era el mejor de los tres por más del doble.
  Está anotado en el tablero, no aquí.
