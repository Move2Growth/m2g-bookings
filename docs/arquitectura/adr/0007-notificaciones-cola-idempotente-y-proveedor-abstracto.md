# ADR-0007 · Notificaciones: una cola idempotente detrás de un proveedor intercambiable

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

NTF-1 a NTF-4: WhatsApp (Meta Cloud API) como canal principal, push y correo, y SMS solo como respaldo del OTP. Los eventos son muchos —reserva creada, confirmada, cancelada, reprogramada, recordatorio a 24 h y a 2 h, «¿cómo te fue?», invitación de staff, avisos de plan y de ads— y dos de las reglas duras aplican de lleno: **jobs idempotentes** («un recordatorio duplicado a las 7 de la mañana es una queja») y **control de coste**, porque cada mensaje de WhatsApp se paga.

Hay además una dependencia externa que no está en nuestras manos: las plantillas de WhatsApp **las tiene que aprobar Meta**, y la credencial aún no existe.

## Decisión

**[decisión]** Toda notificación pasa por **una tabla `notifications` que es la cola**, y el envío es un trabajo que la consume.

- Cada notificación se crea con una **clave de idempotencia** derivada del hecho, no del momento: `recordatorio_24h:booking:{id}`. La clave es **única en la tabla**. Encolar dos veces el mismo recordatorio es un conflicto que no inserta, no un segundo mensaje. Esto sobrevive a que el planificador se ejecute dos veces, a un reintento y a un redespliegue a mitad de trabajo.
- Estados: `pendiente` → `enviando` → `enviada` | `fallida` | `descartada`. Los reintentos son con retroceso exponencial y **tope**; una notificación que caduca (el recordatorio de 2 h que se intenta cuando la cita ya pasó) se marca `descartada`, no se reintenta para siempre.
- **[decisión]** El envío se separa en **decidir** y **entregar**. Decidir mira las preferencias del usuario y del negocio (NTF-3) y elige canal; entregar habla con el proveedor. Así, apagar un canal es configuración y no toca el código de negocio.
- **[decisión]** Los proveedores están detrás de una interfaz (`NotificationProvider`) con implementaciones para WhatsApp, correo y push, más una **de desarrollo que escribe a disco y a la consola**. La Fase 1 se construye y se prueba entera con esa: no se para el núcleo esperando a Meta.
- **[decisión]** Las **plantillas son datos** (`notification_templates`), con su nombre en Meta, sus variables y su idioma. Cambiar un texto no es un despliegue (ADM-4). Español en v1, pero la tabla lleva idioma desde el principio.
- **[decisión]** Se guarda **registro de entrega** por notificación (identificador del proveedor, estado, coste estimado) para poder responder a «¿le llegó el recordatorio?» sin adivinar, que es la primera pregunta de soporte que va a llegar.
- **[decisión]** El teléfono **no se expone**: el click-to-chat de WhatsApp (NEG-1) se resuelve con un salto en servidor que registra el clic y redirige, y el número no viaja en el listado.

## Alternativas consideradas

- **Enviar en línea dentro de la petición HTTP.** Descartado: la reserva no puede depender de que Meta responda, y un fallo del proveedor no puede tumbar una confirmación.
- **Cola solo en Redis, sin tabla.** Descartado: se pierde el historial de entregas, la idempotencia depende de la memoria de Redis y soporte se queda sin respuestas.
- **Un proveedor único cableado.** Descartado: la dependencia de Meta es un riesgo declarado del brief, y el respaldo por correo y push tiene que poder entrar sin reescribir.

## Consecuencias

- **Se necesitan credenciales de Meta WhatsApp Cloud API** y plantillas aprobadas para verificar el canal real. Va al tablero como bloqueo con dueño (Luis), no como nota en prosa.
- La cola en tabla es más lenta que una cola en memoria y no importa: el volumen de v1 (50.000 reservas/mes) está lejísimos de necesitar otra cosa.
- La clave de idempotencia obliga a pensar **qué hecho** dispara cada mensaje. Es trabajo de diseño por adelantado, y es exactamente el que evita el mensaje duplicado.
- El coste por mensaje queda medible desde el día uno, que es lo que permite decidir si el recordatorio de 24 h vale lo que cuesta.
