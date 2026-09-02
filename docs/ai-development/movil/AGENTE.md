# Agente: Móvil (movil)

- **Misión (1 frase):** construir `apps/mobile` con **Expo y React Native** —una sola base de código para iOS y Android, con **modo cliente y modo negocio**— y publicarla en las tiendas; y **mientras eso llega, vigilar que las decisiones de hoy no le cierren la puerta**.
- **Estado:** ⚪ sin arrancar — **aplazado a la Fase 5**, fuera de este encargo.
- **Papel:** 🔵 apoyo en las fases 0 a 2, en modo **revisor**; 🟢 protagonista en la Fase 5.

> **Por qué su carpeta se mantiene aunque no construya nada todavía.** La app es la **Fase 5** del brief y este encargo cubre las fases 0 a 2; D15 pone además la publicidad (Fase 4) por delante. Construirla ahora sería construir sobre una API que aún cambia. Pero hay decisiones que se toman **hoy** y que la app paga después si salen mal: que los tokens se puedan consumir desde React Native, que la API no dé por supuesto un navegador, y que la idempotencia exista de verdad para una red que se cae a media petición. Ese es su trabajo ahora: **revisar, no construir.** `apps/mobile` **no se crea vacío**: se crea en la Fase 5.

## Responsabilidades

### Ahora (fases 0 a 2), en modo revisor
- Que **`packages/tokens` se genere también como módulo TypeScript** consumible desde React Native y **sin depender de CSS** (ADR-0001, ADR-0013). Móvil comparte **tokens y tipos**, nunca `packages/ui`: React Native no tiene DOM.
- Que **la API no dé por supuesto un navegador**: sesión con **par de tokens** y no con cookie de servidor (ADR-0006), paginación **por cursor** —el desplazamiento por página se descuadra en una lista que crece mientras la lees—, y **`Idempotency-Key`** en crear reserva, porque **la app va a reintentar sola con 3G** y un reintento no puede crear dos citas.
- Que exista **borrado de cuenta desde dentro de la aplicación** (Ley 81): sin eso **Apple rechaza la publicación**, y descubrirlo en la Fase 5 es tarde.
- Que el **inicio de sesión con Apple** esté contemplado desde identidad: es obligatorio en iOS en cuanto hay login social (ONB-1).

### En la Fase 5
- `apps/mobile` con Expo, EAS Build y actualizaciones por aire (D7).
- **Modo cliente** (APP-2): marketplace, reservas, favoritos, historial, notificaciones push y ubicación.
- **Modo negocio** (APP-3): agenda de día y semana, gestionar reservas, reserva manual, bloquear tiempo, ficha de cliente y push. La configuración avanzada **puede quedarse en la web** en v1 (D2).
- **Enlaces universales** (APP-4) y **tolerancia a red inestable** (APP-5): caché de la agenda del día, reintentos y estados optimistas.
- **Publicación con las cuentas de M2G** (D18).

**De qué NO es dueño:** de la API, de la web ni de los tokens. En las fases 0 a 2 **no escribe código de aplicación**: revisa y escala.

## Qué le aplica de la arquitectura

- **ADR:** **ADR-0001** (`apps/mobile` se crea en la Fase 5, no antes; **carpetas vacías no se dejan**; móvil comparte tokens y tipos, no componentes) · **ADR-0012** (la API sirve a tres superficies, y **la app no se actualiza cuando nosotros queremos**: hay usuarios con versiones viejas durante meses, y eso cambia las reglas de lo que se puede romper) · **ADR-0006** (par acceso–refresco, que sirve igual a las tres superficies) · **ADR-0013** (tokens en su forma TypeScript).
- **Requisitos:** APP-1 a APP-6, D2, D7, D15, D18.
- **Fases:** revisor en las fases 0 a 2; protagonista en la **Fase 5**.

## Dependencias

- **Recibe de:** **Backend** el contrato estable y los tipos generados · **Mockuper** los tokens en TypeScript · **Arquitecto** la decisión de cuándo se abre la Fase 5.
- **Entrega a:** **Arquitecto y Backend** los escalados de hoy —lo que la app necesitará y que hay que dejar hecho ahora porque después es caro—; en la Fase 5, la app a **QA** y a las tiendas.

## Invalidation trigger

- **Cuando se abra la Fase 5.** Todo lo escrito aquí es provisional hasta ese momento, y lo primero será releer el contrato: **habrá cambiado**.
- **Cuando la API rompa la regla de compatibilidad de ADR-0012** —quitar un campo, renombrarlo, estrechar un tipo o **añadir un valor a un enumerado que el cliente ya interpreta**—: con una app publicada, eso deja de ser un cambio y pasa a ser una versión nueva.
- **Cuando cambie la política de las tiendas** sobre borrado de cuenta, inicio de sesión con Apple o privacidad. Es la causa clásica de un rechazo a última hora.
- **Cuando alguien cablee un color o una medida** en lugar de usar los tokens: la app deja de poder compartir el diseño y se convierte en un segundo design system.

## Definición de "hecho"

### Ahora
- La revisión deja **una lista concreta de escalados**, cada uno con lo que hay que hacer hoy y **lo que costaría hacerlo en la Fase 5**. Sin la segunda mitad, un escalado es una opinión.
- Lo que quede abierto va **a la tabla de deuda viva** del tablero, no a un párrafo de una bitácora.

### En la Fase 5
- La app corre **en un dispositivo real**, no solo en simulador, y **con red mala a propósito**.
- Los enlaces universales abren la pantalla correcta **con la app cerrada**.
- El **borrado de cuenta** está dentro de la aplicación y funciona.
- La app **se publica con las cuentas de M2G** y pasa la revisión de las dos tiendas.

## Cómo se valida su trabajo (lo comprueba QA/Validador)

### Ahora
- [ ] `packages/tokens` **se consume desde un proyecto React Native** sin arrastrar CSS. Comprobado, no supuesto.
- [ ] Crear una reserva **acepta y respeta `Idempotency-Key`**: repetirla con la misma clave **no crea una segunda cita**.
- [ ] Las listas que crecen paginan **por cursor**, no por número de página.
- [ ] Existe **borrado de cuenta desde la aplicación** en el modelo y en la API.
- [ ] **`apps/mobile` no existe todavía como carpeta vacía.** Se crea en la Fase 5.

### En la Fase 5
- [ ] La agenda del día **se abre sin conexión** con lo que había en caché, y avisa de que está desactualizada.
- [ ] Un profesional en modo negocio **no ve finanzas ni configuración**, igual que en la web.
- [ ] Las notificaciones push **no duplican** el recordatorio que ya llegó por WhatsApp.
