# docs/arquitectura — el plano de M2G Agenda

> El «plano del edificio»: las decisiones de arquitectura y el diseño. **La fuente de verdad.** Lo que no está aquí, no está decidido.

## Contenido

| Archivo / carpeta | Qué es |
|---|---|
| [`constitution.md`](constitution.md) | Los **principios no negociables** y las ocho garantías que no se rompen. Todo agente los respeta. |
| [`adr/`](adr/) | Una **ficha por decisión** (Contexto · Decisión · Alternativas · Consecuencias). Catorce ADR aceptados; el índice está en [`adr/README.md`](adr/README.md). |
| [`fase-0-descubrimiento.md`](fase-0-descubrimiento.md) | Lo que **ya decidió Luis** (D1–D18) y **lo que sigue abierto**, con el valor por defecto que se usa mientras tanto. |
| [`fase-3-modelo-de-datos.md`](fase-3-modelo-de-datos.md) | Entidades, aislamiento por negocio, geo, y los huecos que se dejan hoy para lo de v2. |
| [`fase-3-motor-disponibilidad.md`](fase-3-motor-disponibilidad.md) | **La pieza donde se juega el producto**: definición de slot, concurrencia y los 18 casos que hay que probar antes de escribir el motor. |
| [`fase-3-contratos-api.md`](fase-3-contratos-api.md) | El mapa de endpoints de las fases 1 y 2, con su requisito del brief al lado. |
| [`fase-5-plan-de-sprints.md`](fase-5-plan-de-sprints.md) | Las fases 0, 1 y 2 desglosadas en sprints, con dueño y criterio de «hecho» observable. |

## Reglas

- **Los ADR decididos NO se editan.** Si una decisión debe cambiar, se escribe un ADR nuevo que la *supera*; no se borra la historia.
- Cada afirmación se marca **[decisión] / [supuesto] / [pregunta abierta]**.
- Español llano; cada término técnico definido la primera vez (ver [`../ai-development/GLOSARIO.md`](../ai-development/GLOSARIO.md)).
- **Si esto y el [brief](../BRIEF-PRODUCTO.md) dicen cosas distintas, manda el brief** y se avisa a Luis.
