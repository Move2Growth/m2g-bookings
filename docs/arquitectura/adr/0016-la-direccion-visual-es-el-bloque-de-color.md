# ADR-0016 · La dirección visual es el bloque de color

- **Estado:** aceptada
- **Fecha:** 2026-09-01
- **Supera:** la parte tipográfica y cromática de ADR-0013; complementa a ADR-0015

## Contexto

ADR-0015 fijó el nombre y dejó la identidad en manos del brandbook. El proceso adversarial
produjo tres direcciones con prototipos comparables y tres críticos con lentes distintas
(vetos, accesibilidad y 3G, negocio y verdad), y **ninguna salió aprobada por los tres**.

De ahí salieron dos señales que apuntaban al mismo sitio:

- **Luis eligió la dirección B**, «bloque de color panameño».
- **El crítico de accesibilidad rechazó A y C y dejó B como la única aceptable**, con cinco
  condiciones. Su argumento no era estético: A dibuja su estructura con 23 filetes a 1,31:1 y C
  con 32 a 1,33:1, y **este producto se usa de pie, con una mano y con el sol de frente**.
  Cuando el reflejo aplasta el rango de contraste, lo primero que desaparece son las
  diferencias pequeñas.

## Decisión

**[decisión]** La dirección visual del producto es **el bloque de color**: el color es la
estructura, las secciones van planas y a sangre, y la tipografía hace de imagen con lenguaje de
rótulo de local, no de panel de control.

**[decisión] La regla de los dos saturados, que es la que no se rompe.** Hay dos colores
saturados y **cada uno tiene un trabajo**:

- **El naranja mango `#FF7A1F` abre**: empieza algo (buscar, crear el salón, publicar) y es el
  filo que corta la página entre bloques.
- **El azul chiva `#1636C7` cierra**: remata (elegir la hora, confirmar la cita) y es el bloque
  de sección.
- **Nunca compiten en el mismo botón.** Si en una pantalla hay dos acciones saturadas, una está
  mal clasificada. El color lo decide **la fase del flujo, no la pantalla**: el mismo botón no
  puede salir naranja en `/entrar` y azul en `/reservar`.

**[decisión] El naranja nunca es color de texto.** Sobre cal se queda en 2,4:1, por debajo de
AA. Vive siempre como fondo con tinta noche encima. Es una consecuencia de la medida, no una
preferencia.

**[decisión] Una sola familia tipográfica, Archivo Variable, con tres anchos** —rótulo 112 %,
texto 100 %, cifra 125 %—, autoalojada. El contraste que otras direcciones daban con un salto
de familia lo da aquí el eje de anchura, y sale **una petición de red en vez de dos**.

**[decisión] El anillo de foco no es del color de marca.** Va en tinta noche sobre claro y en
cal dentro de los bloques oscuros. En azul se quedaba en 2,07:1 justo encima del bloque azul y
del botón naranja, que son los dos sitios donde más se pulsa.

**[decisión] Ninguna forma de píldora.** Superficies y bloques a canto vivo, controles a 4 px.
Desaparece la excepción que ADR-0013 dejaba abierta para fichas de filtro.

## Alternativas consideradas

- **La dirección A, editorial de barrio.** Es la que mejor aguanta el marketplace vacío y de
  ella se conserva esa disciplina —cero cifras de escala inventadas—, pero su idea central es
  su defecto medido: filetes de 1 px a 1,31:1 en 23 reglas.
- **La dirección C, herramienta afilada.** La mejor construida con un cronómetro (269 KB frente
  a 579) y de ella queda pendiente trasplantar el perfil de carga. Se cae por nueve
  `div role="button"` sin JavaScript y 169 nodos de texto por debajo de 14 px.
- **Una síntesis de las tres.** Descartada por Luis: una identidad que toma un poco de cada una
  no tiene ninguna idea que defender.

## Consecuencias

- **Habilita** que una pantalla nueva se resuelva sin inventar nada: se elige el bloque, se
  elige qué acción abre y cuál cierra, y el resto sale de los tokens.
- **Cierra** la puerta a las tarjetas con sombra y a los filetes finos como mecanismo de
  estructura. Lo que separa es color, filo o aire.
- **Obliga** a clasificar cada acción del producto en «abre» o «cierra». Es trabajo real en cada
  pantalla nueva, y es justo lo que evita que el color deje de significar nada.
- Las cinco condiciones de la auditoría de accesibilidad están aplicadas y anotadas en
  [`docs/marca/DECISION-DE-MARCA.md`](../../marca/DECISION-DE-MARCA.md) §4.
