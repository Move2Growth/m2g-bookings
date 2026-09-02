# PLANTILLAS — formatos de los archivos de cada agente

Los formatos que usan los once agentes de M2G Agenda. Se copian y se rellenan. Como ejemplo ya relleno sirve cualquiera de los `AGENTE.md` de esta carpeta: **todos están adaptados a este proyecto**, ninguno es un esqueleto.

---

## Plantilla A — `AGENTE.md` (identidad del agente)

```markdown
# Agente: <Nombre> (<carpeta>)

- **Misión (1 frase):** <qué consigue este agente en M2G Agenda, con el stack concreto>
- **Estado:** ⚪ sin arrancar | 🟡 en curso | 🟢 al día | 🔴 bloqueado

## Responsabilidades
- <de qué es dueño este agente, con nombres de archivo y de módulo reales>

**De qué NO es dueño:** <la frontera con los demás roles, dicha en voz alta>

## Qué le aplica de la arquitectura
- **ADR:** <los ADR concretos que gobiernan su trabajo, con lo que decide cada uno>
- **Requisitos:** <los códigos del brief que cubre: ONB-2, AGD-4, MKT-3…>
- **Fases:** <en qué bloque de la §3 del README entra y con qué papel>

## Dependencias
- **Recibe de:** <qué agentes le entregan algo, y qué exactamente>
- **Entrega a:** <a qué agentes, y qué>

## Invalidation trigger
- <cuándo CADUCA una decisión técnica de este rol y hay que revisarla. Una decisión sin fecha de caducidad se arrastra en silencio>

## Definición de "hecho"
- <condiciones objetivas para que una entrega se considere terminada>

## Cómo se valida su trabajo (lo comprueba QA/Validador)
- [ ] <criterios objetivos y verificables, uno por línea, comprobables con una llamada o mirando una pantalla>
```

> El campo **`Invalidation trigger`** no es decorativo: obliga a escribir **cuándo deja de ser válida** una decisión del rol. En este proyecto hay varias con fecha de caducidad conocida —el proveedor de mapas, la pasarela, el nombre comercial—, y ninguna puede quedar solo en la cabeza de quien la tomó.

---

## Plantilla B — `TAREAS.md` (backlog del agente)

**Todo documento de tareas lleva su estado junto al título:** `sin iniciar` · `en proceso` · `completado`.

```markdown
# Tareas: <Nombre del agente> — **Estado: sin iniciar**

> Derivadas de la guía de lanzamiento por fase (`../README.md` §3) y del brief (§9).
> Estados de tarea: `pendiente` · `en curso` · `bloqueada` · `hecha` · `validada`.
> La columna **Zona** la usa el Orquestador para detectar colisiones (ver abajo).

| ID | Descripción | Fase | Zona | Estado | Depende de | Criterio de aceptación |
|---|---|---|---|---|---|---|
| <AG>-T001 | <qué hay que hacer, citando su requisito y su ADR> | 1.a | apps/api/identidad | pendiente | <id o —> | <cómo se sabe que está bien, en términos observables> |
```

**Los prefijos de identificador de este proyecto:** `ARQ` Arquitecto · `ING` Ingeniería de Software · `DEV` DevOps · `BE` Backend · `FE` Frontend Web · `MCK` Mockuper · `MOV` Móvil · `TST` Testing · `SEC` Seguridad · `QA` QA/Validador · `ORQ` Orquestador.

**La columna `Zona`** es el directorio o módulo caliente que la tarea toca de forma principal. Es lo que el orquestador usa para detectar colisiones **sin abrir el código**. Cuanto más específica, mejor: `apps/api/disponibilidad`, no `apps/api`. Si toca varias, se separan por coma. Una zona a secas como `apps/api` se trata como **transversal y no paralelizable** con ninguna otra de `apps/api`.

**Las zonas reales de M2G Agenda**, según ADR-0001:

| Zona | Qué hay |
|---|---|
| `apps/api/contrato` | Convenciones comunes: forma del error, identificadores, cursor, idempotencia |
| `apps/api/identidad` | Usuarios, OTP, sesiones, membresías |
| `apps/api/negocios` | Negocios, ubicación, horarios, medios, ajustes |
| `apps/api/catalogo` | Servicios, variantes, categorías |
| `apps/api/equipo` | Profesionales, horarios propios, bloqueos |
| `apps/api/disponibilidad` | **El motor. Zona serializada** |
| `apps/api/reservas` | Ciclo de la reserva y su historial |
| `apps/api/clientes` | Ficha de cliente por negocio |
| `apps/api/notificaciones` | Cola, plantillas, proveedores |
| `apps/api/marketplace` | Búsqueda, zonas, ranking, reviews, favoritos |
| `apps/api/migraciones` | Alembic. **Zona serializada** |
| `apps/api/pruebas` | La suite contra PostgreSQL real, de Testing |
| `apps/worker` | Trabajos y planificación con arq |
| `apps/web` | Next con SSR: marketplace, reserva y panel de negocio |
| `apps/backoffice` | React con Vite: el equipo M2G |
| `packages/tokens` | Design tokens. **Zona serializada** |
| `packages/ui` | Componentes compartidos entre web y back-office |
| `packages/api-types` | Tipos generados del OpenAPI. **Nunca escritos a mano** |
| `infra/local` | `docker-compose.yml`, seed y utilidades |
| `docs/arquitectura/adr` | ADR. **Zona serializada** |
| `docs/ingenieria` | Especificaciones y diagramas |
| `docs/diseno` | Design system y flujos de usuario |
| `mockups` | Prototipos navegables del Mockuper |

---

## Plantilla C — entrada de `BITACORA/` (memoria incremental)

> Nombre del archivo: `NNNN-<tarea-en-kebab>.md`, por ejemplo `0001-entorno-local-de-un-comando.md`. Se numera en orden.

```markdown
# <NNNN> · <Título de la tarea>

- **Agente:** <nombre> · **Tarea:** <ID> · **Fecha:** <la de hoy, formato 2026-09-01>
- **Estado al cerrar:** hecha | validada | bloqueada

## Qué hice
<resumen en español llano>

## Decisiones tomadas
<decisiones y por qué; si alguna roza la arquitectura, se enlaza el ADR o se escala>

## Archivos creados o tocados
<rutas absolutas o desde la raíz del repo>

## Cómo verificar que funciona
<pasos concretos y reproducibles: el comando exacto, la llamada exacta. En interfaz, VERIFICAR EN VIVO en el navegador y a 390 px, nunca "build verde">

## Pendiente o bloqueado
<lo que queda; si hay bloqueo, va TAMBIÉN a la tabla de deuda viva de ESTADO-GLOBAL.md>

## Qué necesita saber el siguiente que llegue (HANDOFF)
<el contexto mínimo para que otro agente retome sin ti: estado real, decisión pendiente, comando para arrancar, fichero clave>
```

---

## Plantilla D — definición de subagente (`.claude/agents/<nombre>.md`)

**El prefijo de este proyecto es `agenda-`.** Los once: `agenda-arquitecto`, `agenda-ingenieria-software`, `agenda-devops`, `agenda-backend`, `agenda-frontend-web`, `agenda-mockuper`, `agenda-movil`, `agenda-testing`, `agenda-seguridad-compliance`, `agenda-qa-validador`, `agenda-orquestador`.

```markdown
---
name: agenda-<rol>
description: Agente <Rol> de M2G Agenda. Úsalo cuando <cuándo>. Lo primero que hace es leer su documentación en docs/ai-development/<carpeta>/.
tools: Read, Write, Edit, Bash
# model: opusplan        # opcional: opusplan para planificar, sonnet para ejecutar
# isolation: worktree    # opcional: para los roles que el orquestador paraleliza
---

Eres el **agente <Rol>** de M2G Agenda. Tu memoria vive en archivos, no en este chat.

ANTES DE NADA, lee en orden: docs/ai-development/README.md, tu <carpeta>/AGENTE.md, tu <carpeta>/TAREAS.md, las últimas entradas de tu <carpeta>/BITACORA/, y ESTADO-GLOBAL.md.

Ejecuta SOLO la tarea que te pida el director. Reglas: la memoria vive en archivos —al terminar, escribes bitácora y actualizas ESTADO-GLOBAL en la misma sesión—; no editas ADR decididos, los escalas en ESTADO-GLOBAL; no tocas archivos de otros agentes sin avisar; marcas `hecha`, y solo QA marca `validada`; nada pendiente solo en prosa. Si te topas con algo que decide Luis —el nombre comercial, la pasarela, los mapas, o cualquier cosa que cobre dinero de verdad—, PARAS y lo escalas. Hablas en español llano.
```

---

## Plantilla E — formato de `ESTADO-GLOBAL.md` (el tablero)

El tablero **no es una lista de tareas**. Tiene siete piezas, y el orden es el que es porque así se lee de arriba abajo sin buscar:

1. **Último hito**: una o varias líneas con emoji que resumen el estado más reciente — qué está vivo, qué validado, qué se puede mirar. Lo primero que se lee.
2. **Fase actual**: en qué fase se está y qué falta para cerrarla.
3. **Lo primero que tiene que pasar**: las decisiones y credenciales que se esperan, por orden de urgencia real, **y qué pasa mientras tanto**. Sin esa segunda columna, un bloqueo parece una parálisis.
4. **Estado de los agentes** (tabla): rol · estado ⚪🟡🟢🔴 · fase en que entra · subagente. Debajo, **los roles descartados** con su motivo.
5. **Pendientes abiertos (deuda viva)** (tabla): **todo lo que queda abierto, de un vistazo**, con categoría **(S)** siguiente · **(P)** planificado · **(B)** bloqueado, dueño, referencia y **por qué sigue abierto**. **Nada se difiere en silencio.**
6. **Lotes en vuelo** (tabla): qué corre en paralelo ahora y en qué worktree, para que nadie más lo toque. Lo gestiona solo el Orquestador y se limpia al mergear.
7. **Avisos entre agentes** y **Bloqueos abiertos**: los toques fuera de la propia carpeta y las dependencias que no llegan.

---

## Criterios de handoff (traspaso entre agentes o sesiones)

Un traspaso está **bien hecho** cuando quien llega puede retomar **sin preguntar nada**. La sección «Qué necesita saber el siguiente» de la bitácora debe contener:

- [ ] **Estado real**, no el deseado: qué funciona, qué está a medias, qué está roto.
- [ ] **La decisión pendiente** que impide avanzar, si la hay, y a quién se escala.
- [ ] **El comando exacto** para arrancar y verificar. No «se arranca como siempre».
- [ ] **El archivo o la función concreta** que hay que tocar a continuación, con su ruta.
- [ ] **Lo que NO hay que hacer**: los caminos ya probados que no funcionan, para no repetirlos.

> Una bitácora que no permite retomar es una bitácora a medias. Es el problema real del método multi-sesión, y se resuelve escribiendo, no recordando.
