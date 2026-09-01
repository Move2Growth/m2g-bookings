# ADR-0001 · Monorepo con pnpm workspaces y `apps/` + `packages/`

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

El producto son **tres superficies** (web pública SSR, back-office SPA, app Expo) contra **una sola API**. El brief §8 pide monorepo con paquetes compartidos: tipos generados desde OpenAPI, design tokens y componentes. El backend es Python y las tres superficies son JavaScript, así que el monorepo tiene que convivir con dos gestores de dependencias.

## Decisión

**[decisión]** Un único repositorio con esta estructura:

```
apps/
  api/          FastAPI · Python 3.12 · uv           (pyproject.toml propio)
  worker/       jobs y cron sobre la misma imagen que la API
  web/          Next.js (SSR) — marketplace + panel de negocio
  backoffice/   React + Vite (SPA) — equipo M2G
  mobile/       Expo / React Native                  (Fase 5, no en este encargo)
packages/
  api-types/    tipos TypeScript generados desde el OpenAPI de la API
  tokens/       design tokens (fuente única: JSON → CSS vars + TS)
  ui/           componentes compartidos entre web y backoffice
infra/
  local/        docker-compose.yml, seeds y utilidades de desarrollo
docs/
```

- **[decisión]** JavaScript se gestiona con **pnpm workspaces**; Python con **uv**, con su `pyproject.toml` dentro de `apps/api`. No se intenta meter Python en el workspace de pnpm.
- **[decisión]** `apps/worker` **no es otro proyecto Python**: comparte código con `apps/api` y se distingue solo por el proceso que arranca. Evita duplicar modelos y configuración.
- **[decisión]** `packages/api-types` es **generado, nunca escrito a mano**. La API publica el OpenAPI y un comando regenera los tipos; si el contrato cambia, los consumidores rompen en compilación, que es exactamente lo que se quiere.
- **[decisión]** `packages/ui` **no lo consume `apps/mobile`**: React Native no comparte DOM. Lo que se comparte con móvil son los tokens y los tipos.

## Alternativas consideradas

- **Repos separados por superficie.** Descartado: el contrato de API se desincroniza en cuanto hay dos repos, y aquí la API es la misma para las tres superficies.
- **Nx o Turborepo.** Descartado para v1: aportan caché y grafo de tareas que aún no hacen falta, y añaden una capa que hay que aprender. Se puede adoptar después sin mover archivos.
- **Un solo `package.json` en la raíz sin workspaces.** Descartado: las dependencias de Next y de Expo chocan.

## Consecuencias

- Un cambio de contrato se ve en un solo commit que toca API y consumidores. Es lo que se quiere.
- El arranque local necesita **dos herramientas** (`uv` y `pnpm`); el README lo dice en pasos numerados.
- `apps/mobile` se crea vacío en la Fase 5, no ahora: carpetas vacías no se dejan.
- La raíz queda con `pnpm-workspace.yaml`, `package.json` de orquestación y `Makefile` con los comandos de un solo golpe.
