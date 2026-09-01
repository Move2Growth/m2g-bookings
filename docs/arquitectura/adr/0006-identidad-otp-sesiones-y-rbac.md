# ADR-0006 · Identidad: teléfono con OTP, sesiones con refresco revocable, permisos por membresía

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

ONB-1 pide registro y login por teléfono con OTP (WhatsApp, SMS solo como respaldo según D14) y login social de Google y Apple — Apple es obligatorio en iOS si hay social. D9 cierra la puerta a reservar como invitado: **el teléfono verificado es obligatorio**, porque es lo único que sostiene el control de no-shows sin depósito.

ONB-3 añade la complicación de verdad: **una cuenta puede ser cliente y a la vez tener rol en varios negocios**. El permiso no es del usuario: es del par (usuario, negocio).

## Decisión

**[decisión]** Tres piezas separadas: quién eres, cómo lo demuestras y qué puedes hacer.

**Quién eres — `users`.** Una fila por persona. El teléfono en E.164 es el identificador natural y va **único y verificado**. El correo es opcional.

**Cómo lo demuestras — `auth_identities`.** Una fila por método (`telefono`, `google`, `apple`), todas apuntando al mismo usuario. Añadir un método nuevo no toca `users`. Si el correo verificado de Google coincide con uno ya verificado, se enlaza a la cuenta existente; si no coincide o no está verificado, se crea cuenta nueva — enlazar por correo no verificado es un secuestro de cuenta.

**OTP.** Código de 6 dígitos, **guardado con hash** y no en claro, validez 5 minutos, máximo 5 intentos por código, límite por teléfono y por IP con retroceso exponencial. Se invalidan los códigos anteriores al emitir uno nuevo. Canal principal WhatsApp; SMS **solo** como respaldo (D14) y con control de coste, porque es el vector clásico de fraude por tarificación.

**Sesión.** Par de tokens: acceso JWT corto (15 min, sin estado) y **refresco opaco y persistido** (30 días, rotatorio). El refresco se puede **revocar de verdad** — cerrar sesión en un dispositivo, borrar la cuenta, o bloquear a un usuario tienen que surtir efecto ya. Un JWT de larga vida no se puede revocar, y eso choca con el borrado de cuenta que exige la Ley 81. Reutilizar un refresco ya rotado invalida toda la familia de tokens: es la señal de un token robado.

**Qué puedes hacer — `memberships`.** Una fila por (usuario, negocio, rol) con roles `dueno` y `profesional` en v1, y hueco para `recepcion` (v2). El token de acceso **no lleva la lista de permisos**: lleva el usuario y, si está en modo negocio, el negocio activo; los permisos se resuelven contra la membresía en cada petición. Así, revocar a un profesional surte efecto en la siguiente llamada y no cuando caduque su token.

- **[decisión]** El **negocio activo** es explícito (ONB-3): va en el token de sesión de negocio y es lo que alimenta `app.current_business_id` de RLS (ADR-0002). Cambiar de negocio es un intercambio de token, no un parámetro de consulta que el cliente pueda manipular.
- **[decisión]** El equipo interno de M2G vive en **`admin_users`, aparte**, con su propio inicio de sesión y **2FA obligatorio**, como el resto de la casa. Un superadmin no es un usuario con una casilla marcada.
- **[decisión]** La **impersonación** (ADM-2) emite un token marcado, con caducidad corta, deja rastro en `audit_logs` y **avisa al negocio**. Sin las tres cosas, no se construye.

## Alternativas consideradas

- **JWT autocontenido con permisos dentro.** Descartado: no se puede revocar, y aquí revocar es requisito legal y de producto.
- **Sesión de servidor con cookie clásica.** Encaja en la web, pero la app y los clientes móviles quedan peor servidos; el par acceso/refresco sirve a las tres superficies igual.
- **Reserva como invitado con OTP al confirmar.** Es la alternativa que el propio brief recoge en D9, pero **la decisión de Luis es «no»**: sin teléfono verificado el contador de no-shows no sostiene nada.
- **Permiso por rol global del usuario.** Descartado: rompe con ONB-3 en cuanto alguien trabaja en dos salones.

## Consecuencias

- La prueba de aislamiento (ADR-0002) tiene un hermano: un profesional del negocio A **no ve** la agenda del negocio B aunque su usuario tenga membresía en los dos.
- El coste de WhatsApp por OTP es real y hay que vigilarlo; el límite por teléfono es tanto seguridad como control de gasto.
- Se necesita la **credencial de Meta WhatsApp Cloud API** para probar el OTP de verdad. Hasta que llegue, el proveedor de mensajería tiene una implementación de desarrollo que escribe el código en el log, y **el flujo real queda marcado como no verificado en el tablero**.
- El **borrado de cuenta desde la app** (Ley 81) obliga a que todo lo que cuelga del usuario tenga política de borrado o anonimización decidida en el modelo de datos, no improvisada.
