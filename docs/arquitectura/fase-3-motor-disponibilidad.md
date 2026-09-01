# Motor de disponibilidad (AGD) — diseño y casos de prueba

> **Estado:** en proceso (Fase 0 · diseño aprobado pendiente de Luis; la construcción es la primera puerta de la Fase 1)
>
> Esta es **la pieza donde se juega el producto**. Si el motor está mal, todo lo que se construya encima hay que rehacerlo. Por eso **las pruebas de esta lista se escriben antes que el código** y el motor se enseña en verde **antes** de montar pantallas.
>
> Decisiones que lo gobiernan: [ADR-0003](adr/0003-tiempo-utc-y-zona-del-negocio.md) (tiempo) y [ADR-0004](adr/0004-no-doble-reserva-restriccion-de-exclusion.md) (no doble reserva).

---

## 1. Qué es un slot libre

```
slot libre = horario del negocio ∩ horario del profesional
             − bloqueos − reservas existentes − buffers
```

Con tres parámetros por negocio, todos configurables (AGD-1):

| Parámetro | Default | Qué significa |
|---|---|---|
| Granularidad | **15 min** | Cada cuánto empieza un slot candidato. A las 9:00, 9:15, 9:30… |
| Antelación mínima | **1 h** | No se puede reservar para dentro de diez minutos: el negocio no llega |
| Antelación máxima | **60 días** | No se puede reservar para dentro de un año |

**La granularidad es la rejilla de comienzos, no la duración del servicio.** Un servicio de 45 minutos en una rejilla de 15 puede empezar a las 9:00, 9:15 o 9:30, y ocupa hasta las 9:45, 10:00 o 10:15 respectivamente. Confundir las dos cosas es el error clásico: obliga a que todo dure múltiplos de la rejilla y deja huecos muertos.

## 2. Las dos preguntas que responde

Son distintas y conviene no mezclarlas:

1. **«¿Qué huecos hay?»** — consulta de lectura, la que pinta el calendario. Puede estar ligeramente desactualizada; no promete nada.
2. **«Quiero este hueco»** — escritura transaccional. Es la única que decide, y decide **en la base de datos** (ADR-0004).

Todo el diseño parte de aceptar que **entre la pregunta 1 y la 2 pasa tiempo** y el mundo cambia. El motor no intenta evitarlo: lo hace irrelevante.

## 3. El algoritmo, paso a paso

Entrada: negocio, servicio o lista de servicios, profesional (o «cualquiera»), y un rango de fechas.

1. **Resolver la duración total.** Suma de las duraciones de los servicios pedidos, en orden. Para una reserva encadenada (D13, RSV-2) es **un bloque continuo**, no tres huecos sueltos.
2. **Resolver los buffers.** El buffer anterior es el del primer servicio; el posterior, el del último. Los buffers **intermedios** entre servicios encadenados del mismo profesional **no se aplican**: son tiempo de preparación entre clientes, no entre dos servicios de la misma persona sentada en la misma silla. *(Si algún negocio necesitara lo contrario, es una opción de configuración, no un cambio del motor.)*
3. **Construir la ventana efectiva:** desde `max(ahora + antelación mínima, inicio pedido)` hasta `min(ahora + antelación máxima, fin pedido)`.
4. **Materializar el horario del negocio** en esa ventana: para cada día, convertir las reglas locales (`weekday`, `opens_at`, `closes_at`) a instantes UTC usando la zona del negocio. Aquí, y **solo aquí**, se hace aritmética de husos (ADR-0003). Un tramo con `closes_at < opens_at` cruza medianoche y termina al día siguiente. Los días festivos precargados (AGD-6) son sugerencias que el negocio pudo aceptar o no: si los aceptó, son cierres.
5. **Materializar el horario del profesional** igual, e **intersecarlo** con el del negocio. Que el profesional tenga horario distinto del negocio **es el caso normal, no la excepción**: la peluquera que solo trabaja de tarde es la mitad de los salones.
6. **Restar la ocupación**: todas las filas de `staff_occupancy` de ese profesional que solapen la ventana, sean reservas activas o bloqueos (puntuales o materializados desde una regla recurrente). Se resta el **rango bloqueado**, que ya incluye los buffers de cada reserva.
7. **Recorrer la rejilla**: para cada comienzo candidato dentro de los tramos disponibles, comprobar que el rango bloqueado `[comienzo − buffer_antes, comienzo + duración + buffer_después)` **no solapa ninguna ocupación**, y que el servicio con su buffer posterior **cabe dentro del tramo**.

   Los dos buffers **no se tratan igual**, y es deliberado: el **posterior** tiene que caber en la jornada —si un servicio termina justo al cierre pero su limpieza se sale, el profesional se iría a casa dejando el puesto sin recoger—, mientras que el **anterior** solo se comprueba contra la ocupación. A primera hora no hay cliente anterior del que separarse, y exigirlo dejaría el primer hueco del día siempre inservible.

   **La rejilla se ancla a la medianoche local, no a la apertura.** Un negocio que abre a las 9:05 con granularidad de 15 minutos ofrece 9:15, 9:30, 9:45…, no 9:05, 9:20, 9:35, que no es lo que nadie espera ver en un calendario.
8. **Filtrar por antelación** y devolver.

Para **«cualquier profesional disponible»** (STF-5) se ejecuta lo mismo por cada profesional que preste esos servicios y se unen los resultados; cada hora ofrecida recuerda **con quién** se puede hacer. El reparto entre varios candidatos **equilibra carga**: se elige al que menos ocupación tenga ese día, no siempre al primero de la lista, o el mismo profesional acaba con toda la agenda.

## 4. La confirmación

La reserva se crea en **una transacción**:

1. Se insertan la reserva y su fila de ocupación con `blocked_from` / `blocked_to` **generadas por la base** a partir de los buffers vigentes.
2. La **restricción de exclusión** (ADR-0004) decide. Si otro cliente se adelantó por milisegundos, la inserción falla con `23P01`.
3. Ese fallo se traduce a `SLOT_NO_DISPONIBLE` (HTTP 409) con un mensaje que el cliente entiende: *«ese horario se acaba de ocupar»*, y la interfaz recarga los huecos.

Las validaciones de negocio (antelación, que el servicio esté activo, que el profesional lo preste, que el negocio esté publicado) se comprueban **dentro de la misma transacción**. Comprobarlas antes y confiar en que sigan siendo ciertas es la misma carrera con otro nombre.

**No hay reintento automático.** Reservar automáticamente el siguiente hueco libre en nombre del cliente es meterle una cita a otra hora sin que la haya elegido.

## 5. Rendimiento

Objetivo del brief: **p95 < 300 ms**.

- La ocupación se lee con **una consulta por profesional y ventana**, apoyada en el índice GiST de la restricción de exclusión, que sirve igual para consultar solapes.
- El horario semanal de un negocio son pocas filas y se **cachea en Redis** con invalidación al editarlo. Es lo que más se lee y lo que menos cambia.
- El cálculo de la rejilla es aritmética en memoria: no se toca la base por cada slot.
- La vista de calendario pide **rangos**, no días sueltos: siete peticiones para pintar una semana es lo que hunde la experiencia en 3G.

## 6. Los casos que rompen este motor

**Estas pruebas se escriben antes que el código.** Corren contra un **Postgres real** (ADR-0014): la restricción de exclusión, el RLS y los rangos no existen en SQLite, y una prueba que no los ejerce no prueba nada. El proceso de pruebas corre con `TZ=UTC` para que un huso local no tape un error.

| # | Caso | Qué tiene que pasar | Requisito |
|---|---|---|---|
| 1 | **Dos clientes confirman el mismo slot a la vez**, en dos transacciones simultáneas de verdad | Una gana; la otra recibe `SLOT_NO_DISPONIBLE`. **Nunca dos filas solapadas.** Se ejecuta con concurrencia real y repetido, no con dos llamadas seguidas | AGD-4 |
| 2 | **Un buffer que cruza el final de la jornada** | Un servicio que termina justo al cierre pero cuyo buffer posterior se sale **no se ofrece** | AGD-1 |
| 3 | **Profesional con horario distinto del negocio** | Solo se ofrece la intersección. El caso normal, no la excepción | STF-1 |
| 4 | **Cambiar el horario del negocio con reservas dentro de lo que se elimina** | El cambio **no borra ni invalida en silencio** las reservas existentes: se guardan, se avisa de cuáles quedan fuera del nuevo horario y el negocio decide. Las citas siguen en la agenda | AGD-2 |
| 5 | **Servicio más largo que el hueco antes del cierre** | No se ofrece. Un servicio de 3 h a las 17:00 con cierre a las 19:00 no aparece | AGD-1 |
| 6 | **Multi-servicio encadenado** (tres servicios seguidos, mismo profesional) | Necesita un **bloque continuo**, no tres huecos sueltos, y se guarda como **una sola fila de ocupación** | RSV-2, D13 |
| 7 | **Bloqueo recurrente contra bloqueo puntual** | El almuerzo de todos los días y el bloqueo de un martes concreto conviven; ninguno de los dos se pierde ni se duplica | AGD-3 |
| 8 | **Zona horaria** | `America/Panama` no tiene DST, pero el mismo motor con un negocio en `Europe/Madrid` resuelve bien el cambio de hora de marzo y de octubre, incluida la madrugada duplicada de octubre | AGD-5 |
| 9 | **Cierre que cruza medianoche** | Un spa abierto de 15:00 a 00:30 ofrece huecos después de las 00:00 del día siguiente, y la última cita cabe entera | AGD-1 |
| 10 | **Antelación mínima y máxima** | No se ofrece nada antes de `ahora + 1 h` ni después de `ahora + 60 días`; el límite se comprueba **también** al confirmar, no solo al listar | AGD-1 |
| 11 | **Cancelar libera el hueco** | Al cancelar, el slot vuelve a ofrecerse de inmediato, y la fila cancelada **no** impide una reserva nueva en el mismo rango | RSV-3, RSV-4 |
| 12 | **Reprogramar es un evento, no una fila nueva** | Mover una cita libera el hueco viejo y ocupa el nuevo **en la misma transacción**; si el nuevo está ocupado, no se libera el viejo | RSV-3 |
| 13 | **«Cualquier profesional»** | Se ofrecen los huecos de todos los que prestan el servicio, sin duplicar la misma hora, y el reparto equilibra carga | STF-5 |
| 14 | **Profesional inactivo o de vacaciones** | No aparece, y sus huecos no se ofrecen ni siquiera vía «cualquier profesional» | STF-2 |
| 15 | **Aislamiento entre negocios** | Con el tenant A fijado, el motor **no ve** la ocupación de B, ni siquiera para un profesional que trabaje en los dos | ADR-0002 |
| 16 | **Granularidad distinta de la duración** | Con rejilla de 15 min y servicio de 45, los comienzos son 9:00, 9:15, 9:30…, no solo 9:00 y 9:45 | AGD-1 |
| 17 | **Día festivo aceptado** | Si el negocio aceptó el feriado, ese día no ofrece nada; si lo rechazó, funciona normal | AGD-6 |
| 18 | **Idempotencia al confirmar** | Dos peticiones con la misma `Idempotency-Key` (la app reintentando con 3G) crean **una** reserva y devuelven la misma respuesta | ADR-0012 |

## 7. Lo que este motor **no** hace en v1

Está deliberadamente fuera, con su sitio ya previsto en el modelo de datos:

- **Recursos físicos** como restricción de capacidad (SRV-5, v2): la silla de lavado, la cabina. Necesitará su propia restricción de exclusión, análoga y separada.
- **Multi-servicio con profesionales distintos** (RSV-2, v2).
- **Lista de espera** (RSV-8) y **reservas recurrentes** (RSV-9).
- **Google Calendar** (AGD-7).
- **Solapes permitidos a propósito** (la peluquera que atiende dos clientas mientras una tiene el tinte actuando). Es una petición previsible del negocio real y **hoy la restricción de exclusión lo impide**. Cuando se pida, se resuelve modelando la capacidad del profesional, no relajando la restricción.
