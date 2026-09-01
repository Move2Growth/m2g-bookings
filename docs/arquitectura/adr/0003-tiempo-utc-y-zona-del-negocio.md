# ADR-0003 · El tiempo se guarda en UTC; la zona vive en el negocio

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

Panamá (`America/Panama`, UTC−5) **no tiene horario de verano**. La tentación es guardar horas locales y ahorrarse las conversiones. Pero el brief dice que el modelo tiene que aguantar **España después**, donde sí hay DST, y una migración de husos con reservas vivas dentro es de las peores que existen.

Además hay dos clases de tiempo distintas que se confunden con facilidad:

- **Instantes**: cuándo empieza una reserva. Tienen un punto en la línea del tiempo.
- **Reglas locales recurrentes**: «el salón abre los martes a las 9:00». Eso no es un instante; es una hora de pared que se repite y cuyo instante depende de la fecha y del huso.

## Decisión

**[decisión]** Dos representaciones, sin mezclarlas:

| Qué | Cómo se guarda | Ejemplo |
|---|---|---|
| Instantes (reservas, bloqueos puntuales, auditoría, notificaciones) | `timestamptz`, **siempre en UTC** | `bookings.starts_at` |
| Reglas horarias recurrentes (horario del negocio, horario del profesional, descansos, bloqueos recurrentes) | día de la semana + **hora local** (`time`), sin fecha | `business_hours(weekday, opens_at, closes_at)` |
| La zona | **`businesses.timezone`**, texto IANA (`America/Panama`), obligatorio | — |

- **[decisión]** La conversión de regla local a instante ocurre **en un único sitio**: el motor de disponibilidad. Ninguna otra capa hace aritmética de husos.
- **[decisión]** Toda la API habla **ISO-8601 con desplazamiento explícito**; nunca fechas sin huso. Las respuestas incluyen además la zona del negocio para que el cliente pueda pintar «10:00» sin recalcular.
- **[decisión]** Los cierres que cruzan medianoche (un spa que cierra a las 00:30) se modelan con `closes_at < opens_at` y se resuelven sumando un día en el motor. No se parten en dos filas.
- **[supuesto]** Un negocio tiene **una** zona. Multi-sede es v2, y ahí la zona pasará a la sede; la columna se deja donde tocará moverla.

## Alternativas consideradas

- **Guardar hora local de Panamá y punto.** Descartado: cierra España y obliga a reescribir el motor con datos vivos.
- **Guardar todo como instantes, incluido el horario semanal.** Descartado: obliga a materializar el horario hasta el infinito y a rehacerlo cuando el negocio cambia de horario.
- **`timestamp` sin huso + columna de zona.** Descartado: es UTC disfrazado con más margen de error humano.

## Consecuencias

- El motor de disponibilidad tiene una responsabilidad más, pero **es el único sitio donde puede fallar un huso**, y ahí es donde están las pruebas.
- España entra sin migración de datos: cambia la zona del negocio y el mismo código resuelve el DST.
- Coste real: al probar hay que fijar la zona explícitamente. Las pruebas del motor corren con `TZ=UTC` en el proceso para que un despiste local no pase desapercibido.
