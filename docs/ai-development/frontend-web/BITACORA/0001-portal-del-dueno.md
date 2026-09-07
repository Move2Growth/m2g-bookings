# 0001 · El portal del dueño

- **Agente:** Frontend Web · **Tareas:** FE-T013 a FE-T020 · **Fecha:** 2026-09-07
- **Estado al cerrar:** hecha (falta QA)

## Qué hice

Las **siete pantallas del dueño** que quedaban por hacer en `docs/producto/PANTALLAS-PENDIENTES.md`,
más el enganche que faltaba en la ficha pública para que una de ellas no mienta.

| Pantalla | Ruta | Con qué |
|---|---|---|
| Portada del portal | `/panel/local` | `agenda/columnas` + `finanzas` + `anuncios` |
| Todos los calendarios | `/panel/local/calendarios` | `GET /negocio/agenda/columnas` |
| Finanzas | `/panel/local/finanzas` | `GET /negocio/finanzas` |
| Mejor del mes | `/panel/local/mejor-del-mes` | `GET /negocio/mejor-del-mes` |
| Publicidad flash | `/panel/local/publicidad` | `/negocio/anuncios` (GET, POST, PATCH, DELETE) |
| Fichaje | `/panel/local/fichaje` | `PUT /negocio/profesionales/{id}/fichaje` + `GET /negocio/fichajes` |
| Personas del local | `/panel/local/personas` | `/negocio/miembros` y sus invitaciones |
| Alta del local en tres pasos | `/panel/alta` | `POST /negocios` → invitaciones → `POST /negocio/servicios` |

**No inventé aspecto.** La dirección visual está en revisión y se sustituye entera, así que todo
usa el vocabulario que ya existía —`.boton`, `.entrada`, `.campo`, `.panel`, `.filas`/`.fila`,
`.tira`, `.ficha`, `.cifras-clave`, `.serie`, `.aviso`, `.tenue`, `.interruptor`, `.hoja`— y las
variables de `packages/tokens`. Lo único que se añadió a `globales.css` es la rejilla del día en
columnas (`.jornada`), porque **no existía ninguna clase que colocara cajas por hora en columnas
paralelas**, y dos líneas de arreglo estructural (`.fila__boton { text-decoration: none }`).

## Decisiones tomadas

**1 · Cómo se diferencia el portal del dueño (lo que pidió Luis).** No por color, que se va a
cambiar: por estructura. El dueño estrena **una zona con nombre propio** —«Portal del local»— con
su propia navegación de siete secciones, y es la **primera** pestaña de su barra. Un profesional
entra en su día; un dueño entra en su negocio. Un profesional no la ve y no por esconderle un
enlace: `panel/layout.tsx` lo manda a su agenda y, debajo, la API le cierra esos endpoints con
`exigir_dueno` y con las políticas de fila. Comprobado en vivo: escribir
`/panel/local/finanzas` con la cuenta `pro.` acaba en `/panel/agenda`, sin sermón de permisos.

**2 · Las cuatro columnas en un teléfono de 390 px.** Es el problema de verdad de esta entrega.
Tres salidas posibles y solo una no rompe nada:

- *Encoger la letra*: descartado. El encargo pone el suelo en 15 px y bajarlo hace ilegible la
  pantalla que más se mira. Verificado en el navegador: el texto más pequeño de una cita mide
  exactamente **15 px**.
- *Apilar por persona*: pierde el paralelo, que es justo lo que se venía a ver.
- **Las dos cosas a la vez, que es lo que se hizo:** el carril de columnas **se arrastra a lo
  ancho dentro de sí mismo** (la columna de horas se queda quieta a la izquierda) **y** arriba se
  puede **elegir a quién ver**, con la columna elegida ocupando la pantalla entera. Medido a
  390 px: 306 px visibles de 600 px de carril, y el documento sigue midiendo 390 — el arrastre es
  del carril, nunca de la página.

**3 · El dinero se pinta, no se calcula.** `dinero()` divide entre cien y formatea con la moneda
que manda la API. Ni un total se recompone sumando barras: el `importe_centavos` y el
`ticket_medio_centavos` ya vienen, y dos aritméticas acaban dando dos cifras. Se usa
`currencyDisplay: 'narrowSymbol'` para que salga `$18.00` y no `USD 18.00`, que es como se escribe
un precio en el resto del producto.

**4 · Las citas sin precio, con el mismo tamaño que el total.** Es la cifra que pidió Luis y va en
las cuatro cifras clave, con una frase debajo diciendo que **no suman**. Cuando hay alguna, el
texto dice literalmente que lo cobrado de verdad es más que el total que se está viendo.

**5 · El «mejor del mes» no es un concurso.** Sale la lista entera y, en cada fila menos la
primera, a cuánto está del de arriba. Enseñar solo al ganador y esconder que el segundo se quedó a
dos servicios convierte un dato en un cartel, y en un equipo de cuatro personas eso hace daño.

**6 · La publicidad se ve antes de publicarse, y en la ficha pública se ve de verdad.** El
recuadro de previsualización se actualiza **mientras se escribe**. Y como la ficha pública **no
pintaba el anuncio** —la API ya lo devolvía y nadie lo usaba—, se añadió a `app/[slug]/page.tsx`:
sin eso, la previsualización habría sido una mentira. La ficha se sirve cacheada un minuto, así
que la pantalla lo avisa con esas palabras en vez de dejar creer que no se guardó.

**7 · El interruptor del fichaje cambia en el acto.** Se mueve ya y se deshace si el servidor dice
que no. Esperar a la respuesta hace que se sienta roto: se toca, no pasa nada en 3G, se vuelve a
tocar y se acaba de apagar lo que se quería encender.

**8 · Al último dueño se le avisa antes, no después del error.** La API lo impide con
`NEGOCIO_SIN_DUENO`; aquí, al único dueño activo **no se le ofrecen** «quitar» ni «bajar a
profesional», y su fila lo explica. Dejar el botón puesto y explicar el error al pulsarlo es
enseñar una puerta que no abre. Quitar a alguien va abajo del todo, separado y con confirmación,
diciendo lo que **se conserva**: sus citas y su ficha de equipo.

**9 · El precio del servicio, opcional y con esas palabras.** El paso 3 del alta ofrece «Fijo»,
«Desde» y **«A consultar»**, y al elegir «A consultar» el campo del precio desaparece. Debajo, la
ayuda cambia con lo elegido y dice que no hace falta inventarse un número.

**10 · El alta no lleva pestañas y guarda paso a paso.** Son tres pasos seguidos: una barra de
navegación en medio solo invita a abandonarlos. Cada paso guarda al terminarlo, así que quedarse
sin batería en el paso tres deja el local creado y las personas invitadas. El paso de las personas
**se puede saltar** («Trabajo sola, seguir»): un salón de una persona es el caso normal.

**11 · El mapa del alta, con coordenadas y no con un mapa.** Dibujar baldosas necesita proveedor y
clave (**D8, sin decidir**). Mientras tanto: dos campos y un botón «usar dónde estoy» del propio
teléfono, que no depende de nadie.

**12 · Los tipos ya no se escriben a mano.** Se enganchó `@agenda/api-types` a `apps/web` y
`lib/dueno.ts` son **alias en español de los esquemas generados del OpenAPI**. Un cambio de
contrato ahora rompe en compilación y no en el navegador de un salón.

## Archivos / recursos creados o tocados

Creados:

- `apps/web/lib/dueno.ts` — tipos (de `@agenda/api-types`) y formato de dinero, horas y fechas.
- `apps/web/app/panel/local/layout.tsx` — el armazón del portal, con su navegación.
- `apps/web/app/panel/local/page.tsx` — portada «Tu local hoy».
- `apps/web/app/panel/local/calendarios/page.tsx`
- `apps/web/app/panel/local/finanzas/page.tsx`
- `apps/web/app/panel/local/mejor-del-mes/page.tsx`
- `apps/web/app/panel/local/publicidad/page.tsx`
- `apps/web/app/panel/local/fichaje/page.tsx`
- `apps/web/app/panel/local/personas/page.tsx`
- `apps/web/app/panel/alta/page.tsx` — el alta en tres pasos.

Tocados:

- `apps/web/app/panel/layout.tsx` — pestaña «Local» la primera para el dueño y `/panel/alta`
  accesible **sin** negocio activo (es la única pantalla de la zona a la que se llega sin tener uno).
- `apps/web/app/panel/agenda/page.tsx` — atajo a los calendarios del equipo, solo para el dueño.
- `apps/web/app/[slug]/page.tsx` y `apps/web/lib/api.ts` — la ficha pública pinta el anuncio vigente.
- `apps/web/app/globales.css` — **solo se añade**: el bloque `.jornada` (rejilla del día en
  columnas) y `.fila__boton { text-decoration: none }`. Ni un color retocado.
- `apps/web/package.json` — dependencia `@agenda/api-types`.
- `apps/web/app/para-negocios/page.tsx` — los dos «crear mi salón» ya llevan al alta y no a la
  pantalla de entrar.
- `scripts/barrer-pantallas.mjs` — las ocho pantallas nuevas en la lista, y `BASE`/`API` por
  variable de entorno para poder barrer un árbol de trabajo en otro puerto.

Capturas en `docs/capturas/dueno-*.png`.

## Cómo verificar que funciona

```bash
# 1 · el entorno, con la semilla cargada
make arriba

# 2 · el barrido de las 30 pantallas, a 390 y a 1440
node scripts/barrer-pantallas.mjs
#    (desde un árbol de trabajo en otro puerto: BASE=http://localhost:3300 node scripts/…)

# 3 · a mano, en el navegador, con dueno.salon-obarrio@demo.pa / demo-panama-2026
#     → /panel/local, y de ahí las siete secciones
```

Lo comprobado **en el navegador**, no en el build, con `dueno.salon-obarrio@demo.pa` (y
`pro.salon-obarrio@demo.pa` para el desvío) — 46 comprobaciones, todas en verde:

- Los calendarios traen **4 columnas y 8 citas colocadas por hora**, el documento mide 390 px, el
  carril tiene 306 px visibles de 600, y el texto más pequeño de una cita mide **15 px**. Al elegir
  a una persona queda **una** columna y ocupa 305 px.
- Finanzas: ticket medio y citas sin precio en pantalla, importe con símbolo (`$4,725.00`), y las
  tres agrupaciones —día, semana, mes— devolviendo datos.
- Mejor del mes: las cuatro personas del equipo, y cambiar de criterio y de categoría no rompe.
- Publicidad de punta a punta: se escribe, se ve en la previsualización, **sale en la ficha
  pública**, se apaga, **desaparece de la ficha pública** y sigue en la lista para volver a
  lanzarlo.
- Fichaje: cuatro interruptores, encender a una persona se guarda y aparece su parte de horas,
  apagarla lo deja como estaba.
- Personas: el aviso del último dueño sale **antes**, al único dueño no se le ofrece «quitar», a un
  profesional sí, y quitar pide confirmación explicando que las citas se quedan.
- Alta: los tres pasos, «A consultar» con esas palabras, sin servicios no se puede terminar, y al
  acabar se cae dentro del portal del local recién creado.
- **Estados vacíos**, comprobados con un local recién creado: calendarios, finanzas, mejor del
  mes, publicidad, fichaje y personas dicen qué pasa y por dónde salir. Ninguno se queda en blanco.

`pnpm --filter @agenda/web lint` (que es `tsc --noEmit`) y `next build` en verde; las ocho rutas
nuevas pesan lo mismo que el resto del panel (~110 kB de primera carga).

## Pendiente o bloqueado

- 🔴 **Bug de la API, no mío, y es un callejón sin salida:** `GET /mi/negocios` **no devuelve los
  locales en borrador**, porque las políticas de `businesses` solo dejan ver los publicados cuando
  no hay negocio activo. Consecuencia: quien acaba de dar de alta su local, si cierra sesión, ya
  **no puede volver a entrar en él** —aterriza en sus citas de clienta— y como publicar exige entrar
  al panel, no hay salida. Se reproduce sin tocar nada: `dueno.unas-por-vanessa@demo.pa` es el
  salón en borrador de la semilla y su `GET /mi/negocios` devuelve `[]`. **Es de Backend**
  (`apps/api/agenda/api/cliente.py` y la política `businesses_tenant`), y no lo toco. Anotado en el
  tablero.
- **Sin decidir, D8:** el alta pide latitud y longitud porque no hay proveedor de mapas. El día que
  lo haya, es un componente.
- **Deuda de esta entrega:** `scripts/barrer-pantallas.mjs` da por buena una pantalla que carga
  **enseñando su estado de error**. Se vio con estos ojos: con el CORS bloqueando, las ocho
  pantallas nuevas salían «OK» mientras ponían «Failed to fetch». No se tocó para no romper el
  barrido de las demás, pero hay que añadirle una comprobación de `.aviso--error` visible.
- **Un hallazgo de camino, en una pantalla que no es mía:** `/panel/agenda` —la lista del día—
  **sale partida en dos columnas**. `.agenda` (`globales.css:777`) es una sobra de la dirección
  oscura descartada, `display:grid` con `58px minmax(0,1fr)`, y choca con la lista `<ul>` que usa
  esa pantalla: medido en el navegador, el `<ul>` computa `58px 300px` y cada `<li>` cae en una
  celda, con la hora repetida. **No se ha tocado a propósito**: esa pantalla está en la lista de
  «rehacer, no añadir» y arreglarla suelta antes de que haya dirección visual es tocar dos veces
  lo mismo. Anotado en el tablero.
- **Basura en la demo local**, que se va con `python -m agenda.semilla`: cuatro anuncios apagados
  con el texto «Jueves de brushing…» en *Salón Obarrio* y un negocio en borrador «Local de prueba
  del portal 664432» de `nadia@demo.pa`, los dos de probar las pantallas de punta a punta.

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **El portal del dueño vive en `/panel/local/*`** y no en una ruta de primer nivel a propósito:
  `panel` es un slug reservado en la API y `local` no lo es, así que un salón llamado «Local»
  chocaría con la ruta.
- **La dirección visual se va a cambiar entera.** Estas pantallas están escritas para sobrevivirlo:
  toda la maqueta sale de clases que ya existían y el único bloque nuevo (`.jornada`) solo mide,
  no colorea. Cuando se cambie `globales.css`, estas ocho pantallas no se tocan.
- **Levantar un árbol de trabajo en otro puerto:** `cd apps/web && pnpm exec next dev --port 3300`
  y barrer con `BASE=http://localhost:3300`. Ojo: ese puerto tiene que estar en
  `ORIGENES_PERMITIDOS` de la API o **la pantalla carga entera y no sale ni una petición**, que es
  un síntoma que no se parece a lo que es. Y `docker compose restart api` **no relee el `.env`**:
  hace falta `make recargar`.
- **Lo que NO hay que hacer:** recalcular dinero en el navegador (el total y el ticket medio ya
  vienen), pintar horas en la zona del navegador (van en la del negocio, ADR-0003), y meter un
  interruptor de fichaje «para todo el salón»: es persona a persona y nace apagado, y eso es del
  encargo, no una preferencia.
