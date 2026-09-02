# CLAUDE.md — contexto del proyecto Bukeo

> El contexto que Claude Code carga al arrancar en este repo. **Corto a propósito:** lo que ya está en `context/` o en `docs/` no se duplica aquí, se **importa** o se enlaza.

## El proyecto en una frase

**Bukeo es una plataforma de reservas y marketplace de belleza y bienestar para Panamá, gratis para el negocio:** el salón gestiona agenda, equipo y clientes sin pagar nada, el cliente descubre y reserva desde el móvil, y M2G monetiza con posicionamiento pagado y una suscripción cuyo precio es un parámetro (0 al lanzamiento).

**El nombre comercial es Bukeo** (ADR-0015, que supera el «por definir» de D1). Aun así **no se escribe a fuego en ninguna pantalla**: sale de configuración y de los tokens, para que un cambio de marca sea cambiar valores y no componentes.

## Principio rector (NO cambia)

La memoria del proyecto vive en **archivos `.md` versionados**, no en el chat. Cualquier agente arranca leyendo sus archivos y entiende quién es, qué le toca y en qué estado está todo. Lo que no está escrito, no existe.

## Briefs de contexto (importados)

@context/negocio.md
@context/producto.md
@context/restricciones.md

## Dónde está cada cosa

| Necesitas… | Está en | Qué es |
|---|---|---|
| **Qué hay que construir** | [`docs/BRIEF-PRODUCTO.md`](docs/BRIEF-PRODUCTO.md) | **La ley de producto.** Trece secciones, requisitos codificados (ONB-1, RSV-3, MKT-4…), fases y 18 decisiones con su valor por defecto. Es de Luis: no se edita. |
| **Cómo hay que construirlo** | [`PROMPT-CONSTRUCTOR.md`](PROMPT-CONSTRUCTOR.md) | **El encargo.** Orden, reglas duras y lo que no decide el equipo. Si choca con el brief, **manda el brief**. |
| **Las decisiones ya tomadas** | [`docs/arquitectura/adr/`](docs/arquitectura/adr/) | Una ficha por decisión. **Un ADR decidido no se edita: se supera con otro.** |
| **Lo que aún no está decidido** | [`docs/arquitectura/fase-0-descubrimiento.md`](docs/arquitectura/fase-0-descubrimiento.md) | Preguntas abiertas a Luis. Ningún agente resuelve una por su cuenta. |
| **Los principios que nadie rompe** | [`docs/arquitectura/constitution.md`](docs/arquitectura/constitution.md) | Si una tarea choca con un principio de aquí: **parar y escalar**. |
| **El modelo de datos** | [`docs/arquitectura/fase-3-modelo-de-datos.md`](docs/arquitectura/fase-3-modelo-de-datos.md) | Entidades, multi-tenant, geo y los huecos dejados para v2. |
| **El motor de disponibilidad** | [`docs/arquitectura/fase-3-motor-disponibilidad.md`](docs/arquitectura/fase-3-motor-disponibilidad.md) | La pieza donde se juega el producto: definición de slot, concurrencia y los casos límite que hay que probar. |
| **El plan de fases** | [`docs/arquitectura/fase-5-plan-de-sprints.md`](docs/arquitectura/fase-5-plan-de-sprints.md) | Fases 0–2 (este encargo) desglosadas en sprints con criterio de hecho. |
| **Quién hace qué** | [`docs/ai-development/README.md`](docs/ai-development/README.md) | Reglas del sistema, mapa de roles y guía de lanzamiento. |
| **En qué estado está todo** | [`docs/ai-development/ESTADO-GLOBAL.md`](docs/ai-development/ESTADO-GLOBAL.md) | **El tablero. El primer sitio que mira cualquiera**, incluida la deuda viva. |
| **Secretos y variables** | [`docs/operacion/SECRETOS-Y-VARIABLES.md`](docs/operacion/SECRETOS-Y-VARIABLES.md) | Inventario único. Todo secreto nuevo se documenta aquí **y** en `.env.example` en la misma sesión. Nombre y para qué, **nunca el valor**. |

## Cómo se trabaja aquí

- **Todo entra por la rama `development`.** `main` no recibe commits directos.
- **La arquitectura antes que el código.** Cada decisión se escribe como ADR; los decididos no se editan, se superan.
- **Nada pendiente solo en prosa:** va al tablero con estado `sin iniciar` | `en proceso` | `completado`.
- **Un foco cada vez.** Nada pasa a `validada` sin QA.
- **Verificar en vivo, no "build verde":** la UI se mira en el navegador y **a 390 px**, que es donde vive esto.
- **Infra y despliegue no son de este equipo** (ver `PROMPT-CONSTRUCTOR.md`): se desarrolla y valida en local, y se deja `docker-compose.yml`, migraciones desde cero, `.env.example` y README de arranque impecables.

## Equipo de agentes

Once roles, definidos en [`.claude/agents/`](.claude/agents/) con el prefijo `agenda-`. Cada definición es corta: arranca el motor y manda al agente a leer sus `.md` en `docs/ai-development/<rol>/`. **Si la definición y los `.md` divergen, mandan los `.md`.** Datos/IA está descartado: en las fases 0–2 no hay pipeline de datos ni modelos.

## Preferencias personales

Tus preferencias (no compartidas, no commiteadas) van en `CLAUDE.local.md` (copia de `CLAUDE.local.md.example`).
