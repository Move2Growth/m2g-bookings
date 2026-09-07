# 0001 · Las pantallas del cliente y del profesional (encargo 2026-09-07)

- **Agente:** Frontend Web · **Tareas:** FE-T013 a FE-T019 · **Fecha:** 2026-09-07
- **Estado al cerrar:** hecha (falta QA)

## Qué hice

Las siete pantallas que `docs/producto/PANTALLAS-PENDIENTES.md` pone en «Del cliente» y «Del
profesional». **El mapa no**, que necesita la decisión D8, y **las del dueño tampoco**, que son
de otro bloque.

**Del cliente**

| Pantalla | Dónde vive |
|---|---|
| El perfil de una persona | `/[salón]/[persona]` — servidor, con metadatos y `Person` de schema.org |
| Buscar personas | `/buscar/personas` — servidor, con conmutador «Locales · Personas» en las dos |
| Reservar empezando por la persona | El propio perfil: persona → uno de **sus** servicios → hora → `/reservar` |
| Aceptar una invitación | `/invitacion/[token]` — **la ruta que escribe el correo** |

**Del profesional** (pestañas nuevas dentro de `/panel`)

| Pantalla | Dónde vive |
|---|---|
| Su ficha pública, editada por él | `/panel/mi-perfil` |
| Sus fotos, y atarlas a un servicio | `/panel/mis-fotos` |
| Fichar entrada y salida | `/panel/fichar`, **solo si el dueño se lo activó** |

Y dos piezas que no estaban en el encargo y hacían falta igual: la **página de «no está aquí»**
(`app/not-found.tsx`), porque al meter un perfil en `/[salón]/[persona]` **cualquier dirección
de dos tramos mal escrita cae ahí** y hasta ahora salía la de Next, en blanco y en inglés; y el
**enlace del equipo** en la ficha del salón, que era una lista de nombres muertos y ahora es la
puerta al perfil de cada persona.

**Aspecto, ninguno.** La dirección visual está rechazada y se sustituye entera, así que no se
inventó ni un color: todo sale del vocabulario que ya existía (`.boton`, `.entrada`, `.campo`,
`.resultado`, `.panel`, `.aviso`, `.filas`, `.sello`, `.vistazo`, `.tenue`…) y de
`packages/tokens`. `app/globales.css` **no se ha tocado**. Cuando Luis elija dirección, estas
pantallas vienen detrás sin abrirlas.

## Decisiones tomadas

- **Dos búsquedas, no una con un filtro.** `/buscar` y `/buscar/personas` son dos URL con dos
  listas. Lo que devuelven no se parece —un salón tiene dirección, categorías y precio desde;
  una persona tiene oficio, años y el salón donde está— y meterlas en la misma fila obligaría a
  que una de las dos mienta. El conmutador es de enlaces, no de botones: cada modo es una
  dirección que se comparte y que indexa Google.
- **La próxima hora libre de cada persona no viene de la API.** `ProfesionalEnLista` no la trae,
  así que se sonda el motor una vez por persona con su servicio más corto. Se hace **para toda
  la página, no para las primeras**: media lista con hora y media sin ella se lee como si a las
  de abajo no les quedara ninguna. Sale a cuenta porque cada sonda se cachea un minuto — medido:
  1,17 s la primera carga de veinte, 0,32 s las siguientes.
- **Reservar con la persona se resuelve en dos pantallas, no en tres.** Servicio y hora caben en
  el mismo perfil: al tocar un servicio se recarga con sus horas debajo. Y **la persona viaja
  explícita** en la reserva; ahí no vale «cualquiera», que es justo lo que distingue este camino
  del de siempre. El camino de siempre no se ha tocado.
- **La invitación son dos formularios distintos**, no uno con un campo opcional. Con
  `cuenta_con_contrasena: false` la cuenta la creó la invitación y se elige contraseña ahí
  mismo; con `true`, esa cuenta ya tiene dueño y hace falta estar dentro con ella. Y como no se
  puede saber desde el navegador si la sesión abierta es la de esa persona, la pantalla lleva
  **siempre la salida** a entrar con el correo correcto.
- **La pestaña «Fichar» sale solo si está encendido.** El propio `layout.tsx` del panel dice que
  enseñar una puerta que no abre es peor que no enseñarla. Se pregunta **sin bloquear** el resto
  del panel: la agenda es la pantalla que más se abre y no puede esperar a una consulta que solo
  decide una pestaña. El precio es que la pestaña aparece un instante después; el precio de la
  otra opción sería que la agenda tarde más siempre.
- **Subir una foto se dice que no está montado**, en vez de enseñar un botón de subir que pide
  una URL. Es deuda viva compartida con Backend: la API recibe una `clave` y no está decidido de
  dónde sale.

## Archivos creados o tocados

Creados:

- `apps/web/app/[slug]/[profesional]/page.tsx` — el perfil de una persona
- `apps/web/app/buscar/personas/page.tsx` — buscar personas
- `apps/web/app/invitacion/[token]/page.tsx` — aceptar la invitación
- `apps/web/app/panel/mi-perfil/page.tsx` — su ficha
- `apps/web/app/panel/mis-fotos/page.tsx` — sus fotos y el atado a un servicio
- `apps/web/app/panel/fichar/page.tsx` — fichar
- `apps/web/app/not-found.tsx` — la página de «no está aquí»
- `apps/web/componentes/ficha-profesional.tsx` — una persona en una lista
- `apps/web/componentes/modo-busqueda.tsx` — el conmutador locales / personas
- `apps/web/componentes/redes.tsx` — Instagram, Facebook y X

Tocados:

- `apps/web/lib/api.ts` — los tipos y las llamadas del profesional; **solo se añade**
- `apps/web/lib/taxonomia.ts` — `nombreDeCategoria`, que no existía
- `apps/web/app/buscar/page.tsx` — el conmutador encima del buscador
- `apps/web/app/[slug]/page.tsx` — el equipo pasa a enlazar a cada perfil
- `apps/web/app/panel/layout.tsx` — pestañas del profesional y la de fichar, condicionada
- `scripts/barrer-pantallas.mjs` — las pantallas nuevas, el grupo del profesional, y `BASE`
  configurable por entorno

## Cómo verificar que funciona

Con el entorno arriba (`make arriba`) y la semilla cargada:

```bash
node scripts/barrer-pantallas.mjs          # 3100, el entorno de siempre
BASE=http://localhost:3200 node scripts/barrer-pantallas.mjs   # un árbol de trabajo aparte
```

**Ojo con el puerto:** si se apunta a otro, tiene que estar en `ORIGENES_PERMITIDOS` de la API o
las pantallas con sesión **cargan enteras y no sale ni una petición**, que no se parece en nada
a un problema de CORS. Y `docker compose restart api` no relee el `.env`: hace falta
`make recargar`.

Lo que se comprobó **en el navegador**, a 390 y a 1440 px:

- **32 pantallas** en el barrido (eran 26): las diez nuevas más las de siempre, sin regresión.
  Ninguna revienta, ninguna desborda a lo ancho, y el 404 devuelve 404 con salida.
- **Perfil de una persona**, `barberia-el-cangrejo/kevin-ortega`: **sin JavaScript**, 2.486
  caracteres de contenido en el HTML —nombre, oficio, nota, años, personas atendidas, servicios,
  horas, reseñas—. Enlaza por **slug o por identificador**: una ficha recién creada, sin slug ni
  servicios, sale igual y dice quién le asigna los servicios.
- **Buscar personas**: 20 personas con salón, nota, años y su próxima hora libre. **El buscador
  funciona sin JavaScript** (formulario GET): «cejas» → Katherine Sánchez.
- **Reservar por la persona**, como `abdiel@demo.pa`: lista → perfil de Kevin → «Corte + barba»
  → 15:30 → confirmar. `POST /mi/reservas` **201**, y acaba en `/mi/citas` diciendo «Cita
  confirmada en Barbería El Cangrejo, el lunes, 7 de septiembre, 15:30».
- **Invitación**, las tres ramas: cuenta nueva (elige contraseña → cae en `/panel/agenda` con el
  salón en la barra); cuenta que ya existe sin sesión (no pide contraseña, ofrece entrar y
  volver); y **con la sesión de otra persona** (el servidor lo rechaza, se lee el porqué y hay
  salida al correo correcto). Un token gastado da mensaje y botón de reintentar.
- **Ficha del profesional**, como `pro.barberia-el-cangrejo@demo.pa`: se guarda, y al pegar
  `https://instagram.com/kevin.prueba/?utm_source=x` **se recorta a `kevin.prueba`** y el
  servidor monta el enlace.
- **Sus fotos**: se añade una atada a «Corte + barba» y **sale en su página pública con la
  etiqueta del servicio**. Eso es «que se vea quién hizo qué», comprobado de punta a punta.
- **Fichar**: con el interruptor apagado no hay pestaña ni botón, solo de quién depende
  encenderlo. Encendido por la dueña, «Ya llegué» → «Estás dentro» y la marca en el parte;
  «Ya salgo» → las dos marcas del día. Y una dueña que no atiende ve un mensaje, no un botón.

Los datos de la demo **se dejaron como estaban**: se retiraron las fichas y las invitaciones de
prueba y se devolvió a la semilla el titular y el Instagram de Kevin. Quedan dos citas de Abdiel
con Kevin, que son las que se crearon reservando de verdad.

## Pendiente o bloqueado

- **El mapa no se hizo**, y no es un olvido: dibujar las baldosas necesita proveedor y clave
  (D8, abierta desde el 1 de septiembre). La consulta por rectángulo ya existe en la API.
- **Subir una foto de verdad** sigue bloqueado (deuda viva ya anotada, Backend + Frontend). La
  pantalla lo dice en vez de fingirlo.
- **Lighthouse no se ha medido** en las rutas nuevas. Con la dirección visual sin elegir, medir
  el peso de una página que se va a rehacer entera no informa de nada; se mide cuando haya
  dirección. Lo que sí se sabe del build: `/[slug]/[profesional]` pesa 1,81 kB y
  `/buscar/personas` 1,82 kB, **por debajo** de sus equivalentes de salón (2,47 y 2,52 kB),
  porque ninguna de las dos arrastra componentes de cliente.
- **El barrido pide rutas que solo existen aquí.** Hasta que esto se fusione, correrlo contra el
  3100 falla en las seis pantallas nuevas. Es lo esperado, no un fallo.

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **No se tocó `apps/api` ni `app/globales.css`.** Todo lo nuevo usa clases que ya existían. Si
  al aplicar la dirección visual alguna clase desaparece, estas pantallas la piden en:
  `.resultado`/`.resultados` (las dos listas), `.servicio` y `.hora` (elegir servicio y hora),
  `.filas`/`.fila` (parte de fichaje y lista de fotos), `.datos.vistazo` (los números del
  perfil), `.pastillas` (las redes) y `.campo`/`.entrada` (todos los formularios).
- **`/[slug]/[profesional]` es una ruta atrapalotodo de dos tramos.** Cualquier URL de dos
  segmentos que no case con una ruta estática entra aquí. Por eso se añadió `not-found.tsx`; si
  algún día hace falta una sección pública de dos tramos, va **antes** y con segmento estático.
- **La pestaña «Fichar» depende de una consulta que se resuelve después de pintar.** Si alguien
  la ve aparecer con retraso, es a propósito y está razonado en `app/panel/layout.tsx`.
- **Un parte de fichaje vacío significa «apagado», no «no tiene ficha».** La API solo devuelve a
  quien lo tiene encendido. Confundir las dos cosas le decía a quien sí atiende que no trabajaba
  allí; está arreglado y comentado en `app/panel/fichar/page.tsx`.
- **La base de desarrollo se resembró a mitad de sesión** y cambiaron todos los identificadores.
  Si algo deja de encontrarse de golpe, es eso: se vuelve a entrar y se piden los ids otra vez,
  no se apuntan a mano.
