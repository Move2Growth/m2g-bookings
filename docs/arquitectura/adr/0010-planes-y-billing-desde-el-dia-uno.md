# ADR-0010 · El motor de planes existe desde el día uno aunque cobre 0

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

PAY-1 y la segunda consecuencia de la tesis del encargo: *«pasar el precio a un dólar tiene que ser cambiar un número en el back-office, no un desarrollo. Si lo dejas para después, ese cambio será un proyecto.»*

La trampa está en que un plan gratuito no tiene ni estado de suscripción, ni ciclo, ni impago, ni gracia. Si el modelo nace sin esos conceptos, meterlos luego significa migrar 5.000 negocios vivos e inventarles una fecha de alta y un ciclo que nadie registró.

## Decisión

**[decisión]** El motor de suscripciones se construye **completo** en la Fase 3, con el plan «Gratis» a precio 0 como único plan activo, y **todo negocio tiene una suscripción desde que se registra**, aunque valga 0.

- **`plans`**: precio, moneda, periodicidad, límites y funciones por plan, y **fecha efectiva**. Un cambio de precio es una **fila nueva**, no un `UPDATE` sobre la vigente: hay que poder decir qué precio tenía cada negocio en cada momento.
- **`subscriptions`**: una por negocio, con estado `activa` | `en_gracia` | `suspendida` | `cancelada`, inicio de ciclo, fin de ciclo y **plan congelado** (*grandfathering* configurable: quien entró con un precio se queda con él si así se decide).
- **`subscription_events`**: el historial de todo lo que le pasó — alta, cambio de plan, aviso previo, entrada en gracia, suspensión. Es lo que permite responder a «¿por qué a este negocio se le cobró esto?».
- **[decisión]** Con precio 0, el ciclo **se ejecuta igual**: el trabajo periódico de renovación corre, marca el ciclo cumplido y no genera cobro. Así el camino está **probado antes** de que haya dinero de por medio. Un motor de cobro que se estrena el día que empieza a cobrar es un motor sin probar.
- **[decisión]** La **suspensión por impago no borra datos ni cancela reservas**: limita funciones y, si se decide, despublica del marketplace. Un negocio que no paga sigue teniendo derecho a su agenda y a sus clientes — y volver a publicarlo tiene que ser inmediato al regularizar.
- **[decisión]** El cobro real está **detrás de una interfaz `PaymentProvider`** con implementación de desarrollo. **La pasarela concreta es D5 y la decide Luis**; sus credenciales también. Se construye contra la interfaz, se prueba con la implementación de desarrollo, y **no se enciende ningún cobro real sin OK explícito**.
- **[decisión]** **Nunca se tocan datos de tarjeta** (PAY-3): solo el token de la pasarela en `payment_methods`. El proyecto no entra en el alcance de PCI porque los datos no pasan por aquí.
- **[decisión]** Moneda desde el principio: importes en **enteros de la unidad mínima** (centavos), nunca en coma flotante, con código de moneda por fila (`USD`/`PAB`). El símbolo que se pinta es `$` (D12) y es **configuración**, no una constante en el código.

## Alternativas consideradas

- **No construir billing hasta que haya que cobrar.** Es justamente lo que el encargo prohíbe, y con razón: obliga a migrar con datos vivos.
- **Un booleano `es_de_pago` en el negocio.** Descartado: no soporta ciclos, ni gracia, ni historial, ni cambios de precio con fecha.
- **Integrar la pasarela ya.** Descartado: la elección es de Luis (D5) y no hay credenciales. La interfaz permite avanzar sin esa decisión.

## Consecuencias

- Se escribe código de billing que en producción no cobra nada durante meses. Es deliberado: el día que el precio pase a 1 $, el camino ya se recorrió miles de veces.
- Hace falta una prueba explícita de que **subir el precio de 0 a 1 desde el back-office** cambia lo que se le cobra al negocio siguiente sin tocar código. Es el criterio de «hecho» de la Fase 3.
- Los importes en enteros obligan a formatear en la capa de presentación. Es la fuente de errores de redondeo que se está evitando.
