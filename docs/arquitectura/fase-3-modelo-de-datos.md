# Fase 3 · Modelo de datos — Estado: completado (Fase 0, pendiente de aprobación de Luis)

> El esquema completo de M2G Agenda, dominio a dominio. Es la traducción a tablas de los requisitos
> del [brief](../BRIEF-PRODUCTO.md) y de las decisiones ya tomadas en los
> [ADR 0001–0014](adr/). **Los ADR no se discuten aquí: el modelo los obedece.** Si algo de este
> documento contradice un ADR, manda el ADR y este documento está mal.

---

## 0. Cómo leer esto

Cada dominio empieza con un índice de sus tablas con tres columnas: el nombre, **si lleva RLS o no**
y el propósito en una frase. Después viene el detalle de columnas de cada tabla en bloques de
pseudo-DDL, y a continuación, en prosa, las restricciones e índices que importan y **por qué**.

No hay DDL literal de todo: sesenta tablas de DDL completo son un documento que nadie lee y que se
desincroniza con la primera migración. Sí hay **DDL literal y ejecutable** de las cinco piezas donde
un error de transcripción cuesta caro: las extensiones y la función de UUID v7, la tabla de
ocupación con su restricción de exclusión, el disparador que la mantiene sincronizada con las
reservas, las políticas RLS de ejemplo y los índices geográficos.

La columna **RLS** de los índices toma exactamente tres valores, que vienen de ADR-0002:

| Valor | Qué significa |
|---|---|
| **sí** | La tabla lleva `business_id NOT NULL` y una política que la compara contra `app.current_business_id`. Es dato de un negocio y ningún otro negocio lo ve. |
| **no · catálogo global** | Taxonomías y configuración compartida, de solo lectura para el negocio. No lleva `business_id` y no tiene sentido aislarla. |
| **no · plataforma** | Datos de una persona o del sistema, que **no pertenecen a un negocio**: un cliente es de la plataforma, no de un salón. Se protegen por identidad del usuario o por rol interno, no por tenant. |

---

## 1. Convenciones que valen para todas las tablas

### 1.1 Identificadores

**UUID v7 en todas las claves primarias** (ADR-0012). Ordenables en el tiempo —el índice primario no
se fragmenta como con UUID v4—, y no revelan cuántas reservas hay ni permiten enumerarlas, que es lo
que pasa con un `bigserial` expuesto en una URL pública.

PostgreSQL 16 no trae `uuidv7()` nativo, así que la migración inicial instala la función. La
aplicación también genera identificadores del lado de Python, porque necesita conocer el ID antes de
insertar para encadenar filas relacionadas; el `DEFAULT` de la base es la red por si alguna ruta
inserta sin darlo.

### 1.2 Tiempo

Directamente de ADR-0003, y **no se mezcla**:

- **Instantes** (`bookings.starts_at`, `notifications.scheduled_for`, todo lo que termina en `_at`):
  `timestamptz`, siempre UTC.
- **Reglas horarias recurrentes** (horario del negocio, horario del profesional, descansos, bloqueos
  recurrentes): `weekday smallint` + `time` **local**, sin fecha y sin huso.
- **La zona** vive en `businesses.timezone`, texto IANA, `NOT NULL`, con `America/Panama` por
  defecto. Es obligatoria porque el motor de disponibilidad no puede convertir una regla local en un
  instante sin ella, y porque España viene después.
- `weekday` va de 0 a 6 con **0 = lunes**. Se fija aquí para que nadie lo interprete al revés: es la
  clase de detalle que produce un horario desplazado un día y una tarde perdida buscándolo.
- Un cierre que cruza medianoche se modela con `closes_at < opens_at` en la misma fila, no en dos.

### 1.3 Enumerados

**Texto en minúsculas con guion bajo, validado con `CHECK`**, exactamente los valores que nombra el
brief. No se usan tipos `ENUM` nativos de PostgreSQL: añadir un valor obliga a `ALTER TYPE` fuera de
transacción en algunas versiones, quitarlo es imposible, y las taxonomías que el back-office tiene
que poder tocar sin desplegar (ADM-4) son tablas, no tipos.

Los valores son **los mismos en base de datos, en la API y en el cliente** (ADR-0012). En esta casa
ya se rompió un front por serializar enumerados en mayúsculas y compararlos en minúsculas; aquí hay
un solo formato y una prueba que lo fija.

El enumerado de estado de reserva es **literalmente** el de RSV-3, sin sinónimos ni abreviaturas:

```
pendiente · confirmada · completada · no_show · cancelada_cliente · cancelada_negocio
```

La reprogramación **no es un estado**: es una fila en `booking_events` y un puntero
`bookings.rescheduled_from_id`. Una cita reprogramada sigue `confirmada`.

### 1.4 Dinero

**Enteros de la unidad mínima** (`bigint`, centavos) más `currency char(3)` por fila (ADR-0010).
Nunca coma flotante y nunca `numeric` para importes: el redondeo de dinero se hace una vez, al
presentar. El símbolo que se pinta (`$`, D12) es configuración en `platform_settings`, no una
constante en el código, y el nombre comercial tampoco se mete a fuego en ninguna parte (D1).

### 1.5 Columnas de auditoría y borrado

Toda tabla de dominio lleva `created_at timestamptz NOT NULL DEFAULT now()` y, si es mutable,
`updated_at`. Las tablas cuyo borrado destruiría historia del negocio llevan `deleted_at` y se
borran de forma lógica; el resto se borran de verdad. Qué se borra y qué se anonimiza cuando un
usuario ejerce su derecho al olvido está en la sección 14, tabla por tabla, y no se improvisa
(ADR-0006 lo exige explícitamente).

### 1.6 Índices

Toda clave foránea que se usa para filtrar lleva índice; PostgreSQL **no** los crea solos y el
primer `DELETE` de un negocio con 4.000 reservas lo descubre por las malas. Los índices que se
listan en cada dominio son los que responden a una consulta real del producto, no un barrido
preventivo: un índice que nadie usa se paga en cada escritura.

### 1.7 Extensiones y utilidades — DDL literal

```sql
-- Migración inicial. Las tres extensiones son obligatorias desde el primer día
-- (ADR-0005 PostGIS, ADR-0004 btree_gist, pgcrypto para hashes y bytes aleatorios).
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- UUID v7. PostgreSQL 16 no lo trae; se instala aquí para que el DEFAULT exista
-- aunque alguna ruta inserte sin generar el identificador en la aplicación.
CREATE OR REPLACE FUNCTION uuid_generate_v7() RETURNS uuid
LANGUAGE plpgsql VOLATILE PARALLEL SAFE AS $$
BEGIN
  -- Se toma un UUID v4 aleatorio, se le sobreescriben los 48 primeros bits con la
  -- marca de tiempo en milisegundos y se corrige el nibble de versión de 4 a 7.
  RETURN encode(
    set_bit(
      set_bit(
        overlay(
          uuid_send(gen_random_uuid())
          PLACING substring(
            int8send(floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint) FROM 3
          )
          FROM 1 FOR 6
        ),
        52, 1),
      53, 1),
    'hex')::uuid;
END $$;

-- Desplazamiento de un instante por un número entero de minutos.
-- Existe por una razón concreta: `timestamptz + interval` está marcado STABLE en
-- PostgreSQL (porque un intervalo con días o meses depende del huso), y una columna
-- generada exige IMMUTABLE. Con `secs =>` el intervalo no tiene componente de día ni
-- de mes, así que la suma es aritmética pura sobre el instante y sí es inmutable de
-- verdad. Esto es lo que permite que blocked_from y blocked_to sean columnas
-- generadas y persistidas por la base, como manda ADR-0004, y no calculadas por la
-- aplicación.
CREATE OR REPLACE FUNCTION desplazar_minutos(t timestamptz, minutos integer)
RETURNS timestamptz
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
  SELECT t + make_interval(secs => minutos * 60);
$$;

-- Lector del tenant activo. Devuelve NULL si nadie lo fijó, y una política que
-- compara contra NULL no devuelve filas: el fallo es cerrado, no abierto.
CREATE OR REPLACE FUNCTION app_negocio_actual() RETURNS uuid
LANGUAGE sql STABLE PARALLEL SAFE AS $$
  SELECT nullif(current_setting('app.current_business_id', true), '')::uuid;
$$;
```

### 1.8 Roles de base de datos

Cuatro roles, porque el aislamiento de ADR-0002 depende de que el rol de la API no pueda saltárselo:

| Rol | Quién lo usa | Qué puede |
|---|---|---|
| `agenda_owner` | Solo las migraciones | Dueño de las tablas. La aplicación nunca se conecta con él. |
| `agenda_api` | La API en modo negocio | Sujeto a RLS. **No tiene `BYPASSRLS` y no es dueño de las tablas**, así que ni un `SELECT *` sin `WHERE` se lleva datos ajenos. |
| `agenda_publico` | Marketplace y páginas públicas | Solo lectura, y solo sobre las filas publicables: negocios `publicado`, sus servicios activos, su equipo visible y sus reviews publicadas. **Nunca ve reservas ni fichas de cliente.** |
| `agenda_admin` | Back-office de M2G | Acceso amplio y **auditado**, con su propia sesión y 2FA (ADR-0006). Nunca es el mismo rol que la API pública. |

Además, **el filtro de aplicación se escribe igual** (ADR-0002): RLS es la red, no la excusa para
consultar sin `WHERE`. Sin filtro explícito el planificador elige peor y los índices por
`business_id` no se aprovechan.

---
