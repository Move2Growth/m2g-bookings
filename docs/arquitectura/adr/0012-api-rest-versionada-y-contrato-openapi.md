# ADR-0012 · Una API REST versionada, con el OpenAPI como contrato generado

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

Una sola API sirve a tres superficies (§4 del brief), y una de ellas —la app— **no se actualiza cuando nosotros queremos**: hay usuarios con versiones viejas durante meses. Eso cambia las reglas de lo que se puede romper.

## Decisión

**[decisión]** REST sobre HTTP, versionada en la ruta: **`/api/v1/…`**. El OpenAPI lo **genera FastAPI** desde el código y de él se derivan los tipos de `packages/api-types`. El contrato no se escribe dos veces.

**Convenciones que no se discuten en cada endpoint:**

- Recursos en plural y en español (`/negocios`, `/reservas`, `/servicios`), coherentes con el vocabulario de [`context/restricciones.md`](../../context/restricciones.md). El mismo término en el código, en la API y en la pantalla.
- Identificadores **UUID v7**: ordenables en el tiempo, sin revelar cuántas reservas hay ni permitir enumerarlas.
- Paginación **por cursor** en todo lo que crece (reservas, reviews, resultados). El desplazamiento por página se degrada y se descuadra cuando entran filas nuevas.
- Fechas y horas **ISO-8601 con desplazamiento explícito** (ADR-0003).
- Importes en **enteros de la unidad mínima** con su código de moneda (ADR-0010).
- **Errores con forma única**: `{ "error": { "codigo": "SLOT_NO_DISPONIBLE", "mensaje": "…", "detalles": {…} } }`. El `codigo` es estable y lo consume el cliente; el `mensaje` es para leer y puede cambiar. Los códigos de dominio (`SLOT_NO_DISPONIBLE`, `FUERA_DE_ANTELACION`, `NEGOCIO_NO_PUBLICADO`, `OTP_INVALIDO`…) se listan en el contrato.
- **Idempotencia en las escrituras que importan**: crear una reserva y cualquier cobro aceptan `Idempotency-Key`. La app va a reintentar sola con 3G, y un reintento no puede crear dos citas.
- **Límite de peticiones** en OTP, búsqueda y escritura, por usuario y por IP. El scraping de la base de negocios es un riesgo declarado.

**[decisión] Regla de compatibilidad dentro de una versión:** se pueden **añadir** campos y valores opcionales; **no** se puede quitar un campo, renombrarlo, estrechar un tipo ni añadir un valor a un enumerado que el cliente ya interpreta. Lo que rompe eso va a `v2`.

- **[decisión]** Los **enumerados viajan en minúsculas con guion bajo** (`cancelada_cliente`), tal como los nombra el brief, y son los mismos en base de datos, API y cliente. *En la casa ya se ha roto un front por serializar enumerados en mayúsculas y comparar en minúsculas: aquí hay un único formato y una prueba que lo fija.*
- **[decisión]** Toda respuesta pública pasa por un **serializador explícito**. Nada de devolver el modelo entero: es como se escapan los teléfonos y los correos.
- **[decisión]** Cada endpoint **cita su requisito** (`RSV-1`, `MKT-3`…) en la descripción del OpenAPI. Es la trazabilidad que pide el brief y sale gratis.

## Alternativas consideradas

- **GraphQL.** Descartado: una sola API, tres clientes propios y un equipo pequeño; añade coste de caché, de autorización por campo y de límites sin resolver ningún problema que tengamos.
- **Versionar por cabecera.** Descartado: se depura peor y se cachea peor que una ruta visible.
- **Sin versión, «ya rompeimos cuando toque».** Descartado: hay app en tiendas.
- **Contrato escrito a mano (OpenAPI primero).** Descartado: dos fuentes de verdad se desincronizan; FastAPI genera el contrato y las pruebas lo verifican.

## Consecuencias

- Cualquier cambio de contrato se ve en el OpenAPI generado; una prueba compara el contrato con el confirmado y **falla si cambia sin querer**.
- El cliente de la web y del back-office son **generados**: un campo renombrado rompe en compilación, no en producción.
- Las claves de idempotencia hay que guardarlas con su respuesta y una caducidad. Es trabajo extra en dos endpoints y evita reservas duplicadas en la calle.
