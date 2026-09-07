# ADR-0019 · El acceso es correo y contraseña

- **Estado:** aceptada
- **Fecha:** 2026-09-07
- **Supera a:** la parte de **ADR-0006** que hacía del código por WhatsApp la única puerta de
  entrada. Lo demás de aquel ADR —el refresco opaco y rotatorio, la familia de sesiones, el
  token de acceso sin permisos— sigue en pie y no se toca.

## Contexto

ADR-0006 eligió el código de un solo uso como identidad: sin contraseña que recordar, y el
teléfono verificado como identificador natural. Para un marketplace panameño donde el salón
llama a la clienta por teléfono, tenía sentido.

En la práctica, el coste lo pagó el desarrollo. Para mirar cualquier pantalla había que pedir un
código, buscarlo y teclearlo antes de que caducara a los cinco minutos, y el límite de envíos
—cinco por número cada quince minutos, que existe porque cada WhatsApp se paga— cortaba la
sesión de trabajo a la tercera prueba. Durante una demo en vivo hubo que borrar 115 filas de
`otp_codes` a mano para poder seguir.

Y hay un argumento que no es de comodidad: **el código tampoco daba la seguridad que parecía
dar.** Un WhatsApp interceptado es una sesión, el canal real ni siquiera existe todavía —faltan
las credenciales de Meta— y en local el código viaja en la propia respuesta HTTP.

Luis lo zanjó el 7 de septiembre: *«lo del código no tiene sentido, sobre todo si esto es lo que
estamos haciendo desarrollo. Debería ser con una simple usuario y contraseña por ahora»*.

## Decisión

**[decisión] Se entra con correo y contraseña. El código de un solo uso se queda para verificar
el teléfono antes de la primera reserva, que es lo único para lo que hacía falta de verdad.**

De ahí salen cuatro consecuencias que no son negociables:

**[decisión] El teléfono deja de ser obligatorio para existir.** Si el correo identifica, exigir
un número para poder tener cuenta devuelve el trámite que se quitaba. `users.phone_e164` admite
nulo; el único sigue en pie porque en PostgreSQL los nulos no chocan entre sí. El teléfono se
pide **al reservar**, porque ahí sí hace falta: el salón tiene que poder llamar (D9).

**[decisión] Verificar el teléfono no abre sesión.** Existe `/api/v1/mi/telefono`, que ata el
número a la cuenta que **ya está dentro** y no devuelve credenciales. Reutilizar
`/auth/otp/verificar` desde una sesión abierta metía a la persona en **otra cuenta** —la del
número, creada al vuelo, vacía y sin sus citas— sin un solo error a la vista.

**[decisión] La contraseña trae su freno.** Argon2id, mínimo de diez caracteres sin exigir
mayúsculas ni símbolos —esa regla produce «Panama1!» en todas las cuentas del país—, el mismo
mensaje para correo inexistente y contraseña incorrecta, verificación contra un hash señuelo
para que el cronómetro tampoco lo diga, y bloqueo tras ocho fallos. **El contador vive en su
propia transacción**: la de la petición se deshace al lanzar la excepción, así que un contador
escrito ahí dentro es un bloqueo de adorno.

**[decisión] `password_hash` admite nulo, y eso es el sitio hecho para lo que viene.** Nulo
significa «esta persona demuestra quién es por otra vía»: hoy el código, mañana el segundo
factor opcional y la entrada con Google o Apple que Luis ya pidió. `auth_identities` admite el
proveedor `email` junto a `telefono`, `google` y `apple`.

## Consecuencias

- Las cuentas de ejemplo comparten contraseña y su correo se deriva del slug del salón, así que
  se adivina sin consultar ninguna tabla. Están en `docs/operacion/CREDENCIALES-DE-DEMO.md`.
- El límite de envíos de OTP deja de estorbar: solo lo toca quien verifica su teléfono.
- Queda una asimetría que hay que tener presente: **una cuenta sin teléfono no puede reservar**,
  y eso solo se descubre al intentarlo. La pantalla de reserva lo pide en el sitio, sin sacar a
  nadie del flujo, pero es una puerta que sigue ahí.
- El segundo factor y los proveedores externos **no están construidos**. Están previstos en el
  modelo, que es distinto de estar hechos.
