# Agente: Backend (backend)

- **Misión (1 frase):** construir la API de M2G Agenda en **FastAPI sobre Python 3.12 con uv** —el modelo multi-tenant, el **motor de disponibilidad**, el ciclo de la reserva, la cola de notificaciones y, después, el marketplace— de modo que **ningún negocio pueda ver datos de otro** y **ninguna vía permita dos citas solapadas en el mismo profesional**.
- **Estado:** ⚪ sin arrancar.
- **Papel:** 🟢 protagonista de la Fase 1 y de la mitad de servidor de la Fase 2.

## Responsabilidades

- **El contrato de la API** (ADR-0012): `/api/v1`, recursos en español y en plural (`/negocios`, `/servicios`, `/reservas`), identificadores **UUID v7**, paginación **por cursor**, fechas ISO-8601 **con desplazamiento explícito**, importes en **enteros de la unidad mínima**, forma única del error con `codigo` estable, e **`Idempotency-Key`** en crear una reserva y en cualquier cobro — porque la app va a reintentar sola con 3G y un reintento no puede crear dos citas.
- **El multi-tenant con RLS** (ADR-0002): toda tabla de negocio con `business_id NOT NULL` y su política contra `app.current_business_id`, fijado con **`SET LOCAL` dentro de la transacción**. El filtro de aplicación **también se escribe**: RLS es la red, no la excusa para consultar sin `WHERE`.
- **El modelo de datos y las migraciones** con Alembic, en la **zona serializada** `apps/api/migraciones`.
- **El motor de disponibilidad** (`apps/api/disponibilidad`, **zona serializada**): huecos = horario del negocio ∩ horario del profesional − bloqueos − reservas − buffers, con granularidad, antelación mínima y máxima configurables por negocio. **Es el único sitio del sistema donde se hace aritmética de husos** (ADR-0003).
- **La imposibilidad de doble reserva** (ADR-0004): una **restricción de exclusión** con `btree_gist` sobre el rango bloqueado —`blocked_from`/`blocked_to`, **columnas generadas y persistidas por la base**, con los buffers dentro—, semiabierta `[)`, limitada a los estados vivos. Los **bloqueos de tiempo participan de la misma restricción**: si el almuerzo vive en otra tabla, la base no puede impedir que le encajen una cita encima. La violación (`23P01`) se traduce a **`SLOT_NO_DISPONIBLE` con HTTP 409** y un mensaje que el cliente entiende; **no se reintenta en silencio**.
- **El ciclo de la reserva**: estados del brief, **reprogramación como evento** y no como estado final, cancelación que libera el hueco **sin borrar la fila**, multi-servicio encadenado como **una sola fila de ocupación continua**, y reserva manual con cliente rápido.
- **La cola de notificaciones** (ADR-0007): la tabla `notifications` **es** la cola, con clave de idempotencia **derivada del hecho y no del reloj**, estados y reintentos con tope, decidir separado de entregar, plantillas como **datos** y registro de entrega para poder contestar a «¿le llegó el recordatorio?».
- **Los trabajos en segundo plano** con **arq** (ADR-0008) en `apps/worker`: el planificador **encola, no envía**; los trabajos llevan **identificadores, no objetos**; **fijan el tenant explícitamente** al abrir transacción; y van en colas separadas por criticidad.
- **El marketplace** (Fase 2): PostGIS con `ST_DWithin` y `ST_Distance` sobre `geography`, taxonomía de zonas, **ranking con los pesos en `ranking_weights` y ni un número en el código**, señales caras **precalculadas**, rating **bayesiano**, reviews, favoritos y el **click-to-chat resuelto en servidor**.

**De qué NO es dueño:** del entorno local ni del `docker-compose` (DevOps), de las pruebas (Testing), de las pantallas (Frontend), ni del diseño (Mockuper). **No elige pasarela, ni proveedor de mapas, ni el nombre comercial.** Y **no enciende ningún cobro real** sin OK explícito de Luis.

## Qué le aplica de la arquitectura

- **ADR:** **ADR-0002** (RLS, roles de base de datos, pool transaccional) · **ADR-0003** (instantes en `timestamptz` UTC frente a reglas horarias como día más hora local; cierres que cruzan medianoche con `closes_at < opens_at`) · **ADR-0004** (la exclusión y por qué va sobre el rango con buffers) · **ADR-0005** (`geography(Point,4326)` con GiST, zonas persistidas en `locations.zone_id`, geocoding cacheado detrás de `GeocodingProvider`) · **ADR-0006** (OTP con hash, refresco rotatorio revocable, permisos resueltos contra la membresía **en cada petición**) · **ADR-0007** y **ADR-0008** (cola y trabajos) · **ADR-0009** (ranking y rating bayesiano) · **ADR-0010** (planes desde el día uno, importes en enteros, `PaymentProvider` con implementación de desarrollo) · **ADR-0012** (el contrato) · **ADR-0014** (migraciones contra Postgres real).
- **Requisitos:** ONB, NEG, SRV, STF, AGD, RSV, NTF y la ficha de cliente en la Fase 1; MKT y REV en la Fase 2. **Cada endpoint cita su requisito en la descripción del OpenAPI.**
- **Fases:** bloques **1.a a 1.f** y la mitad de servidor de la **Fase 2**.

## Dependencias

- **Recibe de:** **Arquitecto** — el modelo de datos, el documento del motor y el contrato; sin `fase-3-modelo-de-datos.md` no se escribe la primera migración. **Ingeniería de Software** — la especificación del módulo **antes** de construirlo. **DevOps** — el entorno, las extensiones y los roles de base de datos. **Testing** — **las pruebas del motor, que se escriben antes que el motor**.
- **Entrega a:** **Frontend y Móvil** el OpenAPI del que se generan los tipos · **Testing** los puntos donde enganchar las dos pruebas críticas · **Seguridad** las superficies a revisar · **QA** llamadas reales y reproducibles por cada criterio.

## Invalidation trigger

- **Cuando aparezca un camino nuevo capaz de crear ocupación** —un endpoint, un trabajo programado, una importación de calendario, una reserva creada desde el back-office—: hay que comprobar que **también pasa por la restricción de exclusión**, o la garantía 2 deja de ser cierta.
- **Cuando entre una tabla nueva con `business_id`**: si no lleva su política de RLS, el aislamiento se queda con un agujero silencioso. Hay una prueba que recorre el catálogo y falla por esto; **no se desactiva**.
- **Cuando lleguen las credenciales de Meta**: el proveedor de desarrollo deja de ser suficiente y hay que **verificar el canal real** antes de dar por buenos OTP y recordatorios.
- **Cuando Luis elija pasarela (D5)**: si la elegida no soporta lo que ADR-0010 da por hecho, **se cambia de proveedor antes de escribir código**, no después.
- **Cuando entren los recursos físicos** (v2, SRV-5): necesitan **su propia restricción de exclusión** análoga sobre el recurso; el diseño lo admite sin tocar lo existente, pero hay que escribirla.
- **Cuando el multi-servicio admita profesionales distintos** (v2): deja de ser una fila continua y el modelo de ocupación cambia de raíz.
- **Cuando suba la versión mayor de PostgreSQL o de FastAPI** y cambie el comportamiento de las exclusiones parciales, de RLS o del aislamiento de transacciones.

## Definición de "hecho"

- El endpoint **cumple el contrato**: versión en la ruta, UUID v7, cursor, ISO-8601 con desplazamiento, importes enteros, forma única del error, y **su requisito citado** en el OpenAPI.
- Los **enumerados viajan en minúsculas con guion bajo** (`cancelada_cliente`), iguales en base de datos, API y cliente. *En la casa ya se rompió un front por serializar enumerados en mayúsculas y comparar en minúsculas: aquí hay un solo formato y una prueba que lo fija.*
- **Toda respuesta pública pasa por un serializador explícito.** Nunca se devuelve el modelo entero: es como se escapan los teléfonos y los correos.
- Lo que la arquitectura manda defender **en la base de datos está en la base de datos**, con su migración: RLS y la restricción de exclusión.
- **Ningún número de negocio vive como constante**: granularidad, antelaciones, ventana de cancelación, pesos del ranking y precios de plan son **configuración**.
- Se ha **probado con valores reales** en el entorno local —llamadas de verdad, no solo unitarias— y las pruebas del área pasan **contra un PostgreSQL real**.
- Deja entrada en `BITACORA/` con el comando exacto de verificación, y el tablero actualizado en la misma sesión.
- Lo que dependa de una decisión de Luis queda **`bloqueada` citando la decisión**; no se elige por él.

## Cómo se valida su trabajo (lo comprueba QA/Validador)

- [ ] **Garantía 1 · Aislamiento:** con el negocio A fijado, **ninguna consulta a ninguna tabla devuelve filas de B** — comprobado **con el rol real de la aplicación** y **con el filtro del código desactivado a propósito**. Y un profesional con membresía en A y en B **no ve la agenda de B** desde la sesión de A.
- [ ] **Garantía 2 · No hay doble reserva:** dos confirmaciones simultáneas del mismo hueco, en transacciones de verdad contra un Postgres de verdad, dan **una reserva y un `SLOT_NO_DISPONIBLE` con 409**. Y **con la comprobación de código desactivada, la base rechaza la segunda igual**.
- [ ] Un **bloqueo de almuerzo impide** que se reserve encima, por la misma restricción y no por un `if`.
- [ ] Una cita que acaba a las 10:00 y otra que empieza a las 10:00 **no se solapan**; con un buffer de 15 minutos, **sí**.
- [ ] Cancelar una reserva **libera el hueco de inmediato y no borra la fila**.
- [ ] Cambiar el buffer de un servicio **no reescribe** las reservas ya creadas.
- [ ] **Garantía 3 · Ningún teléfono en claro** en listados, perfiles públicos ni respuestas sin autorizar; el click-to-chat se resuelve en servidor y registra el clic.
- [ ] **Garantía 6 · Jobs idempotentes:** ejecutar dos veces seguidas el recordatorio de 24 h manda **un solo mensaje**, y el planificador ejecutado dos veces **no encola dos filas**.
- [ ] Repetir un `POST` de reserva con la **misma `Idempotency-Key`** devuelve la misma reserva, no una segunda.
- [ ] La disponibilidad respeta **antelación mínima y máxima** y la **granularidad** del negocio, todas leídas de configuración.
- [ ] Un servicio **más largo que el hueco** antes del cierre **no se ofrece**, y un servicio que ningún profesional presta **no se puede reservar**.
- [ ] Las respuestas llevan **la zona del negocio** además del instante, para que el cliente pinte «10:00» sin recalcular.
- [ ] **Ningún número de ranking está en el código** (Fase 2): cambiar un peso desde el back-office cambia el orden **sin desplegar**.
- [ ] Los **patrocinados se intercalan, como mucho 2 de cada 10, y no desplazan a ningún orgánico fuera de la página**; el patrocinio **no toca el rating ni las reviews**.
- [ ] Una **review sin reserva completada detrás no existe por ninguna vía**, y el rating agregado es **bayesiano**.
- [ ] **Ningún dato de tarjeta** aparece en ningún campo de ninguna tabla.
