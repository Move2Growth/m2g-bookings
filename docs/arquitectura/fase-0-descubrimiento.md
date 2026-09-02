# Fase 0 · Descubrimiento — Estado: en proceso

> **Qué es este documento.** El inventario de lo que **ya está decidido** y de lo que **todavía no**.
> Cualquier agente que se pregunte «¿esto puedo elegirlo yo?» viene aquí antes de escribir una línea.
> La respuesta es casi siempre no: o está en el §10 del [brief](../BRIEF-PRODUCTO.md), o está en un
> [ADR](adr/), o está en la lista de preguntas abiertas del final y **la contesta Luis**.
>
> **Regla de uso.** Ningún agente resuelve por su cuenta una pregunta abierta. Lo que tiene un valor
> por defecto se construye con ese valor y se marca; lo que no lo tiene, se para y se escala en
> [`../ai-development/ESTADO-GLOBAL.md`](../ai-development/ESTADO-GLOBAL.md). Cuando Luis conteste,
> la respuesta se convierte en **un ADR nuevo** y esta lista se acorta.

---

## 1. Las dieciocho decisiones ya tomadas

> **RECUADRO DE DECISIONES CERRADAS — no se reabren.**
>
> Son las del §10 del brief. Vienen **con su valor por defecto y ese valor se usa**. Ningún agente
> las discute, las matiza ni las «mejora»; si alguna resulta imposible de cumplir por un impedimento
> técnico real, se para, se escribe un ADR explicando por qué y **se avisa a Luis** — no se cambia
> sobre la marcha.

| # | Decisión | **Valor que se usa** | Dónde se materializa |
|---|---|---|---|
| **D1** | Nombre comercial y dominio | **Codename *M2G Agenda***, nunca a fuego en el código | Configuración y tokens · ADR-0013 · pregunta abierta **P1** |
| **D2** | Alcance de la app | **Dos modos, cliente y negocio**; la configuración avanzada se queda en la web | Fase 5 · APP-3 |
| **D3** | Unidad de cobro futura | **Por negocio**, con el modelo preparado para cobrar por profesional | ADR-0010 · `subscriptions` |
| **D4** | Comisión por reserva | **No en v1** | Ninguna tabla de comisiones en el modelo |
| **D5** | Pasarela de pago | **Yappy + tarjetas por pasarela local** | ADR-0010, interfaz `PaymentProvider` · pregunta abierta **P2** |
| **D6** | Web pública | **Next.js con SSR**; el template SPA de la casa no sirve para lo indexable | ADR-0011 · `apps/web` |
| **D7** | App nativa | **Expo / React Native**, una sola base de código | ADR-0001 · `apps/mobile`, Fase 5 |
| **D8** | Mapas y geocoding | **Mapbox** | ADR-0005, interfaz `GeocodingProvider` · pregunta abierta **P3** |
| **D9** | Reserva como invitado | **No.** Teléfono verificado obligatorio | ADR-0006 · RSV-1 |
| **D10** | Confirmación de la reserva | **Auto-confirmar**, configurable por negocio | RSV-3 · `business_settings` |
| **D11** | Mínimo para publicar | **1 servicio activo, horario, ubicación y 1 foto** | ONB-6 · puerta de publicación |
| **D12** | Símbolo de moneda | **`$`** | ADR-0010, es configuración y no una constante |
| **D13** | Multi-servicio en una reserva | **Sí en v1**, encadenado y con el mismo profesional | ADR-0004 · una sola fila de ocupación continua |
| **D14** | SMS | **Solo como respaldo del OTP**, con control de coste | ADR-0006, ADR-0007 |
| **D15** | Orden de fases | **Ads (4) antes que app (5)** | §9 del brief |
| **D16** | Factura fiscal DGI | **v2** | El modelo deja sitio, no se construye |
| **D17** | Profesional en varios negocios | **v2** | `memberships` ya lo admite; la interfaz no lo expone |
| **D18** | Cuentas de las tiendas | **De M2G**, no del cliente | Fase 5 · pregunta abierta **P9** |

**Lo marcado v2 en el brief no se construye**, pero el modelo de datos le deja sitio cuando es
barato: multi-sede, recursos físicos, profesional en varios negocios, depósitos y cobro al cliente
final, y el rol de recepción. Una columna hoy no cuesta nada; una migración con datos vivos, mucho.

---

## 2. Índice de los catorce ADR

Cada ficha es una decisión de arquitectura ya tomada. **Un ADR aceptado no se edita: se supera con
otro.** Si una tarea choca con uno de estos, se para y se escala, no se improvisa una excepción.

| ADR | Qué decidió, en una línea | Requisitos del brief que toca |
|---|---|---|
| [0001](adr/0001-monorepo-y-estructura.md) | Un solo repositorio con `apps/` y `packages/`, JavaScript con pnpm workspaces y Python con uv; los tipos de la API se generan, no se escriben. | §8 (monorepo y paquetes compartidos), APP-1 |
| [0002](adr/0002-multi-tenant-con-rls.md) | El aislamiento entre negocios lo garantiza **PostgreSQL con Row Level Security**, no el filtro de la aplicación, y desde la primera migración. | §6 (multi-tenant), STF-3, ADM-2, garantía nº 1 de la constitution |
| [0003](adr/0003-tiempo-utc-y-zona-del-negocio.md) | Los instantes se guardan en UTC y las reglas horarias recurrentes como día de la semana más hora local; la zona vive en el negocio y solo el motor convierte. | AGD-1, AGD-5, §6 (listo para multi-país) |
| [0004](adr/0004-no-doble-reserva-restriccion-de-exclusion.md) | La imposibilidad de doble reserva es una **restricción de exclusión** sobre el rango ocupado —buffers incluidos—, no un `if`; los bloqueos comparten tabla con las reservas. | AGD-3, AGD-4, RSV-2, D13, garantía nº 2 |
| [0005](adr/0005-geo-postgis-y-taxonomia-de-zonas.md) | Distancia con PostGIS y `geography`; zonas como taxonomía jerárquica administrable, con la del negocio persistida y editable por el dueño. | MKT-1, MKT-2, MKT-6, MKT-7, NEG-1 |
| [0006](adr/0006-identidad-otp-sesiones-y-rbac.md) | Identidad separada en quién eres, cómo lo demuestras y qué puedes hacer: OTP con hash y límites, refresco revocable y permisos por membresía de negocio. | ONB-1, ONB-3, ONB-4, STF-3, ADM-2, ADM-5, D9, D14 |
| [0007](adr/0007-notificaciones-cola-idempotente-y-proveedor-abstracto.md) | Toda notificación pasa por una tabla que es la cola, con **clave de idempotencia derivada del hecho**, plantillas como datos y proveedores intercambiables. | NTF-1, NTF-2, NTF-3, NTF-4, REV-6, NEG-1 |
| [0008](adr/0008-trabajos-en-segundo-plano-con-arq.md) | Trabajos en segundo plano con **arq** sobre el Redis del stack; el planificador **encola, no envía**, y ningún trabajo lleva objetos en los argumentos. | NTF-2 (recordatorios), MKT-3 (precálculo), PAY-1 (ciclo), ADS-4 |
| [0009](adr/0009-ranking-configurable-y-rating-bayesiano.md) | El ranking es una fórmula con **pesos en base de datos** y desglose explicable; el rating es bayesiano; los patrocinados se intercalan aparte y nunca tocan el rating. | MKT-3, MKT-4, MKT-8, REV-5, ADM-4, ADS-7 |
| [0010](adr/0010-planes-y-billing-desde-el-dia-uno.md) | El motor de planes existe completo aunque cobre 0, con historial y ciclo que se ejecuta igual; el cobro real vive detrás de una interfaz y no se enciende sin permiso. | PAY-1, PAY-2, PAY-3, PAY-6, ADM-4, D3, D12 |
| [0011](adr/0011-superficies-next-ssr-y-vite-spa.md) | Next.js con SSR para lo público **y para el panel de negocio**; Vite SPA solo para el back-office; la web nunca habla directamente con la base de datos. | §4 (superficies), MKT-7, D6, ADM-1 a ADM-7 |
| [0012](adr/0012-api-rest-versionada-y-contrato-openapi.md) | Una API REST en `/api/v1` con el OpenAPI **generado**, identificadores UUID v7, paginación por cursor, errores con forma única, enumerados en minúsculas e idempotencia en las escrituras que importan. | §4, RSV-1, APP-1, §6 (seguridad, límites) |
| [0013](adr/0013-design-system-propio-mobile-first.md) | Design system propio con `packages/tokens` como fuente única, IBM Plex Sans, paleta por función, 44 px de objetivo táctil y diseño **a 390 px primero**. | §8 (design system), §6 (accesibilidad, mobile-first), D1 |
| [0014](adr/0014-entorno-local-migraciones-y-seed.md) | Entorno local de un comando en `infra/local/`, migraciones con Alembic contra Postgres real y un **seed con datos panameños verosímiles** y la agenda medio llena. | Encargo §«lo que no es tuyo», §6 (calidad), ADR-0005 |

---

## 3. Preguntas abiertas para Luis

> **Cómo leer esta sección.** Cada pregunta se entiende sola: lleva su contexto dentro y no
> referencia códigos de tarea ni notas previas. De cada una se dice **qué se pregunta**, **por qué
> hace falta**, **qué se hace mientras tanto para no quedarse parado** y **a partir de qué momento
> bloquea de verdad**. Cuando lo que se pide es una credencial, se dice exactamente qué es, para qué
> la necesitamos, los pasos concretos para conseguirla y con qué nombre guardarla en Bitwarden.

### 3.1 Las cuatro cosas que el equipo no puede decidir

Son las que el encargo aparta explícitamente de las manos del equipo.

---

#### P1 · ¿Cómo se va a llamar esto de cara al público y en qué dominio va a vivir?

**Qué se pregunta.** El nombre comercial de la plataforma y el dominio de internet donde se va a
publicar. Hoy se usa *M2G Agenda*, que es un nombre interno para entendernos, no un nombre de
producto.

**Por qué hace falta.** El nombre aparece en muchos sitios que después cuesta cambiar: el logotipo,
los correos que salen de la plataforma, los textos de las notificaciones de WhatsApp que Meta tiene
que aprobar una a una, las direcciones de las páginas que Google va a indexar, la ficha en las
tiendas de aplicaciones y el remitente del correo transaccional. Cambiar el nombre después de que
Google haya indexado las páginas cuesta posiciones de búsqueda, que es exactamente el canal por el
que se espera que llegue la mitad de los clientes.

**Qué se hace mientras tanto.** El nombre **no se escribe en ningún sitio del código**: sale de una
variable de configuración y de los tokens de diseño, así que cambiarlo el día que se decida es tocar
un archivo, no repasar pantallas. Todo lo que se construya en las fases 0, 1 y 2 funciona igual con
el nombre puesto o sin él.

**Cuándo bloquea de verdad.** No bloquea la Fase 0 ni la Fase 1. **Bloquea al final de la Fase 2**,
porque las páginas públicas se indexan con su dirección definitiva y las plantillas de WhatsApp se
mandan a aprobar con el nombre dentro. Conviene tener el nombre y el dominio decididos **antes de
enseñarle el marketplace a nadie de fuera**.

---

#### P2 · ¿Con qué pasarela se va a cobrar en Panamá, y cuál es la cuenta?

**Qué se pregunta.** La empresa concreta que va a procesar los pagos con tarjeta y con Yappy, y a
nombre de quién está la cuenta de comercio.

**Por qué hace falta.** Cada pasarela tiene su propia forma de integrarse, sus propias credenciales
y su propia manera de avisar de que un pago se completó. La decisión por defecto del brief es
«Yappy más tarjetas por pasarela local», pero eso no es una empresa: hay que elegirla, abrir la
cuenta de comercio —que exige papeleo de la sociedad panameña— y obtener las claves de prueba y las
de producción.

**Qué se hace mientras tanto.** El cobro está **detrás de una interfaz** con una implementación de
desarrollo que simula pagos correctos, pagos rechazados y avisos duplicados. El motor de planes se
construye entero contra esa implementación y se prueba con el plan gratuito, que cuesta 0: el camino
del cobro se recorre miles de veces antes de que haya un dólar de por medio.

**Cuándo bloquea de verdad.** No bloquea nada de las fases 0, 1 y 2. **Bloquea la Fase 4**, que es
la de publicidad pagada, y con ella el primer ingreso real del producto. Como abrir una cuenta de
comercio con papeleo de sociedad tarda semanas, conviene empezarlo mientras se construye la Fase 2,
no cuando llegue la Fase 4.

---

#### P3 · ¿Se confirma Mapbox para los mapas, sabiendo que tiene coste por uso?

**Qué se pregunta.** Si el proveedor de mapas y de conversión de direcciones en coordenadas es
Mapbox, como dice el valor por defecto del brief, o si se prefiere Google Maps u otro; y si se acepta
el gasto mensual que eso supone.

**Por qué hace falta.** El marketplace necesita dos cosas distintas de un proveedor de mapas:
pintar el mapa que ve el cliente y traducir la dirección que escribe un negocio en un punto
geográfico para poder ordenar por cercanía. Las dos se pagan por uso y el propio brief declara el
coste de mapas como un riesgo del proyecto. Hay además un detalle contractual que conviene mirar
antes de firmar: guardar las coordenadas en nuestra base de datos —que es justo lo que hacemos para
no pagar dos veces por la misma dirección— **no está permitido con el uso temporal de Mapbox** y
requiere el permiso de almacenamiento permanente, que se contrata aparte y cuesta más.

**Qué se hace mientras tanto.** La conversión de direcciones vive detrás de una interfaz con una
implementación local que resuelve las direcciones del conjunto de datos de ejemplo sin llamar a
nadie, y el mapa del marketplace se construye con una capa de mapa gratuita y sin cuenta. Toda la
Fase 2 se puede terminar así: la búsqueda por cercanía la calcula PostgreSQL, no el proveedor.

**Cuándo bloquea de verdad.** No bloquea la construcción. **Bloquea el momento en que un negocio
real escriba su dirección**, es decir, la primera vez que alguien de fuera use el producto. En la
práctica: antes de enseñárselo a un salón de verdad.

---

#### P4 · ¿Quién autoriza que se cobre dinero de verdad, y cuándo?

**Qué se pregunta.** Esto no es una credencial: es un permiso. Que quede por escrito que **ningún
cobro real a un negocio ni a un cliente se enciende sin que Luis lo diga explícitamente**, aunque el
código esté terminado y probado.

**Por qué hace falta.** El motor de planes y el de publicidad se construyen completos y probados.
Llegado el momento, la diferencia entre «esto simula un cobro» y «esto le pasa un cargo a la tarjeta
de un salón» es un interruptor de configuración. Ese interruptor no lo toca ningún agente.

**Qué se hace mientras tanto.** Todo se ejecuta contra la implementación de desarrollo. El plan
activo es el gratuito, a precio 0, y el ciclo de renovación corre igual sin generar cargo: así el
camino queda probado sin mover dinero.

**Cuándo bloquea de verdad.** Nunca bloquea la construcción. Es una barrera permanente, no una
dependencia.

---

### 3.2 Credenciales y servicios externos que hoy no existen

Ninguno de estos servicios está contratado ni tiene cuenta. **Nada del entorno local depende de
ellos**: el stack arranca y las pruebas pasan sin una sola credencial, porque cada integración tiene
su implementación de desarrollo. Lo que no se puede es dar por verificado un flujo real sin ellas.

---

#### P5 · Meta WhatsApp Cloud API — la que hay que pedir primero

**Qué es.** El servicio oficial de Meta que permite que un programa mande mensajes de WhatsApp desde
un número de empresa. No es WhatsApp Business, la aplicación del móvil: es la interfaz para
programas, y el número que se registre **deja de poder usarse en la aplicación normal**.

**Para qué la necesitamos.** Es el canal principal de todo el producto: el código de verificación
que confirma el teléfono al registrarse, la confirmación de la reserva, los recordatorios de
veinticuatro horas y de dos horas antes de la cita, la petición de opinión después, y la invitación
a un profesional para que se una al equipo del salón. Sin WhatsApp, en Panamá esto no funciona: es
donde la gente lee.

**Lo que de verdad tarda.** Dos cosas, y por eso esta es la primera que hay que pedir: la
**verificación de la empresa** por parte de Meta, que exige documentación de la sociedad y puede
llevar días o semanas, y la **aprobación de cada plantilla de mensaje**, porque WhatsApp no permite
mandar texto libre a quien no ha escrito antes. Cada mensaje distinto que envía la plataforma es una
plantilla que Meta revisa una a una.

**Pasos para conseguirla:**

1. Entrar en `business.facebook.com` con la cuenta de Facebook de M2G y crear —o elegir— la cuenta
   de empresa que va a ser la dueña del número.
2. En **Configuración del negocio → Centro de seguridad**, iniciar la **verificación de la empresa**
   y subir la documentación de la sociedad. Esto es lo que tarda; se lanza el primer día y se sigue
   con lo demás mientras se resuelve.
3. Ir a `developers.facebook.com` → **Mis aplicaciones** → **Crear aplicación**, tipo **Empresa**, y
   asociarla a esa cuenta de empresa.
4. Dentro de la aplicación, **añadir el producto WhatsApp**. Al hacerlo se crea automáticamente una
   cuenta de WhatsApp Business.
5. En **WhatsApp → Configuración de la API**, registrar un número de teléfono **que no esté en uso en
   la aplicación normal de WhatsApp** y verificarlo por SMS o por llamada. Anotar dos identificadores
   que aparecen en esa misma pantalla: el **identificador del número** y el **identificador de la
   cuenta de WhatsApp Business**.
6. Generar un acceso que no caduque: **Configuración del negocio → Usuarios → Usuarios del sistema**
   → crear uno de tipo administrador → **Añadir activos** y darle la aplicación y la cuenta de
   WhatsApp Business → **Generar token** con los permisos de envío y de gestión de mensajes, sin
   caducidad. El token se enseña **una sola vez**: hay que copiarlo en ese momento.
7. En **WhatsApp Manager → Plantillas de mensajes**, crear las plantillas y mandarlas a aprobación.
   El código de verificación va en la categoría de **autenticación** y los recordatorios en la de
   **utilidad**; la categoría equivocada es motivo de rechazo. Los textos exactos los redacta el
   equipo y se pasan para revisión antes de enviarlos a Meta.
8. Inventarse una palabra secreta cualquiera para que Meta y nuestra API se reconozcan cuando Meta
   nos avise de que un mensaje se entregó, y guardarla como una credencial más. La dirección de
   internet que hay que darle a Meta la aporta el equipo cuando exista un entorno publicado; hasta
   entonces no hace falta.

**Cómo guardarlo en Bitwarden.** Una entrada llamada **`M2G Agenda · Meta WhatsApp Cloud API`** con
estos campos, cada uno con su nombre tal cual:

- `WHATSAPP_TOKEN` — el acceso del usuario del sistema, el del punto 6.
- `WHATSAPP_PHONE_NUMBER_ID` — el identificador del número, del punto 5.
- `WHATSAPP_WABA_ID` — el identificador de la cuenta de WhatsApp Business, del punto 5.
- `WHATSAPP_APP_SECRET` — la clave secreta de la aplicación, en *Configuración → Básica* de la
  aplicación de desarrolladores; sirve para comprobar que los avisos vienen de verdad de Meta.
- `WHATSAPP_WEBHOOK_VERIFY_TOKEN` — la palabra secreta del punto 8.

**Qué se hace mientras tanto.** Hay un proveedor de mensajería de desarrollo que escribe el mensaje
y el código de verificación en el registro y en un archivo. Con eso se construyen y se prueban
enteros el registro, el onboarding, las reservas y los recordatorios. **El flujo real queda marcado
como no verificado en el tablero**, que es distinto de dar por hecho que funciona.

**Cuándo bloquea de verdad.** No bloquea la Fase 0. **Bloquea el cierre de la Fase 1**, cuyo
criterio es que un salón real opere su agenda: un salón real necesita que a sus clientes les llegue
el recordatorio de verdad. Dado lo que tarda la verificación de la empresa y la aprobación de
plantillas, **pedirla el primer día** es lo que evita que sea un bloqueo.

---

#### P6 · Clave del proveedor de mapas y de geocoding

**Qué es.** La clave que autoriza a nuestro programa a pintar mapas y a convertir direcciones en
coordenadas. Depende de qué se conteste en la pregunta P3; con el valor por defecto del brief, es
una cuenta de Mapbox.

**Para qué la necesitamos.** Para dos cosas: que el cliente vea en un mapa dónde está el salón, y
que cuando un negocio escriba su dirección se pueda calcular a qué distancia queda de quien busca.
Lo segundo es lo que hace posible «barberías cerca de mí», que es el gesto principal en el móvil.

**Pasos para conseguirla, con Mapbox:**

1. Crear la cuenta en `account.mapbox.com` con el correo de la empresa, no con uno personal.
2. Añadir un método de pago en **Billing**. Sin él, el servicio se corta al superar el nivel gratuito
   y se corta un martes por la tarde, sin avisar antes.
3. En **Tokens → Create a token**, crear uno llamado `m2g-agenda-web` con los permisos públicos que
   vienen marcados por defecto. Este es el que va en la página web, empieza por `pk.` y es público
   por naturaleza; cuando haya dominio, se restringe a él desde esa misma pantalla.
4. Crear un segundo token, `m2g-agenda-servidor`, con permiso de geocoding. Este es secreto, empieza
   por `sk.`, lo usa solo nuestra API y existe aparte del anterior para poder cambiarlo sin tocar la
   web.
5. **Confirmar con Mapbox el permiso de almacenamiento permanente de resultados de geocoding.** Es
   el punto que decide el precio: guardar las coordenadas de un negocio en nuestra base de datos —lo
   que hacemos para no pagar dos veces por la misma dirección— no entra en el uso temporal.

**Cómo guardarlo en Bitwarden.** Una entrada **`M2G Agenda · Mapbox`** con los campos
`MAPBOX_PUBLIC_TOKEN` y `MAPBOX_SECRET_TOKEN`, y una nota indicando si el almacenamiento permanente
quedó contratado o no.

**Qué se hace mientras tanto.** La conversión de direcciones tiene una implementación local que
resuelve las direcciones del conjunto de ejemplo, y el mapa se construye contra una capa gratuita.
La ordenación por cercanía **no depende del proveedor**: la calcula PostgreSQL con PostGIS.

**Cuándo bloquea de verdad.** No bloquea la construcción de la Fase 2. **Bloquea el primer negocio
real que escriba su dirección**, porque su punto en el mapa no se puede inventar.

---

#### P7 · Almacenamiento de fotos compatible con S3

**Qué es.** Un espacio en internet donde guardar archivos —las fotos— que se sirve por dirección
web. «Compatible con S3» quiere decir que habla el mismo idioma que el almacenamiento de Amazon, que
es el estándar de hecho; sirve Hetzner Object Storage, Cloudflare R2, Backblaze B2 o el propio
Amazon S3. Como el resto de la infraestructura del brief está en Hetzner, lo natural es Hetzner
Object Storage.

**Para qué lo necesitamos.** El brief exige una foto como mínimo para que un negocio pueda
publicarse, y el perfil lleva portada y galería; además hay fotos de servicios, de profesionales y
de las opiniones. Eso no se guarda en la base de datos ni en el disco del servidor: se guarda aparte,
se sirve rápido y se procesa a varios tamaños para que la web cargue en 3G.

**Pasos para conseguirlo, con Hetzner:**

1. Entrar en la consola de Hetzner Cloud con la cuenta de M2G, elegir el proyecto y abrir **Object
   Storage**.
2. Crear dos espacios: `m2g-agenda-media` para las fotos reales y `m2g-agenda-media-dev` para
   pruebas, ambos en la misma región que vaya a estar el servidor.
3. En **Security → S3 credentials**, generar una pareja de claves. **La clave secreta se enseña una
   sola vez.**
4. Anotar la dirección del servicio y la región, que aparecen en la ficha del espacio.

**Cómo guardarlo en Bitwarden.** Una entrada **`M2G Agenda · Almacenamiento de fotos`** con los
campos `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` y
`S3_PUBLIC_BASE_URL`.

**Qué se hace mientras tanto.** El entorno local levanta un almacenamiento compatible dentro del
propio `docker-compose`, con las mismas claves de acceso que usaría el real. El código que sube y
sirve fotos es exactamente el mismo: cambia la dirección del servicio y nada más.

**Cuándo bloquea de verdad.** No bloquea nada en local. **Bloquea el primer despliegue a un entorno
publicado**, que no es trabajo de este equipo pero sí depende de que la credencial exista.

---

#### P8 · Correo transaccional

**Qué es.** El servicio que envía los correos que salen de la plataforma: no boletines, sino los
correos de uno en uno que se disparan por algo que pasó. En la casa ya se usa Resend con el dominio
`m2g.dev` verificado, así que lo barato es reutilizarlo.

**Para qué lo necesitamos.** Es el respaldo de WhatsApp, y el brief lo pide expresamente porque
depender solo de Meta es un riesgo declarado. Además hay correos que no encajan en WhatsApp: la
invitación a un profesional que no da su teléfono, el recibo de una compra, y los avisos del equipo
interno.

**Pasos para conseguirlo:**

1. Entrar en `resend.com` con la cuenta de M2G.
2. Comprobar en **Domains** que el dominio desde el que se va a enviar está verificado. Si el nombre
   comercial que se decida en la pregunta P1 trae dominio nuevo, **hay que verificarlo ahí y añadir
   los registros de DNS**; mientras tanto se envía desde `m2g.dev`, que ya está verificado.
3. En **API Keys → Create API Key**, crear una llamada `m2g-agenda` con permiso solo de envío. Se
   enseña una sola vez.
4. Decidir la dirección del remitente. Por coherencia con el resto de la casa, algo del estilo de
   `noreply@m2g.dev` hasta que haya dominio propio.

**Cómo guardarlo en Bitwarden.** Una entrada **`M2G Agenda · Resend`** con los campos
`RESEND_API_KEY` y `MAIL_FROM`.

**Qué se hace mientras tanto.** El correo usa el mismo proveedor de desarrollo que WhatsApp: escribe
a disco y a la consola. Todo el flujo de notificaciones se prueba así.

**Cuándo bloquea de verdad.** No bloquea las fases 0, 1 ni 2. Bloquea el mismo momento que
WhatsApp: cuando haya usuarios de verdad esperando que les llegue algo.

---

#### P9 · Cuentas de las tiendas de aplicaciones

**Qué es.** Las dos cuentas de desarrollador que hacen falta para publicar una aplicación: el
programa de desarrolladores de Apple y la consola de Google Play. El brief ya decide que van **a
nombre de M2G**, no del cliente.

**Para qué las necesitamos.** Sin ellas no se puede publicar la aplicación, y tampoco se pueden
enviar avisos al móvil, porque las claves de notificaciones cuelgan de esas mismas cuentas.

**Lo que de verdad tarda.** La cuenta de Apple de tipo organización exige un **número D-U-N-S** de la
sociedad, que es un identificador de empresas que se solicita aparte y **puede tardar semanas**. Es
la razón de mencionarlo ahora aunque no haga falta hasta la Fase 5.

**Pasos para conseguirlas:**

1. **Apple.** Comprobar o solicitar el número D-U-N-S de la sociedad en el sitio de Apple para
   desarrolladores. Con él, inscribirse en el Apple Developer Program como organización, que cuesta
   noventa y nueve dólares al año. Luego, dentro de App Store Connect, crear en **Users and Access →
   Integrations** una clave de acceso para publicar automáticamente, y en el portal de
   desarrolladores una clave de notificaciones push. Las dos se descargan como archivo **una sola
   vez**.
2. **Google.** Crear la cuenta en la consola de Google Play, que cuesta veinticinco dólares una sola
   vez, y superar la verificación de identidad de la organización. Después, crear un proyecto en
   Firebase para las notificaciones y descargar el archivo de configuración de la aplicación
   Android, y una cuenta de servicio con permiso de publicación.

**Cómo guardarlo en Bitwarden.** Tres entradas separadas: **`M2G Agenda · Apple Developer`** con el
correo de la cuenta, el número D-U-N-S, y adjuntos el archivo de la clave de App Store Connect y el
de la clave de notificaciones, cada uno con su identificador de clave y su identificador de emisor;
**`M2G Agenda · Google Play Console`** con el correo y adjunto el archivo de la cuenta de servicio;
y **`M2G Agenda · Firebase`** con el archivo de configuración de Android.

**Qué se hace mientras tanto.** Nada que dependa de esto entra en las fases 0, 1 y 2: la aplicación
es la Fase 5. Lo único que se hace ahora es no cerrarle la puerta: la interfaz de la web se diseña
para caber en un móvil y el borrado de cuenta desde dentro del producto se construye desde el
principio, porque **sin él Apple rechaza la publicación**.

**Cuándo bloquea de verdad.** **Bloquea la Fase 5 entera.** Se pide con antelación por el asunto del
D-U-N-S, no porque haga falta ya.

---

### 3.3 Los valores que el brief deja «configurables» sin fijar

Son parámetros de producto, no decisiones de arquitectura. El brief dice «X horas» o «X días» y da
un valor por defecto entre paréntesis. **El equipo usa ese valor por defecto, lo deja en
configuración y no se bloquea.** Si Luis quiere otro, cambiarlo es modificar un número en la
configuración del negocio o de la plataforma; no hay que tocar código ni volver a desplegar.

| # | Qué hay que fijar | **Valor que se usa mientras tanto** | Dónde vive el valor | Qué cambia si Luis dice otra cosa |
|---|---|---|---|---|
| **P10** | Con cuánta antelación puede un cliente cancelar o cambiar su cita por su cuenta; pasado ese plazo, solo el negocio puede tocarla | **2 horas antes de la cita** | Ajuste **por negocio**, para que un spa con preparación pueda exigir más margen que una barbería | Un número en la configuración del negocio. La pantalla ya avisa del plazo antes de reservar, que es requisito legal |
| **P11** | Cuánto tiempo tiene un cliente para dejar su opinión después de la cita | **14 días** desde que la cita se marca como completada | Ajuste **de plataforma**, igual para todos: si cada negocio pudiera elegirlo, las opiniones dejarían de ser comparables | Un número en la configuración general. Pasado el plazo, el botón de opinar desaparece |
| **P12** | Cuántos negocios como máximo pueden comprar el destacado en una misma combinación de categoría y barrio para un mismo periodo | **3 sitios** por combinación y periodo | Tabla de inventario de publicidad, editable desde el back-office | Un número por combinación. Es la palanca que decide si el destacado es escaso y caro o abundante y barato |
| **P13** | Cuántos resultados pagados se intercalan entre los resultados normales de una búsqueda | **2 de cada 10**, etiquetados «Patrocinado» y sin desplazar a ninguno fuera de la página | Configuración de la plataforma, junto a los pesos del ranking | Un número. Tiene tope por principio: los patrocinados **nunca ocultan a los orgánicos** y **no tocan el rating ni las opiniones**, y eso no es configurable |

**Otros valores que se aplican por defecto sin preguntar**, porque el brief los fija y solo se
recuerdan aquí para que estén en un sitio: granularidad de los huecos de agenda de **15 minutos**,
antelación mínima para reservar de **1 hora**, antelación máxima de **60 días**, y zona horaria
`America/Panama`. Todos son ajuste por negocio. Del ranking, los pesos de cada señal, el radio a
partir del cual la distancia deja de contar y la duración del impulso a los negocios nuevos también
son datos en base de datos, no números en el código, y arrancan con valores razonables que se ajustan
mirando resultados reales.

---

### 3.4 Tres decisiones de política que salieron al escribir el modelo de datos

No son técnicas: son de política de la empresa, y el equipo no debería elegirlas por su cuenta
aunque técnicamente pueda implementar cualquiera de las tres. Salieron al decidir **qué se borra
y qué se conserva** cuando alguien cierra su cuenta, que es un requisito de la Ley 81 y también
de Apple para publicar la app.

| # | Qué hay que decidir | **Lo que se hace mientras tanto** | Por qué no lo decide el equipo |
|---|---|---|---|
| **P14** | Qué pasa con **el texto de una opinión cuando su autor borra la cuenta**: si desaparece con él o se queda con el nombre borrado | **Se conserva el texto con el autor anonimizado.** Un negocio que reunió cuarenta opiniones no puede perderlas porque un cliente se dé de baja, y quien las lee tampoco | Es el equilibrio entre el derecho de supresión de una persona y el interés legítimo del negocio y de los demás clientes. Tiene que quedar escrito en la política de opiniones **antes** de que haya una sola opinión publicada |
| **P15** | **Cuánto tiempo se guarda el registro de auditoría** de las acciones internas: quién entró en qué negocio, quién forzó una cancelación, quién suplantó a quién | **Se guarda sin borrar**, y se anota como deuda | Sin un plazo, la tabla crece para siempre. Con un plazo demasiado corto, se pierde la única prueba de qué hizo el equipo interno el día que alguien reclame |
| **P16** | **Cuánto hay que conservar las facturas y los recibos** en Panamá | **Se conservan indefinidamente** y no se borran nunca por error | Es un plazo fiscal, no una decisión de producto: lo dice la asesoría, y equivocarse hacia abajo es un problema con la DGI |
| **P17** | Si **la verificación del teléfono cuenta como una de las tres pantallas** del flujo de reserva | **No cuenta**: se resuelve como una hoja que sube sobre la pantalla de confirmar, sin sacar a la persona del flujo | El brief pide dos cosas que solo caben juntas así: máximo tres pantallas tras elegir servicio (RSV-1) y teléfono verificado obligatorio (D9). Si Luis la cuenta como pantalla, hay que fusionar la elección de profesional con la de hora, y elegir hora empeora |

---

## 4. Resumen: qué bloquea y desde cuándo

| Pregunta | ¿Bloquea la Fase 0? | ¿Bloquea la Fase 1? | ¿Bloquea la Fase 2? | Primer momento en que bloquea de verdad |
|---|---|---|---|---|
| **P1** Nombre y dominio | No | No | **Al cerrarla** | Antes de que Google indexe y antes de mandar plantillas a Meta |
| **P2** Pasarela de pago | No | No | No | Fase 4, la de publicidad pagada |
| **P3** Proveedor de mapas | No | No | No | El primer negocio real que escriba su dirección |
| **P4** Encender cobros reales | No | No | No | Barrera permanente, no dependencia |
| **P5** WhatsApp de Meta | No | **Al cerrarla** | Sí | El cierre de la Fase 1 con un salón real. **Pedirla el primer día** |
| **P6** Clave de mapas | No | No | No | El primer negocio real que escriba su dirección |
| **P7** Almacenamiento de fotos | No | No | No | El primer despliegue a un entorno publicado |
| **P8** Correo transaccional | No | No | No | Cuando haya usuarios de verdad esperando un correo |
| **P9** Cuentas de las tiendas | No | No | No | Fase 5. **Se pide con semanas de antelación** por el D-U-N-S |
| **P10** a **P13** Parámetros | No | No | No | **Nunca bloquean**: se usa el valor por defecto y se marca |

**Lectura corta.** De todo lo anterior, lo único que hay que mover ya es **la cuenta de WhatsApp de
Meta**, porque la verificación de la empresa y la aprobación de plantillas tardan y son lo que
sostiene el criterio de «hecho» de la Fase 1. Todo lo demás se puede contestar mientras se construye,
y nada de ello impide levantar el entorno local ni pasar las pruebas.
