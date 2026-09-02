# Design system — M2G Agenda · Estado: en proceso

> El sistema de diseño de la Fase 1, documentado **sobre los tokens que ya existen** en
> [`packages/tokens/tokens.json`](../../packages/tokens/tokens.json), verificados en contraste AA y
> generados a `variables.css` para web y back-office y a `tokens.ts` para la app.
>
> Aquí no se inventa paleta ni tipografía: la decisión está tomada en
> [ADR-0013](../arquitectura/adr/0013-design-system-propio-mobile-first.md) y **un ADR decidido no
> se edita, se supera con otro**. Lo que hace este documento es explicar **cuándo se usa cada
> token** y cómo se comporta cada componente, que es justo lo que un JSON no puede decir.
>
> Los flujos que estos componentes tienen que servir están en [`FLUJOS.md`](FLUJOS.md).

---

## 1. Los principios, y por qué cada uno

**Modo claro por defecto.** `:root` define la paleta clara y el modo oscuro vive tras
`[data-tema="oscuro"]`. No es una preferencia estética: el caso de uso principal es un teléfono
dentro de un salón con luz fuerte, donde el modo oscuro pierde. El oscuro está **definido desde el
día uno** en los tokens —los mismos nombres, otros valores— precisamente para que encenderlo algún
día sea cambiar un atributo en la raíz y no un rediseño. Lo que está prohibido es escribir un color
suelto en un componente: eso es lo que convierte el modo oscuro en un proyecto.

**Mobile-first a 390 px, y eso significa diseñar ahí primero.** `--pantalla-movil` es 390px,
`--pantalla-tableta` 768px y `--pantalla-escritorio` 1120px. Las media queries van **hacia arriba**,
nunca hacia abajo. Un diseño de escritorio comprimido siempre acaba con la acción principal fuera
de pantalla, y en este producto la acción principal es reservar o mover una cita.

**Objetivo táctil de 44 px.** `--espacio-toque-minimo` es 44px y es un mínimo, no un objetivo. En la
agenda, donde se toca con prisa y con una mano, **la fila entera de la cita es el objetivo**, no un
icono a la derecha. Un icono de 24 px al borde de la pantalla es un fallo de puntería garantizado
para un pulgar que sostiene el teléfono a la vez.

**Cifras tabulares en horas, precios y duraciones.** `--tipografia-cifras-tabulares` es
`tabular-nums` y se aplica con `font-variant-numeric` a toda columna de horas, todo precio y toda
duración. Sin ello, «9:15» y «11:00» tienen anchos distintos y una columna de horas de una agenda
queda visualmente torcida; el ojo lee eso como desorden aunque no sepa por qué.

**Sin degradados decorativos.** No hay ningún token de degradado y no se va a añadir. Un degradado
tras un texto arruina el contraste medido y no comunica nada.

**Sin todo redondeado.** La escala de radios llega hasta `--radio-grande` a 8px, y `--radio-pildora`
existe **solo** para los chips de filtro y los indicadores de estado, donde la forma de píldora
transmite «esto se quita» y «esto es una etiqueta». Botones y campos usan `--radio-normal` a 4px.
Cuando todo está redondeado, el redondeo deja de significar nada.

**Fuentes: IBM Plex Sans, y las vetadas están vetadas.** Inter, Fraunces, Bricolage y General Sans
no entran. Plex Sans se elige por tres razones prácticas: dibuja bien a tamaños pequeños, que es
donde vive una fila de agenda de 14 px; tiene **cifras tabulares reales** en el archivo, no
simuladas; y es una familia abierta con formato variable que se sirve desde el propio dominio.
**Una sola familia**, y solo los pesos que se usan —400, 500 y 600, en `--tipografia-pesos-*`—.
Dos familias pesan el doble en 3G y rinden menos que una bien usada.

---

## 2. Tipografía: la escala y cuándo se usa cada tamaño

Un solo eje. `--tipografia-familia` en todo, `--tipografia-familia-cifras` para bloques puramente
numéricos donde no interesa arrastrar los fallbacks con métricas distintas.

| Token | Valor | Dónde se usa | Dónde **no** |
|---|---|---|---|
| `--tipografia-tamano-titulo-1` | 2rem · 32px | Título de página en escritorio | En móvil, casi nunca: se come una fila de agenda entera |
| `--tipografia-tamano-titulo-2` | 1.5rem · 24px | Título de pantalla en móvil, nombre del negocio en su perfil | Dentro de listas |
| `--tipografia-tamano-titulo-3` | 1.25rem · 20px | Cabecera de hoja modal, encabezado de sección | Como cuerpo destacado |
| `--tipografia-tamano-mayor` | 1.125rem · 18px | Nombre del negocio en una tarjeta de resultados, precio total en el pie | — |
| `--tipografia-tamano-cuerpo` | 1rem · 16px | Texto corrido, **todos los campos de formulario**, nombre del cliente en la fila de agenda, texto de botón | — |
| `--tipografia-tamano-menor` | 0.875rem · 14px | Servicio y duración en la fila de agenda, metadatos, texto de ayuda bajo un campo | En un `input`. Nunca |
| `--tipografia-tamano-micro` | 0.75rem · 12px | Etiqueta «Patrocinado», contadores, pie legal | Cualquier cosa que haya que leer para decidir |

**La regla que no se salta: 16 px como mínimo en cualquier campo de formulario.** Por debajo de eso,
Safari en iOS hace zoom al enfocar el campo, la pantalla se descuadra sola y el usuario acaba
haciendo pinch para volver. Vale también para el `select` y para el campo de OTP.

**Interlineado.** `--tipografia-interlineado-apretado` (1.2) en títulos y en cifras que ocupan una
línea; `--tipografia-interlineado-normal` (1.5) en texto corrido y en listas;
`--tipografia-interlineado-suelto` (1.7) solo en bloques de texto legal largos, que se leen peor.

**Pesos.** 400 para todo, 500 para el nombre del cliente y las etiquetas de campo, 600 para títulos
y para el texto del botón primario. **No se usa el peso para dar énfasis dentro de un párrafo**: para
eso está el color de texto.

---

## 3. El color se usa por función, no por tono

Los tokens de color no se llaman «verde» ni «gris-300»: se llaman `--color-acento`,
`--color-texto-suave`, `--color-peligro`. Esa es la única razón por la que el día que Luis decida el
nombre comercial (D1) cambiar la identidad será cambiar valores y no recorrer pantallas.

| Token | Función exacta |
|---|---|
| `--color-superficie` `#FFFFFF` | El fondo de la pantalla y de las tarjetas |
| `--color-superficie-suave` `#F6F5F3` | Fondo de zonas agrupadas: cabecera de lista, franja de resumen, campo deshabilitado |
| `--color-superficie-elevada` `#FFFFFF` | Hoja modal y menú, que se separan del fondo con `--sombra-hoja` o `--sombra-menu`, no con color |
| `--color-borde` `#DFDCD6` | Separadores y borde de campo en reposo. Es decorativo: no lleva información |
| `--color-borde-fuerte` `#8A857C` | Borde de campo enfocado o de control que hay que distinguir. Sí lleva información, y por eso tiene contraste ≥ 3:1 contra la superficie |
| `--color-texto` `#1B1A18` | Todo lo que hay que leer |
| `--color-texto-suave` `#5C5851` | Metadatos que acompañan: duración, categoría, distancia |
| `--color-texto-tenue` `#8A857C` | Placeholder y texto desactivado. **Nunca información necesaria** |
| `--color-acento` `#125E52` | La acción principal, el enlace, el estado seleccionado |
| `--color-acento-hover` `#0E4C42` | Puntero encima y pulsación |
| `--color-acento-suave` `#E4F0ED` | Fondo del elemento seleccionado y del aviso informativo |
| `--color-acento-texto` `#FFFFFF` | Texto sobre `--color-acento` |
| `--color-exito` `#1F7A45` | Confirmación de que algo ocurrió |
| `--color-aviso` `#9A6206` | Algo requiere atención pero nada se ha roto |
| `--color-peligro` `#A32118` | Error y acción destructiva |
| `--color-peligro-suave` `#FBEAE8` | Fondo del bloque de error |

**Tres reglas sobre el color, y las tres tienen consecuencias prácticas:**

1. **El color nunca es el único portador de significado.** WCAG 1.4.1, y además hay daltonismo en la
   sala. Un estado lleva color **y** texto; un campo con error lleva borde de peligro **y** mensaje
   escrito **y** `aria-invalid`.
2. **El acento no se usa para decorar.** Si media pantalla es del color de la acción principal,
   ninguna parte de la pantalla es la acción principal.
3. **`--color-texto-tenue` no lleva nada que haga falta.** Es el token con el contraste más bajo de
   la paleta; si un dato importa, va en `--color-texto-suave` o superior.

**Hueco conocido.** No existen `--color-exito-suave` ni `--color-aviso-suave` para los fondos de
banner de éxito y de aviso, mientras que `--color-peligro-suave` sí existe. Hasta que se añadan, el
banner de éxito usa `--color-acento-suave` con `--color-exito` en el texto y el icono, y el de
aviso usa `--color-superficie-suave` con borde en `--color-aviso`. Está anotado como deuda en §9.

---

## 4. Los cinco colores de estado de reserva

Los estados de RSV-3 tienen tokens propios con tres valores cada uno —fondo, texto y borde— porque
un indicador de estado necesita las tres cosas para leerse sobre cualquier superficie:

| Estado | Tokens | Qué comunica |
|---|---|---|
| `pendiente` | `--estado-reserva-pendiente-fondo` · `-texto` · `-borde` | Espera acción del negocio. Amarillo terroso: llama sin alarmar |
| `confirmada` | `--estado-reserva-confirmada-fondo` · `-texto` · `-borde` | Va a ocurrir. Comparte familia con el acento a propósito: es el estado normal y deseado |
| `completada` | `--estado-reserva-completada-fondo` · `-texto` · `-borde` | Ya ocurrió y salió bien. Verde, distinto del de confirmada para que no se confundan en una lista mezclada |
| `no_show` | `--estado-reserva-no_show-fondo` · `-texto` · `-borde` | El cliente no vino. **Neutro a propósito**: es un hecho administrativo, no un castigo pintado en rojo |
| `cancelada` | `--estado-reserva-cancelada-fondo` · `-texto` · `-borde` | No ocurre. Rojo apagado |

**La regla de oro: significan lo mismo en las tres superficies.** El mismo verde de `completada` en
la web pública, en el panel de negocio y en la app. Un estado que se ve distinto en cada sitio es un
estado que nadie aprende, y este producto tiene usuarios que van a mirar la misma cita desde el
móvil del salón y desde la web del cliente en la misma tarde. Por eso los tokens salen del mismo
JSON y llegan a React Native por `tokens.ts`, no por copia manual.

**Seis estados, cinco colores.** `cancelada_cliente` y `cancelada_negocio` comparten el color de
`cancelada` y se distinguen por la **etiqueta** —«Cancelada por el cliente» / «Cancelada por el
salón»— y por el evento en el historial de la reserva. Es correcto: para el ojo son lo mismo, la
cita no ocurre; la diferencia importa en el detalle, no en un vistazo a la lista.

**Nombre irregular.** `--estado-reserva-no_show-*` lleva guion bajo, heredado del valor del
enumerado de la API, mientras el resto del sistema es kebab-case. Se deja así deliberadamente: el
token vale exactamente lo que devuelve el backend, y una tabla de traducción entre nombres de
estado sería justo el sitio donde se cuela un caso sin mapear. Los enumerados del backend viajan en
minúsculas en esta API; **si algún día serializan en mayúsculas, el comparador del front necesita
fallback o la interfaz se queda sin color de estado**.

---

## 5. Espacio, forma, elevación y movimiento

**Espacio.** Escala de 4 px, de `--espacio-1` (4px) a `--espacio-8` (64px). Los saltos son
deliberadamente pocos: con nueve valores nadie inventa un `13px`. El ritmo habitual en móvil es
`--espacio-4` (16px) como margen lateral de pantalla y `--espacio-3` (12px) entre elementos
relacionados. **Márgenes verticales solo hacia abajo**, para que dos componentes apilados no
negocien quién manda.

**Radio.** `--radio-normal` (4px) en botones, campos y tarjetas; `--radio-grande` (8px) solo en la
hoja modal, y solo en sus dos esquinas superiores; `--radio-pildora` en chips de filtro e
indicadores de estado; `--radio-nada` en separadores y en elementos a sangre. `--radio-chico` (2px)
para piezas pequeñas como la barra de estado del borde de una fila.

**Sombra.** Solo dos, y las dos comunican elevación real: `--sombra-menu` para menús desplegables y
`--sombra-hoja` —que proyecta **hacia arriba**— para la hoja modal que sube desde el borde inferior.
No hay sombra de tarjeta, porque una tarjeta que no se levanta de la pantalla no está elevada; se
separa con `--color-borde`. Una sombra decorativa cuesta pintado en un teléfono de gama media y no
dice nada.

**Movimiento.** `--movimiento-rapido` (120ms) para respuestas al toque —estado pulsado, aparición de
un mensaje— y `--movimiento-normal` (200ms) para la entrada de una hoja modal, con
`--movimiento-curva`. Nada más largo. Y **todo respeta `prefers-reduced-motion`**: con la
preferencia activa las transiciones se reducen a un cambio de opacidad o desaparecen. No hay
scrollytelling ni animaciones de entrada al hacer scroll: no las hay porque están prohibidas y
porque a 3G lo que hacen es retrasar la lectura.

---

## 6. Catálogo de componentes de la Fase 1

Los componentes compartidos viven en `packages/ui` y **no dependen de la lógica de negocio**. El
móvil no consume ese paquete: comparte tokens, no componentes (ADR-0001). Todos los textos salen
del sistema de cadenas desde el primer componente, aunque solo haya español (§6 del brief).

### 6.1 Botón

Tres variantes y una sola por pantalla en la primaria.

| Variante | Fondo | Texto | Borde | Para qué |
|---|---|---|---|---|
| Primaria | `--color-acento` | `--color-acento-texto` | ninguno | La acción que hace avanzar. **Una por pantalla** |
| Secundaria | `--color-superficie` | `--color-texto` | `--color-borde-fuerte` | Alternativa válida: «Cancelar», «Volver» |
| Destructiva | `--color-superficie` | `--color-peligro` | `--color-peligro` | Cancelar una cita, borrar la cuenta |

Alto mínimo `--espacio-toque-minimo` (44px); en móvil, el botón primario ocupa el ancho completo del
contenedor, porque un botón de 120 px centrado en una pantalla de 390 obliga a apuntar.

**Comportamiento.** Al pulsar, fondo a `--color-acento-hover` en `--movimiento-rapido`. Mientras
hay una petición en vuelo el botón entra en estado de carga: **conserva su ancho**, sustituye el
texto por un indicador y queda inerte. Que no cambie de tamaño evita que el layout salte y que el
siguiente toque caiga en otro sitio. Un botón deshabilitado **siempre dice por qué** en una línea
debajo; un botón gris sin explicación es la forma más eficiente de que alguien lo pulse siete
veces.

La acción destructiva **nunca comparte fila** con la frecuente: cancelar una cita no puede estar
pegado a moverla.

### 6.2 Campo de formulario

Estructura fija: **etiqueta visible arriba** (`--tipografia-tamano-menor`, peso 500), campo, y una
línea de ayuda o de error debajo. La etiqueta va siempre; el placeholder como etiqueta es
inaccesible y desaparece justo cuando hace falta.

- Campo en reposo: borde `--color-borde`, fondo `--color-superficie`, texto
  `--tipografia-tamano-cuerpo` (16px, no negociable), alto 44px, radio `--radio-normal`.
- Enfocado: borde `--color-borde-fuerte` **más** un anillo de foco de 2px en `--color-acento`
  separado 2px del borde. Dos señales, no una.
- Con error: borde `--color-peligro`, mensaje debajo en `--color-peligro`, `aria-invalid="true"` y
  `aria-describedby` apuntando al mensaje.
- Deshabilitado: fondo `--color-superficie-suave`, texto `--color-texto-tenue`, y el porqué al lado.

**La validación se muestra al salir del campo, no mientras se escribe.** Marcar en rojo un teléfono
a medio teclear es decirle a alguien que se equivoca mientras acierta. La excepción es el contador
de caracteres, que sí es continuo.

Cada campo declara su `inputmode` y su `autocomplete`: `tel` para teléfono, `one-time-code` para el
OTP —que además permite el autorrelleno del código de iOS, y eso vale más que cualquier microcopia
en el flujo A—, `decimal` para precios.

### 6.3 Selector de fecha y hora

No es un `datepicker` genérico: es el componente que decide si la reserva ocurre.

**La fecha** es una tira horizontal de siete días con desplazamiento, cada día con su marca de
disponibilidad —**hay huecos**, **no hay huecos**— derivada de la respuesta de disponibilidad, no
adivinada. El día seleccionado se marca con fondo `--color-acento-suave`, borde `--color-acento` y
texto `--color-acento`: tres señales, porque el color solo no basta. **No hay vista de mes**: a 390
px las celdas quedan en 50 px y no admiten una marca legible.

**La hora** es una rejilla de tres columnas de botones de 48 px con separación de 8px, agrupada por
franja —mañana, tarde, noche— con encabezados. Las horas en cifras tabulares. El slot seleccionado
usa el mismo tratamiento de tres señales que el día.

**Estados que este componente tiene que resolver de verdad:**

| Estado | Qué se pinta |
|---|---|
| Cargando | Esqueleto de la rejilla con la forma real de los botones. Nunca un giro sobre pantalla en blanco: el salto de altura al llegar los datos hace que el pulgar toque otra cosa |
| Día sin huecos | Mensaje corto **y** salto a la primera fecha con huecos. Nunca una rejilla vacía |
| Semana sin huecos | «El primer hueco es el jueves 11 a las 10:15», tocable |
| Nada en 60 días | Se dice, y se ofrece el botón de WhatsApp |
| Se ocupó el hueco elegido | Los datos se recargan y el aviso aparece **sobre la rejilla**, sin diálogo modal que haya que cerrar y sin perder la selección de servicios |

El componente **no aparta ni bloquea slots** (ADR-0004): informa, no promete. Esa honestidad tiene
que estar en el texto: «Estos son los huecos ahora mismo».

### 6.4 Tarjeta de cita

El detalle de una reserva, en hoja modal desde la agenda o como pantalla en «Mis reservas».

De arriba abajo: indicador de estado; hora de inicio y de fin en cifras tabulares en el tamaño
mayor; nombre del cliente o del negocio según quién mire; servicios con duración y precio; el
profesional; las notas si las hay; y las acciones al pie, con la primaria a ancho completo y la
destructiva separada por un `--espacio-5` y una línea.

Fondo `--color-superficie`, borde `--color-borde`, radio `--radio-normal`, **sin sombra**.

### 6.5 Fila de agenda

El componente más usado del producto. Alto 72px, **toda la fila es el objetivo táctil**.

Estructura: barra de 3px del color de borde del estado en el flanco izquierdo; columna fija de horas
con inicio y fin en cifras tabulares y `--tipografia-tamano-menor`; nombre del cliente en
`--tipografia-tamano-cuerpo` peso 500; servicio y duración en `--tipografia-tamano-menor` y
`--color-texto-suave`; e indicador de estado a la derecha **solo cuando el estado no es
`confirmada`**, que es el normal y no merece ruido.

Entre citas no contiguas se pinta un separador tenue con el hueco libre —«45 min libres»— en
`--color-texto-tenue`, tocable para crear una reserva ahí. Huecos de menos de 15 minutos no se
listan: no cabe nada y gastan una fila.

**En estado pendiente de envío** —una acción encolada sin red— la fila lleva un indicador propio y
texto explícito: «Sin enviar». Jamás se pinta como confirmado algo que no llegó al servidor.

### 6.6 Hoja modal

Sube desde el borde inferior, con `--sombra-hoja`, `--radio-grande` en las dos esquinas superiores,
fondo `--color-superficie-elevada` y un velo oscuro detrás. Es el contenedor por defecto de toda
acción del panel: crear un servicio, reservar un walk-in, verificar el OTP. El motivo es de pulgar,
no de estética: el contenido aparece cerca de donde está la mano, y la pantalla de detrás sigue
visible, lo que dice sin palabras que se puede volver.

Comportamiento obligatorio: alto máximo del 90 % del viewport con desplazamiento **interno**;
cabecera con título y botón de cerrar de 44px; **el foco entra en la hoja y queda atrapado**
mientras está abierta; `Escape` y el gesto de arrastrar hacia abajo la cierran; al cerrarse, el foco
vuelve al elemento que la abrió. Con teclado en pantalla, el pie de acciones queda por encima del
teclado, no debajo.

**Una hoja no abre otra hoja.** Si un flujo lo necesita, es una pantalla.

### 6.7 Mensaje de error

Dos formatos, y no se mezclan.

**En línea**, bajo el campo que falla: texto en `--color-peligro`, `--tipografia-tamano-menor`,
enlazado por `aria-describedby`. Para errores de validación.

**En bloque**, sobre el contenido: fondo `--color-peligro-suave`, borde izquierdo de 3px en
`--color-peligro`, texto en `--color-texto` —no en rojo: un párrafo entero en rojo se lee peor—,
`role="alert"` para que el lector de pantalla lo anuncie. Para errores de servidor y de red.

**El texto dice qué pasó y qué hacer ahora, en ese orden, y no culpa a nadie.** «Ese horario se
acaba de ocupar. Estos son los huecos que quedan» es información. «Selección inválida» es un
reproche por algo que la persona no hizo mal. Y cuando hay un límite temporal se dice el número
real: «Prueba de nuevo en 45 segundos», no «inténtalo más tarde».

### 6.8 Estado vacío

Un estado vacío tiene tres partes y ninguna es una ilustración: **qué falta**, **por qué** y **la
acción que lo resuelve**, esta última como botón primario real.

| Sitio | Qué dice | Acción |
|---|---|---|
| Agenda de un día sin citas | «No hay citas el lunes 8» | «Nueva reserva» |
| Búsqueda sin resultados | Qué filtro aprieta: «8 negocios en San Francisco, ninguno con hueco hoy» | Quitar ese filtro |
| Sin servicios | «Tus clientes no pueden reservar hasta que tengas un servicio» | «Añadir servicio» |
| Sin reservas del cliente | «Todavía no has reservado nada» | «Buscar un salón cerca» |

El vacío del día sin citas **no es un error y no se pinta como tal**: un martes tranquilo es un
martes tranquilo.

### 6.9 El patrón de carga en 3G

La restricción de rendimiento del brief —Lighthouse móvil ≥ 90, disponibilidad p95 < 300 ms,
búsqueda p95 < 500 ms— no se cumple solo con backend. Las reglas de interfaz que la sostienen:

1. **Esqueleto con la forma real, no un giro.** El esqueleto de una lista tiene el alto exacto de sus
   filas. Si al llegar los datos la altura cambia, el pulgar que ya iba en camino toca otra cosa.
2. **Nada de esqueleto por debajo de 300 ms.** Un parpadeo se percibe como un fallo. Si la respuesta
   llega antes, no ha habido carga.
3. **Se pide por rango, nunca por unidad.** Una petición para la semana de agenda, una para siete
   días de disponibilidad. Siete peticiones para pintar una semana es lo que hunde la experiencia en
   3G.
4. **Las escrituras van optimistas solo cuando son reversibles y locales.** Marcar «completada» se
   pinta al instante y se revierte con aviso si falla. **Crear una reserva no es optimista jamás**:
   el servidor decide y el usuario espera, porque una cita fantasma es peor que dos segundos.
5. **Toda escritura lleva `Idempotency-Key` y se reintenta con la misma clave.** Tres intentos con
   espera creciente. Reintentar con clave nueva duplica reservas.
6. **Las imágenes se sirven dimensionadas y perezosas**, con `width` y `height` declarados para que
   no haya salto de layout, y solo las visibles en el primer pantallazo cargan con prioridad.
7. **Presupuesto de peso en las rutas indexables** (ADR-0011). Si un componente no cabe en el
   presupuesto, no entra. No es una aspiración, es un requisito del §6 del brief.

---

## 7. Accesibilidad: WCAG AA en los flujos de reserva

El brief pide AA básico en reserva. Estas son las reglas concretas, no el principio general.

**Contraste.** Ya verificado en los tokens por `verificar-contraste.mjs`, incluidos los cinco
estados de reserva. Lo que hay que mantener al construir: **el texto no se pone sobre imágenes** sin
una capa sólida detrás, y no se rebaja la opacidad de un texto para «suavizarlo» —eso rompe la
medición que ya está hecha—. Si algo tiene que ser más tenue, existe `--color-texto-suave`.

**Foco visible, siempre.** Anillo de 2px en `--color-acento` separado 2px del elemento, en **todos**
los elementos interactivos, incluidos los botones de slot y las filas de agenda. `outline: none` sin
sustituto es un defecto de accesibilidad, no una decisión estética. En elementos sobre fondo de
acento el anillo cambia a `--color-superficie` para no desaparecer.

**Orden de tabulación = orden visual.** Nada de `tabindex` positivos. En la hoja modal el foco entra
al abrir, queda atrapado dentro, y **vuelve al elemento que la abrió** al cerrar. En la rejilla de
slots, las flechas del teclado mueven entre horas y el tabulador salta la rejilla entera: veinte
tabuladores para cruzar un día es inservible.

**Etiquetas reales.** Todo campo con su `<label for>` visible. Todo botón que solo lleva icono con
`aria-label`. El campo de OTP es un `input` con `autocomplete="one-time-code"` y etiqueta, no seis
cajas sueltas sin nombre accesible.

**Tamaños mínimos.** 44 px de objetivo táctil en todo lo interactivo, y **8 px de separación** entre
objetivos adyacentes. Dos botones de 44 px pegados producen fallos de puntería igual que uno de 24.

**Los cambios se anuncian.** El bloque de error lleva `role="alert"`; el resultado de una búsqueda o
una recarga de huecos va en una región `aria-live="polite"` que dice cuántos resultados hay. Quien
usa lector de pantalla no ve que la lista cambió.

**El color nunca solo.** Estado con color y texto. Campo con error con borde, mensaje y
`aria-invalid`. Día con huecos con color, marca y texto accesible.

**Movimiento reducido.** `prefers-reduced-motion` respetado en las tres animaciones que existen.

**Zoom.** La página soporta zoom al 200 % sin pérdida de contenido ni scroll horizontal. Nada de
`user-scalable=no`.

---

## 8. Errores que no se cometen aquí

Derivados de las prohibiciones del encargo y de los casos que rompen este producto en concreto.

1. **Escribir un color, una medida o un tamaño de letra suelto en un componente.** Todo sale de los
   tokens. Es la regla que hace que el modo oscuro y el cambio de identidad sean posibles.
2. **Usar Inter, Fraunces, Bricolage o General Sans.** Vetadas por el encargo. Tampoco se cuelan por
   la puerta de atrás en un fallback ni en una librería de terceros.
3. **Degradados decorativos.** No existe el token y no se añade.
4. **Redondearlo todo.** El radio de píldora es de los chips y los estados; los botones son de 4 px.
5. **Sombras decorativas.** Solo `--sombra-menu` y `--sombra-hoja`, y solo donde hay elevación real.
6. **Scrollytelling y animaciones de entrada al hacer scroll.** Prohibidas, y además retrasan la
   lectura en 3G.
7. **Texto por debajo de 16 px en un campo de formulario.** iOS hace zoom y el diseño se rompe solo.
8. **Objetivos táctiles por debajo de 44 px** o pegados entre sí.
9. **Poner cancelar junto a mover.** Las acciones destructivas se separan de las frecuentes.
10. **Un botón deshabilitado sin decir por qué.**
11. **Un giro sobre pantalla en blanco** en vez del esqueleto con la forma real.
12. **Pintar como confirmado algo que no llegó al servidor.** Ni en la agenda sin red, ni en una
    reserva optimista. Crear una reserva nunca es optimista.
13. **Un error genérico donde hay un motivo concreto.** «Ese horario se acaba de ocupar» tiene un
    motivo; «algo salió mal» no informa de nada.
14. **Perder lo que la persona escribió** al fallar una petición. Ni el walk-in a medio rellenar, ni
    la review de tres párrafos.
15. **Enseñar el teléfono del negocio en el HTML.** El click-to-chat se resuelve en servidor; si no,
    alguien raspa la base entera en una tarde.
16. **Que «Patrocinado» se disfrace de adorno** o que llene el primer pantallazo. Máximo 2 de cada
    10, etiquetado y legible, y nunca ocultando a los orgánicos.
17. **Meter el nombre comercial a fuego** en un componente. Está sin decidir (D1) y sale de
    configuración.
18. **Un string escrito directamente en JSX.** Todos externalizados desde el primer componente,
    aunque hoy solo haya español.
19. **Un color de estado distinto en la web y en la app.** Los cinco estados salen del mismo JSON.
20. **Dar una pantalla por buena con un build verde.** Se mira en el navegador y a 390 px. La CSP, el
    runtime y el diseño no salen en un build.

---

## 9. Deuda de este documento

Va aquí y **también al tablero**, porque nada pendiente vive solo en prosa.

| Deuda | Por qué importa | Estado |
|---|---|---|
| Faltan `--color-exito-suave` y `--color-aviso-suave` | Los banners de éxito y aviso usan hoy sustitutos de otra familia; existe el equivalente de peligro | sin iniciar |
| No hay token de anillo de foco | El anillo se describe aquí en prosa; debería ser `--foco-anillo` para no reinventarlo por componente | sin iniciar |
| No hay token de opacidad de velo de la hoja modal | Misma razón | sin iniciar |
| `--color-superficie-elevada` es idéntico a `--color-superficie` en claro | Correcto por diseño —la elevación la da la sombra— pero conviene dejarlo escrito para que nadie lo «arregle» | resuelto aquí |
| El modo oscuro está definido y sin construir | Es Fase 1 solo en tokens, por ADR-0013 | fuera de alcance de la Fase 1 |
| Inventario de componentes de Fase 2 | Este catálogo cubre la Fase 1; mapa, filtros y reviews necesitan su vuelta | sin iniciar |
