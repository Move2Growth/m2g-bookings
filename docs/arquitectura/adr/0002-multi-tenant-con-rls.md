# ADR-0002 · Multi-tenant con Row Level Security de PostgreSQL

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

El tenant es **el negocio**. La garantía nº 1 de la [constitution](../constitution.md) es que ninguna consulta devuelva datos de otro negocio, y el encargo lo exige **desde la primera migración**: meterlo después toca todas las consultas.

El filtro en la capa de aplicación (`WHERE business_id = :actual` en cada query) falla por omisión: basta que un endpoint nuevo olvide el filtro para filtrar la base entera. Y va a haber muchos endpoints y varios agentes escribiéndolos.

## Decisión

**[decisión]** Aislamiento en **la base de datos, con Row Level Security**, no solo en la aplicación.

- Toda tabla con datos de un negocio lleva **`business_id NOT NULL`** y una política RLS que compara contra el ajuste de sesión **`app.current_business_id`**.
- La API abre cada petición fijando ese ajuste con `SET LOCAL` dentro de la transacción, a partir del token del usuario y del negocio activo. `SET LOCAL` muere con la transacción: una conexión reutilizada del pool no arrastra el tenant anterior.
- El usuario de aplicación de Postgres **no es el dueño de las tablas y no tiene `BYPASSRLS`**. Ni siquiera un `SELECT *` sin `WHERE` se lleva datos ajenos.
- Las tablas globales (`service_categories`, `zones`, `plans`, `feature_flags`, taxonomías) **no llevan RLS**: son catálogo compartido de solo lectura para el negocio.
- Las tablas del cliente final (`users`, `client_profiles`, `favorites`) **no se aíslan por negocio** — un cliente es de la plataforma, no de un salón. Lo que sí se aísla es su **ficha en un negocio** (`business_clients`) y sus reservas.
- El back-office de M2G usa un rol distinto con política de *bypass explícito y auditado*, del mismo modo que el resto de la casa: nunca el mismo rol que la API pública.
- **[decisión]** El filtro de aplicación **también se escribe**. RLS es la red, no la excusa para consultar sin `WHERE`: sin filtro explícito los planes de consulta empeoran y los índices no se usan igual.

## Alternativas consideradas

- **Solo filtro en la aplicación.** Descartado: una omisión es una fuga de la base entera y no hay forma de probarlo exhaustivamente.
- **Una base de datos (o esquema) por negocio.** Descartado: 5.000 negocios en v1; las migraciones y las consultas del marketplace, que cruzan todos los negocios, se vuelven inviables.
- **Vistas filtradas.** Descartado: mismo problema que el filtro de aplicación, con más piezas.

## Consecuencias

- **Habilita una prueba decisiva:** con el tenant A fijado, ninguna consulta a ninguna tabla devuelve filas de B. Es una prueba automática obligatoria (la escribe Testing) y criterio de rechazo de QA.
- Las consultas del **marketplace** cruzan negocios: se sirven con el rol de lectura pública sobre columnas publicables, no con el rol del negocio.
- El pool de conexiones debe ser **transaccional**; si algún día entra PgBouncer, va en modo *transaction* y `SET LOCAL` sigue siendo correcto.
- Coste: cada migración nueva tiene que acordarse de activar la política. Se cubre con una prueba que recorre el catálogo y falla si aparece una tabla con `business_id` y sin RLS.
