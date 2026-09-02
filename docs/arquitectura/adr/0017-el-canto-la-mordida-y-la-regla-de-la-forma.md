# ADR-0017 · El canto, la mordida y la regla de la forma

- **Estado:** aceptada
- **Fecha:** 2026-09-02
- **Complementa a:** ADR-0016, que fijó el color y la tipografía y dejó la forma sin decidir

## Contexto

ADR-0016 decidió que el color es la estructura, que el naranja abre y el azul cierra, y que hay
una sola familia tipográfica con tres anchos. **No dijo nada de la forma de los controles**, y
esa omisión se pagó entera: lo que se construyó fue un botón rectangular de 4 px de radio, un
campo con filete y unas rayas grises entre filas.

Luis lo rechazó con estas palabras: «no hay botones personalizados, no hay nada que siga el brand
book, todo super IA, trabajo muy perezoso». Tres agentes adversariales lo confirmaron por caminos
distintos y con pruebas:

- Ni un botón, campo, tarjeta, lista o icono habría sobrevivido a una comparación a ciegas contra
  una plantilla.
- La jerarquía se estaba expresando con **seis grises**, que es lo que hace cualquier sistema por
  defecto.
- El símbolo de la marca, «el hueco» —un bloque con una muesca calada, que es literalmente lo que
  vende el producto—, estaba dibujado en el brandbook y **no aparecía en ninguna pantalla**.

## Decisión

**[decisión] El canto.** Todo lo que se toca lleva un **zócalo macizo dentro de su propia caja**,
dibujado con `currentColor`. Al pasar por encima crece de 4 a 6 px, la chapa se levanta; al
pulsar se lo traga y el contenido baja 2 px.

**[decisión] La mordida.** Al canto le faltan los **últimos 14 px por la derecha**. Es la muesca
calada del icono de Bukeo, tumbada. Es la firma: con el texto tapado, un control de este producto
se distingue de cualquier plantilla.

**[decisión] La forma manda.** Radio de 4 px **y canto** significa «se toca». Canto vivo y **sin
canto** significa «se lee». El brandbook ya lo decía como estilo; aquí pasa a significar algo, y
por eso un sello de estado no puede confundirse con un botón.

**[decisión] La jerarquía se mide en píxeles de canto, no en grises:** 4 px la acción que abre o
cierra, 3 px la secundaria, 2 px la de texto, 0 lo que no se toca.

**[decisión] El canto se dibuja con `background-image`, nunca con `box-shadow`.** No es una
preferencia de implementación: es lo que resuelve tres problemas a la vez. No se solapa con el
control de al lado, la altura total no cambia al pulsar —48 px en reposo y apagado, medido—, y
**la misma declaración vale para un `<button>` y para un `<input>`**, que no admite
pseudoelementos. Esa es la razón real de que el campo y el botón se reconozcan como familia.

**[decisión] Nada de remates redondos en el dibujo.** Los iconos se dibujan con remate a escuadra
y unión en ángulo vivo, como el wordmark, con trazo de 2 sobre caja de 24 en coordenadas enteras.
No se usa librería de iconos: la que había traía remates redondos al lado de un rótulo a
escuadra.

**[decisión] El filete de 1 px deja de dibujar estructura.** `--color-borde` mide **1,29:1** sobre
papel, peor que los 1,31:1 por los que ADR-0016 descartó la dirección A. Donde una línea de
verdad separa, sube a `--color-borde-fuerte` (3,88:1), que es el mínimo que AA pide para un
elemento de interfaz. Donde dibujaba una caja alrededor de algo, desaparece: una caja con filete
es una tarjeta, y lo que separa es color, filo o aire.

## Alternativas consideradas

- **Dejarlo en el radio y el color, como estaba.** Es lo que produjo el rechazo. Un sistema que
  solo cambia colores sobre formas por defecto sigue siendo la plantilla por defecto.
- **La sombra desplazada dura**, tipo brutalismo. Descartada: ADR-0016 reserva la sombra para lo
  que de verdad flota, y una sombra fuera de la caja se solapa con el control vecino y cambia la
  altura de la fila al pulsar.
- **Superar ADR-0016 para admitir el filete de 1,29:1.** Descartado: habría sido cambiar la regla
  para que encajara el defecto, cuando el argumento con el que ganó esta dirección era
  precisamente ese defecto en la otra.

## Consecuencias

- **Habilita** reconocer un control de Bukeo sin leerlo, que es lo que faltaba, y expresar
  jerarquía sin inventar grises nuevos.
- **Obliga** a que toda pieza nueva declare su canto. Una pieza sin canto está diciendo «esto no
  se toca», y si se toca, es un fallo.
- **Cierra** la puerta a las librerías de iconos y a la tarjeta con filete.
- **Cuesta** una variable registrada con `@property` para poder animar el canto. Sin registrarla,
  el zócalo salta de un grosor a otro en vez de moverse, y el gesto no existe.
- La propuesta completa, con sus cinco estados y su contraste medido, está en
  [`docs/marca/revision-2/lenguaje-de-componentes.html`](../../marca/revision-2/lenguaje-de-componentes.html).
