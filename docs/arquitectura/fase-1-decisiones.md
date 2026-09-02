# Decisiones de cimientos — Estado: completado (Fase 0)

> Qué se decidió antes de escribir una línea de código, y **por qué esas y no otras**. El
> detalle de cada una está en su ficha: el índice completo, con el estado de cada ADR, vive en
> [`adr/README.md`](adr/README.md) y es la fuente de verdad. Este documento es la lectura
> corta: agrupa las catorce decisiones por el problema que resuelven.
>
> **Un ADR aceptado no se edita: se supera con otro.** Si algo de aquí deja de ser cierto, lo
> que hay que escribir es una ficha nueva, no una corrección.

---

## Las cuatro decisiones de las que cuelga todo lo demás

Si solo se van a leer cuatro, que sean estas. Las diez restantes se pueden revisar más
adelante sin rehacer nada; estas cuatro, no.

| Decisión | Qué fija | Qué costaría cambiarla después |
|---|---|---|
| [ADR-0002 · Multi-tenant con RLS](adr/0002-multi-tenant-con-rls.md) | El aislamiento entre negocios lo garantiza PostgreSQL, no un `WHERE` que alguien puede olvidar, y **desde la primera migración** | Tocar todas las consultas del proyecto. Es lo más caro que se puede dejar para luego, y el encargo lo dice con esas palabras |
| [ADR-0004 · Restricción de exclusión](adr/0004-no-doble-reserva-restriccion-de-exclusion.md) | Que **no pueda existir** una doble reserva, aunque el código de aplicación esté mal | Rehacer el modelo de ocupación con reservas vivas dentro, y descubrir los solapes ya creados |
| [ADR-0003 · UTC con la zona en el negocio](adr/0003-tiempo-utc-y-zona-del-negocio.md) | Instantes en UTC y reglas horarias como día más hora local. España entra sin migrar datos | Una migración de husos con citas dentro: de las peores que existen |
| [ADR-0011 · Next con SSR para lo público](adr/0011-superficies-next-ssr-y-vite-spa.md) | Que Google pueda indexar perfiles y páginas de zona, de donde llega media clientela | Reescribir la superficie más grande del producto |

---

## Cómo se organiza el código

- [**ADR-0001 · Monorepo**](adr/0001-monorepo-y-estructura.md): un repositorio con `apps/` y
  `packages/`, JavaScript con pnpm y Python con uv, sin intentar que convivan en el mismo
  gestor. Los tipos del cliente se **generan** del OpenAPI.
- [**ADR-0012 · API REST versionada**](adr/0012-api-rest-versionada-y-contrato-openapi.md):
  una sola API para las tres superficies, errores con forma única, idempotencia donde importa,
  y una regla de compatibilidad escrita, porque hay una app en tiendas que no se actualiza
  cuando nosotros queremos.

## Cómo se guardan y se protegen los datos

- [**ADR-0002 · RLS**](adr/0002-multi-tenant-con-rls.md) y
  [**ADR-0006 · Identidad**](adr/0006-identidad-otp-sesiones-y-rbac.md): quién eres, cómo lo
  demuestras y qué puedes hacer, en tres piezas separadas, con refresco revocable porque el
  borrado de cuenta es un requisito legal.
- [**ADR-0005 · PostGIS y zonas**](adr/0005-geo-postgis-y-taxonomia-de-zonas.md): «cerca de mí»
  y «barbería en San Francisco» son dos problemas distintos y se resuelven con dos mecanismos
  distintos.

## Cómo se comporta el producto

- [**ADR-0004 · No doble reserva**](adr/0004-no-doble-reserva-restriccion-de-exclusion.md) y
  [**ADR-0003 · Tiempo**](adr/0003-tiempo-utc-y-zona-del-negocio.md): el motor de
  disponibilidad y su garantía.
- [**ADR-0009 · Ranking y rating bayesiano**](adr/0009-ranking-configurable-y-rating-bayesiano.md):
  ningún número de ranking en el código, y una review de cinco estrellas no adelanta a ochenta
  de 4,7.
- [**ADR-0010 · Planes desde el día uno**](adr/0010-planes-y-billing-desde-el-dia-uno.md):
  subir el precio de 0 a 1 dólar es un cambio en el back-office, no un proyecto.

## Cómo se trabaja fuera de la petición

- [**ADR-0007 · Cola de notificaciones**](adr/0007-notificaciones-cola-idempotente-y-proveedor-abstracto.md):
  la tabla es la cola, la clave de idempotencia sale del hecho y no del reloj, y el proveedor
  es intercambiable.
- [**ADR-0008 · Trabajos con arq**](adr/0008-trabajos-en-segundo-plano-con-arq.md): el
  planificador encola, no envía.

## Cómo se ve y cómo se levanta

- [**ADR-0013 · Design system propio**](adr/0013-design-system-propio-mobile-first.md): tokens
  como fuente única, modo claro por defecto, y se diseña a 390 px primero.
- [**ADR-0014 · Entorno local**](adr/0014-entorno-local-migraciones-y-seed.md): un comando,
  migraciones desde cero y un seed con datos de un salón panameño de verdad.

---

## Lo que deliberadamente **no** se ha decidido

No por olvido: porque **no le corresponde al equipo**. Están todas en
[`fase-0-descubrimiento.md`](fase-0-descubrimiento.md) con el valor que se usa mientras tanto —
el nombre comercial y el dominio, la pasarela concreta, el proveedor de mapas, y cualquier cosa
que cobre dinero de verdad. Ninguna bloquea construir las fases 0 a 2.
