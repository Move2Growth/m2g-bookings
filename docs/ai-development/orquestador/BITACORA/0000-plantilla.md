# 0000 · Plantilla de entrada de BITACORA (Orquestador)

> El orquestador escribe **una** entrada por LOTE despachado: qué corrió en paralelo, en qué worktrees, cómo se mergeó y qué se escaló. Detalle en `../../PLANTILLAS.md`.

- **Agente:** Orquestador · **Lote:** <id/fecha> · **Fecha:** <la de hoy, p. ej. 2026-09-01>
- **Estado al cerrar:** hecha | bloqueada (escalado)

## Objetivo del lote
<qué pidió el director paralelizar>

## Grafo de decisión
- Tareas consideradas: <IDs + Zona de cada una>
- Paralelizables: <cuáles y por qué (zonas disjuntas / worktree)>
- Serializadas: <cuáles y por qué (dependencia / misma función / migración)>

## Despacho
| Tarea | Rol | Worktree / rama |
|---|---|---|
| <ID> | <rol> | <.claude/worktrees/...> |

## Merge
<orden de menor a mayor riesgo; conflictos triviales resueltos; migraciones al final>

## Pruebas sobre el combinado
<resultado de `make pruebas` sobre el combinado; si aún no hay suite, se dice y se deja a QA>

## Escalado al director (si lo hubo)
<conflicto no trivial / choque de diseño que NO se forzó>

## Estado final
<qué tareas quedaron `hecha` (listas para QA); ESTADO-GLOBAL actualizado>
