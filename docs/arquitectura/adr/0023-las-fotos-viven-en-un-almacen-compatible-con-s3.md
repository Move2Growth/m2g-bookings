# ADR-0023 · Las fotos viven en un almacén compatible con S3, y el navegador sube directo

- **Estado:** aceptada
- **Fecha:** 2026-09-10

## Contexto

El brief exige **una foto como mínimo** para que un salón pueda publicarse (D11), y la ficha lleva
portada y galería. `POST /negocio/fotos` existía desde el principio y recibía **una clave**… que
nadie sabía cómo conseguir: el registro estaba construido y el sitio donde guardar el archivo, no.
Era lo único que le faltaba a un salón real para trabajar entero.

La pregunta abierta **P7** dejaba la elección del proveedor a Luis. Esperar a esa elección para
construir era esperar a lo que no hace falta: la elección es de proveedor, no de tecnología.

## Decisión

**[decisión] El almacén habla S3.** Es el estándar de hecho y lo hablan Hetzner Object Storage,
Cloudflare R2, Backblaze B2, DigitalOcean Spaces y el propio Amazon. Elegir proveedor deja de ser
una decisión de arquitectura y pasa a ser cuatro variables de entorno.

**[decisión] En local corre MinIO dentro del `docker-compose`.** Una máquina recién clonada sube
una foto **sin ninguna credencial de nadie**. El código que sube y sirve es exactamente el mismo
que correrá contra el proveedor de pago: cambia la dirección del servicio.

**[decisión] El archivo NO pasa por la API.** El navegador sube directo al almacén con un permiso
firmado por el servidor. No es comodidad: una foto de cinco megas subiendo por una conexión de
Panamá ocuparía un trabajador de la API durante un minuto, y con diez salones a la vez la agenda
deja de responder por culpa de unas fotos.

**[decisión] El permiso es una política de subida firmada (`POST`), no una URL de `PUT`.** Es lo
único que **impone el tipo y el tamaño antes de que llegue un solo byte**. Con un `PUT` firmado, el
tope de cinco megas sería una promesa del navegador — y el navegador es de quien sube.

**[decisión] La clave lleva el negocio delante:** `negocios/{negocio}/{uuid7}.{extensión}`. Permite
borrar todo lo de un salón de una pasada —lo va a pedir la Ley 81— y un listado accidental del cubo
no mezcla archivos de dos salones. El identificador es un UUID v7, así que **el nombre que trae el
archivo del teléfono no llega nunca al almacén**: ni sus espacios, ni sus tildes, ni el `../` de
alguien con ganas.

**[decisión] El cubo es de lectura pública y de escritura firmada.** Son las fotos que un salón
enseña en su ficha, hechas para que las vea cualquiera y las indexe un buscador; firmar cada lectura
las volvería incacheables y añadiría una petición a la API por cada imagen de cada listado.

**[decisión] Solo JPEG, PNG, WebP y AVIF.** `image/*` dejaría entrar **SVG, que es un documento con
JavaScript dentro**: servido desde el dominio de las fotos, es una puerta abierta. HEIC se queda
fuera porque no lo pinta ningún navegador — quien sube desde un iPhone manda JPEG, que es lo que
hace el propio iPhone al compartir.

**[decisión] Se guarda la clave, nunca la URL.** Las URL firmadas caducan y guardarlas obligaría a
reescribir filas. La URL se compone al servir, con `URL_BASE_MEDIA`.

**[decisión] Al registrar una foto se comprueban dos cosas**: que la clave es de ese negocio y que
el archivo llegó de verdad. Que la clave la haya dado este mismo servidor hace un minuto no la
convierte en un dato de confianza: llega por la API como cualquier otro. Sin la primera, registrar
la clave de otro salón pondría su foto en tu ficha; sin la segunda, quedaría una fila apuntando a
nada — un hueco roto que no descubre nadie hasta que lo mira un cliente.

**[decisión] Al borrar, primero el archivo y luego la fila, y la fila pase lo que pase.** Al revés,
un almacén caído dejaría al salón sin poder quitar de su ficha la foto que subió por error, que es
justo lo que se hace con prisa. Un archivo huérfano no lo ve nadie; una foto que no se puede quitar,
sí.

**[decisión] Se firma con `boto3`, no con un SigV4 escrito a mano.** La firma es terreno de
seguridad: un SigV4 casero falla dentro de un año con una clave que lleva un carácter raro, y el
error que sale habla de credenciales y no de firmas.

## Alternativas consideradas

- **Guardar las fotos en la base de datos.** Descartado: infla las copias de seguridad, no se cachea
  y convierte cada imagen de cada listado en una consulta.
- **Guardarlas en el disco del servidor.** Descartado: no sobrevive a un segundo servidor ni a un
  redespliegue, y el brief pide poder crecer.
- **Subir a través de la API y que ella reenvíe.** Descartado por lo dicho arriba, y porque duplica
  el tráfico de cada foto.
- **`PUT` firmado.** Descartado: no puede imponer el tamaño.
- **Firmar cada lectura.** Descartado: las fotos públicas dejarían de cachearse.

## Consecuencias

- **En local no bloquea nada.** `make arriba` levanta el almacén y subir una foto funciona.
- **Bloquea el primer despliegue publicado**, que no es trabajo de este equipo: hace falta contratar
  un espacio y rellenar `S3_*` y `URL_BASE_MEDIA`. Está documentado en
  `docs/operacion/SECRETOS-Y-VARIABLES.md`.
- Los tamaños derivados —miniaturas para que un listado no baje cinco fotos de cinco megas— **no
  están**. Es la deuda que deja este ADR, y el sitio donde vive es el trabajador pesado, que se
  declaró vacío justamente para esto.
