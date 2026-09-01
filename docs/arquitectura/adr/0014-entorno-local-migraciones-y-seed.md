# ADR-0014 · Entorno local de un comando, migraciones desde cero y un seed con datos reales

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

El despliegue **no es de este equipo**. Lo que sí es nuestro es que Luis pueda levantar y desplegar esto **sin adivinar nada**. El encargo lista lo que tiene que quedar impecable: un `docker-compose.yml` de un solo comando con datos de ejemplo, migraciones que corran contra una base limpia sin pasos manuales, `.env.example` documentado variable a variable, un README en pasos numerados y las pruebas corriendo en local con un comando.

Y una advertencia con historia en la casa: *«nunca Servicio 1 · 100,00»*. Con datos de mentira **no se ve** que una reserva de tres horas no cabe en el hueco de las cinco de la tarde.

## Decisión

**[decisión]** Todo el entorno local vive en **`infra/local/`** y se gobierna desde un `Makefile` en la raíz:

| Comando | Qué hace |
|---|---|
| `make arriba` | Levanta el stack entero: API, Postgres con PostGIS, Redis, worker y web. Aplica migraciones y carga el seed **automáticamente** |
| `make abajo` | Lo para y libera los puertos |
| `make migrar` | Aplica migraciones contra la base local |
| `make semilla` | Recarga el seed sobre una base limpia |
| `make pruebas` | Ejecuta todas las pruebas |
| `make contrato` | Regenera el OpenAPI y los tipos de `packages/api-types` |

- **[decisión]** El proyecto de Compose lleva **`name:` explícito** (`m2g-agenda`). *En esta casa ya ha pasado que un `docker compose up` en un repo recreara el Postgres de otro por compartir el nombre del proyecto.* No es opcional.
- **[decisión]** La imagen de base de datos es **`postgis/postgis:16-3.4`**, no `postgres:16`. La extensión hace falta desde la primera migración (ADR-0005) y el `postgres` pelado no la trae.
- **[decisión]** Migraciones con **Alembic**, una por cambio, **siempre probadas contra un Postgres real** desde una base vacía. Las extensiones (`postgis`, `btree_gist`, `pgcrypto`) se activan en la migración inicial, no a mano.
- **[decisión]** El seed no es un accesorio: es **material de prueba**. Carga un barrio de Ciudad de Panamá con negocios verosímiles —una barbería con dos barberos, un salón con cuatro profesionales y horarios distintos entre sí, un spa que cierra al mediodía, una manicurista independiente— con servicios de verdad: «Corte + barba · 45 min · $18», «Balayage · 3 h · desde $120», «Manicura semipermanente · 1 h 15 · $25». Y con **la agenda medio llena**, para que los huecos difíciles existan sin fabricarlos.
- **[decisión]** El seed es **idempotente y determinista**: se puede volver a cargar, y las fechas se generan **relativas a hoy** (no fijas), para que la agenda de ejemplo nunca aparezca vacía por haber quedado en el pasado.
- **[decisión]** `.env.example` lleva **todas** las variables con una línea de para qué sirve cada una, y el inventario vive en [`../operacion/SECRETOS-Y-VARIABLES.md`](../operacion/SECRETOS-Y-VARIABLES.md). **Nombre y propósito, nunca el valor.** Toda variable nueva se documenta **en la misma sesión** en que aparece.
- **[decisión]** Ningún servicio externo es necesario para levantar el entorno. WhatsApp, pasarela y mapas tienen **implementación de desarrollo** (ADR-0007, ADR-0010, ADR-0005): sin credenciales, el stack arranca y las pruebas pasan.

## Alternativas consideradas

- **Documentar los pasos a mano en el README sin Makefile.** Descartado: los pasos se desactualizan; un comando que se ejecuta, no.
- **Seed mínimo (un negocio, un servicio).** Descartado: es exactamente el seed con el que un fallo de agenda no se ve. *En otro repo de la casa un fallo se coló hasta producción porque los datos de prueba no se parecían a los reales.*
- **SQLite para las pruebas.** Descartado: aquí lo que hay que probar son restricciones de exclusión, RLS y PostGIS. Nada de eso existe en SQLite. Las pruebas corren contra Postgres real.

## Consecuencias

- Las pruebas necesitan un Postgres levantado. `make pruebas` lo levanta si hace falta: que las pruebas «pasen» porque se saltaron todas es un fallo conocido en la casa y aquí **el corredor de pruebas falla si no hay base de datos**, en vez de saltárselas en silencio.
- El seed hay que mantenerlo cuando cambie el modelo. Es coste real y compra la única forma de ver el producto funcionando de verdad.
- Luis recibe un README de arranque numerado. **Si al leerlo hay que adivinar algo, no está terminado.**
