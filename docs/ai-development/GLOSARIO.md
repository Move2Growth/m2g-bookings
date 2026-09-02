# GLOSARIO — el vocabulario de Bukeo

> Dos bloques: los términos del **método** (estables, iguales en todos los proyectos de la casa) y los términos **de este producto**. El vocabulario del producto **no se negocia**: la misma palabra en el modelo de datos, en la API, en la pantalla y en la conversación. La versión corta está en [`../../context/restricciones.md`](../../context/restricciones.md) §1; esto es el diccionario completo.

## Términos del método (estables)

| Término | Qué significa |
|---|---|
| **Agente** | Una instancia de IA (Claude Code) con un rol fijo, sus tareas y su memoria en archivos. |
| **Bitácora** | El registro incremental de un agente: un `.md` por tarea terminada. Su memoria a largo plazo. |
| **ESTADO-GLOBAL** | El tablero compartido con el estado de todo el equipo. El primer sitio que mira cualquiera. |
| **Hecha frente a validada** | «Hecha» = el agente cree que terminó. «Validada» = QA lo confirmó contra los criterios. Solo lo validado cuenta. |
| **Definición de hecho** | La lista de condiciones objetivas que una entrega debe cumplir para considerarse terminada. |
| **ADR** | Ficha de una decisión de arquitectura, en [`../arquitectura/adr/`](../arquitectura/adr/). **Las decididas no se editan**: se escribe otra que la supera. |
| **Constitution** | Los principios que ningún agente rompe, en [`../arquitectura/constitution.md`](../arquitectura/constitution.md), con las **ocho garantías** del producto. |
| **Garantía** | Una invariante que, si se rompiera, invalidaría el producto. QA la trata como criterio de rechazo, no como recomendación. |
| **Fase** | Bloque de trabajo del brief (§9), del 0 al 6. Este encargo cubre las fases 0, 1 y 2. |
| **Zona** | El directorio o módulo «caliente» que una tarea toca; el orquestador la usa para detectar colisiones sin abrir el código. |
| **Zona serializada** | Zona en la que **nunca** trabajan dos agentes a la vez, ni con worktree, porque el merge no puede ser trivial: migraciones, motor de disponibilidad, tokens, ADR y el propio tablero. |
| **Worktree** | Copia de trabajo de git aislada (`.claude/worktrees/<nombre>`) para que dos agentes no se pisen trabajando en paralelo. |
| **Orquestador** | El rol transversal que detecta tareas independientes y las paraleliza en worktrees, mergeando con seguridad. No construye ni valida. |
| **Lote en vuelo** | Conjunto de tareas que el orquestador corre en paralelo ahora mismo. |
| **Invalidation trigger** | La condición que hace **caducar** una decisión técnica de un rol. Cada `AGENTE.md` lleva las suyas: una decisión sin fecha de caducidad se arrastra en silencio. |
| **Handoff** | El traspaso entre agentes o sesiones. Bien hecho, quien llega retoma **sin preguntar nada**. |
| **KB (base de conocimiento)** | El conocimiento común a todos los proyectos (skills, agentes base, convenciones), referenciado con `--add-dir`. |
| **INDEX de la KB** | El índice ligero de la KB, siempre en contexto; dice qué skill cargar y cuándo. |

## Términos del producto

### El negocio y su gente

| Término | Qué significa |
|---|---|
| **Negocio** | La unidad de tenencia y la pieza central del modelo: un salón, una barbería, un spa o un profesional independiente. Todo dato de agenda cuelga de un negocio. **No se dice «tienda», ni «local», ni «cuenta».** |
| **Profesional** | Quien presta el servicio y **tiene agenda propia**. Puede no tener cuenta: el dueño lo crea «sin cuenta» y lo convierte después (ONB-4). **No se dice «empleado» ni «recurso»** — los recursos físicos son otra cosa y son v2. |
| **Dueño** | El rol que manda en un negocio: servicios, equipo, agenda, publicidad y facturación. En la base es un valor del rol de la membresía (`dueno`), no un usuario distinto. |
| **Membresía** | La fila que une a un **usuario** con un **negocio** y le da un rol. El permiso no es de la persona: es del par usuario–negocio, y por eso alguien puede ser dueño de un salón y profesional en otro. |
| **Negocio activo** | El negocio en el que estás trabajando ahora mismo. Va en el token de sesión, es lo que alimenta el aislamiento por filas, y **cambiarlo es intercambiar el token**, no pasar un parámetro. Lo que el usuario ve como «modo negocio». |
| **Cliente** | Quien reserva. Es de la plataforma, **no de un salón**: su cuenta no se aísla por negocio. Lo que sí es del negocio es su **ficha**. |
| **Ficha de cliente** | Lo que un negocio sabe de un cliente suyo: historial, notas, contador de ausencias. Vive dentro del negocio y **no se comparte con otro** aunque sea la misma persona. |
| **Cliente rápido** | El cliente que el negocio apunta a mano en el mostrador o por teléfono, sin cuenta en la plataforma. Sirve para reservar; no puede entrar a la aplicación. |
| **Equipo M2G** | Quienes operan la plataforma desde el back-office. Viven en una tabla aparte, con su propio inicio de sesión y **2FA obligatorio**. Un superadministrador **no** es un usuario con una casilla marcada. |

### La agenda

| Término | Qué significa |
|---|---|
| **Servicio** | Lo que se reserva: nombre, categoría, duración, precio y **buffers**. **No se dice «producto» ni «tratamiento».** |
| **Variante** | Una versión del servicio con su propia duración y precio — «corte de caballero» frente a «corte de niño». Lista simple en v1; combinar opciones es v2. |
| **Reserva** | La cita de un cliente con un profesional para uno o más servicios. **No se dice «booking» ni «turno».** |
| **Slot** | Un hueco reservable, del tamaño de la **granularidad** del negocio. **No se dice «franja» ni «hora».** Un slot libre es: horario del negocio ∩ horario del profesional − bloqueos − reservas − buffers. |
| **Granularidad** | Cada cuánto empieza un slot en ese negocio. Configurable, **15 minutos por defecto**: con granularidad de 15 los huecos salen a y cuarto, y media, y menos cuarto y en punto. |
| **Buffer** | El tiempo muerto **antes y después** de un servicio, para preparar o recoger. Es parte del servicio, no del calendario, y **cuenta como ocupado**: el rango que bloquea una reserva incluye sus buffers, y por eso dos citas pegadas no pueden violar el buffer aunque el hueco parezca libre. |
| **Bloqueo** | Tiempo que el profesional marca como no reservable sin que haya cita: el almuerzo, una vacación, un recado. **Puntual** (una vez) o **recurrente** (cada día, cada martes). Vive en la **misma tabla de ocupación** que las reservas: si viviera aparte, la base de datos no podría impedir que le encajaran una cita encima. |
| **Antelación mínima** | Con cuánto tiempo hay que reservar antes de la hora de la cita. **Una hora por defecto**, configurable: sin esto, alguien reserva a las 10:58 para las 11:00 y el salón se entera cuando ya llegó. |
| **Antelación máxima** | Hasta cuándo se puede reservar hacia adelante. **Sesenta días por defecto**, configurable: evita agendas llenas de citas que nadie recuerda. |
| **Multi-servicio encadenado** | Tres servicios seguidos con **el mismo profesional**, que necesitan un **bloque continuo** y no tres huecos sueltos. Es una sola fila de ocupación, no tres. Con profesionales distintos es v2. |
| **Reprogramación** | Mover una reserva a otra hora. **Es un evento del historial, no un estado final**: la reserva sigue viva y se sabe dónde estaba antes. |
| **No-show** | El cliente no apareció. **Lo marca el negocio**, cuenta para el contador del cliente y puede acabar bloqueando a un reincidente. Sin depósito, es lo único que sostiene el problema. |

### El marketplace

| Término | Qué significa |
|---|---|
| **Marketplace** | La parte pública: buscar, comparar y reservar sin conocer al negocio de antes. La otra mitad del producto; la agenda vale aunque esté vacío, pero el negocio de M2G vive aquí. |
| **Zona** | Un nivel de la taxonomía geográfica: provincia → distrito → corregimiento → barrio. Es una **entidad con nombre y URL estable**, no un radio. **No se dice «área» ni «región».** La zona de un negocio **la puede corregir su dueño**: en Panamá el límite del corregimiento no coincide con lo que la gente llama su barrio. |
| **Categoría × zona** | La página pública que cruza un tipo de servicio con una zona — «barberías en San Francisco» —. Es de donde llega la mitad del tráfico, y **solo se genera si hay negocios publicados**: mil páginas vacías son contenido de baja calidad. |
| **Slug** | El trozo legible de la URL de un negocio. Estable: si cambia, se pierde el posicionamiento y los enlaces que ya circulan. |
| **SSR** | Renderizado en servidor: el servidor devuelve el HTML **ya con el contenido dentro**, en vez de una página vacía que se rellena con JavaScript. Sin esto Google no indexa fiablemente los perfiles, **y sin indexación no hay marketplace**. Es la razón de que la web pública sea Next y no Vite. |
| **Ranking** | El orden de los resultados. Es **una fórmula con pesos guardados en base de datos** —distancia, rating, reservas recientes, tasa de completado, completitud, actividad y boost de nuevo—, ajustable desde el back-office. **No hay ni un número de ranking escrito en el código.** |
| **Rating bayesiano** | La nota agregada que se calcula con `(C·m + Σ notas) / (C + n)`, donde `m` es la media global de la plataforma y `C` un número de reviews de confianza. Traducido: **una sola review de 5 estrellas no adelanta a un negocio con ochenta de 4,7**; con pocas opiniones te pareces a la media y solo con volumen te separas de ella. **Se dice «rating bayesiano», no «media de estrellas».** |
| **Boost de nuevo** | El impulso temporal y decreciente que recibe un negocio recién llegado. Sin él **el marketplace nace bloqueado** para quien entra, que el primer día son todos. |
| **Completitud del perfil** | Cuánto le falta al negocio: fotos, descripción, servicios, horario, atributos. Entra en el ranking porque **es la palanca que el negocio sí controla**. |
| **Patrocinado** | Un resultado pagado. Va **intercalado y etiquetado «Patrocinado»**, como mucho 2 de cada 10, **nunca oculta a un orgánico** —se inserta, no sustituye— y **no toca el rating ni las reviews. Jamás.** **No se dice «destacado» ni «premium».** |
| **Orgánico** | El resultado que sale por la fórmula, sin pagar. |
| **Click-to-chat** | El botón que abre WhatsApp con el negocio. **Se resuelve en el servidor**, que registra el clic y redirige: el número **nunca viaja** en el listado, o alguien raspa la base entera de negocios en una tarde. |

### Cómo está hecho por dentro

| Término | Qué significa |
|---|---|
| **Multi-tenant** | Que muchos negocios comparten la misma base de datos sin verse entre ellos. **Tenant = negocio.** Está desde la primera migración porque meterlo después toca todas las consultas: es lo más caro que se puede dejar para luego. |
| **RLS (aislamiento por filas)** | *Row Level Security*: la propia base de datos filtra las filas por el negocio activo de la sesión, de modo que **ni un `SELECT *` sin `WHERE` se lleva datos ajenos**. Es la red, no la excusa: el filtro en el código **también se escribe**, porque sin él los índices no se usan igual. |
| **Restricción de exclusión** | La regla de PostgreSQL que hace **imposible** que dos reservas del mismo profesional se solapen, buffers incluidos. Es lo que convierte «no hay doble reserva» en una garantía transaccional y no en un `if` que alguien puede olvidar. |
| **OTP** | El código de seis dígitos que verifica un teléfono. Se guarda **con hash**, caduca en cinco minutos y tiene límite de intentos: es el vector clásico de fraude por tarificación. |
| **Idempotencia** | Que repetir la misma operación **no duplica su efecto**. Aplica a los recordatorios —«un recordatorio duplicado a las siete de la mañana es una queja»—, a los cobros y a crear una reserva desde un móvil con 3G que reintenta solo. |
| **Cola de notificaciones** | La tabla `notifications`, que **es** la cola. Cada aviso lleva una clave derivada del hecho (`recordatorio_24h:booking:{id}`), única: encolarlo dos veces no inserta nada. |
| **Superficie** | Cada una de las tres aplicaciones que consumen la misma API: **W1** web pública con SSR (marketplace, reserva y panel de negocio), **W2** back-office del equipo M2G, **A1** app Expo (Fase 5). |
| **Panel de negocio** | La parte de la web donde el dueño y el profesional gestionan lo suyo. Vive **dentro de la web pública**, no en una aplicación aparte, porque a menudo son la misma persona que también es cliente. |
| **Back-office** | La herramienta interna de M2G: configuración, moderación, planes, publicidad y métricas. **Es de cuenta interna y no se indexa.** No confundir con el panel de negocio. |
| **Plan y suscripción** | El plan es el precio y los límites; la suscripción es lo que un negocio tiene contratado. **Todo negocio tiene una desde que se registra, aunque valga 0**: el día que el precio pase a un dólar, el camino ya se recorrió miles de veces. |
| **Seed** | Los datos de ejemplo que carga el entorno local. **No es un accesorio: es material de prueba.** Un barrio real, horarios distintos entre profesionales y **la agenda medio llena**, con precios de verdad — «Corte + barba · 45 min · $18». **Nunca «Servicio 1 · 100,00»**: con datos de mentira no se ve que una reserva de tres horas no cabe en el hueco de las cinco. |
| **Ley 81** | La ley panameña de protección de datos de 2019: consentimiento, derechos del titular, política de privacidad, retención y **borrado de cuenta desde dentro de la aplicación**. Sin eso, Apple rechaza la publicación. |
