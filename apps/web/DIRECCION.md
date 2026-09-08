# Dirección C · «La hora primero» — Estado: completado

> **En una frase:** el producto no es un catálogo de salones, es una lista de **horas
> concretas con un nombre detrás**, y todo —la portada, la búsqueda, la ficha, la reserva y la
> agenda del salón— está ordenado por *cuándo* y no por *qué*.

---

## La idea que la sostiene

Una clienta en Panamá no navega un directorio de peluquerías. Tiene **un hueco** —hoy después
del trabajo, el sábado antes del mediodía— y una pregunta muy concreta: *¿quién me puede
atender dentro de ese hueco?*

Los buscadores de reservas están construidos al revés: primero eliges negocio, luego servicio,
luego persona y al final descubres que no hay hora. Se recorren cuatro pantallas para llegar al
único dato que decide la compra, y ese dato aparece el último.

Aquí la hora va delante. La portada pregunta **cuándo puedes**, no qué buscas. Cada resultado
lleva pegada su primera hora libre de verdad —calculada por el motor de disponibilidad, no
inventada— y esa hora es un botón que lleva a reservar. Y la marca dice exactamente eso: una
tanda es el turno que vuelve, y lo que se vende es el turno.

De ahí salen tres decisiones que ninguna otra pantalla del producto contradice.

---

## Las tres decisiones que la distinguen

### 1 · La unidad del producto es una hora con nombre, no un salón

La portada abre con un bloque cobalto que es un reloj: **«Dime cuándo puedes y te digo con
quién»**, con cuatro fichas —ahora mismo, hoy, mañana, cualquier día— y un campo de texto
debajo, no encima. La lista que sigue no se titula «Salones cerca de ti» sino **«Turnos que
salen hoy»**, y cada fila termina en un bloque fucsia con una hora: `hoy · 3:00 p. m.`

Cada fila tiene **dos objetivos distintos y los dos miden 44 px**: el nombre lleva a la ficha
(cobalto, que abre e informa) y la hora lleva a reservar (fucsia, que cierra). No hay que
apuntar con el pulgar para elegir entre «mirar» y «coger».

*Por qué:* porque el dato que decide es la hora, y ponerla al final del embudo es lo que hace
que la gente abra cuatro salones y no reserve en ninguno. Y porque la API ya lo da:
`con_proxima_hora=true` calcula la primera hora libre de cada salón. Estaba ahí y nadie la
pintaba.

*Lo que cuesta:* la búsqueda pide una consulta de agenda por salón. Se paga a propósito y se
tapa con un estado de carga que dice qué está pasando: «Buscando y calculando la primera hora
libre de cada salón».

### 2 · A 390 px el día del salón es un riel de horas, no seis columnas

El encargo pide que el dueño vea «los calendarios de todas las personas del local». La lectura
literal es seis columnas. En un móvil de 390 px, seis columnas son **seis rendijas de 55 px**
donde no cabe el nombre de la clienta: el dueño acaba haciendo zoom para leer una cita, que es
justo lo que no puede pasar en la mañana de un sábado.

Aquí el día es **una sola columna de horas de arriba abajo**, con las dos personas
entrelazadas y el nombre de quien atiende **dentro** de cada bloque. Se lee de un vistazo quién
entra por la puerta y a qué hora. A partir de 1024 px el mismo día se abre en columnas, una por
persona, que es cuando esa forma sí ayuda. *(Comprobado: a 390 px `.riel` visible y `.columnas`
oculto; a 1280 px, al revés, con una columna por persona.)*

Y una decisión de producto que vino de mirarlo con datos de verdad: **las citas canceladas no
se pintan por defecto**. Una cita cancelada no es tiempo ocupado, es tiempo libre; mezclarlas
obliga a leer el estado de cada bloque para saber quién viene. Hay un botón —«Ver las N canceladas»— porque cuántas se cayeron sí importa a fin de mes.

El color de cada bloque es el del **estado** de la cita (`estado-reserva-*`), nunca el cobalto
ni el fucsia de marca: un estado no es una acción, y confundirlos hace que la gente toque lo
que no debe.

### 3 · Cada paso vive en una URL. Cero ventanas emergentes

El servicio, la persona, el día y la hora elegida están **en la barra de direcciones**. Se
vuelve atrás con el botón del navegador, se recarga sin perder la hora, se le pasa el enlace a
alguien y se recupera después de entrar. Los filtros de la búsqueda son enlaces, no botones con
memoria: funcionan con el JavaScript apagado.

No hay una sola ventana emergente en todo el producto. Cancelar una cita no abre un diálogo: **la
fila se convierte en su propia pregunta**, con el sí y el no a la vista, encima del dato que
hay que leer antes de decidir. Un diálogo en un móvil tapa exactamente eso.

*Consecuencia medible:* cuando la API contesta **409 «Ese horario se acaba de ocupar»**, no se
pierde el camino. Se enseña su mensaje **donde estaba la hora**, se vuelven a pedir los huecos
de ese día y se sigue. Está probado robando la hora de verdad por la API mientras la clienta
mira el resumen.

---

## Lo que hay debajo, en dos párrafos

**Nada está inventado.** Todo lo que se pinta sale de `http://localhost:8000`. Lo público
(portada, búsqueda, ficha, perfil) se pinta en el servidor con `Suspense`, así que la cabecera
del salón se ve antes de que la agenda termine de calcularse y el estado de carga es real, no
decorativo. Lo que cambia con cada toque (huecos, sesión, envío) va en el navegador. Lo único
que se cachea en toda la web son las categorías de la plataforma, cinco minutos: una agenda
cacheada es una agenda mentirosa.

**La hora que se pinta es la del salón**, no la del navegador: la API devuelve la zona horaria
de cada negocio y se usa siempre esa. Y los seis estados del contrato se traducen: la API sirve
`cancelada_cliente` y `cancelada_negocio`, que son dos cosas distintas para el negocio pero
comparten la familia de color `cancelada`, que es la única que definen los tokens.

---

## Cómo se levanta

La API tiene que estar corriendo en `http://localhost:8000` con los datos de ejemplo cargados.
Solo acepta el origen `http://localhost:3400`.

```bash
cd /Users/luisgomez/Desktop/kraken/m2g-bookings/.claude/worktrees/agent-ac64aedc6a80f0a09
pnpm install
pnpm --filter @agenda/web dev      # arranca en http://localhost:3400
```

No hace falta `.env`: `NEXT_PUBLIC_API_URL` y `NEXT_PUBLIC_NOMBRE_COMERCIAL` tienen valor por
defecto (`http://localhost:8000` y el nombre del ADR-0022, que vive **solo** en `lib/marca.ts`).

**Credenciales** (contraseña de las dos: `demo-panama-2026`):

| Quién | Correo |
|---|---|
| Clienta | `abdiel@demo.pa` |
| Dueño | `dueno.barberia-el-cangrejo@demo.pa` |

---

## Los cinco caminos, con sus URL exactas

### 1 · Descubrir

1. <http://localhost:3400/> — la portada. Escribe `corte` en «Qué necesitas» y pulsa **Buscar**.
2. <http://localhost:3400/buscar?texto=corte> — resultados, cada uno con su primera hora libre.
3. Pulsa el nombre de un salón → <http://localhost:3400/salon/barberia-el-cangrejo>

Sus tres estados:
- **Cargando:** cualquiera de las dos anteriores en la primera visita (el bloque «Buscando y
  calculando la primera hora libre de cada salón»).
- **Vacío:** <http://localhost:3400/buscar?texto=zzzzz>
- **Error:** <http://localhost:3400/buscar?simular=error> — la pantalla pide **de verdad** una
  ruta que la API no sirve y enseña el error que devuelva. No hay ningún error de mentira
  escrito en un componente.
- **No publicado:** <http://localhost:3400/salon/no-existe-este-salon>

### 2 · Elegir persona

1. <http://localhost:3400/salon/barberia-el-cangrejo> — «¿Con quién quieres ir?» va **encima**
   de la carta de precios.
2. Pulsa **Su perfil** → <http://localhost:3400/salon/barberia-el-cangrejo/con/kevin-ortega>

Ahí están los años detrás de la silla, las citas atendidas, las clientas distintas, la bio, el
Instagram, lo que hace, sus reseñas con la respuesta del salón y **sus horas libres de verdad**
de los próximos siete días, agrupadas por día. La otra persona del equipo es
<http://localhost:3400/salon/barberia-el-cangrejo/con/yaritza-beitia>.

### 3 · Reservar

1. <http://localhost:3400/reservar/barberia-el-cangrejo>
2. **1 · Qué** — pulsa `Corte clásico`. Se pueden encadenar varios (corte + barba).
3. **2 · Con quién** — `Con Kevin`, o `Me da igual quién · quiero la hora más pronta`, que pide
   los huecos del salón entero y reserva con quien traiga el hueco.
4. **3 · Cuándo** — elige día y hora. Fíjate en la URL: lleva `servicio`, `profesional`, `dia` e
   `inicio`.
5. **4 · Confirmar** — sin sesión sale **Entrar y confirmar**, que vuelve aquí con todo puesto.
6. Confirmada → **Ver mis citas** → <http://localhost:3400/mis-citas>

Sus tres estados: cargando al pedir los huecos de cada día; **vacío** si eliges un día lleno
(«Ese día está lleno»); **error** con el 409, que se puede provocar reservando la misma hora
desde otro navegador.

También se llega por atajo desde una hora concreta del perfil de la persona, y desde el botón
fucsia de cualquier fila de resultados.

### 4 · Entrar

1. <http://localhost:3400/entrar>
2. Con el correo y una contraseña mala: sale el mensaje de la API, el campo queda marcado con
   `aria-invalid`, el foco vuelve a la contraseña y **el correo se conserva**.
3. Con `demo-panama-2026` entra. Si además trabajas en un salón, te pregunta a qué vienes.

El botón arranca inhabilitado con los campos vacíos y pasa por sus seis estados.

### 5 · El salón

1. <http://localhost:3400/entrar> con `dueno.barberia-el-cangrejo@demo.pa`.
2. **La agenda del salón** → <http://localhost:3400/local>
3. El día en un riel de horas, con las fichas Ayer / Hoy / Mañana / el día siguiente, tres
   cifras arriba (citas del día, personas trabajando, lo que se factura) y el botón de encender
   las canceladas (que en los datos de ejemplo son unas cuantas: son las pruebas de esta ronda). Ensancha la ventana por encima de 1024 px y el mismo día se abre en columnas.

Sin sesión, <http://localhost:3400/local> enseña su estado propio y la puerta de entrada.

**Extra:** <http://localhost:3400/esto-no-existe> también es una pantalla entera.

---

## Cómo comprobar los siete descartes sin fiarte de mí

Los seis verificadores viven en `apps/web/verificacion/` y hablan con el navegador de verdad a
390 px. Con el servidor levantado:

```bash
cd apps/web
node verificacion/recorrer.mjs     # 15 pantallas: ancho, AA, animaciones, cabecera y pie
node verificacion/caminos.mjs      # los 5 caminos con toques reales, midiendo AA en cada paso
node verificacion/tokens.mjs       # D1 · cero hexadecimales y color solo de tokens
node verificacion/forma.mjs        # D3 · dos radios y ni un degradado
node verificacion/movimiento.mjs   # D6 · nada en bucle y todo apagable
node verificacion/botones.mjs      # D2 · los seis estados, provocados y fotografiados
```

Lo que dan hoy:

| Descarte | Cómo se comprueba | Resultado |
|---|---|---|
| **D1** · ni un hexadecimal ni una familia a mano | `grep` sobre `.css`/`.ts`/`.tsx` **y** los colores que el navegador acaba pintando en las 15 pantallas, contrastados contra `tokens.json` | 0 hexadecimales · **31 770 colores medidos, todos de los tokens** · dos únicas familias: Public Sans y Familjen Grotesk |
| **D2** · nada a medias | Los seis estados provocados sobre el botón real de `/entrar`, con `getComputedStyle` de cada uno | **los seis se pintan distintos**; cabecera y pie en las 15 pantallas |
| **D3** · cero redondeo y degradado decorativos | Todos los `border-radius` y `background-image` calculados | **9 128 radios medidos: solo 0 y 4 px** · 0 degradados · la píldora no aparece ni en los avatares |
| **D4** · se navega contra la API | Los cinco caminos con clics reales; la reserva se crea y se cancela de verdad | **los cinco enteros** |
| **D5** · 390 px primero | `document.documentElement.scrollWidth` en cada pantalla y en cada paso | **390 en las 15 pantallas y en los 22 pasos de los caminos** |
| **D6** · movimiento con motivo | `document.getAnimations()` quieta, esperando y con `prefers-reduced-motion` | **0 animaciones en una pantalla quieta** · 1 sola mientras se espera, y muere con la respuesta · con movimiento reducido, 0,001 s |
| **D7** · AA de verdad | Contraste calculado sobre el color y el fondo **efectivos** de cada nodo con texto, en la pantalla renderizada | **1 361 combinaciones solo en el barrido, ninguna por debajo del mínimo** (4,5:1, o 3:1 si el texto es grande) |

Dos cosas que salieron **solo** por medir en la pantalla y no en la paleta, y que están
arregladas:

- Una ficha elegida cambiaba de fondo y de letra a la vez con un fundido de 120 ms. En el punto
  medio el rótulo y el fondo eran el mismo gris: **1:1**. Invisible durante un octavo de
  segundo, y ninguna revisión de la paleta lo habría visto.
- El botón que pasaba de fucsia a arena tenía un instante a **2,48:1**.

De ahí sale la regla escrita en la hoja: **se anima el movimiento —el canto, el alzado, el
hundimiento—, nunca el color**. El color dice qué es cada cosa, y una cosa no puede estar a
medias entre dos significados.

---

## Lo que NO hay

Para que nadie lo tenga que descubrir usándolo:

- **Registro.** Se entra con las cuentas que ya existen; `POST /auth/registrar` no tiene
  pantalla.
- **Mapa.** El encargo lo pide y la API lo sirve (`/publico/mapa`). No está: no es ninguno de
  los cinco caminos y prefiero cinco caminos enteros que seis a medias.
- **Escribir una reseña, reprogramar una cita y el alta del local en tres pasos.** La API los
  sirve; no son de esta ronda.
- **El resto del portal del dueño** —finanzas, mejor del mes, publicidad flash, fichaje,
  personas del local—. El camino 5 pide «ver su agenda del día» y eso es lo que hay. Los
  endpoints existen y la navegación está preparada para colgarlos.
- **Fotos.** No es una decisión: en los datos de ejemplo **no hay ninguna**, la API devuelve 404
  en `/fotos/*`. Donde iría una foto hay un bloque de color con la inicial, que es coherente con
  la dirección y no miente. Con fotos de verdad, ese bloque es el hueco donde entran.
- **Modo oscuro.** Definido en los tokens y sin encender, como manda el ADR-0022.
