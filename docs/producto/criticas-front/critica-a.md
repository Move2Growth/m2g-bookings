# Crítica de la dirección A · «Te toca» — Estado: completado

> Ronda adversarial a ciegas del 8 de septiembre de 2026. Crítico: QA / Validador.
> Juzgada contra `docs/producto/LISTON-FRONT.md` y **solo** contra eso.
> Todo lo que sigue está medido por mí, en un navegador a 390 px contra `http://localhost:3200`
> y la API en `:8000`. **No se ha aceptado como prueba nada de `apps/web/verificacion/`**:
> cada descarte se volvió a medir por fuera.
>
> Código juzgado: `/Users/luisgomez/Desktop/kraken/m2g-bookings/.claude/worktrees/agent-a5c6c6cf6ce25de67/apps/web`

---

## Veredicto en una línea

**Rechazada: falla D7.** Seis descartes de siete están limpios y los cinco caminos casi todos
enteros, pero la mitad de D7 que habla de **elementos de interfaz** no solo no se cumple: es
que su propio verificador **nunca la mide**.

---

## 1 · Los siete descartes, uno a uno

### D1 · Ni un hexadecimal, ni una familia tipográfica a mano — **PASA**

| Qué comprobé | Cómo | Resultado |
|---|---|---|
| Hexadecimales en el CSS de la propuesta | `grep -rnE "#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?\b" --include="*.css" --include="*.tsx" --include="*.ts"` sobre `apps/web` (fuera `node_modules`, `.next`, `verificacion`) | **0** |
| El carácter almohadilla en la hoja | `grep -n "#" app/globales.css` sobre 1.287 líneas | **0**. El archivo no contiene ni una |
| Colores por otra vía | `grep -rnE "\b(rgb|rgba|hsl|hsla|oklch|lab)\("` y nombres CSS (`white`, `black`, …) | **0** en ambos |
| Que no tape los tokens tras importarlos | Listé **todas** las declaraciones de custom property de `globales.css`: 21, y las 21 valen `var(--otro-token)`, `transparent` o `currentColor` | Nada literal |
| Que no haya hecho trampa tocando la fuente de verdad | `git diff --name-only development -- packages apps/api scripts infra` | **vacío**: `packages/tokens` intacto |
| Familias escritas a mano | En el navegador: `--tipografia-familia` computa a `'texto', 'texto Fallback', "Helvetica Neue", Arial, sans-serif`; los nombres `rotulo`/`texto` los genera `next/font/local` y la cadena de reserva sale de `tokens.tipografia.familia` (`lib/fuentes.ts`) | Ninguna familia literal en `apps/web` |
| Que las fuentes sean las que dice y no un parecido | Tabla `name` de los dos `.woff2` con `fontTools` | `rotulo-latin.woff2` → **Familjen Grotesk**; `texto-latin.woff2` → **Public Sans**. Los dos cargan con HTTP 200 y `document.fonts` los da `loaded` |

Este descarte no está aprobado por grep: está aprobado porque además **la pantalla pinta lo que
dice la paleta**, que es donde se rompió la vez anterior.

### D2 · Nada a medias — **PASA**

Medí los seis estados sobre un botón **real** de la aplicación (el de enviar de `/entrar`), y
recortando **siempre la misma región de pantalla**: si recortas la caja del botón, la caja se
mueve con el `transform` y la diferencia entre «encima» y «pulsado» se anula sola. Con la caja
móvil salían idénticos (22 px de diferencia sobre 89.760); con la región fija, no.

| Estado | Lo medido |
|---|---|
| Reposo | fondo `rgb(200,30,100)`, canto interior de 4 px `rgb(163,24,79)` |
| Encima | fondo `rgb(163,24,79)`, canto de 6 px, `translateY(-2px)` |
| Pulsado | fondo `rgb(163,24,79)`, **sin canto**, `translateY(+4px)` |
| Foco | `outline: rgb(16,16,20) 3px` (tinta, no color de marca) |
| Cargando | texto cambia a «Entrando…», `aria-busy="true"`, `disabled`, **conserva el fucsia**, `cursor: progress` |
| Inhabilitado | fondo `rgb(237,237,233)`, texto `rgb(92,92,102)`, `cursor: not-allowed` |

Diferencia píxel a píxel de los cinco capturados en el mismo encuadre: **los diez pares
difieren**, el par más parecido en 18.874 px de 89.760. Cargando ≠ inhabilitado, que es
exactamente el fallo que se citó como textual.

Pantallas enteras: comprobé `document.querySelector('header')` y `footer` en **18 paradas**,
incluidas las cuatro que nadie entrega —vacío, 404, error de la API y API caída—. **Cabecera y
pie en las dieciocho.**

### D3 · Cero redondeo y cero degradado decorativos — **PASA**

- Estático: `grep -rniE "gradient"` sobre todo el css/tsx/ts de `apps/web` → **0**.
- En la pantalla renderizada, recorriendo `getComputedStyle` de todos los elementos visibles en
  **15 estados de pantalla a 390, 768 y 1440 px**: elementos con `background-image` que case
  `/gradient/` → **0**.
- Radios calculados en esos mismos 15 estados: **el único valor no cero de todo el documento es
  `4px`** (de 4 a 540 elementos según la pantalla). Nada de 12 px, ninguna píldora, superficies
  a 0. `4px` es `--radio-control` y solo lo llevan cosas que se tocan.

### D4 · Se navega de verdad contra la API — **PASA**

- Un único punto de entrada: `lib/api.ts:15` `export const API = process.env.NEXT_PUBLIC_API ?? 'http://localhost:8000'`,
  con un solo `fetch` en la línea 48. `grep -rnE "const (DATOS|MOCK|FALSOS|EJEMPLO|demo)"` → **0**.
- Registré todas las peticiones del navegador. La portada dispara
  `GET /api/v1/catalogo/categorias`, `GET /api/v1/publico/profesionales?orden=nota` y
  `GET /api/v1/publico/buscar?con_proxima_hora=true`. Reservar dispara
  **una sola** `GET /api/v1/publico/profesionales/{id}/disponibilidad?desde=…&hasta=…` para los
  siete días —lo comprobé contando las peticiones tras marcar el servicio: **1**, no 7—.
  Confirmar dispara `POST /api/v1/mi/reservas`. Cancelar, `POST /api/v1/mi/reservas/{id}/cancelar`.
- Contrasté lo que pinta con lo que responde la API: «Kevin Ortega · 9 años · 18 citas
  atendidas · 4 personas distintas», los cuatro servicios a B/. 12.00 / 18.00 / 8.00 / 10.00, y
  el «CERRADO AHORA» de la ficha, que coincide con `abierto_ahora: false` de
  `/api/v1/publico/negocios/barberia-el-cangrejo` porque en Panamá eran las 02:36.

### D5 · 390 px primero — **PASA**

`document.documentElement.scrollWidth` medido en **cada parada a la que llegué haciendo clic**:
portada sin sesión, portada con sesión, buscar, resultados de personas, resultados de locales,
búsqueda vacía, ficha de salón, perfil de persona, reservar (sin servicio / con huecos / con la
barra), confirmación, mis citas, agenda del local, entrar, error de contraseña, 404, error de la
API y API caída.

**En las dieciocho: `scrollWidth` = `clientWidth` = 390.** Repetido a 768 y a 1440: también
iguales. Y la medida es honesta porque `html` **no** lleva `overflow-x: hidden` (comprobado en
`globales.css`), que es lo que la falsearía.

### D6 · Movimiento con motivo — **PASA**

- Un solo `@keyframes` en toda la hoja (`sube`). `grep` de `infinite` y `alternate` → **0**.
- Medido en pantalla al elegir hora: `animation-name: sube`, `duration: 0.24s`,
  `iteration-count: 1`, y el `transform` va de `translateY(25.5px)` a `0`. Sube desde el borde
  de abajo, una vez, y porque has tocado algo.
- **La espera no se anima**: con la API frenada 9 s, dos fotogramas separados 800 ms difieren en
  **2 píxeles de 936.000** (ruido de antialiasing), y la lista de elementos con
  `animationName !== 'none'` está vacía. Lo que se ve son bloques grises quietos con la forma de
  lo que viene y un «Cargando categorías…».
- Con `prefers-reduced-motion: reduce`: `sube` baja a `1e-06s` y el `transform` del botón al
  pasar por encima pasa de `matrix(1,0,0,1,0,-2)` a `none`. **Se apaga de verdad.**

### D7 · AA de verdad — **NO PASA**

**La mitad del texto está impecable.** Mi propio medidor (color calculado del elemento contra el
fondo opaco real de sus antepasados, con mezcla por alfa, y umbral 4,5 / 3 según tamaño y peso)
recorrió ~114 elementos con texto por pantalla en **15 estados a 390, 768 y 1440 px, con sesión
y sin ella**: **cero fallos**.

**La mitad de los elementos de interfaz falla, y falla en las dos pantallas que más importan.**
Medido con un barrido de píxeles sobre la captura, no con teoría de CSS:

**(a) El botón «Buscar» de la portada — 1,64:1.** Es el fucsia sobre el bloque cobalto. Barrido
vertical cruzando su borde superior, en píxeles reales de la pantalla renderizada:

```
  y=291: (27, 52, 196)   ← cobalto
  y=292: (200, 30, 100)  ← fucsia
```

No hay nada en medio: ni borde, ni anillo. `#C81E64` contra `#1B34C4` = **1,64:1**. Y su único
canto, el de abajo, es `--color-cierra-hover` `#A3184F`, que contra ese mismo cobalto mide
**1,20:1**. Los cuatro lados por debajo de 3:1 y ninguno compensa a otro. Es el botón principal
de la primera pantalla del producto.

**(b) Las cuatro opciones de servicio de la pantalla de reservar — 1,38:1.** Son los botones con
los que se abre el camino de reservar. Barrido horizontal cruzando el borde izquierdo:

```
  x=23: (251, 251, 249)  ← papel
  x=24 … x=35: (216, 216, 210)  ← el filo, 6 px de --color-borde
  x=36: (255, 255, 255)  ← el relleno del control
```

`#D8D8D2` contra `#FBFBF9` = **1,38:1**; y el relleno blanco contra el papel, **1,04:1**. Solo
la opción **elegida** se pinta con cobalto (8,68:1); las tres que todavía no has elegido —que son
justo las que tienes que poder distinguir para elegir— están delimitadas por un filo que no llega
ni a la mitad del mínimo.

**(c) El mismo patrón, a 1,75:1**, en las chapas de categoría dentro del bloque cobalto: la
regla `.bloque--cobalto .boton--secundario` cambia fondo, color y `--canto-color`, pero **no**
toca el anillo de 1 px, que sigue siendo `--color-borde-fuerte` `#6E6E68` sobre cobalto.

**Y por qué se le coló:** su propio `verificacion/contraste.mjs` **solo mide texto**. Su
cabecera lo dice con todas las letras: *«Sale con error si algo baja de 4,5:1 en texto normal o
de 3:1 en texto grande»*. El 3:1 lo aplica al **texto grande**, nunca a un elemento de interfaz.
La mitad de D7 que falla es exactamente la mitad que su verificación no comprueba. Por eso el
documento puede decir «34 pantallas-estado, cero por debajo de AA» y ser verdad y estar
incompleto a la vez.

**Un descarte fallado es un rechazo. D7 está fallado.**

---

## 2 · Los cinco caminos, recorridos a clics

No escribí ni una URL en la barra salvo para volver al punto de partida: campo, escribir, botón,
enlace.

### Camino 1 · Descubrir — **entero**

Portada → clic en el campo → «barber» → clic en **Buscar** → `/buscar?texto=barber`, que llega
con las dos listas y **sus cuentas antes de tocar nada**: «Personas · 3 · Locales · 2» → clic en
la pestaña **Locales** → clic en **Barbería El Cangrejo** → ficha. Cuatro paradas, `scrollWidth`
390 en las cuatro, cero errores de JavaScript, cabecera y pie en todas. La ficha abre por **su
gente** (Kevin Ortega y Yaritza Beitía con nota, años y citas atendidas) y los precios van
debajo.

### Camino 2 · Elegir persona — **entero**

Desde la ficha, clic en **«Ver su perfil y sus horas»** → perfil de Kevin Ortega con lo que pide
el listón y algo más: 4,3 de 10 reseñas, **9 años de oficio**, 18 citas atendidas, 4 personas
distintas, su biografía, los cuatro servicios que hace, sus diez reseñas con la respuesta del
salón, y su Instagram. Sin fotos, porque no las hay, y lo dice: «Todavía no ha subido fotos de su
trabajo».

### Camino 3 · Reservar — **se rompe en el último paso, y solo en 4 de los 7 días que ofrece**

Lo que sí funciona, y funciona bien: clic en **Reservar con Kevin** → marcar **Corte + barba** →
la semana entera aparece de un tirón (martes 21 huecos, miércoles 23, jueves 21, viernes 23,
sábado 14, **domingo «sin huecos · Ese día no queda nada libre con esta persona»**, lunes) con
**una sola petición** → clic en una hora → la barra de cierre sube desde el borde y se queda
pegada abajo (`position: sticky`, `top: 739` de una ventana de 844 **aunque elijas la primera
hora del primer día**, o sea que no hay que buscarla) → **Confirmar** → `POST /api/v1/mi/reservas`
→ pantalla «LISTO · Te toca en 6 días» con con quién, dónde, cuándo (18:00 – 18:45) y total.

**Dónde se rompe:** el paso siguiente del listón es «verla en mis citas». Reservé *Corte + barba
con Kevin Ortega, lunes 14 de septiembre a las 18:00* (respuesta 200, id `01a07ff7-3e4d-…`) y
pulsé **Ver mis citas**. En esa pantalla:

- «14 de septiembre» → **no aparece**
- «Kevin» → **no aparece**
- la cabecera sigue diciendo **«30 por venir · 30 en el historial»**, los mismos 30 de antes

Comprobado contra la API para saber de quién es la culpa: `GET /api/v1/mi/reservas` devuelve
**exactamente 30 futuras y 30 pasadas, sin ningún parámetro de paginación** (lo confirmé en el
`openapi.json`: el único parámetro es `authorization`), y las 30 futuras de la semilla se acaban
el **10 de septiembre**. Todo lo que se reserve del 11 en adelante cae fuera de la ventana y no
existe para esa pantalla.

Lo repetí con un hueco cercano —**Corte niño, hoy a las 09:00**— y ahí **sí** sale, la primera de
la lista, marcada «La siguiente». Así que el camino se cierra para los 3 primeros días de los 7
que la pantalla ofrece, y se queda a medias para los otros 4. La pantalla ofrece siete días; el
camino solo llega al final en tres.

**Extras que probé porque el listón pide los estados y porque si no falla es que no se ha
probado bastante:**

- **Hueco ocupado (409), de verdad y no simulado:** dos pestañas, misma persona, mismo servicio,
  mismo hueco. Una reserva y en la otra un `role="alert"` que dice *«Ese hueco ya no está / Ese
  horario se acaba de ocupar. Elige otro y lo confirmamos enseguida. / SLOT_NO_DISPONIBLE ·
  HTTP 409»*, la hora se suelta —deja de estar `aria-pressed`— y se vuelven a pedir los huecos.
  El aviso queda **dentro de la ventana** (top 456 de 844), no arriba del todo a 2.500 px.
- **Sin sesión:** elegir hora saca la misma barra, con **«Entrar y confirmar»** en vez de
  «Confirmar». No es un callejón.
- **Cancelar:** funciona (`POST …/cancelar`, la lista pasa a «29 por venir · 31 en el historial»
  y sale «Cancelada la cita de Barbería El Cangrejo»). **No pide confirmación de ningún tipo:**
  un toque y la cita se va.

### Camino 4 · Entrar — **entero**

Clic en **Entrar** de la cabecera → correo + contraseña mala → *«No se pudo entrar / Correo o
contraseña incorrectos. / CREDENCIALES_INVALIDAS · HTTP 401»* dentro de un `role="alert"`, **el
correo se queda escrito** y **el foco vuelve al campo de la contraseña** (comprobado:
`document.activeElement` es el `input[type=password]`). Con la buena, va a **Mis citas**.

### Camino 5 · El salón — **entero**

Entrar como dueño → clic en **Mi local** → agenda del día: «martes, 8 de septiembre», botones
**← Ayer / Hoy (inhabilitado) / Mañana →**, los tres números (5 citas · 2 personas de turno ·
B/. 48.00 a facturar) y el día como **reloj**: una fila por hora, y en cada cita quién la
atiende. A 768 y 1440 pasa a **columnas por persona** de verdad, como promete. Es solo lectura,
cosa que su propio documento avisa.

Una pega concreta: la cabecera dice **«Tu papel aquí: dueno.»** — el enumerado del backend en
crudo, sin ñ, en la pantalla.

### Y el gesto que da nombre a la dirección

**«Repetir»** en la portada con sesión lleva a la pantalla de horas con **la misma persona y el
mismo servicio ya marcados** y 45 huecos que elegir. Funciona. Lo que hay debajo es más flojo que
la idea: el bloque «Vuelve a lo de siempre» solo puede ofrecer **dos** cosas y las dos dicen
**«1 VEZ»**, porque se cuenta de las citas *atendidas* y en la semilla solo hay 2 completadas
frente a 14 no-shows. La idea de la repetición se sostiene sobre un dato que ahora mismo casi no
existe.

### Limpieza

Creé **6 reservas** y **las 6 quedan canceladas**: una por la pantalla (para ver qué hace el
botón) y el resto con `POST /api/v1/mi/reservas/{id}/cancelar`. Verificado con la agenda del
dueño del 7 al 16 de septiembre: **ninguna reserva mía sigue viva**.

> **Aviso, para que nadie confunda residuo ajeno con el mío:** durante la sesión aparecieron
> reservas que **no creé yo** —una a las 07:43:01 UTC y otra a las 08:01:11, ya con mis pruebas
> terminadas—. No las toqué; la primera la canceló su dueño mientras yo escribía esto. Es la
> señal de que hay **otro crítico trabajando a la vez sobre la misma base de datos**: quien
> revise el estado de la agenda después de esta ronda debe filtrar por identificador y no dar
> por hecho que lo que quede vivo sea de nadie en concreto.

---

## 3 · Qué hace mejor que nadie y qué hace peor

**Mejor:** pinta **la semana entera de huecos en una sola petición y en la misma pantalla en la
que se elige el servicio** —siete días, los vacíos dichos por su nombre— así que se ve dónde hay
y dónde no **sin tocar ni un día**, y sin un asistente de tres pasos.

**Peor:** **no hay una sola línea de contenido en el HTML antes del JavaScript** —
`curl http://localhost:3200/salon/barberia-el-cangrejo` devuelve 19.604 bytes con **cero**
apariciones de «Barbería El Cangrejo», «Kevin Ortega», «Corte clásico», `LocalBusiness` u `og:`,
y `<title>Tanda</title>` para **todas** las páginas, porque las dos rutas que se indexan
(`/salon/[slug]` y `/salon/[slug]/[profesional]`) no declaran ni un `metadata` — de modo que las
fichas que este producto existe para que Google indexe no las puede indexar nadie.
