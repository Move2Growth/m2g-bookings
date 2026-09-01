# ADR-0004 · La imposibilidad de doble reserva se garantiza con una restricción de exclusión

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

AGD-4 y la garantía nº 2 de la [constitution](../constitution.md): **dos clientes confirmando el mismo slot a la vez no pueden solaparse**. El encargo es explícito — *«que no haya doble reserva es transaccional, no un `if`»*.

El patrón habitual («consulto si está libre y luego inserto») tiene una ventana entre la consulta y la inserción. Bajo dos peticiones simultáneas, las dos leen «libre» y las dos insertan. No es teórico: pasa el primer día que un negocio comparte su enlace por WhatsApp.

## Decisión

**[decisión]** La garantía la da **PostgreSQL con una restricción de exclusión** sobre el rango ocupado de cada profesional, con la extensión `btree_gist`:

```sql
ALTER TABLE bookings ADD CONSTRAINT bookings_sin_solape
  EXCLUDE USING gist (
    staff_id WITH =,
    tstzrange(blocked_from, blocked_to, '[)') WITH &&
  ) WHERE (status IN ('pendiente', 'confirmada'));
```

- **[decisión]** Se excluye sobre **`blocked_from` / `blocked_to`, no sobre `starts_at` / `ends_at`**. El rango bloqueado incluye los buffers: `blocked_from = starts_at − buffer_antes` y `blocked_to = ends_at + buffer_después`. Si la exclusión mirara solo el servicio, dos citas pegadas violarían el buffer sin que la base se enterara. Ambas columnas son **generadas y persistidas por la base**, no calculadas por la aplicación.
- **[decisión]** El rango es **semiabierto `[)`**: una cita que acaba a las 10:00 y otra que empieza a las 10:00 **no** se solapan.
- **[decisión]** La cláusula `WHERE` deja fuera los estados terminales (`completada`, `no_show`, `cancelada_*`): una cita cancelada libera su hueco de inmediato, sin borrar la fila.
- **[decisión]** **Los bloqueos de tiempo (`time_blocks`) participan de la misma restricción.** Se modelan como filas de la misma tabla de ocupación con `kind = 'bloqueo'`, no en una tabla aparte: si el almuerzo vive en otra tabla, la base no puede impedir que le encajen una cita encima. La tabla se llama `staff_occupancy` y las reservas y los bloqueos son dos tipos de fila suya.
- **[decisión]** La reserva **multi-servicio encadenada** (D13, RSV-2) se inserta como **una sola fila de ocupación continua** que cubre los tres servicios, más sus `booking_items`. Tres filas sueltas permitirían que otra cita se cuele en medio.
- **[decisión]** La violación de la restricción (`SQLSTATE 23P01`) se traduce a un **error de dominio `SLOT_NO_DISPONIBLE`** con HTTP 409 y un mensaje que el cliente entiende: «ese horario se acaba de ocupar». No se reintenta en silencio.
- **[decisión]** El cálculo de huecos libres sigue existiendo y sigue siendo la ruta normal: la restricción es **la red que atrapa la carrera**, no el mecanismo de consulta.

## Alternativas consideradas

- **`SELECT … FOR UPDATE` sobre el profesional.** Serializa todas las reservas de ese profesional y sigue dependiendo de que alguien se acuerde de bloquear. Más lento y más frágil.
- **Bloqueo consultivo (`pg_advisory_xact_lock`) por profesional y día.** Funciona, pero la corrección depende de derivar bien la clave en cada ruta de escritura; la exclusión no depende de que nadie se acuerde de nada.
- **`SERIALIZABLE` en toda la aplicación.** Coste alto y errores de serialización por todas partes para resolver un problema que es local a una tabla.
- **Bloqueo en Redis.** Descartado: la garantía quedaría fuera de la base, y si Redis se cae o se reinicia se pierde.

## Consecuencias

- **Es imposible** insertar un solape aunque el código de aplicación esté mal. Es la propiedad que se quería.
- Cambiar los buffers de un servicio **no reescribe** las reservas ya creadas: `blocked_*` se calculó con los buffers del momento de reservar, que es lo correcto — reescribirlas podría hacer inválidas citas ya confirmadas.
- Aparecen las pruebas de concurrencia real (dos transacciones simultáneas contra un Postgres de verdad), no simuladas. Están en la lista obligatoria de [`fase-3-motor-disponibilidad.md`](../fase-3-motor-disponibilidad.md).
- Cuando entren los **recursos físicos** (v2, SRV-5), necesitarán su propia restricción análoga sobre el recurso. El diseño lo admite sin tocar lo existente.
- La extensión `btree_gist` pasa a ser obligatoria en la migración inicial, junto con PostGIS.
