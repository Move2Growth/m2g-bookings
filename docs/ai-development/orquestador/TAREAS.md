# Tareas: Orquestador — **Estado: sin iniciar**

> El orquestador **no tiene backlog de construcción**: el director le da un objetivo o un bloque que paralelizar en el momento. Esta tabla recoge lo **metodológico** que sí es suyo y los lotes candidatos que ya se ven en los `TAREAS.md` de los demás.
> Estados de tarea: `pendiente` · `en curso` · `bloqueada` · `hecha` · `validada`.

| ID | Descripción | Fase | Zona | Estado | Depende de | Criterio de aceptación |
|---|---|---|---|---|---|---|
| ORQ-T001 | **Verificar el `.gitignore` antes del primer lote**: `.claude/worktrees/`, `__pycache__/`, `*.pyc`, `node_modules/`, `dist/`, `build/` y `.DS_Store`. **Si falta, no se paraleliza nada hasta corregirlo** — sin esto, un worktree propaga artefactos a la rama, y ya ha pasado | — | raíz | pendiente | DEV-T001 | El `.gitignore` está completo y comprobado **antes** de crear el primer worktree |
| ORQ-T002 | **Lote candidato de la Fase 0**: `ARQ-T009` —árbol de zonas—, `MCK-T001` —tokens— y `DEV-T001` —esqueleto del monorepo— tocan `docs/arquitectura`, `packages/tokens` y la raíz. **Zonas disjuntas, sin dependencia entre ellas y ninguna escribe una migración** | 0 | transversal | pendiente | ORQ-T001 | El lote mergea sin conflicto; el tablero lo escribió **solo el orquestador**; ninguna tarea tocó la zona de otra |
| ORQ-T003 | **Lote candidato del bloque 1.c**: `BE-T006` —catálogo de servicios— y `BE-T007` —equipo— viven en módulos distintos de la API. **Solo paralelizables si ninguna de las dos escribe en `apps/api/migraciones`**; si las dos necesitan migración, se serializan | 1.c | apps/api/catalogo, apps/api/equipo | pendiente | ORQ-T001 | Si alguna necesita migración, **se serializa y se dice por qué**. Las migraciones se mergean al final y en serie, renumerando si chocan |
| ORQ-T004 | **Mantener la lista de zonas serializadas** del `AGENTE.md` cada vez que aparezca un módulo nuevo en la API. Una zona caliente que nadie declaró es un conflicto garantizado la primera vez que se paralelice sobre ella | — | docs/ai-development | pendiente | — | La lista de zonas serializadas coincide con los módulos que existen de verdad |

> **Lo que NO se paraleliza nunca en este proyecto:** cualquier cosa que toque `apps/api/disponibilidad` —el motor es una sola pieza y una sola verdad—, dos tareas que escriban migraciones a la vez, y dos que toquen `packages/tokens`.
