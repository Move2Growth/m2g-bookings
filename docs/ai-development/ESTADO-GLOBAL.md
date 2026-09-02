# ESTADO-GLOBAL — tablero del equipo

> **El primer sitio que mira cualquiera.** Refleja el estado real de cada agente y sus tareas clave, qué bloquea a qué, y el último hito alcanzado.
>
> **Quién lo actualiza y cuándo:** **el agente que cambia el estado de una tarea**, en la **misma sesión** (regla 6 del [README](README.md)). **QA/Validador** actualiza la validación. Durante un lote en paralelo, lo escribe **solo el Orquestador** (serializa el tablero, ver §9 del README). Si hay duda de quién, lo hace el último que tocó la tarea.
>
> **Secretos y variables de entorno:** inventario único en [`../operacion/SECRETOS-Y-VARIABLES.md`](../operacion/SECRETOS-Y-VARIABLES.md). Cada secreto/variable nuevo se documenta ahí **y** en `.env.example` en la misma sesión (nombre y para qué, **nunca el valor**).

**Última actualización:** 2026-09-01 · por: Arquitecto.

**🟢 Último hito:** 🧭 **El método de trabajo está instalado y la arquitectura tiene cimientos escritos.** Hay **14 ADR aceptados** que fijan lo que no se vuelve a discutir: monorepo y estructura, multi-tenant con RLS, tiempo en UTC con la zona en el negocio, la no doble reserva como restricción de exclusión, PostGIS más taxonomía de zonas, identidad con OTP y refresco revocable, cola de notificaciones idempotente, trabajos con arq, ranking con pesos en base de datos y rating bayesiano, motor de planes desde el día uno, Next con SSR frente a Vite SPA, API REST versionada con OpenAPI generado, design system propio con tokens, y entorno local de un comando. La `constitution.md` está escrita con sus **ocho garantías**. Encima de esos cimientos ya hay **trabajo en vuelo**: varios documentos de fase redactados, el design system y los flujos en `docs/diseno/`, y el esqueleto del monorepo con `apps/api`, `infra/local` y `packages/tokens`. **La arquitectura fue antes que el código, que es el orden que se pedía.**

**🟢 Segundo hito del día:** ⚙️ **El motor de disponibilidad está construido y en verde.** El núcleo es puro —no toca base de datos, no mira el reloj— y lleva **69 pruebas** que fijan los casos que rompen este tipo de motor: la rejilla marca comienzos y no duraciones, el buffer posterior tiene que caber antes del cierre pero el anterior no bloquea el primer hueco del día, el multi-servicio necesita un bloque continuo, el spa que cierra a las 00:30 ofrece huecos después de medianoche, y el mismo código resuelve bien el cambio de hora de Madrid aunque Panamá no lo tenga. Con ellas van la **máquina de estados de la reserva** y el **ranking con rating bayesiano**, cada uno con las reglas del brief fijadas en pruebas. **Lo que falta del motor es lo que solo se puede probar contra un PostgreSQL real**: la carrera por el mismo slot, el aislamiento entre negocios y la idempotencia.

**Fase actual:** **Fase 0 · Diseño, en curso.** Cerrada la ronda de ADR, están redactados descubrimiento, contratos de API, modelo de datos, motor de disponibilidad y plan de sprints; **faltan** `fase-1-decisiones.md`, `fase-2-requisitos-y-mvp.md` y `fase-4-diagramas-sistema.md`. **La Fase 0 termina cuando Luis la aprueba**, no cuando el equipo la dé por buena.

---

## Lo primero que tiene que pasar

> Por orden real de urgencia. Nada de esto lo decide un agente por su cuenta.

| Cuándo hace falta | Pregunta | Qué pasa mientras tanto |
|---|---|---|
| **Antes de cerrar la Fase 0** | **¿Luis aprueba flujos, design system, modelo de datos y contratos?** | La Fase 1 no arranca. El criterio de «hecho» de la Fase 0 es literalmente su aprobación |
| **Antes de dar por verificado el registro de un usuario** | **Credenciales de Meta WhatsApp Cloud API** (número, identificador de la cuenta y token) | El OTP y los avisos se construyen y se prueban contra el proveedor de desarrollo, que escribe el código en el log (ADR-0006, ADR-0007). **El canal real queda marcado como no verificado** |
| **Antes de la Fase 2** | **¿Mapbox o Google Maps?** (D8) — tiene coste y hay que confirmarlo | La distancia la resuelve PostGIS sin proveedor. El geocoding vive detrás de `GeocodingProvider` con implementación local (ADR-0005): la búsqueda por zona no espera a esto, el mapa interactivo sí |
| **Antes de la Fase 4** | **¿Qué pasarela?** (D5, por defecto Yappy más tarjetas) | El motor de planes se construye contra `PaymentProvider` con implementación de desarrollo (ADR-0010). **No se enciende ningún cobro real sin OK explícito de Luis** |
| **Antes de la identidad visual definitiva** | **Nombre comercial y dominio** (D1) | Se usa el codename *M2G Agenda* y **no se mete a fuego en ningún sitio**: sale de configuración, y cambiarlo es cambiar tokens y un valor de entorno, no pantallas (ADR-0013) |
| **Antes de publicar el primer negocio de verdad** | **Árbol de zonas de Ciudad de Panamá** y **feriados panameños** | El seed carga un árbol verosímil de corregimientos y barrios y una tabla de feriados sugeridos; ambos son **datos administrables** (MKT-6, AGD-6), no código |

---

## Estado de los agentes

| Agente | Estado | Fase en que entra | Subagente |
|---|---|---|---|
| Arquitecto / Coordinador | 🟡 en curso — 14 ADR y `constitution.md` escritos; documentos de fase en redacción | Transversal (diseño + coordinación) | `agenda-arquitecto` |
| Ingeniería de Software | ⚪ sin arrancar | Transversal (especifica antes de construir) | `agenda-ingenieria-software` |
| DevOps / Infraestructura | ⚪ sin arrancar | Fase 1, bloque 1.a (entorno local, **no despliegue**) | `agenda-devops` |
| Backend | ⚪ sin arrancar | Fase 1, bloque 1.a en adelante | `agenda-backend` |
| Frontend Web | ⚪ sin arrancar | Fase 1, bloque 1.e en adelante | `agenda-frontend-web` |
| Mockuper | ⚪ sin arrancar | Fase 0 (por delante del frontend) | `agenda-mockuper` |
| Móvil | ⚪ sin arrancar — **aplazado a la Fase 5** | Fase 5 (fuera de este encargo) | `agenda-movil` |
| Testing | ⚪ sin arrancar | Fase 1, bloque 1.a en adelante | `agenda-testing` |
| Seguridad y Cumplimiento | ⚪ sin arrancar | Transversal (acompaña a todos) | `agenda-seguridad-compliance` |
| QA / Validador | ⚪ sin arrancar | Transversal (cierra cada tarea) | `agenda-qa-validador` |
| Orquestador | ⚪ sin arrancar | Transversal (paraleliza bajo demanda) | `agenda-orquestador` |

> Estados: ⚪ sin arrancar · 🟡 en curso · 🟢 al día · 🔴 bloqueado.
>
> **Trabajo en vuelo al cerrar esta actualización.** En el repositorio ya existen, además de los ADR: `docs/arquitectura/fase-0-descubrimiento.md`, `fase-3-contratos-api.md`, `fase-3-modelo-de-datos.md`, `fase-3-motor-disponibilidad.md` y `fase-5-plan-de-sprints.md`; `docs/diseno/DESIGN-SYSTEM.md` y `docs/diseno/FLUJOS.md`; y el esqueleto del monorepo con `apps/api`, `infra/local`, `packages/tokens` y `packages/api-types`. **El estado de cada agente de la tabla se ajusta cuando cada uno escriba su bitácora y marque sus tareas**: aquí no se le atribuye a nadie un trabajo que no ha firmado.
>
> **Rol descartado: Datos / IA.** En las fases 0 a 2 no hay pipeline de datos ni modelos: el ranking es **una fórmula con pesos en base de datos** (ADR-0009) y las métricas son consultas del backend. Motivo y condición de reactivación en [`README.md`](README.md) §6. **No está olvidado: está descartado con fecha de caducidad.**

---

## Pendientes abiertos (deuda viva) — vista única

> **Aquí está, de un vistazo, TODO lo que queda abierto.** El detalle por tarea vive en cada `<rol>/TAREAS.md`. **Nada se difiere en silencio: si está aquí, está rastreado.** Categorías: **(S)** siguiente a construir · **(P)** planificado en una fase posterior · **(B)** bloqueado por una dependencia que aún no existe.

| Cat. | Pendiente | Dueño | Ref / Fase | Por qué sigue abierto |
|---|---|---|---|---|
| **(B)** | **No existen credenciales de Meta WhatsApp Cloud API** | Luis | ONB-1, NTF-1 · ADR-0006, ADR-0007 · Fase 1 | Sin número, identificador de cuenta y token no se puede verificar **ni un solo OTP real** ni un recordatorio real. Se construye contra el proveedor de desarrollo, que escribe el mensaje en el log y a disco; el stack arranca y las pruebas pasan sin la credencial (ADR-0014). **Lo que no se puede hacer es dar por verificado el canal**: hasta que llegue, el registro por teléfono queda «construido y no verificado en real» |
| **(B)** | **Las plantillas de WhatsApp las tiene que aprobar Meta** | Luis | NTF-3 · ADR-0007 · Fase 1 | Es un trámite con Meta, no trabajo de desarrollo, y va detrás de la credencial. Las plantillas son **datos** en `notification_templates` con su nombre en Meta, sus variables y su idioma: cuando lleguen aprobadas se cargan sin desplegar código |
| **(B)** | **Pasarela de pago sin decidir** | Luis | D5, PAY-2 · ADR-0010 · Fase 4 | El default del brief es Yappy más tarjetas por pasarela local, pero **la elección y las credenciales son de Luis**. El motor de planes se construye entero contra la interfaz `PaymentProvider` y se prueba con la implementación de desarrollo. **Nada que cobre dinero de verdad se enciende sin OK explícito** |
| **(B)** | **Proveedor de mapas sin confirmar por coste** | Luis | D8, MKT-1 · ADR-0005 · Fase 2 | Mapbox es el valor por defecto y **tiene coste recurrente**; el coste de mapas es un riesgo declarado del brief (§12). Ordenar por distancia no lo necesita —eso es PostGIS—, pero el **mapa interactivo** y el **geocoding de direcciones** sí. Mientras tanto, `GeocodingProvider` con implementación local y caché por texto normalizado |
| **(B)** | **Nombre comercial y dominio sin decidir** | Luis | D1 · ADR-0013 · Fase 0 | *M2G Agenda* es codename. Afecta a la identidad visual, al dominio de los perfiles públicos y a los enlaces de las notificaciones. Se mitiga sacándolo **todo de configuración y de tokens**: el día que se decida, no se tocan pantallas. **Si aparece escrito a fuego en algún sitio, es un fallo de QA** |
| **(S)** | **Faltan tres documentos de fase que enlazan `CLAUDE.md` y `docs/arquitectura/README.md`** | Arquitecto | Fase 0 | Ya están redactados descubrimiento, contratos de API, modelo de datos, motor de disponibilidad y plan de sprints. **Siguen sin existir `fase-1-decisiones.md` —el índice de los ADR—, `fase-2-requisitos-y-mvp.md` y `fase-4-diagramas-sistema.md`**, y los tres están enlazados desde documentos que sí existen: un enlace roto en el mapa del proyecto manda a la gente a buscar lo que no está |
| **(S)** | **La §3 del README y el plan de sprints hay que reconciliarlos** | Arquitecto | Fase 0 | La guía de lanzamiento se derivó de las fases del brief y está **partida en bloques** (0, 1.a a 1.f, 2). Ahora que `fase-5-plan-de-sprints.md` existe, los dos tienen que decir lo mismo, y hay que renumerar la columna «Fase» de los `TAREAS.md` si el plan usa otra numeración |
| **(S)** | **Faltan los casos del motor que solo se pueden probar contra la base de datos** | Testing | AGD-4 · ADR-0002, ADR-0004 · Fase 1 | El núcleo puro del motor está construido con **69 pruebas en verde** (rejilla, buffers, horarios distintos, multi-servicio, medianoche, husos, festivos, reparto por carga). Lo que **todavía no está probado** es lo que no se puede simular: la **carrera de dos clientes por el mismo slot** contra un PostgreSQL real, el **aislamiento entre negocios** y la **idempotencia** al confirmar. Van en `apps/api/pruebas/bd/` y dependen de que exista la migración inicial |
| **(B)** | **Tres decisiones de política pendientes de Luis, que salieron al escribir el modelo de datos** | Luis | Ley 81 · `fase-0-descubrimiento.md` §3.4 | Qué pasa con **el texto de una opinión cuando su autor borra la cuenta** (mientras tanto: se conserva con el autor anonimizado), **cuánto se guarda el registro de auditoría** (mientras tanto: no se borra, y por eso crece sin límite) y **cuánto hay que conservar las facturas en Panamá** (mientras tanto: indefinidamente). Ninguna bloquea construir; las tres tienen que estar escritas **antes** de que haya datos reales de personas |
| **(P)** | **La app móvil es Fase 5 y no se construye ahora** | Móvil (aplazado) | APP-1 a APP-6 · D7, D15 · Fase 5 | Este encargo son las fases 0 a 2, y D15 pone además los ads (Fase 4) por delante de la app (Fase 5). Lo que sí se hace ahora es **no cerrarle la puerta**: `packages/tokens` se genera también como módulo TypeScript consumible desde React Native (ADR-0013) y la API es la misma para las tres superficies (ADR-0012). `apps/mobile` **no se crea vacío**: se crea en la Fase 5 |
| **(P)** | **Modo oscuro: preparado en tokens, no construido** | Mockuper + Frontend Web | ADR-0013 · Fase 6 | La decisión es **modo claro por defecto** y el oscuro no es la Fase 1. Lo que sí se hace desde el primer componente es **no cablear ni un color**: todo sale de `packages/tokens`. Construir el oscuro después es añadir una paleta; cablear colores hoy lo convertiría en un rediseño |
| **(P)** | **Falta el árbol real de zonas de Ciudad de Panamá** | Arquitecto (dato) + Backend (carga) | MKT-6 · ADR-0005 · Fase 2 | El seed necesita provincia → distrito → corregimiento → barrio de verdad —Bella Vista, San Francisco, El Cangrejo, Costa del Este, Obarrio— porque las páginas categoría × zona son URL públicas indexadas. **Nunca «Zona 1 / Zona 2»**. Es un dato administrable, no código |
| **(P)** | **Faltan los feriados de Panamá** | Arquitecto (dato) + Backend (carga) | AGD-6 · Fase 1 | Se precargan como **sugeridos, no impuestos**: un salón puede abrir el 3 de noviembre. Sin la lista real, la agenda propone abrir días en que media ciudad cierra |
| **(P)** | **Hay que sembrar la media global del rating bayesiano** | Backend | REV-5 · ADR-0009 · Fase 2 | La fórmula `(C·m + Σ notas) / (C + n)` necesita un valor de `m` razonable **mientras no haya reviews**; si arranca en cero, el primer negocio con una review de 5 se dispara. Va en la configuración inicial de `ranking_weights`, no en el código |
| **(P)** | **La familia tipográfica hay que autoalojarla** | Frontend Web | ADR-0013 | IBM Plex Sans, en formato variable, **solo los pesos que se usan** y servida desde el propio dominio: en 3G una fuente de más se nota, y una petición a un tercero es una dependencia y un problema de CSP |

> Estados de tarea: `pendiente` · `en curso` · `bloqueada` · `hecha` · `validada`. Cuando una se cierra o se añade otra, **se actualiza esta tabla**.

---

## Lotes en vuelo (orquestador)

> Qué tareas corren **en paralelo ahora mismo** y en qué worktree o rama, para que nadie más las toque. Lo gestiona **solo el Orquestador**. Se limpia al mergear el lote.

| Lote | Tareas | Zona | Estado | Riesgo de merge |
|---|---|---|---|---|
| Fase 0 · documentación | Modelo de datos · plan de fases y preguntas abiertas · flujos y design system · método de trabajo | `docs/arquitectura`, `docs/diseno`, `docs/ai-development` | ✅ cerrado y commiteado | Ninguno: zonas disjuntas, un archivo por agente |
| Fase 0 · esquema | Migración inicial, modelos y seed | `apps/api/agenda/modelos`, `apps/api/migraciones`, `apps/api/agenda/semilla.py` | 🟡 en curso | **Zona serializada**: nadie más toca `apps/api/migraciones` hasta que cierre |

> **Zonas serializadas de este proyecto** —nunca dos agentes a la vez, ni con worktree—: `apps/api/migraciones`, `apps/api/disponibilidad`, `packages/tokens`, `docs/arquitectura/adr/`, y este mismo archivo.

---

## Avisos entre agentes (toques fuera de la propia carpeta)

| Aviso | De | A | Detalle |
|---|---|---|---|
| — | — | — | *(cuando un agente toca algo de otra carpeta, lo anuncia aquí antes)* |

---

## Bloqueos abiertos

| Bloqueo | Quién lo levanta | Desde | A quién afecta |
|---|---|---|---|
| **Credenciales de Meta WhatsApp Cloud API** y plantillas aprobadas | Luis | 2026-09-01 | Backend (identidad y notificaciones), Testing y QA. **No bloquea construir la Fase 1**: bloquea darla por verificada en el canal real |
| **Pasarela de pago** (D5) y sus credenciales | Luis | 2026-09-01 | Backend (planes y pagos). **Bloquea la Fase 4, no antes** |
| **Proveedor de mapas** (D8) por coste | Luis | 2026-09-01 | Frontend Web y Backend (marketplace). **Bloquea el mapa interactivo y el geocoding de la Fase 2**, no la búsqueda por zona |
| **Nombre comercial y dominio** (D1) | Luis | 2026-09-01 | Mockuper, Frontend Web y Arquitecto. Mientras tanto, todo sale de configuración |
| **Aprobación de la Fase 0** | Luis | 2026-09-01 | Todo el equipo: la Fase 1 no arranca sin ella |
