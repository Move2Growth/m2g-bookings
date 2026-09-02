# Tareas: Móvil — **Estado: sin iniciar** (rol **aplazado a la Fase 5**)

> **La app es la Fase 5 del brief y este encargo cubre las fases 0 a 2.** Lo que este rol hace ahora es **revisar que las decisiones de hoy no le cierren la puerta**; construir la app viene después. El motivo y la condición de reactivación están en `../README.md` §6, y el pendiente está en la **tabla de deuda viva** del tablero.
> Estados de tarea: `pendiente` · `en curso` · `bloqueada` · `hecha` · `validada`.

## Lo que sí se hace ahora: revisión

| ID | Descripción | Fase | Zona | Estado | Depende de | Criterio de aceptación |
|---|---|---|---|---|---|---|
| MOV-T001 | Revisar que **`packages/tokens` se genere también como módulo TypeScript** consumible desde React Native, **sin depender de CSS** (ADR-0001, ADR-0013). Móvil comparte tokens y tipos, **nunca `packages/ui`**: React Native no tiene DOM | 0 | packages/tokens | pendiente | MCK-T001 | Se **importa el módulo de tokens desde un proyecto React Native de prueba** y compila. Comprobado, no supuesto |
| MOV-T002 | Revisar que **el contrato de la API no dé por supuesto un navegador** (ADR-0006, ADR-0012): par acceso–refresco en vez de cookie de servidor, **paginación por cursor** en todo lo que crece, e **`Idempotency-Key` en crear reserva** — la app reintenta sola con 3G y un reintento **no puede crear dos citas** | 1.a | apps/api/contrato | pendiente | BE-T001 | Repetir el `POST` de reserva con la misma clave **devuelve la misma cita**; ninguna lista que crece pagina por número de página |
| MOV-T003 | Revisar que existan desde la Fase 1 **las dos cosas que hacen rechazar una app**: **borrado de cuenta desde dentro** (Ley 81) e **inicio de sesión con Apple** contemplado en identidad, obligatorio en iOS en cuanto hay login social (ONB-1) | 1.b | apps/api/identidad | pendiente | BE-T015 | Las dos existen en el modelo y en la API. Descubrir que faltan en la Fase 5 es descubrirlo tarde |
| MOV-T004 | Dejar escrita **la lista de escalados** de este rol: qué hay que hacer hoy y **cuánto costaría hacerlo en la Fase 5**. Lo que quede abierto va a la tabla de deuda viva del tablero | 1.a | docs/ai-development | pendiente | MOV-T001, MOV-T002 | Cada escalado lleva las dos mitades. Sin la segunda, un escalado es una opinión |

## Lo que se construirá en la Fase 5 (no ahora)

> Aquí anotado para que **no se olvide ni se dé por hecho**, no para trabajarlo. Estas filas están `bloqueada` porque **la fase no está abierta**, no porque falte nada técnico.

| ID | Descripción | Fase | Zona | Estado | Depende de | Criterio de aceptación |
|---|---|---|---|---|---|---|
| MOV-T005 | Crear `apps/mobile` con **Expo, EAS Build y actualizaciones por aire** (APP-1, D7). **No se crea vacío antes de la Fase 5** (ADR-0001) | 5 | apps/mobile | bloqueada | Fase 5 sin abrir | La app corre en **un dispositivo real**, no solo en simulador |
| MOV-T006 | **Modo cliente** (APP-2): marketplace, reservas, favoritos, historial, push y ubicación | 5 | apps/mobile | bloqueada | MOV-T005 | Un cliente reserva desde la app sin ayuda, igual que en la web |
| MOV-T007 | **Modo negocio** (APP-3): agenda de día y semana, gestionar reservas, reserva manual, bloquear tiempo, ficha de cliente y push. La configuración avanzada **puede quedarse en web** (D2) | 5 | apps/mobile | bloqueada | MOV-T005 | Un profesional **no ve finanzas ni configuración**, igual que en la web |
| MOV-T008 | **Enlaces universales** (APP-4) y **tolerancia a red inestable** (APP-5): caché de la agenda del día, reintentos y estados optimistas | 5 | apps/mobile | bloqueada | MOV-T006 | La agenda del día **se abre sin conexión** y avisa de que está desactualizada; un enlace compartido abre la pantalla correcta **con la app cerrada** |
| MOV-T009 | **Publicación en las tiendas con las cuentas de M2G** (APP-6, D18) | 5 | apps/mobile | bloqueada | MOV-T007, MOV-T003 | Aprobadas en App Store y Google Play. Sin borrado de cuenta dentro de la app, **Apple rechaza** |
