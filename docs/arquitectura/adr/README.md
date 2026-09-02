# ADR — registro de decisiones de arquitectura

> Una **ficha por decisión**. Decididas, **no se editan**: se crea una nueva que la *supera*.

## Formato de cada ADR (`NNNN-titulo-en-kebab.md`)

```markdown
# ADR-NNNN · <Título de la decisión>

- **Estado:** propuesta | aceptada | superada por ADR-MMMM
- **Fecha:** AAAA-MM-DD

## Contexto
<qué problema o fuerza obliga a decidir; restricciones relevantes (ver constitution.md)>

## Decisión
<qué se decide, en frases claras. Marca [decisión]/[supuesto]/[pregunta abierta]>

## Alternativas consideradas
<las opciones que se descartaron y por qué>

## Consecuencias
<qué implica esta decisión: lo bueno, lo malo, lo que habilita y lo que cierra>
```

## Índice

| ADR | Título | Estado | Qué decide |
|---|---|---|---|
| [0001](0001-monorepo-y-estructura.md) | Monorepo con pnpm workspaces y `apps/` + `packages/` | aceptada | Dónde vive cada superficie y cómo conviven Python y JavaScript |
| [0002](0002-multi-tenant-con-rls.md) | Multi-tenant con Row Level Security | aceptada | El aislamiento entre negocios lo garantiza Postgres, no un `WHERE` que alguien puede olvidar |
| [0003](0003-tiempo-utc-y-zona-del-negocio.md) | El tiempo se guarda en UTC; la zona vive en el negocio | aceptada | Instantes en `timestamptz` y reglas horarias como día + hora local; España entra sin migrar |
| [0004](0004-no-doble-reserva-restriccion-de-exclusion.md) | La no doble reserva es una restricción de exclusión | aceptada | `EXCLUDE USING gist` sobre el rango bloqueado con buffers incluidos. La garantía la da la base |
| [0005](0005-geo-postgis-y-taxonomia-de-zonas.md) | PostGIS para distancia, taxonomía de zonas para SEO | aceptada | «Cerca de mí» y «barbería en San Francisco» son dos mecanismos distintos |
| [0006](0006-identidad-otp-sesiones-y-rbac.md) | Teléfono con OTP, refresco revocable, permisos por membresía | aceptada | Quién eres, cómo lo demuestras y qué puedes hacer, separados |
| [0007](0007-notificaciones-cola-idempotente-y-proveedor-abstracto.md) | Cola idempotente detrás de un proveedor intercambiable | aceptada | La tabla `notifications` es la cola; la clave de idempotencia sale del hecho, no del reloj |
| [0008](0008-trabajos-en-segundo-plano-con-arq.md) | Trabajos y planificación con arq | aceptada | El cron encola, no envía; los trabajos llevan identificadores, no objetos |
| [0009](0009-ranking-configurable-y-rating-bayesiano.md) | Ranking con pesos en base de datos; rating bayesiano | aceptada | Ningún número de ranking en el código; los patrocinados se intercalan, no compiten |
| [0010](0010-planes-y-billing-desde-el-dia-uno.md) | El motor de planes existe desde el día uno aunque cobre 0 | aceptada | Subir el precio a 1 $ es un `UPDATE` en el back-office, no un proyecto |
| [0011](0011-superficies-next-ssr-y-vite-spa.md) | Next.js con SSR para lo público; Vite SPA para el back-office | aceptada | Sin SSR indexable no hay marketplace. El panel de negocio va con la web pública |
| [0012](0012-api-rest-versionada-y-contrato-openapi.md) | API REST versionada con el OpenAPI como contrato generado | aceptada | Convenciones, errores con forma única, idempotencia y regla de compatibilidad |
| [0013](0013-design-system-propio-mobile-first.md) | Design system propio, mobile-first, con tokens | aceptada | Se diseña a 390 px primero; modo claro por defecto; tokens como fuente única |
| [0014](0014-entorno-local-migraciones-y-seed.md) | Entorno local de un comando, migraciones desde cero y seed real | aceptada | Lo que hay que dejar impecable para que el despliegue de Luis no adivine nada |
| [0015](0015-la-marca-es-bukeo.md) | La marca es Bukeo | aceptada | Supera el «por definir» de D1. La identidad vive en el brandbook y se implementa en los tokens |
