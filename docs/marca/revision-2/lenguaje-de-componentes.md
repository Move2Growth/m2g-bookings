# Bukeo · El lenguaje de componentes · Estado: propuesta, pendiente de aprobación de Luis

> Revisión 2 de la capa de componentes. **Se mira aquí:**
> [`lenguaje-de-componentes.html`](lenguaje-de-componentes.html) (se abre en el navegador, cada pieza
> en sus cinco estados).
>
> **Qué corrige.** El brandbook y el ADR-0016 prometen un lenguaje de rótulo de local panameño, y lo
> que hay construido en `apps/web/app/globales.css` es un botón rectangular de 4 px de radio, un campo
> con filete y filetes grises entre filas. No hay ni una pieza que solo pueda ser de este producto.
>
> **Qué no cambia.** Ni un color, ni una fuente, ni una decisión de ADR. Los tokens de color son los
> mismos; se proponen **cinco valores nuevos** (cuatro medidas y una anchura tipográfica) y **ni un
> hexadecimal**. Todo lo que no sale de una variable sale de `color-mix()` sobre esas variables.

---

## 1. La idea, en tres reglas

| # | Regla | Qué resuelve |
|---|---|---|
| **1** | **El canto.** Todo lo que se toca lleva un zócalo macizo dentro de su caja, dibujado con `currentColor`. Al pasar por encima crece de 4 a 6 px; al pulsar se lo traga y el contenido baja. | Da peso y respuesta física sin una sola sombra. Y como es `currentColor`, se invierte solo dentro de un bloque de color, igual que el logotipo. |
| **2** | **La mordida.** Al canto le faltan los últimos 14 px. Es la muesca calada del icono, tumbada. | Es la firma. Dos botones idénticos en color y tipografía se distinguen por esto, y no lo hace nadie más. |
| **3** | **La forma manda.** Radio 4 px y canto: **se toca**. Canto vivo y sin canto: **se lee**. | El brandbook ya lo decía como regla de estilo; aquí pasa a significar algo. Un sello de estado no puede confundirse con un botón porque tiene otra forma, no otro color. |

Y una consecuencia que ordena todo el sistema: **la jerarquía de una acción se mide en píxeles de
canto.** 4 px la que abre o cierra, 3 px la secundaria, 2 px la de texto, 0 px lo que no se toca. Un
solo mando, en vez de seis grises que hay que recordar.

---

## 2. Por qué esto y no otra cosa

**Por qué un zócalo y no una sombra.** El moodboard dice «rótulo pintado, color plano, sin degradado»
y «la luz de Panamá: alto contraste, sombra dura». Un zócalo macizo de desenfoque cero es un bloque
de color, que es lo que el ADR-0016 permite; una sombra difusa es lo que prohíbe.

**Por qué dentro de la caja y no fuera.** Un `box-shadow` desplazado se solapa con el elemento de al
lado y obliga a inventar márgenes. El zócalo por dentro deja la altura total constante (44 px de
objetivo táctil más el canto), así que **nada se mueve de sitio al pulsar**: lo que se mueve es el
contenido dentro del control.

**Por qué `currentColor`.** Porque el contraste del canto pasa a ser el mismo que el del texto, que ya
está verificado. En el botón naranja sale tinta (6,99:1) y en el azul sale cal (7,90:1). Si hubiera
sido siempre tinta, en el azul se habría quedado en **2,07:1**, invisible justo en el botón que más se
pulsa del producto.

**Por qué el foco no usa `currentColor`.** El anillo se dibuja fuera del control, sobre la página: en
el botón azul saldría cal sobre papel cal y desaparecería. Va con la variable `--foco-anillo`, tinta
por defecto y cal dentro de bloques oscuros, que es la regla del ADR-0016 convertida en una variable
en lugar de en una lista de selectores que alguien olvidará ampliar.

**Por qué el apagado pierde el canto en vez de bajar la opacidad.** `opacity: .55` deja el texto en
2,9:1 y un botón que no se lee no informa de nada. Sin canto ya dice que no se pulsa, y el texto se
queda en tinta suave sobre arena a **6,48:1**, que es AA con margen.

**Por qué lo elegido no se rellena de color.** Rellenar de azul gasta el color que sirve para cerrar y
obliga a distinguir dos tonos con el sol de frente. Lo elegido se hunde, le crece un filo macizo de
6 px y la letra se ensancha: tres señales, y solo una es de color.

---

## 3. Los tokens que faltan

Ni un color nuevo. Cinco valores para `packages/tokens/tokens.json` (**zona serializada**: los escribe
quien tenga el turno, no dos a la vez).

```jsonc
{
  "canto": {
    "_nota": "El zocalo macizo que llevan dentro las cosas que se tocan. Su grosor ES la jerarquia: 4 px la accion que abre o cierra, 3 px la secundaria, 2 px la de texto, 0 lo que no se toca. Al pasar por encima crece a 6 px (la chapa se levanta) y al pulsar se lo traga. La mordida es lo que le falta por la derecha: la muesca calada del icono.",
    "principal": "4px",
    "secundario": "3px",
    "menor": "2px",
    "alzado": "6px",
    "mordida": "14px"
  },
  "filo": {
    "_nota": "La barra maciza que dice «estas aqui» o «esto esta elegido». Misma medida que el filo de bloque del brandbook y distinto color a proposito: el naranja se reserva para cortar la pagina entre bloques, o dejaria de significar «abre».",
    "grosor": "6px"
  },
  "foco": {
    "_nota": "No es del color de marca (ADR-0016). Tinta sobre claro y cal dentro de bloques oscuros, resuelto con una variable y no con una lista de selectores.",
    "grosor": "3px",
    "separacion": "2px"
  },
  "tipografia": {
    "ancho-estrecho": "87%"
  }
}
```

Y una variable de tema, que va en `variables.css` junto a los colores porque cambia con el fondo:

```css
:root { --foco-anillo: var(--color-tinta); }
/* En cualquier superficie oscura, incluidas .seccion--azul, .seccion--tinta y las filas
   destacadas: */
.seccion--azul, .seccion--tinta, .resultado--destacado { --foco-anillo: var(--color-papel); }
```

---

## 4. El CSS, listo para pegar

Se mantienen **los mismos nombres de clase** que ya usa `apps/web/app/globales.css`
(`.boton--primario`, `.entrada`, `.hora`, `.ficha`, `.estado`, `.resultado`). El cambio entero es CSS:
**no hay que tocar ni un componente de React.**

### 4.0 La base

> **Da por hecho el `box-sizing: border-box` global** que ya tiene el reset de `globales.css`. Sin
> él, los `min-height` se aplican a la caja de contenido y todos los controles salen 20 px más altos.

```css
/* Registrar la variable es lo que permite animarla. Sin esto el canto salta en vez de moverse. */
@property --canto {
  syntax: '<length>';
  inherits: false;
  initial-value: 0px;
}

:root {
  --canto-principal: 4px;
  --canto-secundario: 3px;
  --canto-menor: 2px;
  --canto-alzado: 6px;
  --canto-mordida: 14px;
  --filo-grosor: 6px;
  --foco-grosor: 3px;
  --foco-separacion: 2px;
  --foco-anillo: var(--color-tinta);
  --tipografia-ancho-estrecho: 87%;

  /* Las dos tramas. Gradientes de parada dura: bandas planas, no degradados. Pesan cero. */
  --trama-pauta: repeating-linear-gradient(
    to bottom,
    transparent 0 calc(var(--espacio-toque-minimo) - 1px),
    var(--color-borde-fuerte) calc(var(--espacio-toque-minimo) - 1px) var(--espacio-toque-minimo)
  );
  --trama-rayado: repeating-linear-gradient(
    135deg,
    transparent 0 5px,
    color-mix(in srgb, var(--color-tinta) 14%, transparent) 5px 7px
  );
}
```

### 4.1 El botón

```css
.boton {
  --canto: var(--canto-principal);
  display: inline-flex; align-items: center; justify-content: center; gap: var(--espacio-2);
  /* La altura total NO cambia con el canto: 44 px de objetivo táctil más el canto. */
  min-height: calc(var(--espacio-toque-minimo) + var(--canto-principal));
  padding-inline: var(--espacio-5);
  border: 0;
  border-radius: var(--radio-control);
  font-weight: var(--tipografia-pesos-fuerte);
  font-stretch: var(--tipografia-ancho-texto);
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;

  /* el canto */
  padding-bottom: var(--canto);
  background-image: linear-gradient(
    to right,
    currentColor 0 calc(100% - var(--canto-mordida)),
    transparent calc(100% - var(--canto-mordida))
  );
  background-repeat: no-repeat;
  background-size: 100% var(--canto);
  background-position: left bottom;

  transition:
    --canto var(--movimiento-rapido) var(--movimiento-curva),
    background-color var(--movimiento-rapido) var(--movimiento-curva),
    border-color var(--movimiento-rapido) var(--movimiento-curva),
    transform var(--movimiento-instante) var(--movimiento-curva);
}
.boton:hover  { --canto: var(--canto-alzado); }            /* la chapa se levanta */
.boton:active { --canto: 0px; transform: translateY(2px); } /* y se hunde */
.boton:focus-visible { outline: var(--foco-grosor) solid var(--foco-anillo); outline-offset: var(--foco-separacion); }

/* El naranja ABRE. Siempre con tinta encima: sobre claro no llega a AA y nunca es color de texto. */
.boton--primario { background-color: var(--color-abre); color: var(--color-abre-texto); }
.boton--primario:hover { background-color: var(--color-abre-hover); }

/* El azul CIERRA. El canto sale en cal porque es currentColor: se lee como el papel que se ve
   por debajo del bloque, que es el calado del icono. */
.boton--cierra { background-color: var(--color-acento); color: var(--color-acento-texto); }
.boton--cierra:hover { background-color: var(--color-acento-hover); }

.boton--secundario {
  --canto: var(--canto-secundario);
  background-color: var(--color-lienzo);
  color: var(--color-tinta);
  box-shadow: inset 0 0 0 1px var(--color-borde-fuerte);
}
.boton--secundario:hover { --canto: 5px; box-shadow: inset 0 0 0 1px var(--color-tinta); background-color: var(--color-papel); }
.boton--secundario:active { --canto: 0px; }

/* El llano es solo el canto: un subrayado mordido, y sigue siendo de la misma familia. */
.boton--llano {
  --canto: var(--canto-menor);
  --canto-mordida: 10px;
  background-color: transparent;
  color: var(--color-tinta-suave);
  padding-inline: var(--espacio-2);
}
.boton--llano:hover { --canto: var(--canto-secundario); color: var(--color-tinta); }
.boton--llano:active { --canto: 0px; }

/* El destructivo es de línea, no un bloque rojo: un bloque rojo pesa lo mismo que el que abre y
   acaba pulsándose por inercia. Lo que separa cancelar de mover es la distancia. */
.boton--peligro {
  --canto: var(--canto-secundario);
  background-color: var(--color-lienzo);
  color: var(--color-peligro);
  box-shadow: inset 0 0 0 1px var(--color-peligro);
}
.boton--peligro:hover { --canto: 5px; background-color: var(--color-peligro-suave); }
.boton--peligro:active { --canto: 0px; }

/* Apagado: se apaga el dibujo del canto, no el hueco, para que nada se mueva de sitio. */
.boton[disabled], .boton[aria-disabled="true"] {
  background-size: 100% 0;
  background-color: var(--color-arena);
  color: var(--color-tinta-suave);
  box-shadow: none;
  cursor: not-allowed;
  transform: none;
}
.boton--ancho { width: 100%; }

/* Dentro de un bloque de color no hay que hacer nada: el canto es currentColor y el anillo es
   una variable. */
.seccion--azul .boton--secundario,
.seccion--tinta .boton--secundario {
  background-color: transparent; color: inherit; box-shadow: inset 0 0 0 1px currentColor;
}
.seccion--azul .boton--secundario:hover,
.seccion--tinta .boton--secundario:hover { background-color: color-mix(in srgb, var(--color-papel) 14%, transparent); }
```

### 4.2 El campo de texto

En el botón el canto es la chapa levantada; en el campo es **el renglón sobre el que se escribe**, y
por eso no se hunde: engorda al enfocar. Es la misma declaración de fondo en los dos sitios, y esa es
la razón de que se reconozcan como familia.

```css
.campo { display: grid; gap: var(--espacio-2); }

/* La etiqueta va encima y existe siempre, en versales estrechas. */
.campo-etiqueta {
  font-size: var(--tipografia-tamano-micro);
  font-weight: var(--tipografia-pesos-fuerte);
  font-stretch: var(--tipografia-ancho-estrecho);
  letter-spacing: var(--tipografia-espaciado-etiqueta);
  text-transform: uppercase;
}

.entrada {
  --canto: var(--canto-secundario);
  width: 100%;
  min-height: 48px;                              /* nunca por debajo de 16 px de letra: iOS hace zoom */
  padding: var(--espacio-2) var(--espacio-3);
  padding-bottom: calc(var(--espacio-2) + var(--canto));
  background-color: var(--color-lienzo);
  color: var(--color-tinta);
  border: 1px solid var(--color-borde-fuerte);
  border-radius: var(--radio-control);
  font-size: var(--tipografia-tamano-cuerpo);
  background-image: linear-gradient(
    to right,
    currentColor 0 calc(100% - var(--canto-mordida)),
    transparent calc(100% - var(--canto-mordida))
  );
  background-repeat: no-repeat;
  background-size: 100% var(--canto);
  background-position: left bottom;
  transition:
    --canto var(--movimiento-rapido) var(--movimiento-curva),
    border-color var(--movimiento-rapido) var(--movimiento-curva);
}
.entrada::placeholder { color: var(--color-tinta-tenue); }
.entrada:hover { border-color: var(--color-tinta); }
.entrada:focus-visible {
  --canto: 5px;
  border-color: var(--color-tinta);
  outline: var(--foco-grosor) solid var(--foco-anillo);
  outline-offset: var(--foco-separacion);
}
.entrada[aria-invalid="true"] { color: var(--color-peligro); border-color: var(--color-peligro); }
.entrada:disabled {
  --canto: 0px;
  background-color: var(--color-arena);
  color: var(--color-tinta-suave);
  cursor: not-allowed;
}

/* El código que llega por SMS: cifras a 125 % y tabulares, para que el 1 no baile con el 8. */
.entrada--codigo {
  font-stretch: var(--tipografia-ancho-cifra);
  font-variant-numeric: var(--tipografia-cifras-tabulares);
  font-size: var(--tipografia-tamano-titulo-4);
  font-weight: var(--tipografia-pesos-fuerte);
  letter-spacing: 0.5em;
  text-indent: 0.25em;
}
.campo-ayuda { font-size: var(--tipografia-tamano-menor); color: var(--color-tinta-suave); }
.campo-error { font-size: var(--tipografia-tamano-menor); color: var(--color-peligro); font-weight: var(--tipografia-pesos-medio); }
```

**El dato que justifica el diseño:** la caja blanca sobre papel cal se distingue **1,10:1**, o sea
nada. Lo que identifica el campo es el canto en tinta a **18,22:1**, muy por encima del 3:1 que WCAG
pide para el límite de un control.

### 4.3 La ficha de un salón en una lista

No es una caja: es una fila. En un lenguaje de bloques, una caja con filete de 1 px es lo contrario de
lo que dice el brandbook, y además el filete que se usa hoy (`--color-borde`) se queda en **1,44:1**
sobre lienzo, que es exactamente el defecto medido por el que se descartó la dirección A.

```css
.resultados { border-top: 1px solid var(--color-borde-fuerte); }

.resultado {
  position: relative;
  display: grid;
  grid-template-columns: 64px 1fr auto;
  gap: var(--espacio-1) var(--espacio-3);
  padding: var(--espacio-3) var(--espacio-3) var(--espacio-3) var(--espacio-4);
  border-bottom: 1px solid var(--color-borde-fuerte);   /* 3,88:1, no 1,44:1 */
  background: var(--color-lienzo);
  text-decoration: none; color: inherit;
  min-height: 88px;                                      /* la fila entera es el objetivo táctil */
  align-items: center;
  transition: background-color var(--movimiento-rapido) var(--movimiento-curva),
              padding-left var(--movimiento-rapido) var(--movimiento-curva);
}
/* El filo aparece al tocar la fila y empuja el contenido. Cero relleno de color. */
.resultado::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0;
  width: var(--filo-grosor); background: var(--color-tinta);
  transform: scaleX(0); transform-origin: left;
  transition: transform var(--movimiento-rapido) var(--movimiento-curva);
}
.resultado:hover, .resultado:active { background: var(--color-papel); padding-left: calc(var(--espacio-4) + var(--filo-grosor)); }
.resultado:hover::before, .resultado:active::before { transform: scaleX(1); }
.resultado:focus-visible { outline: var(--foco-grosor) solid var(--foco-anillo); outline-offset: calc(var(--foco-separacion) * -1); }

/* El sello del local: cuadrado y a canto vivo. Un negocio no es una persona, no lleva avatar
   redondo. Y las iniciales pesan cero, que es lo que se ve en 3G antes de que baje la foto. */
.resultado__sello {
  width: 64px; height: 64px; display: grid; place-items: center; grid-row: span 2;
  background: var(--color-tinta); color: var(--color-papel);
  font-weight: var(--tipografia-pesos-display);
  font-stretch: var(--tipografia-ancho-rotulo);
  font-size: var(--tipografia-tamano-mayor);
}
.resultado__nombre { font-weight: var(--tipografia-pesos-fuerte); font-size: var(--tipografia-tamano-mayor); line-height: 1.2; }
/* La anchura hace de jerarquía dentro de la misma línea: nombre a 100 %, barrio a 87 %. */
.resultado__meta {
  grid-column: 2;
  font-size: var(--tipografia-tamano-menor);
  font-stretch: var(--tipografia-ancho-estrecho);
  color: var(--color-tinta-suave);
  font-variant-numeric: var(--tipografia-cifras-tabulares);
}
/* La fila termina en lo único que de verdad importa de un salón: la próxima hora libre. */
.resultado__hora {
  --canto: var(--canto-secundario);
  grid-column: 3; grid-row: span 2;
  display: grid; place-items: center;
  min-width: 76px; min-height: var(--espacio-toque-minimo);
  padding: var(--espacio-1) var(--espacio-2);
  padding-bottom: calc(var(--espacio-1) + var(--canto));
  background-color: var(--color-lienzo); color: var(--color-tinta);
  box-shadow: inset 0 0 0 1px var(--color-borde-fuerte);
  border-radius: var(--radio-control);
  background-image: linear-gradient(to right, currentColor 0 calc(100% - 10px), transparent calc(100% - 10px));
  background-repeat: no-repeat; background-size: 100% var(--canto); background-position: left bottom;
}
.resultado__hora b { font-stretch: var(--tipografia-ancho-cifra); font-variant-numeric: var(--tipografia-cifras-tabulares); font-size: var(--tipografia-tamano-mayor); font-weight: var(--tipografia-pesos-fuerte); line-height: 1.1; }
.resultado__hora small { font-size: var(--tipografia-tamano-micro); font-stretch: var(--tipografia-ancho-estrecho); letter-spacing: var(--tipografia-espaciado-etiqueta); text-transform: uppercase; color: var(--color-tinta-suave); }

/* El patrocinado no lleva letra pequeña: es un bloque de color dentro de la lista. */
.resultado--destacado {
  background: var(--color-tinta); color: var(--color-papel);
  --foco-anillo: var(--color-papel);
}
.resultado--destacado .resultado__sello { background: var(--color-abre); color: var(--color-abre-texto); }
.resultado--destacado .resultado__meta { color: color-mix(in srgb, var(--color-papel) 78%, var(--color-tinta)); }
.resultado--destacado::before { background: var(--color-abre); }
.resultado--destacado:hover { background: var(--color-tinta); }
.resultado--destacado .resultado__hora { background-color: var(--color-papel); color: var(--color-tinta); box-shadow: none; }

/* Cerrado hoy: el equivalente al apagado. Sin chapa de hora y con el rayado en el sello. */
.resultado--cerrado { background: var(--color-papel); cursor: not-allowed; }
.resultado--cerrado .resultado__nombre,
.resultado--cerrado .resultado__meta { color: var(--color-tinta-suave); }
.resultado--cerrado .resultado__sello { background: var(--color-arena); color: var(--color-tinta-suave); background-image: var(--trama-rayado); }
.resultado--cerrado:hover::before { transform: scaleX(0); }
```

### 4.4 La hora reservable

La pieza más importante del producto y la esencia de la marca. Una hora libre es una chapa levantada
con el canto mordido: **hay hueco**. Al elegirla el hueco se cierra, desaparece la mordida, la chapa
se hunde y se pinta del azul que remata. Una hora ocupada no es un botón apagado: **no es un botón**.

```css
.horas { display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); gap: var(--espacio-2); }

.hora {
  --canto: var(--canto-principal);
  display: grid; place-items: center;
  min-height: calc(52px + var(--canto-principal));
  padding-bottom: var(--canto);
  background-color: var(--color-lienzo);
  color: var(--color-tinta);
  box-shadow: inset 0 0 0 1px var(--color-borde-fuerte);
  border: 0; border-radius: var(--radio-control);
  font-size: var(--tipografia-tamano-mayor);
  font-weight: var(--tipografia-pesos-fuerte);
  font-stretch: var(--tipografia-ancho-cifra);           /* 125 %: las columnas cuadran */
  font-variant-numeric: var(--tipografia-cifras-tabulares);
  text-decoration: none; cursor: pointer;
  background-image: linear-gradient(
    to right,
    currentColor 0 calc(100% - var(--canto-mordida)),
    transparent calc(100% - var(--canto-mordida))
  );
  background-repeat: no-repeat;
  background-size: 100% var(--canto);
  background-position: left bottom;
  transition:
    --canto var(--movimiento-rapido) var(--movimiento-curva),
    background-color var(--movimiento-rapido) var(--movimiento-curva),
    box-shadow var(--movimiento-rapido) var(--movimiento-curva),
    transform var(--movimiento-instante) var(--movimiento-curva);
}
.hora:hover { --canto: var(--canto-alzado); box-shadow: inset 0 0 0 1px var(--color-tinta); }
.hora:active { --canto: 0px; transform: translateY(2px); }
.hora:focus-visible { outline: var(--foco-grosor) solid var(--foco-anillo); outline-offset: var(--foco-separacion); }

/* Elegida: el hueco se cerró. Sin canto y en azul, y sin moverse de sitio para que la rejilla
   siga cuadrando. */
.hora[aria-pressed="true"] {
  background-size: 100% 0;
  background-color: var(--color-acento);
  color: var(--color-acento-texto);
  box-shadow: none;
}

/* Ocupada: el rayado sustituye al canto. La misma capa de fondo, otro dibujo. */
.hora--ocupada, .hora[aria-disabled="true"] {
  background-color: var(--color-arena);
  background-image: var(--trama-rayado);
  background-size: auto;
  background-repeat: repeat;
  color: var(--color-tinta-suave);
  box-shadow: none; cursor: not-allowed; transform: none;
}
.hora--ocupada:hover { box-shadow: none; }

/* Pasada: existió y ya no. Doble clase a propósito, porque .hora--pasada a secas pierde contra
   .hora[aria-disabled="true"] y la hora pasada saldría rayada como si estuviera ocupada. */
.hora.hora--pasada {
  background-size: 100% 0;
  background-color: var(--color-papel);
  background-image: none;
  color: var(--color-tinta-tenue);
  box-shadow: none; cursor: not-allowed; transform: none;
}
.hora.hora--pasada:hover { box-shadow: none; }
```

**Tres cosas distintas que hoy se dibujan igual:** ocupada (hay alguien dentro, lleva rayado), pasada
(no hay nada que ver, solo se apaga) y libre (levantada). Medidas: 6,48:1 y 5,15:1, las dos AA.

### 4.5 La ficha de filtro y la pestaña

```css
.tira { display: flex; gap: var(--espacio-2); overflow-x: auto; padding-block: var(--espacio-1) var(--espacio-3); scrollbar-width: thin; }
.tira > * { flex: 0 0 auto; }

.ficha {
  --canto: var(--canto-secundario);
  position: relative;
  display: inline-flex; align-items: center;
  min-height: calc(var(--espacio-toque-minimo) + var(--canto-secundario));
  padding: 0 var(--espacio-3);
  padding-bottom: var(--canto);
  background-color: var(--color-lienzo);
  color: var(--color-tinta);
  box-shadow: inset 0 0 0 1px var(--color-borde-fuerte);
  border: 0; border-radius: var(--radio-control);
  font-size: var(--tipografia-tamano-menor);
  font-weight: var(--tipografia-pesos-medio);
  white-space: nowrap; text-decoration: none; cursor: pointer;
  background-image: linear-gradient(to right, currentColor 0 calc(100% - 10px), transparent calc(100% - 10px));
  background-repeat: no-repeat; background-size: 100% var(--canto); background-position: left bottom;
  transition: --canto var(--movimiento-rapido) var(--movimiento-curva),
              background-color var(--movimiento-rapido) var(--movimiento-curva),
              padding-left var(--movimiento-rapido) var(--movimiento-curva),
              box-shadow var(--movimiento-rapido) var(--movimiento-curva),
              transform var(--movimiento-instante) var(--movimiento-curva);
}
.ficha:hover { --canto: 5px; box-shadow: inset 0 0 0 1px var(--color-tinta); }
.ficha:active { --canto: 0px; transform: translateY(2px); }
.ficha:focus-visible { outline: var(--foco-grosor) solid var(--foco-anillo); outline-offset: var(--foco-separacion); }

/* Elegida: hundida, con filo y en negrita. Ninguna de las tres señales es un relleno saturado. */
.ficha[aria-pressed="true"], .ficha[aria-current] {
  background-size: 100% 0;
  background-color: var(--color-arena);
  background-image: none;
  box-shadow: inset 0 0 0 1px var(--color-tinta);
  font-weight: var(--tipografia-pesos-fuerte);
  padding-left: calc(var(--espacio-3) + var(--filo-grosor));
  transform: translateY(2px);
}
.ficha[aria-pressed="true"]::before, .ficha[aria-current]::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0;
  width: var(--filo-grosor); background: var(--color-tinta);
  border-radius: var(--radio-control) 0 0 var(--radio-control);
}
.ficha[disabled] {
  background-size: 100% 0;
  background-color: var(--color-arena); color: var(--color-tinta-suave);
  box-shadow: inset 0 0 0 1px var(--color-borde-fuerte); cursor: not-allowed; transform: none;
}

.pestanas { display: flex; gap: var(--espacio-5); border-bottom: 1px solid var(--color-borde-fuerte); }
.pestana {
  position: relative;
  background: none; border: 0;
  padding: var(--espacio-3) 0 calc(var(--espacio-3) + var(--filo-grosor));
  min-height: var(--espacio-toque-minimo);
  color: var(--color-tinta-suave);
  font-size: var(--tipografia-tamano-cuerpo);
  font-weight: var(--tipografia-pesos-medio);
  font-stretch: var(--tipografia-ancho-texto);
  cursor: pointer;
  transition: color var(--movimiento-rapido) var(--movimiento-curva);
}
/* Cada pestaña reserva de antemano el ancho que ocupará cuando esté activa y su letra pase de
   100 % a 112 %. Sin esto, elegir una pestaña mueve las otras de sitio. Requiere data-texto. */
.pestana::after {
  content: attr(data-texto); display: block; height: 0; overflow: hidden;
  font-stretch: var(--tipografia-ancho-rotulo);
  font-weight: var(--tipografia-pesos-fuerte);
  visibility: hidden; pointer-events: none;
}
.pestana:hover { color: var(--color-tinta); }
.pestana:focus-visible { outline: var(--foco-grosor) solid var(--foco-anillo); outline-offset: calc(var(--foco-separacion) * -1); }
.pestana[aria-selected="true"] {
  color: var(--color-tinta);
  font-weight: var(--tipografia-pesos-fuerte);
  font-stretch: var(--tipografia-ancho-rotulo);
}
.pestana[aria-selected="true"]::before {
  content: ""; position: absolute; left: 0; right: 0; bottom: 0;
  height: var(--filo-grosor); background: var(--color-tinta);
}
.pestana[disabled] { color: var(--color-tinta-tenue); cursor: not-allowed; }
```

Uso en el marcado: `<button class="pestana" role="tab" aria-selected="true" data-texto="Hoy">Hoy</button>`.

### 4.6 El estado de una cita

```css
/* Canto vivo (radio 0) porque no se toca. El color va en el filo macizo, que es lo único del
   sello que se ve al sol, y el nombre va escrito: quien no distingue el ámbar del verde sigue
   leyendo «pendiente». */
.estado {
  display: inline-flex; align-items: center;
  padding: 3px var(--espacio-2);
  border-left: var(--canto-principal) solid currentColor;
  border-radius: var(--radio-superficie);
  font-size: var(--tipografia-tamano-micro);
  font-weight: var(--tipografia-pesos-fuerte);
  font-stretch: var(--tipografia-ancho-estrecho);
  letter-spacing: var(--tipografia-espaciado-etiqueta);
  text-transform: uppercase;
  white-space: nowrap;
}
.estado--pendiente  { background: var(--estado-reserva-pendiente-fondo);  color: var(--estado-reserva-pendiente-texto); }
.estado--confirmada { background: var(--estado-reserva-confirmada-fondo); color: var(--estado-reserva-confirmada-texto); }
.estado--completada { background: var(--estado-reserva-completada-fondo); color: var(--estado-reserva-completada-texto); }
.estado--no_show    { background: var(--estado-reserva-no_show-fondo);    color: var(--estado-reserva-no_show-texto); }
.estado--cancelada_cliente,
.estado--cancelada_negocio { background: var(--estado-reserva-cancelada-fondo); color: var(--estado-reserva-cancelada-texto); }

/* La banda de la fila usa el color de TEXTO del estado, no el de borde: el token de borde se
   queda entre 2,14:1 y 3,52:1 sobre lienzo y al sol desaparece. No cambia la paleta, cambia qué
   token se consume. */
.agenda { border-top: 1px solid var(--color-borde-fuerte); }
.agenda__fila {
  display: grid; grid-template-columns: 62px 1fr auto;
  gap: var(--espacio-1) var(--espacio-3);
  align-items: center; min-height: 64px; width: 100%;
  padding: var(--espacio-2) var(--espacio-3);
  border: 0;
  border-bottom: 1px solid var(--color-borde-fuerte);
  border-left: var(--filo-grosor) solid var(--color-borde-fuerte);
  background: var(--color-lienzo);
  text-align: left; cursor: pointer;
}
.agenda__fila:hover:not(.agenda__fila--bloqueo) { background: var(--color-papel); }
.agenda__hora {
  grid-row: span 2;
  font-stretch: var(--tipografia-ancho-cifra);
  font-variant-numeric: var(--tipografia-cifras-tabulares);
  font-weight: var(--tipografia-pesos-fuerte);
  font-size: var(--tipografia-tamano-mayor); line-height: 1.1;
}
.agenda__hora small { display: block; font-size: var(--tipografia-tamano-micro); font-stretch: var(--tipografia-ancho-estrecho); color: var(--color-tinta-suave); font-weight: var(--tipografia-pesos-medio); }
.agenda__quien { font-weight: var(--tipografia-pesos-fuerte); }
.agenda__que { grid-column: 2; font-size: var(--tipografia-tamano-menor); font-stretch: var(--tipografia-ancho-estrecho); color: var(--color-tinta-suave); }

.agenda__fila--pendiente  { border-left-color: var(--estado-reserva-pendiente-texto); }
.agenda__fila--confirmada { border-left-color: var(--estado-reserva-confirmada-texto); }
.agenda__fila--completada { border-left-color: var(--estado-reserva-completada-texto); }
.agenda__fila--no_show    { border-left-color: var(--estado-reserva-no_show-texto); }
.agenda__fila--cancelada_cliente,
.agenda__fila--cancelada_negocio { border-left-color: var(--estado-reserva-cancelada-texto); background: var(--color-papel); }

/* Un bloqueo no es una cita: no es un botón, lleva el rayado y no tiene sello. */
.agenda__fila--bloqueo {
  border-left-color: var(--color-borde-fuerte);
  background-color: var(--color-arena);
  background-image: var(--trama-rayado);
  color: var(--color-tinta-suave);
  cursor: default; min-height: 48px;
}
```

### 4.7 Las dos tramas, el vacío y la carga

```css
.trama-pauta  { background-color: var(--color-arena); background-image: var(--trama-pauta); }
.trama-rayado { background-color: var(--color-arena); background-image: var(--trama-rayado); }

/* El vacío no es un icono triste centrado: es el papel pautado del día, sin nada escrito, que es
   justo lo que este producto sustituye. Y siempre lleva la acción que abre. */
.vacio {
  display: grid; place-items: center;
  padding: var(--espacio-6) var(--espacio-4); text-align: center;
  background-color: var(--color-arena);
  background-image: var(--trama-pauta);
  border-block: 1px solid var(--color-borde-fuerte);
}
/* El contenido va sobre un bloque de lienzo, como una nota puesta encima del papel pautado. Si el
   texto se apoya directamente en la trama, una raya lo cruza y parece tachado. Comprobado. */
.vacio__nota {
  display: grid; gap: var(--espacio-3); justify-items: center;
  background: var(--color-lienzo);
  padding: var(--espacio-5) var(--espacio-4);
  max-width: 38ch;
  box-shadow: inset 0 0 0 1px var(--color-borde-fuerte);
}
.vacio strong {
  display: block;
  font-weight: var(--tipografia-pesos-display);
  font-stretch: var(--tipografia-ancho-rotulo);
  font-size: var(--tipografia-tamano-titulo-4);
}
.vacio p { max-width: 34ch; color: var(--color-tinta-suave); }

/* Cargando: bloques macizos con un latido de opacidad. Nada de brillo que recorre la pantalla,
   que es un degradado en movimiento y aquí no hay degradados. */
.esqueleto { background-color: var(--color-arena); background-image: var(--trama-pauta); }
/* `display: block` no es decoración: a un elemento en línea no le aplican ni el alto ni el ancho,
   y el esqueleto se queda invisible. */
.esqueleto__linea, .esqueleto__sello { display: block; background: var(--color-borde-fuerte); animation: latido 1400ms ease-in-out infinite; }
.esqueleto__linea { height: 14px; }
.esqueleto__sello { width: 64px; height: 64px; }
@keyframes latido { 0%, 100% { opacity: .5 } 50% { opacity: .9 } }
```

La trama **nunca lleva encima información que dependa de ella**. En el peor caso medido, el texto que
la cruza se queda en **4,85:1**, por encima de AA.

### 4.8 La tipografía: los cuatro anchos

Hoy Archivo Variable solo se aprovecha en una cosa, que los titulares van a 112 %. El eje llega de
62 % a 125 % y lo interesante está en el otro extremo.

| Ancho | Valor | Dónde, y por qué ahí |
|---|---|---|
| **Estrecho** | `87 %` *(nuevo)* | Etiquetas en versales, metadatos de una fila, rótulos de columna, nombres de día. **El ancho hace lo que otros hacen encogiendo la letra:** «MIÉRCOLES 3 DE SEPTIEMBRE» cabe en una línea de 390 px sin bajar de 12 px. |
| **Texto** | `100 %` | Interfaz y cuerpo. |
| **Rótulo** | `112 %` | Titulares y **la pestaña activa**: el cambio de ancho se percibe antes que un cambio de gris y no gasta ni un token de color. |
| **Cifra** | `125 %` | Horas, duraciones, precios y el código de verificación, siempre con `tabular-nums`. |

```css
.rotulo { font-weight: var(--tipografia-pesos-display); font-stretch: var(--tipografia-ancho-rotulo); line-height: var(--tipografia-interlineado-apretado); letter-spacing: var(--tipografia-espaciado-titular); }
.cifra  { font-stretch: var(--tipografia-ancho-cifra); font-variant-numeric: var(--tipografia-cifras-tabulares); font-weight: var(--tipografia-pesos-fuerte); }
.estrecho { font-stretch: var(--tipografia-ancho-estrecho); }

.etiqueta-versal {
  display: inline-block;
  font-size: var(--tipografia-tamano-micro);
  font-weight: var(--tipografia-pesos-fuerte);
  font-stretch: var(--tipografia-ancho-estrecho);
  letter-spacing: var(--tipografia-espaciado-etiqueta);
  text-transform: uppercase;
}

/* El titular ensancha con la pantalla: a 390 px va a 100 % para que quepan más caracteres por
   línea, y desde 768 px se planta a 112 %. Va con media query porque font-stretch acepta un
   porcentaje puro y no admite calc() con vw. */
h1, h2, .titular-adaptativo { font-stretch: var(--tipografia-ancho-texto); }
@media (min-width: 768px) { h1, h2, .titular-adaptativo { font-stretch: var(--tipografia-ancho-rotulo); } }
```

**Tres usos concretos, no un adjetivo:**

1. **Caber sin encoger.** Una etiqueta larga a 87 % entra en una línea de 390 px con el mismo cuerpo.
   La alternativa de todo el mundo es bajar a 11 px, y ahí empiezan los problemas de verdad.
2. **Dos jerarquías en la misma línea.** El nombre del salón a 100 % y el barrio a 87 %, mismo tamaño
   y mismo color: uno manda sobre el otro sin gastar un gris nuevo.
3. **La pestaña activa.** El ancho es el indicador, con el filo como refuerzo. Y el salto de ancho se
   compensa con el `::after` invisible, así que la barra de pestañas no baila.

---

## 5. Contraste, medido

Calculado con la fórmula WCAG 2.1, el mismo código de `packages/tokens/verificar-contraste.mjs`.
AA pide 4,5:1 en texto normal y 3:1 en los límites de un control.

| Qué | Sobre qué | Pide | Mide | |
|---|---|---|---|---|
| Canto en tinta (secundario, campo, hora) | Lienzo | 3,0 | **18,22** | cumple |
| Canto en tinta | Papel cal | 3,0 | **16,35** | cumple |
| Canto en tinta dentro del botón que abre | Naranja mango | 3,0 | **6,99** | cumple |
| Canto en cal dentro del botón que cierra | Azul chiva | 3,0 | **7,90** | cumple |
| Texto tinta del botón que abre | Naranja mango | 4,5 | **6,99** | cumple |
| Texto tinta del botón que abre, al pasar | Naranja al pasar | 4,5 | **5,64** | cumple |
| Texto cal del botón que cierra | Azul chiva | 4,5 | **7,90** | cumple |
| Texto del botón apagado (tinta suave) | Arena | 4,5 | **6,48** | cumple |
| Filo del elegido y del hover (tinta) | Papel cal | 3,0 | **16,35** | cumple |
| Filete de fila (borde fuerte) | Lienzo | 3,0 | **3,88** | cumple |
| Filete de fila (borde fuerte) | Papel cal | 3,0 | **3,48** | cumple |
| Anillo de foco (tinta) | Papel cal | 3,0 | **16,35** | cumple |
| Anillo de foco (cal) en bloque de color | Azul chiva | 3,0 | **7,90** | cumple |
| Hora ocupada (tinta suave) | Arena | 4,5 | **6,48** | cumple |
| Hora pasada (tinta tenue) | Papel cal | 4,5 | **5,15** | cumple |
| Texto sobre la raya de la trama, peor caso | Rayado al 14 % | 4,5 | **4,85** | cumple |
| Sello pendiente | Su fondo | 4,5 | **7,63** | cumple |
| Sello confirmada | Su fondo | 4,5 | **8,24** | cumple |
| Sello atendida | Su fondo | 4,5 | **9,41** | cumple |
| Sello no vino | Su fondo | 4,5 | **6,48** | cumple |
| Sello cancelada | Su fondo | 4,5 | **8,10** | cumple |
| Banda de agenda con color de texto, peor caso | Lienzo | 3,0 | **7,93** | cumple |
| Fila patrocinada (papel sobre tinta) | Tinta noche | 4,5 | **16,35** | cumple |

**Y las tres que no cumplen, que están aquí porque son las opciones descartadas** y conviene que quede
escrito por qué:

| Opción descartada | Sobre qué | Mide | Por qué se descarta |
|---|---|---|---|
| Canto oscuro dentro del botón azul | Azul chiva | **2,07** | Desaparecería justo en el botón que más se pulsa. Por eso el canto es `currentColor`. |
| El filete que se usa hoy (`--color-borde`) como estructura | Lienzo / papel | **1,44** / **1,29** | Es el mismo defecto medido por el que se descartó la dirección A. Las filas pasan a `--color-borde-fuerte`. |
| El token de borde del estado como banda de la agenda | Lienzo | **2,14** peor caso | La banda pasa a usar el color de **texto** del estado. Ni un color nuevo. |

---

## 6. Lo que esta propuesta NO hace

- **No toca la paleta.** Ni un color nuevo, ni un hexadecimal escrito a mano. Lo que no sale de una
  variable sale de `color-mix()` sobre ella.
- **No usa píldoras, ni degradados decorativos, ni sombras difusas, ni glassmorphism.** La única
  `box-shadow` que aparece es `inset` de 1 px, que es un filete dibujado por dentro para que el canto
  y el borde no se peleen por la misma caja.
- **No mete el nombre comercial** en ninguna clase ni en ningún token.
- **No cambia ningún ADR.** Si algo de aquí exige cambiar una decisión, se anota como bloqueo en
  `ESTADO-GLOBAL.md` y se escala. Lo previsible es lo contrario: si se aprueba, esto **merece un ADR
  propio** que lo recoja, porque «el canto» es una decisión de forma con la misma vida que la regla de
  los dos saturados.
- **No se ha aplicado a `apps/web` ni a `packages/`.** Solo existen estos dos archivos.

---

## 7. Si se aprueba, en qué orden se aplica

| # | Paso | Zona | Riesgo |
|---|---|---|---|
| 1 | Los cinco tokens nuevos en `packages/tokens/tokens.json` y regenerar `variables.css` y `tokens.ts` | `packages/tokens` (**serializada**) | bajo, solo añade |
| 2 | Un ADR que recoja el canto, la mordida y la regla de la forma | `docs/arquitectura/adr/` (**serializada**) | ninguno |
| 3 | La capa de componentes de `apps/web/app/globales.css`, sección a sección | Frontend Web | **medio**: hay que mirar cada pantalla a 390 px en el navegador, no dar por bueno un build verde |
| 4 | Añadir `data-texto` a las pestañas y `aria-pressed` a las horas donde falte | Frontend Web | bajo |
| 5 | Repasar `apps/backoffice` con las mismas clases | Frontend Web | bajo |

**Un aviso para el paso 3:** el canto se anima con `@property`, que necesita Chrome 85, Safari 16.4 o
Firefox 128. Donde no exista, el canto se dibuja igual y los estados funcionan igual; lo único que se
pierde es la interpolación de 140 ms. No hay degradación funcional.

---

## 8. Cómo se comprueba que está bien puesto

- [ ] Con el texto tapado, **un botón de Bukeo se distingue de uno de cualquier plantilla**: tiene el
      zócalo mordido.
- [ ] Pulsar un botón **hunde el canto y baja el rótulo**, y la caja no cambia de altura ni mueve nada.
- [ ] El campo y el botón **comparten la misma línea de fondo**, y se ve que son de la misma familia.
- [ ] En una lista de salones **no hay ni una caja**: hay filas, filo al tocar y una chapa de hora.
- [ ] Una hora **libre, ocupada y pasada se distinguen sin leer el número**.
- [ ] Una ficha de filtro elegida se reconoce **en blanco y negro**.
- [ ] Los cinco estados de una cita **se leen sin distinguir colores**, porque llevan el nombre escrito.
- [ ] No hay ni una imagen de fondo: las dos tramas son CSS.
- [ ] Ni una raya larga, ni un color fuera de tokens, ni una píldora.

---

## 9. Qué hallazgo de la crítica resuelve cada pieza

La [crítica de tells](critica-tells-ia.md) §4 dejó cinco decisiones que sí tenían carácter y una
lista de lo que faltaba. Esta propuesta se construye encima de esas cinco, no al lado.

| De la crítica | Qué hace esta propuesta |
|---|---|
| «El filo naranja de 6 px es la única forma propia que se ve a un metro» | Se conserva **intacto y con su trabajo exclusivo**: cortar la página entre bloques. Por eso el filo que marca lo elegido va en **tinta** y no en naranja: si el naranja también significara «seleccionado», dejaría de significar «abre». |
| «El anillo de foco en tinta con inversión a cal: conservar la decisión y quitarle el `border-radius`» | Se conserva y pasa a ser la variable `--foco-anillo`, en vez de una lista de selectores. Sin `border-radius`. |
| «El titular que interpola con el ancho en vez de saltar por puntos de ruptura» | Se amplía: ahora interpola también **la anchura de la letra**, no solo el tamaño, y aparece un cuarto ancho (87 %) para las etiquetas. |
| «La barra de estado como filete grueso a la izquierda de la fila» | Se conserva y se corrige: pasa a usar el color de **texto** del estado (7,93:1 el peor caso) en vez del token de borde (2,14:1 el peor caso). |
| «Forma propia del icono: no existe» | **La mordida.** El icono es un bloque con una muesca calada, y ahora todo lo que se toca lleva esa muesca en su canto. |
| «Textura o grano: no existe, y el moodboard la pide por escrito» | **Las dos tramas**, el pautado y el rayado, dibujadas con CSS y sin una sola imagen. |
| «No hay la anchura de cifra donde toca» | 125 % con tabulares en horas, precios, duraciones y el código de verificación. |
| «Un botón deshabilitado a 3,4:1 por `opacity: .55`» | El apagado pierde el canto y se queda en **6,48:1**. La opacidad desaparece del sistema. |
