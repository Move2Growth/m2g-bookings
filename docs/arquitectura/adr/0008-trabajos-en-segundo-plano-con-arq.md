# ADR-0008 · Trabajos en segundo plano y planificación con arq

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

Hay dos clases de trabajo fuera de la petición HTTP: **reactivo** (enviar una notificación cuando se crea una reserva, procesar una imagen subida, atender un webhook) y **planificado** (los recordatorios de 24 h y 2 h, recalcular el ranking, cerrar reservas pasadas, cobrar suscripciones, agregar métricas de ads).

El brief §8 deja abierto «arq / Celery». La API es FastAPI y es asíncrona de arriba abajo.

## Decisión

**[decisión]** **arq** sobre el Redis que ya está en el stack, con un proceso `apps/worker` que comparte código con la API.

- **[decisión]** El planificador (`cron`) de arq **no envía nada**: **encola**. El trabajo periódico de recordatorios recorre las reservas de la ventana y **inserta filas en `notifications`** con su clave de idempotencia (ADR-0007). Que se ejecute dos veces no duplica nada. Esto es lo que hace que la idempotencia no dependa de la fiabilidad del planificador.
- **[decisión]** Ningún trabajo lleva **objetos** en los argumentos: solo identificadores. El trabajo relee de la base. Un trabajo que arrastra una copia del estado envía el estado viejo cuando se reintenta.
- **[decisión]** Todo trabajo es **reintentable sin efecto duplicado**. Si un trabajo no puede serlo, la operación se parte hasta que lo sea.
- **[decisión]** Los trabajos que tocan datos de un negocio **fijan el tenant explícitamente** al abrir la transacción (ADR-0002). Un trabajador no tiene sesión de usuario y es donde más fácil se cuela una consulta sin filtrar.
- **[decisión]** Se separan **colas por criticidad**: `default` (reactivo, notificaciones), `programado` (cron) y `pesado` (imágenes, exportaciones, recálculo de ranking). Una exportación grande no puede retrasar la confirmación de una reserva.

## Alternativas consideradas

- **Celery.** Es lo que usa el resto de la casa y esa es una razón real. Se descarta aquí porque su integración con código asíncrono sigue siendo incómoda, arrastra más piezas de las que este proyecto necesita y el volumen de v1 no justifica la complejidad. **Si el proyecto acaba compartiendo infraestructura de trabajadores con otro repo de M2G, esta decisión se supera con un ADR nuevo.**
- **Tareas en segundo plano de FastAPI (`BackgroundTasks`).** Descartado: mueren con el proceso, no se reintentan y no se planifican. Sirven para lo trivial, no para dinero ni para mensajes.
- **Cron del sistema llamando a endpoints.** Descartado: mezcla la planificación con el despliegue, que no es de este equipo.
- **Cola en tabla de Postgres, sin Redis.** Tentador por simplicidad, pero Redis ya está en el stack por caché y el planificador de arq resuelve el cron sin escribir uno.

## Consecuencias

- El `docker-compose.yml` levanta **un contenedor de worker** además de la API, con la misma imagen y otro comando. El README lo explica.
- Las pruebas de trabajos se ejecutan **llamando a la función del trabajo directamente**, sin Redis; lo que se prueba es el efecto, no el transporte.
- Hay que vigilar los trabajos fallidos: sin panel, un trabajo que falla siempre es invisible. Entra en el back-office (Fase 3) y, mientras tanto, en un comando de consulta.
