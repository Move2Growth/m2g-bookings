# ADR-0024 · El correo se manda por SMTP, y en local a un buzón que se puede abrir

- **Estado:** aceptada
- **Fecha:** 2026-09-10

## Contexto

La invitación al equipo y la recuperación de contraseña dependen del correo, y el correo era un
esqueleto que decía la verdad y no servía: *«el proveedor todavía no está elegido»*. Mientras tanto
el alta enseñaba el enlace de la invitación en pantalla y explicaba por qué no salía de ahí.

La pregunta abierta era **qué proveedor se contrata**, que es una decisión de dinero y de dominio
verificado — no de arquitectura.

## Decisión

**[decisión] Se manda por SMTP**, no contra la API de un proveedor concreto. Es el mismo
razonamiento que llevó al almacén a hablar S3: **lo hablan todos** —Resend, SendGrid, Postmark,
Amazon SES, Mailgun—, así que elegir proveedor deja de ser una decisión de arquitectura y pasa a ser
cinco variables de entorno. Escribir contra la API de uno concreto sería atar el código a una
elección que aún no está hecha, y que se cambiará el día que suban sus precios.

**[decisión] En local corre un buzón dentro del `docker-compose`** (Mailpit), que habla SMTP y
enseña lo que se manda en una web. Por el mismo motivo que MinIO: que una máquina recién clonada
pueda **ver un correo de verdad** —su HTML, su asunto, su destinatario— sin credencial de nadie y
sin mandarle nada a una persona real.

**[decisión] El correo se manda de verdad también en local**, y no al buzón de fichero. Un correo
escrito en un registro no enseña que el enlace de la invitación estaba roto, ni que el asunto salía
vacío, ni que el acento del nombre del salón se rompía por el camino. Un buzón que se abre en el
navegador, sí. Los otros canales siguen en el fichero: WhatsApp no se puede simular sin Meta, el
push es de la app y el SMS es el respaldo del OTP.

**[decisión] `configurado` mira el servidor y el remitente, no el usuario y la contraseña.** Un relé
de la propia red no pide credenciales, y exigirlas dejaría ese caso fuera sin motivo.

**[decisión] El envío va en un hilo aparte.** `smtplib` es de la biblioteca estándar y es
bloqueante: llamarlo directamente pararía el bucle de eventos mientras un servidor lento contesta, y
con él todo lo demás que ese proceso esté entregando.

**[decisión] `aceptado` no es `entregado`, y no se finge que lo sea.** SMTP dice si el servidor
recogió el mensaje. Lo que pase después —un rebote, un buzón lleno— lo cuenta el proveedor en su
panel. Por lo mismo, **no se inventan `id_en_el_proveedor` ni `coste_minor`**: SMTP no los da, y
vacío es vacío.

**[decisión] `STARTTLS` obligatorio fuera de local.** Sin él, el usuario y la contraseña del
proveedor viajan en claro.

## Alternativas consideradas

- **La API de Resend** (el proveedor de la casa en otros proyectos). Descartado como acoplamiento:
  Resend habla SMTP igual de bien, así que se puede usar **hoy** sin escribir código específico. Si
  algún día hacen falta sus datos de entrega, se añade un adaptador que se elige por configuración.
- **Amazon SES por API.** Lo mismo, y además ata a una nube.
- **Esperar a que Luis elija.** Es lo que se estaba haciendo, y el resultado era que la invitación al
  equipo no salía del navegador.

## Consecuencias

- **En local no bloquea nada.** `make arriba` levanta el buzón y los correos se leen en
  `http://localhost:8025`.
- **Para un entorno publicado hacen falta dos cosas**, y ninguna es código: contratar el proveedor y
  **verificar el dominio con SPF y DKIM**. Sin eso el correo llega a la carpeta de basura de todo el
  mundo, que se parece mucho a no llegar. Depende de qué dominio se elija, que sigue abierto.
- La plantilla de los correos es texto plano por ahora. El HTML es trabajo aparte y no bloquea nada:
  un texto que se lee es mejor que un HTML que no existe.
