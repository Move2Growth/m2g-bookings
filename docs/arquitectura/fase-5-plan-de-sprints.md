# Fase 5 · Plan de sprints — Estado: sin iniciar

> **Qué es este documento.** El plan de construcción de las **fases 0, 1 y 2** del brief, que es lo
> que se pide en este encargo, desglosado en sprints numerados con su objetivo, su alcance, su
> reparto entre agentes, sus dependencias y su criterio de «hecho». Las fases 3 a 6 se esbozan al
> final en un párrafo cada una, para que se vea hacia dónde apunta lo que se construye ahora, y no
> se planifican en detalle.
>
> **De dónde sale.** Del §9 del [brief](../BRIEF-PRODUCTO.md), del
> [encargo de construcción](../../PROMPT-CONSTRUCTOR.md), de los catorce [ADR](adr/) y de la
> [constitution](constitution.md). Lo que no está decidido está en
> [`fase-0-descubrimiento.md`](fase-0-descubrimiento.md) como pregunta abierta, y ningún sprint la
> resuelve por su cuenta.

---

## 1. El marco: lo que este plan tiene que respetar

Antes de los sprints, las reglas que condicionan el orden. No son recomendaciones: si un sprint
choca con una de ellas, el sprint está mal planteado.

**El motor de disponibilidad va primero, y sus pruebas antes que él.** El encargo lo pide dos veces:
las pruebas de los casos difíciles se escriben antes que el código, y cuando el motor esté en verde
**se para y se enseña antes de montar una sola pantalla encima**. Si ese motor está mal, todo lo que
se construya sobre él hay que rehacerlo. Por eso hay dos sprints dedicados y una **puerta explícita**
entre ellos y el resto de la Fase 1.

**Multi-tenant desde la primera migración.** El aislamiento entre negocios no es una capa que se
añade: es la forma de la primera tabla. La migración inicial ya activa la seguridad a nivel de fila,
y hay una prueba automática que recorre el catálogo y falla si aparece una tabla con datos de negocio
sin su política. Meterlo después toca todas las consultas y es lo más caro que se puede dejar para
luego.

**El equipo no monta infraestructura ni despliega.** Ni CI/CD, ni Docker de producción, ni
servidores, ni dominios, ni entornos. Lo que sí se entrega impecable es el entorno local: un
`docker-compose.yml` que levanta el stack entero con un comando y datos cargados, migraciones que
corren desde cero contra una base limpia, un `.env.example` con todas las variables explicadas, un
README de arranque en pasos numerados y las pruebas corriendo con un comando y pasando. Cuando en
este plan aparece el agente `agenda-devops`, es para eso y solo para eso.

**El motor de planes y cobros es de la Fase 3, pero su modelo de datos se prepara en la Fase 0.**
Todo negocio tiene una suscripción desde que se registra aunque valga cero. Si el modelo nace sin el
concepto de ciclo, de gracia y de historial, meterlos después significa migrar miles de negocios
vivos e inventarles una fecha de alta que nadie registró.

**Nada pasa a «validada» sin QA.** Un agente termina su tarea y la deja en «hecha». Es
`agenda-qa-validador` quien la pasa a «validada», y solo él. Al arquitecto no lo valida QA: lo valida
Luis.

**Lo que se ve, se ve en el navegador y a 390 px.** «Build verde» no es evidencia de nada en la
interfaz: ni la política de seguridad de contenidos, ni el comportamiento en tiempo de ejecución, ni
el diseño salen ahí. Todo criterio de «hecho» de este plan que hable de pantallas se comprueba
mirando, con capturas.

**Los datos de prueba se parecen a los reales.** Nunca «Servicio 1 · 100,00». Un salón panameño de
verdad, con «Corte + barba · 45 min · $18» y «Balayage · 3 h · desde $120», y con la agenda medio
llena. Con datos de mentira no se ve que una reserva de tres horas no cabe en el hueco de las cinco
de la tarde, que es exactamente el fallo que se quiere cazar.

### El equipo

Once roles, todos con el prefijo `agenda-`: **arquitecto**, **ingenieria-software**, **devops**,
**backend**, **frontend-web**, **mockuper**, **movil**, **testing**, **qa-validador**,
**seguridad-compliance** y **orquestador**. En las fases 0 a 2, `agenda-movil` no entra —la
aplicación es la Fase 5— y `agenda-orquestador` solo aparece cuando hay tareas que no colisionan en
los mismos archivos y se pueden lanzar a la vez.

### Cómo se cierra cualquier sprint

Cinco cosas, siempre las mismas, además del criterio propio de cada uno: las pruebas del área pasan
con un comando; `agenda-seguridad-compliance` ha revisado lo que toque datos personales, teléfonos o
dinero; toda variable nueva está en `.env.example` **y** en el inventario de secretos, con nombre y
propósito pero nunca con el valor; el tablero está actualizado en la misma sesión, con la deuda que
quede anotada; y `agenda-qa-validador` ha dado el visto bueno.

---

## 2. Mapa de dependencias

```mermaid
graph LR
  S1[S1 Andamiaje y entorno local] --> S2[S2 Modelo de datos y contrato]
  S1 --> S3[S3 Design system y flujos]
  S2 --> G0{{Puerta Fase 0 · aprueba Luis}}
  S3 --> G0
  G0 --> S4[S4 Pruebas del motor]
  S4 --> S5[S5 Motor de disponibilidad]
  S5 --> G1{{Puerta del motor · se para y se enseña}}
  G1 --> S6[S6 Identidad y alta de negocio]
  S6 --> S7[S7 Servicios y equipo]
  S7 --> S8[S8 Agenda y reservas manuales]
  S8 --> S9[S9 Notificaciones y ficha de cliente]
  S9 --> G2{{Puerta Fase 1 · un salon opera desde el movil}}
  G2 --> S10[S10 Zonas y perfiles indexables]
  S10 --> S11[S11 Busqueda filtros y mapa]
  S11 --> S12[S12 Ranking y rating bayesiano]
  S12 --> S13[S13 Reserva por el cliente]
  S13 --> S14[S14 Opiniones y favoritos]
  S14 --> G3{{Puerta Fase 2 · un cliente reserva solo y Google indexa}}
```

---

## 3. Fase 0 · Diseño

**Qué entrega la fase.** Los flujos, el design system, el modelo de datos y los contratos de la API,
más el entorno local que los sostiene. **Está hecha cuando Luis lo aprueba**, no cuando el equipo lo
dé por bueno.

---

### Sprint 1 · Andamiaje del repositorio y entorno local de un comando

**Objetivo.** Que en una máquina limpia, un solo comando levante el stack completo y las pruebas
pasen, sin adivinar nada y sin una sola credencial externa.

**Qué entra.** La estructura del monorepo con `apps/` y `packages/` tal como la fija el ADR-0001,
con pnpm para JavaScript y uv para Python. El `docker-compose.yml` en `infra/local/` con nombre de
proyecto explícito —para que un arranque aquí no recree la base de datos de otro repositorio de la
casa, que ya ha pasado— levantando API, PostgreSQL con PostGIS, Redis, worker y web. El `Makefile`
de la raíz con los comandos de un solo golpe. La **migración inicial**, que activa las extensiones
`postgis`, `btree_gist` y `pgcrypto` y crea la primera tabla **ya con seguridad a nivel de fila**. El
`.env.example` con todas las variables documentadas una a una y su inventario. El README de arranque
en pasos numerados. Y el corredor de pruebas configurado de modo que **falle si no hay base de datos
en vez de saltárselas en silencio**, que es un fallo conocido en la casa.

**Quién lo construye.** `agenda-devops` lleva el entorno local, el Compose y el Makefile.
`agenda-backend` escribe la migración inicial y el esqueleto de la API. `agenda-testing` monta el
corredor de pruebas y la prueba que verifica que ninguna tabla con datos de negocio se queda sin
política de aislamiento. `agenda-arquitecto` revisa que la estructura es la del ADR-0001.

**De qué depende.** De nada. Es el primer sprint.

**Hecho cuando.** En una máquina donde el repositorio se acaba de clonar: `make arriba` deja los
cinco servicios en marcha y responde el chequeo de salud de la API; `make migrar` corre contra una
base vacía sin ningún paso manual; `make pruebas` pasa; y al parar la base de datos y volver a lanzar
las pruebas, **fallan con un mensaje que dice que falta Postgres** en lugar de dar verde. El README
se sigue de arriba abajo sin preguntar nada a nadie.

---

### Sprint 2 · Modelo de datos completo y contrato de la API

**Objetivo.** Que el esquema de las fases 0 a 2 exista entero, con los huecos que las fases
posteriores van a necesitar, y que el contrato de la API esté publicado y sea consumible.

**Qué entra.** El modelo del §7 del brief, materializado en migraciones: identidad y sesiones,
negocio con su ubicación y su horario, equipo y horarios de profesional, catálogo de servicios con
duración, precio y buffers, fichas de cliente, reservas con sus estados y sus eventos, opiniones,
taxonomía de zonas y atributos administrables. La tabla de ocupación con la **restricción de
exclusión** del ADR-0004, que es lo que hace imposible la doble reserva. Las tablas de **planes y
suscripciones** del ADR-0010, vacías de lógica pero presentes en el esquema, porque el motor es la
Fase 3 y el modelo es ahora. Los huecos declarados para lo que es v2: multi-sede, recursos físicos,
profesional en varios negocios, depósitos, cobro al cliente final y el rol de recepción. El
**seed** con un barrio real de Ciudad de Panamá, negocios verosímiles, horarios distintos entre sí y
la agenda medio llena, generado con fechas relativas a hoy para que nunca aparezca vacío. Y el
contrato: `/api/v1` con el OpenAPI generado desde el código y los tipos de TypeScript derivados de
él.

**Quién lo construye.** `agenda-arquitecto` escribe el documento del modelo de datos y el del motor
de disponibilidad, que es donde se fijan los casos límite. `agenda-ingenieria-software` traduce eso
en los diagramas de secuencia del ciclo de una reserva y en la lista de requisitos por endpoint.
`agenda-backend` escribe las migraciones y el seed. `agenda-testing` escribe **la prueba de
aislamiento cruzado**: fijado el negocio A, ninguna consulta a ninguna tabla devuelve una fila de B.
`agenda-seguridad-compliance` revisa el modelo contra la Ley 81 y decide, tabla por tabla, qué se
borra y qué se anonimiza cuando alguien pide borrar su cuenta. `agenda-qa-validador` cierra.

**De qué depende.** Del Sprint 1, porque las migraciones necesitan el entorno.

**Hecho cuando.** Las migraciones corren de cero contra un PostgreSQL real y dejan el esquema
completo; el seed se puede cargar dos veces seguidas y el resultado es el mismo; la prueba de
aislamiento cruzado está en verde y **falla si se le quita a mano la política a una tabla**; el
OpenAPI se descarga del servidor y `make contrato` regenera los tipos sin diferencias; y hay una
prueba que compara el contrato con el confirmado y falla si alguien lo cambia sin querer.

---

### Sprint 3 · Design system y flujos navegables

**Objetivo.** Que Luis pueda recorrer con el dedo, en un móvil, cómo se va a ver y cómo se va a usar
el producto **antes** de que exista una sola pantalla conectada al backend.

**Qué entra.** El paquete de tokens como fuente única: un archivo del que salen las variables de la
web y el módulo que después usará la aplicación, con la paleta definida por función y no por tono,
los cinco estados de una reserva con su color estable en todas las superficies, la tipografía IBM
Plex Sans con cifras tabulares para que las columnas de horas se alineen, el objetivo táctil de 44
píxeles y el cuerpo de texto de 16 píxeles mínimo. Modo claro por defecto, con el modo oscuro
preparado en los tokens pero sin construir. Y los mockups navegables de los cuatro recorridos que
deciden el producto: **dar de alta un negocio y dejarlo operativo**, **la agenda de un día y de una
semana**, **reservar en tres pantallas después de elegir servicio**, y **la ficha de un cliente**.
Todos los textos externalizados desde el primer componente, aunque solo haya español.

**Quién lo construye.** `agenda-mockuper` va por delante y hace los recorridos navegables.
`agenda-frontend-web` monta el paquete de tokens y los componentes base que consumen los mockups.
`agenda-arquitecto` fija los flujos y comprueba que se respeta el límite de tres pantallas.
`agenda-qa-validador` valida contra los vetos estéticos explícitos del encargo y contra el contraste.

**De qué depende.** Del Sprint 1 para tener dónde vivir. Puede ir **en paralelo** con el Sprint 2:
no comparten archivos.

**Hecho cuando.** Los cuatro recorridos se pueden hacer enteros en un navegador **a 390 píxeles de
ancho**, con capturas de cada paso; el alta de negocio se cronometra y cabe en menos de diez minutos
haciéndola por primera vez; ningún color, medida o tamaño de letra aparece escrito suelto fuera de
los tokens; el contraste cumple el nivel AA, **también en los colores de estado**; y no hay ni una
cadena de texto escrita directamente en un componente.

---

### 🚪 Puerta de la Fase 0 — la aprueba Luis

Se le presenta: el documento del modelo de datos, el del motor de disponibilidad con la lista de
casos límite, el contrato de la API, y los cuatro recorridos navegables con sus capturas a 390
píxeles. **No se empieza la Fase 1 sin ese visto bueno.** Es el criterio del brief y no lo sustituye
la opinión del equipo.

---

## 4. Fase 1 · El núcleo

**Qué entrega la fase.** Identidad, alta de negocio, catálogo de servicios, equipo, agenda, motor de
disponibilidad, reservas manuales, notificaciones y ficha de cliente.

**Está hecha cuando un salón real puede operar su agenda entera desde un teléfono.** Ese es el
criterio; «los endpoints responden» no lo es.

---

### Sprint 4 · Las pruebas del motor de disponibilidad, antes que el motor

**Objetivo.** Que exista la especificación ejecutable del motor y que esté **en rojo**. Este sprint
no escribe motor: escribe lo que el motor tendrá que cumplir.

**Qué entra.** Las pruebas de los casos que el encargo enumera, que son precisamente los que rompen
este tipo de motor, más los que se deducen de los ADR:

- Dos clientes confirmando **el mismo hueco a la vez**, con dos transacciones simultáneas contra un
  PostgreSQL real, no simuladas. Una gana y la otra recibe un error claro.
- Un buffer posterior que **cruza el final de la jornada**: la última cita del día no cabe aunque el
  servicio sí quepa.
- Un profesional con **horario distinto del negocio**, que es el caso normal y no la excepción.
- **Cambiar el horario del negocio cuando ya hay reservas dentro** del tramo que se elimina.
- Un servicio **más largo que el hueco** que queda antes del cierre.
- Una reserva **multi-servicio encadenada**: tres servicios seguidos con el mismo profesional exigen
  un bloque continuo, no tres huecos sueltos donde otra cita pueda colarse en medio.
- **Bloqueos recurrentes** —el almuerzo de todos los días— frente a bloqueos puntuales, y el caso en
  que se solapan.
- Un negocio que **cierra pasada la medianoche** y la aritmética que eso implica.
- La antelación mínima de una hora y la máxima de sesenta días, en el borde exacto.
- Guardado en tiempo universal con la zona en el negocio: la misma prueba, ejecutada con el reloj de
  la máquina en otra zona, da el mismo resultado.

**Quién lo construye.** `agenda-testing` escribe las pruebas. `agenda-ingenieria-software` redacta
antes la especificación de cada caso en lenguaje llano, con el resultado esperado, para que la prueba
no sea la única definición de la regla. `agenda-arquitecto` confirma que la lista cubre lo que dice
el documento del motor.

**De qué depende.** De la puerta de la Fase 0, y del esquema del Sprint 2 para poder insertar datos.

**Hecho cuando.** `make pruebas` ejecuta la lista completa, **todas fallan por falta de
implementación y ninguna por un error de infraestructura**, y la salida se lee de arriba abajo y se
entiende qué se está exigiendo sin abrir el código. El corredor ejecuta con el reloj del proceso
fijado en tiempo universal, para que un despiste de zona horaria no pase desapercibido.

---

### Sprint 5 · El motor de disponibilidad

**Objetivo.** Poner en verde todo lo del sprint anterior. Nada más, y nada menos.

**Qué entra.** El cálculo de huecos libres —horario del negocio intersecado con el del profesional,
menos bloqueos, menos reservas, menos buffers—, con granularidad configurable por negocio y valor por
defecto de quince minutos. La conversión entre reglas horarias locales e instantes **en un único
sitio**, que es este: ninguna otra capa hace aritmética de husos. La creación de reservas apoyada en
la restricción de exclusión de la base de datos, con la violación traducida a un error de dominio con
mensaje entendible —«ese horario se acaba de ocupar»— y no reintentada en silencio. La reserva
encadenada de varios servicios como un único bloque continuo de ocupación. Los bloqueos de tiempo,
puntuales y recurrentes, viviendo en la misma tabla de ocupación que las reservas, porque si el
almuerzo vive aparte la base de datos no puede impedir que le encajen una cita encima. Y los feriados
de Panamá precargados como sugerencia, nunca impuestos.

**Quién lo construye.** `agenda-backend` escribe el motor. `agenda-testing` acompaña y añade los
casos que aparezcan al implementar. `agenda-qa-validador` revisa que no se haya relajado ninguna
prueba para ponerla en verde, que es la forma habitual de que este sprint mienta.

**De qué depende.** Del Sprint 4 por completo.

**Hecho cuando.** Todas las pruebas del Sprint 4 están en verde contra PostgreSQL real, **incluida la
de concurrencia**, y el intento perdedor devuelve el error de hueco ocupado. El cálculo de
disponibilidad de un día completo sobre el conjunto de datos de ejemplo responde por debajo de los
300 milisegundos en el percentil 95, medido y anotado. Y se puede demostrar que quitando la
restricción de la base de datos la prueba de concurrencia falla: eso es lo que prueba que la garantía
la da la base y no un `if`.

---

### 🚪 Puerta del motor — se para y se enseña

**Aquí el equipo se detiene.** Se le enseña a Luis el motor funcionando: la lista de casos cubiertos,
las pruebas en verde por pantalla, la medición de tiempo de respuesta y una demostración de las dos
reservas simultáneas sobre el mismo hueco. **No se construye ni una pantalla encima hasta ese visto
bueno.** Es una exigencia explícita del encargo, y la razón es sencilla: si el motor está mal, todo
lo que se apoye en él hay que rehacerlo.

---

### Sprint 6 · Identidad y alta de negocio

**Objetivo.** Que cualquiera se registre desde el móvil y deje un negocio publicado sin que nadie de
M2G intervenga y sin dar una tarjeta.

**Qué entra.** Registro e inicio de sesión por teléfono con código de un solo uso, guardado con hash
y con límites por teléfono y por dirección de red; el correo como alternativa; y el acceso con Google
y con Apple. El alta de negocio autoservicio completa: datos básicos, categorías, ubicación con el
punto en el mapa, horario semanal, tipo de negocio y primer servicio. Una misma cuenta puede ser
cliente y tener papel en varios negocios, con el cambio a «modo negocio» explícito. La invitación de
profesionales por WhatsApp o correo, y la posibilidad de crear un profesional «sin cuenta» y
convertirlo después. Los estados del negocio —borrador, publicado, suspendido— con el mínimo para
publicar: un servicio activo, horario, ubicación y una foto. La lista de progreso del perfil. Y,
porque sin esto Apple rechaza la aplicación después y porque lo exige la ley panameña, el
**consentimiento explícito y el borrado de cuenta desde dentro del producto**, construidos ahora y no
al final.

**Quién lo construye.** `agenda-backend` la identidad y el alta. `agenda-frontend-web` las pantallas,
sobre los mockups del Sprint 3. `agenda-mockuper` ajusta lo que el uso real desmienta.
`agenda-seguridad-compliance` revisa los límites del código de un solo uso, el enlace de cuentas
sociales —enlazar por un correo no verificado es un secuestro de cuenta— y todo el circuito de
consentimiento y borrado. `agenda-testing` cubre el ciclo de sesión, incluida la revocación.

**De qué depende.** De la puerta del motor. La subida de fotos usa el almacenamiento local del
Compose; la credencial real es una pregunta abierta y no bloquea.

**Hecho cuando.** Una persona que no ha visto el producto, con un teléfono a 390 píxeles, se registra
y deja un negocio publicado **en menos de diez minutos cronometrados**, sin ayuda y sin tarjeta. El
código de verificación se lee del proveedor de desarrollo, y **queda anotado en el tablero que el
canal real de WhatsApp está sin verificar**. Cerrar la sesión en un dispositivo la invalida de
inmediato, y borrar la cuenta hace desaparecer lo que tiene que desaparecer y anonimiza lo que tiene
que quedarse.

---

### Sprint 7 · Catálogo de servicios y equipo

**Objetivo.** Que el negocio configure lo que vende y quién lo hace, y que el motor lo refleje al
instante.

**Qué entra.** Servicios con nombre, categoría global, descripción, duración, precio —fijo, «desde» o
a consultar—, buffer antes y después, foto, orden y estado. Variantes con su propia duración y su
propio precio, en lista simple. Asignación de servicios a profesionales. Categorías globales
administradas por M2G, para que los filtros del marketplace sean consistentes entre negocios. Ficha
del profesional con foto, biografía, servicios, horario propio, descansos, días libres y vacaciones.
Activo o inactivo, y visible u oculto de cara al público. Los permisos de verdad: el dueño lo ve
todo; el profesional ve su agenda y sus clientes y **no** ve las finanzas ni la configuración. Y la
reserva «con cualquier profesional disponible», repartiendo carga en vez de mandarlo todo al primero
de la lista.

**Quién lo construye.** `agenda-backend` el catálogo, el equipo y la resolución de permisos.
`agenda-frontend-web` las pantallas de configuración, pensadas para el pulgar.
`agenda-seguridad-compliance` verifica que el profesional no llega a nada que no le toca, ni por la
interfaz ni llamando a la API directamente. `agenda-testing` cubre el reparto de carga y los
permisos.

**De qué depende.** Del Sprint 6.

**Hecho cuando.** El salón del conjunto de ejemplo se reconfigura entero desde el móvil: se añade un
servicio, se cambia la duración de otro, se le cambia el horario a un profesional y **los huecos que
ofrece la agenda cambian en consecuencia en la misma pantalla**. Un profesional inicia sesión y no
encuentra por ningún camino la configuración del negocio ni sus números, y una llamada directa a la
API con su sesión devuelve un error de permiso, no datos.

---

### Sprint 8 · Agenda y reservas manuales

**Objetivo.** Que el dueño lleve el día entero desde el teléfono: lo que hoy hace con un cuaderno.

**Qué entra.** Vista de día y de semana por profesional, pensada primero para la pantalla estrecha.
Reserva manual para quien entra por la puerta o llama por teléfono, con un cliente ya registrado o
con un «cliente rápido» del que solo se tiene el nombre y el teléfono. Mover y reprogramar, con
arrastre en la web y con una alternativa cómoda en móvil, porque arrastrar con el pulgar en una
agenda apretada no funciona. Bloqueos puntuales y recurrentes. El ciclo completo de estados de una
reserva —pendiente, confirmada, completada, no presentada, cancelada por el cliente y cancelada por
el negocio— con la reprogramación registrada **como un evento y no como un estado final**, y la
autoconfirmación activada por defecto y desactivable. La marca de no presentado con su contador por
cliente y la posibilidad de bloquear a quien reincide. Las notas del cliente. El historial, el
«reservar de nuevo» en un toque y la descarga de la cita para el calendario del móvil.

**Quién lo construye.** `agenda-backend` el ciclo de la reserva sobre el motor.
`agenda-frontend-web` la agenda, que es la pantalla más usada del producto y merece el trabajo.
`agenda-mockuper` resuelve el gesto de mover una cita en pantalla estrecha antes de que se
implemente. `agenda-testing` cubre las transiciones de estado, incluidas las que no deben poder
ocurrir. `agenda-qa-validador` valida a 390 píxeles.

**De qué depende.** De los sprints 5 y 7.

**Hecho cuando.** Con un teléfono y el conjunto de datos de ejemplo: se crea una reserva de alguien
que entra sin cita, se mueve a otra hora, se cancela, y se marca a otro cliente como no presentado;
todo sin salir del móvil y con capturas de cada paso. Intentar encajar un servicio de tres horas en
un hueco de dos **falla con un mensaje que un peluquero entiende**, no con un error técnico. Y el
historial de una reserva enseña quién hizo qué y cuándo, reprogramaciones incluidas.

---

### Sprint 9 · Notificaciones y ficha de cliente

**Objetivo.** Que el cliente reciba lo que tiene que recibir, una sola vez, y que el negocio sepa a
quién tiene delante.

**Qué entra.** La cola de notificaciones con clave de idempotencia derivada del hecho y no del
momento: encolar dos veces el mismo recordatorio es un conflicto que no inserta, no un segundo
mensaje. Los eventos de la Fase 1: reserva creada, confirmada, cancelada y reprogramada, recordatorio
a veinticuatro horas y a dos horas, invitación a un profesional y petición de opinión después de la
cita. La separación entre decidir —mirar las preferencias del usuario y del negocio y elegir canal— y
entregar —hablar con el proveedor—, de modo que apagar un canal sea configuración. Las plantillas
como datos, con su idioma, para que cambiar un texto no sea un despliegue. El registro de entregas,
que es lo que permite responder a «¿le llegó el recordatorio?», que va a ser la primera pregunta de
soporte. El trabajo periódico que **encola y no envía**, para que ejecutarlo dos veces no duplique
nada. El enlace para escribir por WhatsApp al negocio resuelto **en el servidor**, de forma que el
número no viaje nunca en el listado. Y la ficha de cliente por negocio: historial, notas, contador de
ausencias y preferencias.

**Quién lo construye.** `agenda-backend` la cola y los proveedores. `agenda-devops` el proceso de
trabajos en el Compose local. `agenda-testing` la prueba que ejecuta el planificador dos veces
seguidas y comprueba que sale un solo mensaje. `agenda-seguridad-compliance` verifica que ningún
teléfono aparece en una respuesta pública ni en un registro. `agenda-frontend-web` la ficha de
cliente y las preferencias de aviso.

**De qué depende.** Del Sprint 8.

**Hecho cuando.** Ejecutar el planificador dos veces seguidas produce **un** mensaje, no dos, y se
puede enseñar la fila de la cola que lo demuestra. Un recordatorio cuya cita ya pasó se marca como
descartado en vez de reintentarse para siempre. El registro de entregas contesta, para una reserva
concreta, qué se intentó mandar, por qué canal y con qué resultado. En el código fuente de cualquier
página pública y en cualquier respuesta de la API sin autorizar **no aparece ningún número de
teléfono**. Y el proveedor real de WhatsApp queda anotado como no verificado, con su dueño y su
fecha.

---

### 🚪 Puerta de la Fase 1 — un salón opera su agenda desde el móvil

Se enseña el recorrido completo con capturas en escritorio y a 390 píxeles: registrar un negocio,
publicarlo, configurar servicios y equipo, llevar un día entero de agenda con reservas manuales,
mover, cancelar y marcar una ausencia, y ver la ficha de un cliente. Con los datos del conjunto de
ejemplo, que se parecen a los de un salón de verdad. `agenda-qa-validador` valida antes de enseñar;
Luis decide si está hecha.

---

## 5. Fase 2 · El marketplace

**Qué entrega la fase.** Perfiles indexables, búsqueda, filtros, mapa, reserva por parte del cliente,
opiniones, favoritos y ranking orgánico.

**Está hecha cuando un cliente encuentra un negocio y reserva sin que nadie le ayude, y Google indexa
los perfiles.**

---

### Sprint 10 · Zonas, geografía y perfiles indexables

**Objetivo.** Que la página de un negocio exista en internet, se lea sin ejecutar JavaScript y Google
la pueda indexar.

**Qué entra.** La taxonomía de zonas jerárquica y administrable —provincia, distrito, corregimiento,
barrio— con su dirección amigable, y la zona del negocio resuelta al guardar la ubicación pero
**editable por el dueño**, porque en Panamá los límites administrativos no coinciden con lo que la
gente llama su barrio. La ubicación como punto geográfico con su índice, que es lo que después
permite ordenar por cercanía. El perfil público completo: nombre, descripción, categorías, portada y
galería, dirección, horario semanal, redes, servicios con precio y duración, equipo y el botón de
reservar siempre visible. La dirección amigable del perfil, pensada para la biografía de Instagram, y
su código QR descargable. Los atributos filtrables como catálogo administrable y no escritos en el
código. Y el trabajo de posicionamiento: renderizado en servidor con revalidación, metadatos, datos
estructurados de negocio local y mapa del sitio generado **solo con las combinaciones que tienen
negocios publicados**, porque miles de páginas vacías son contenido de baja calidad y penalizan.

**Quién lo construye.** `agenda-backend` las zonas, la geografía y los datos del perfil.
`agenda-frontend-web` las páginas renderizadas en servidor y el presupuesto de peso.
`agenda-seguridad-compliance` verifica que el teléfono no está en el código fuente de la página y que
la política de seguridad de contenidos no rompe nada, comprobándolo **en el navegador y no con
`curl`**, que es como se ha colado ese fallo otras veces en la casa. `agenda-testing` cubre la
generación del mapa del sitio.

**De qué depende.** De la puerta de la Fase 1.

**Hecho cuando.** Al pedir la página de un negocio y mirar el código fuente **sin ejecutar
JavaScript**, ahí están el nombre, los servicios, los precios y el horario. La medición de Lighthouse
en móvil da 90 o más. El mapa del sitio contiene los perfiles publicados y las combinaciones de
categoría y barrio que tienen negocios, y ninguna más. Los datos estructurados pasan el validador de
Google. Y no aparece ningún teléfono en el código fuente.

---

### Sprint 11 · Búsqueda, filtros y mapa

**Objetivo.** Que alguien encuentre lo que busca cerca de donde está, rápido y con 3G.

**Qué entra.** La portada con búsqueda por texto, por categoría y por ubicación —posición del móvil,
dirección escrita o barrio—, con resultados en lista y en mapa. Los filtros: distancia, categoría,
servicio, precio, valoración, atributos, abierto ahora, métodos de pago y **disponibilidad real**,
que es el que de verdad importa y el que obliga a que la búsqueda y el motor de la Fase 1 den la
misma respuesta. El registro de impresiones y clics por negocio, agregado por día y no evento a
evento, porque cinco mil negocios en portada generan mucho ruido y lo que se necesita es la serie. Y
los límites de petición que protegen la base de negocios de que alguien la copie entera en una tarde.

**Quién lo construye.** `agenda-backend` la consulta geográfica y los filtros.
`agenda-frontend-web` la portada, la lista y el mapa. `agenda-testing` la prueba de que el filtro de
disponibilidad coincide con lo que la agenda enseña. `agenda-devops` deja en el conjunto de datos de
ejemplo el volumen necesario para poder medir de verdad.

**De qué depende.** Del Sprint 10.

**Hecho cuando.** Con cinco mil negocios sembrados, buscar «barbería cerca» con la ubicación del
móvil devuelve resultados ordenados por cercanía **por debajo de 500 milisegundos en el percentil
95**, medido y anotado. El filtro «con hueco hoy» devuelve exactamente los negocios que tienen hueco
según el motor, comprobado cruzando ambas respuestas. Y repetir la misma búsqueda muchas veces
seguidas desde la misma dirección de red acaba encontrando el límite de peticiones.

---

### Sprint 12 · Ranking orgánico y valoración bayesiana

**Objetivo.** Que el orden de los resultados sea justo, ajustable sin desplegar y explicable.

**Qué entra.** La puntuación única por negocio y búsqueda, suma ponderada de señales normalizadas:
cercanía, valoración ponderada, reservas recientes con techo para que un negocio grande no lo domine
todo, tasa de citas efectivamente atendidas, completitud del perfil y actividad reciente. El
**impulso temporal para los negocios nuevos**, sin el cual el marketplace nace cerrado para los que
llegan, que el primer día son todos. Los pesos, el radio, las ventanas y la duración del impulso
viviendo en una tabla con fecha de vigencia: **ningún número de ranking en el código**. El precálculo
periódico de las señales caras, que es lo que permite cumplir el tiempo de respuesta. La valoración
agregada con media bayesiana, sembrada con una media global razonable mientras no haya opiniones. El
desglose de por qué salió cada resultado, consultable, porque la primera llamada de un dueño enfadado
va a ser «¿por qué salgo el noveno?». Y el mecanismo de intercalado de resultados patrocinados —dos
de cada diez, etiquetados, insertados y nunca sustituyendo a un orgánico—, construido ahora con el
inventario vacío, porque la publicidad de pago es la Fase 4 pero la regla es de aquí.

**Quién lo construye.** `agenda-backend` la fórmula, el precálculo y el intercalado.
`agenda-arquitecto` fija los valores iniciales de los pesos y de la media global.
`agenda-testing` cubre la bayesiana y el intercalado. `agenda-frontend-web` marca visualmente lo
patrocinado de forma inequívoca.

**De qué depende.** Del Sprint 11.

**Hecho cuando.** Cambiar un peso en la tabla y volver a buscar **reordena los resultados sin tocar
código ni reiniciar nada**. Un negocio recién publicado aparece en la primera página de su barrio por
efecto del impulso, y deja de hacerlo cuando el impulso caduca. Un negocio con una sola opinión de
cinco estrellas **no adelanta** a otro con ochenta de cuatro coma siete. Y para un resultado
cualquiera se puede leer cuánto aportó cada señal.

---

### Sprint 13 · La reserva por parte del cliente, de punta a punta

**Objetivo.** Que alguien que llega de una búsqueda de Google acabe con una cita confirmada, solo.

**Qué entra.** El recorrido completo: negocio, servicio o servicios, profesional o «cualquiera»,
fecha y hora, y confirmar, **en un máximo de tres pantallas después de elegir el servicio**. El
registro del cliente por teléfono verificado dentro del propio flujo, porque reservar como invitado
está descartado y el teléfono verificado es lo único que sostiene el control de ausencias sin pedir
depósito. La reserva de varios servicios encadenados con el mismo profesional. La política de
cancelación **visible antes de reservar**, que es requisito legal, y la cancelación o el cambio por
parte del cliente hasta el plazo configurado, con dos horas como valor de partida. El historial del
cliente, el «reservar de nuevo» en un toque y la descarga para el calendario. Y la clave de
idempotencia en la creación de la reserva, porque un móvil con 3G reintenta solo y un reintento no
puede crear dos citas.

**Quién lo construye.** `agenda-frontend-web` el recorrido, que es la pantalla que decide si el
producto funciona. `agenda-backend` la creación de reserva desde el lado del cliente y la
idempotencia. `agenda-mockuper` afina el paso de elección de hora, que es donde se abandona.
`agenda-testing` cubre el reintento y el borde exacto de la ventana de cancelación.
`agenda-qa-validador` valida con alguien ajeno al equipo.

**De qué depende.** De los sprints 10 y 12, y del motor de la Fase 1.

**Hecho cuando.** Una persona de fuera del equipo, con su propio teléfono y sin instrucciones,
encuentra un negocio y sale con una cita confirmada; se cronometra y se cuentan las pantallas, que no
pasan de tres tras elegir servicio. Enviar dos veces la misma confirmación con la misma clave crea
**una** cita. Cancelar dentro del plazo funciona y fuera del plazo se explica por qué no, con el
plazo dicho antes de reservar y no después.

---

### Sprint 14 · Opiniones y favoritos

**Objetivo.** Cerrar el círculo: la reputación que alimenta el ranking y el gesto de volver.

**Qué entra.** La opinión solo sobre una cita **efectivamente completada**, una por cita y dentro de
la ventana configurada, con catorce días como valor de partida. Valoración de una a cinco estrellas,
texto y fotos, al negocio y opcionalmente al profesional. La respuesta pública del negocio, una por
opinión. El circuito de denuncia, con la cola de moderación preparada aunque el panel interno sea de
la Fase 3. La petición automática de opinión después de la cita, apoyada en la cola idempotente. La
valoración agregada bayesiana ya conectada al ranking. Los favoritos, el enlace para compartir un
perfil y el «reservar de nuevo». Y la política de opiniones publicada, porque el brief la exige.

**Quién lo construye.** `agenda-backend` las opiniones, las respuestas y las denuncias.
`agenda-frontend-web` las pantallas y la ficha pública con su valoración.
`agenda-seguridad-compliance` revisa la moderación de fotos y los datos personales que puede arrastrar
una opinión. `agenda-testing` cubre la ventana y la unicidad.

**De qué depende.** De los sprints 12 y 13.

**Hecho cuando.** Solo se puede opinar sobre una cita completada y solo una vez, y pasados los
catorce días el botón desaparece. El negocio responde una vez y no dos. Publicar una opinión mueve la
valoración agregada **como manda la fórmula bayesiana** y no como una media simple. Y una opinión
denunciada entra en la cola de moderación sin desaparecer del sitio por sí sola.

---

### 🚪 Puerta de la Fase 2 — un cliente reserva solo y Google indexa

Se enseña, con capturas en escritorio y a 390 píxeles: la búsqueda con posición real, el perfil
indexable con su código fuente a la vista, la reserva completa hecha por alguien de fuera del equipo,
la cancelación, la opinión y el efecto en la valoración. Más las mediciones de tiempo de búsqueda, de
tiempo de disponibilidad y de Lighthouse.

---

## 6. Lo que viene después, en un párrafo cada una

**Fase 3 · Back-office, planes y facturación.** El panel interno de M2G: cuadro de mando, gestión y
suspensión de negocios, moderación, taxonomías, pesos del ranking, plantillas de mensaje,
interruptores de funciones, papeles internos, auditoría y exportaciones. Y el motor de suscripciones
completo con el plan gratuito a precio cero como único plan activo, con su ciclo ejecutándose de
verdad para que el camino esté probado antes de que haya dinero. Está hecha cuando M2G cambia un
precio y una taxonomía **sin desplegar código**, y el cambio se refleja en el negocio siguiente.

**Fase 4 · Publicidad y pasarela.** La compra de posicionamiento: el negocio elige categoría, barrio
y periodo, ve el precio, el inventario disponible y una vista previa, y paga. Inventario limitado,
recibo, renovación opcional con aviso y métricas de impresiones, clics y reservas atribuidas frente
al orgánico. Aquí entra la pasarela real, que es una decisión pendiente de Luis, y **ningún cobro se
enciende sin su permiso explícito**. Está hecha cuando un negocio compra un destacado, paga y aparece
etiquetado como patrocinado sin desplazar a ningún orgánico.

**Fase 5 · La aplicación.** Modo cliente y modo negocio sobre una única base de código, avisos al
móvil, enlaces profundos, tolerancia a red inestable con la agenda del día en caché y estados
optimistas, y la publicación en las dos tiendas con las cuentas de M2G. Depende de credenciales que
tardan semanas en conseguirse, así que se piden mucho antes. Está hecha cuando las dos tiendas la
aprueban.

**Fase 6 · Crecimiento.** Lo que el brief aparta a propósito y el modelo de datos deja preparado:
depósito contra las ausencias, sincronización con Google Calendar, varias sedes por negocio, inglés,
lista de espera, reservas recurrentes, recursos físicos, paquetes y promociones, el papel de
recepción, y España como segundo país. Se prioriza con datos de uso, no antes.

---

## 7. Riesgos del plan

> Qué puede descarrilar cada fase y qué se hace al respecto. No son riesgos de producto —esos están
> en el §12 del brief— sino riesgos de **ejecución de este plan**.

| Fase | Qué puede descarrilarla | Señal temprana | Qué se hace |
|---|---|---|---|
| 0 | El modelo de datos se queda corto y hay que migrar con datos dentro | Aparece una tabla nueva «que faltaba» en el Sprint 6 o después | Se deja el hueco de las funciones v2 en el Sprint 2, cuando una columna no cuesta nada; y toda migración se prueba contra PostgreSQL real antes de darla por buena |
| 0 | El aislamiento entre negocios se cuela a medias y se descubre tarde | Una tabla nueva sin política de fila | Prueba automática que recorre el catálogo y falla si aparece una tabla con datos de negocio sin política. Es criterio de rechazo, no un aviso |
| 0 | El design system se convierte en una discusión estética sin fin | Tres versiones del mismo botón y ninguna aprobada | Los tokens los cierra el arquitecto y los recorridos los aprueba Luis en la puerta de fase; después, el diseño se ajusta dentro de los tokens, no se rediscute |
| 1 | **El motor de disponibilidad falla y ya hay pantallas encima** | Se empieza a construir interfaz antes de la puerta del motor | La puerta del motor es explícita y bloqueante. Las pruebas se escriben antes que el código para que el fallo salga en el Sprint 4 y no en el 8 |
| 1 | Las pruebas se relajan para ponerlas en verde | Una prueba cambia de expectativa en el mismo commit que la implementa | QA revisa el historial de las pruebas del motor, no solo su resultado. Cambiar una expectativa exige justificación escrita |
| 1 | La credencial de WhatsApp no llega y el criterio de fase depende de ella | Sigue abierta al empezar el Sprint 6 | Se construye todo con el proveedor de desarrollo y **se pide la credencial el primer día del proyecto**, porque la verificación de empresa y la aprobación de plantillas tardan semanas |
| 1 | La agenda funciona en el escritorio y no en el móvil | Se valida con capturas de escritorio | Todo criterio de «hecho» de interfaz se comprueba **a 390 píxeles**; el mockup del gesto de mover una cita va antes de implementarlo |
| 2 | El posicionamiento en buscadores no funciona y se descubre al final | Se valida el perfil mirando el navegador con JavaScript activado | Se comprueba el código fuente sin JavaScript desde el primer día del Sprint 10, y se mide Lighthouse en cada entrega, no al cerrar la fase |
| 2 | La búsqueda no cumple el tiempo de respuesta con volumen real | Se mide sobre veinte negocios de ejemplo | El conjunto de datos de ejemplo llega a cinco mil negocios en el Sprint 11 y la medición es parte del criterio de «hecho», con el número anotado |
| 2 | El ranking se vuelve inexplicable y nadie se atreve a tocarlo | Los pesos acaban repartidos entre la consulta y el código | Ningún número de ranking en el código, todo en tabla con fecha de vigencia, y el desglose de cada resultado consultable |
| 2 | La reserva se diseña para quien ya conoce el producto | Se prueba siempre con gente del equipo | El criterio de «hecho» exige **una persona de fuera**, sin instrucciones y con su propio teléfono |
| Todas | Dos agentes tocan los mismos archivos y se pisan | Conflictos al integrar | Solo se paraleliza lo que no colisiona; el orquestador lleva el registro de lo que está en vuelo y el tablero lo escribe él durante un lote |
| Todas | Deuda que solo existe en la conversación | «Eso lo dejamos para luego» sin ninguna línea escrita | Nada pendiente solo en prosa: todo va al tablero con su estado y su dueño en la misma sesión |
| Todas | Se da por bueno lo que no se ha probado | «El build está verde» como evidencia | Verificación en vivo con capturas; y el corredor de pruebas falla si no hay base de datos en vez de saltárselas en silencio |
