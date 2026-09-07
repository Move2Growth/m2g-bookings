# El profesional y el dueño · Estado: en proceso

> La ingeniería de los puntos 3 a 6 de [`ENCARGO-2026-09-07.md`](ENCARGO-2026-09-07.md). Decide
> lo que hay que decidir **antes** de repartir el trabajo, para que las piezas encajen.

## Lo que ya existe y NO hay que volver a construir

Se comprobó en el código, no de memoria:

- **El precio ya es opcional.** `services.price_kind` admite `fijo | desde | consultar`, y con
  `consultar` el importe es nulo. Hay hasta una restricción que impide el precio fantasma. Lo
  único pendiente es que la pantalla lo ofrezca con esas palabras.
- **Las reseñas ya apuntan a un profesional**: `reviews.staff_id`, con su índice.
- **La búsqueda ya es geográfica**: PostGIS, radio y distancia calculada. Para el mapa falta la
  consulta por **rectángulo visible**, no el geo.
- **El profesional ya tiene ficha por negocio**: `staff_profiles`, con `bio`, `photo_key` y
  `visible_in_marketplace`. Es la base sobre la que se construye el perfil público.
- **El alta del local ya tiene sus pasos**: crear, horario, servicios, profesionales, checklist
  y publicar. Falta **asignar personas que ya tienen cuenta**, con su papel.

## Los huecos de verdad

### A · El profesional, como entidad pública

`staff_profiles` gana:

| Columna | Para qué |
|---|---|
| `slug` | La URL de su perfil, `/{negocio}/{profesional}`. Único **por negocio**, no global: la misma persona puede trabajar en dos salones |
| `headline` | La descripción corta de una línea, distinta de la `bio` larga |
| `instagram`, `facebook`, `x` | **Se guarda el usuario, no la URL.** Guardar la URL entera invita a meter un enlace a cualquier sitio desde un perfil público, y no hay forma de validar «que sea de Instagram» mirando una cadena arbitraria |
| `years_experience` | Aparece en la ficha; nulo cuando no se dice |

Se calculan al leer, no se guardan: **cuánta gente ha atendido** (citas `completada` con su
`staff_id`) y su nota media. Un contador guardado se desincroniza el primer día que alguien
cancela una cita a mano en la base.

Tabla nueva **`staff_media`**: las fotos del profesional. `service_id` **admite nulo**, y ahí
está lo que pidió Luis: una foto atada a un servicio es «esto lo hizo esta persona»; una foto
suelta es su galería. Con `moderation_status`, como el resto de las fotos.

**Endpoints públicos nuevos**: el perfil de un profesional, la lista de profesionales de un
salón, y la búsqueda de profesionales sueltos —que es lo que hace posible **elegir persona
antes que local**—.

### B · Elegir profesional primero

El flujo de reserva de hoy es negocio → servicio → profesional. Se añade el camino contrario,
**sin quitar el que hay**: profesional → servicio (de los suyos) → hora. Quien busca «Yaris»
entra por ahí; quien busca «una barbería cerca» sigue entrando por donde entraba.

El motor de disponibilidad no cambia: ya sabe calcular los huecos de un profesional concreto.

### C · El portal del dueño

Se distingue del de un profesional por **el rol de la membresía**, que ya existe (`dueno` frente
a `profesional`) y ya viaja dentro del token. No hace falta ninguna tabla para eso.

| Pieza | Cómo |
|---|---|
| Todos los calendarios | La agenda del salón ya existe; falta la vista de **varios profesionales en columnas** el mismo día |
| Lista de profesionales | Existe; se le enlaza el perfil |
| Finanzas | Agregado sobre las citas `completada`: por día, semana y mes, con el importe que se guardó en la cita —no el precio de hoy del servicio— |
| Publicidad flash | Tabla `business_banners`: texto, vigencia y si está activo. Es **del salón y para su propia ficha**; no es `ad_campaigns`, que es el posicionamiento pagado del marketplace y se cobra |
| Fichaje | `staff_profiles.clock_in_enabled`, que **enciende el dueño persona a persona**, y `staff_clock_events` con entrada y salida. Apagado por defecto: un fichaje que aparece sin que nadie lo pida se lee como vigilancia |
| Mejor del mes | Consulta sobre citas completadas, ordenable **por importe facturado o por número de servicios**, y filtrable por categoría de servicio |

### D · El mapa

Un endpoint que devuelve los salones dentro de un **rectángulo** (las cuatro esquinas de lo que
se ve en la pantalla) con su punto, su nota y su número de reseñas. Con tope de resultados: un
mapa alejado que devuelve el país entero es una respuesta de varios megabytes en datos móviles.

### E · Asignar personas al local

`POST` que invita a alguien por correo con un papel (`dueno` o `profesional`), y el que la
acepta. `memberships` ya tiene las columnas de invitación —token con hash y caducidad—; lo que
falta es la puerta.

**Regla que no se negocia:** un salón no puede quedarse sin ningún dueño. Quitarle el papel al
último es un error, no una casilla.

## Lo que NO entra aquí

Nada de esto toca las pantallas: la dirección visual está en revisión y los frontales se
rehacen cuando Luis elija. Esto construye **la API, el modelo y las pruebas**, para que el día
que haya dirección las pantallas sean solo pantallas.
