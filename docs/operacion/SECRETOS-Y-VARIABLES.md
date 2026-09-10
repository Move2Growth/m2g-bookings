# SECRETOS Y VARIABLES — inventario único

> **Regla del proyecto** (memoria "documentar secretos y .env"): **todo secreto o variable de entorno nuevo se documenta aquí Y en su `.env.example` en la misma sesión** en que se introduce. Se anota **el nombre y para qué sirve, NUNCA el valor**. Los valores reales viven cifrados (SOPS/age u el gestor que use el proyecto) y/o en el `.env` local (no commiteado, copiado a los worktrees vía `.worktreeinclude`).

## Variables del método (las trae la plantilla)

| Nombre | Para qué | Dónde se define |
|---|---|---|
| `KB_DIR` | Ruta a la **knowledge-base** centralizada en esta máquina; cada sesión se lanza con `claude --add-dir "$KB_DIR"`. Es **por máquina** (no se commitea una ruta absoluta). | `.env` local / perfil del shell / `CLAUDE.local.md` |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | `=1` para que se cargue el `INDEX.md`/`CLAUDE.md` de los directorios `--add-dir` (la KB). | `.claude/settings.json` |

> **Nota — arranque acotado de contexto.** No existe variable **nativa** de Claude Code para limitar los caracteres del `SessionStart`. `ECC_SESSION_START_MAX_CHARS` pertenecía a herramientas de terceros (tipo ECC) que Claude Code **no honra**, por eso se retiró. El mecanismo nativo y real es: `CLAUDE.md` corto (<200 líneas, importando `context/` con `@`), la KB con lazy-load vía `INDEX.md`, y `model: opusplan` en `settings.json`.

## Variables del dashboard

| Nombre | Para qué | Dónde se define |
|---|---|---|
| `AGENT_HUB_DIR` | (opcional) Carpeta del estado del dashboard; por defecto `~/.agent-hub`. La leen el hook `agent-status.sh` y la app `agent-hub-dashboard`. | perfil del shell / `.env` |

## Secretos y variables del proyecto

> Estado a 1 sep 2026: las de infraestructura local están definidas; las de servicios externos **aún no existen** y su ausencia está anotada como bloqueo en el tablero. Ninguna hace falta para levantar el entorno local: todo servicio externo tiene implementación de desarrollo (ADR-0005, ADR-0007, ADR-0010).

### Base de datos, caché y aplicación

| Nombre | Para qué | Tipo | Dónde se define |
|---|---|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL 16 con PostGIS. El usuario de la aplicación **no es dueño de las tablas y no tiene `BYPASSRLS`** (ADR-0002) | variable | `.env` |
| `DATABASE_URL_MIGRACIONES` | Conexión con el rol dueño, usada **solo** por Alembic para migrar y crear extensiones | secreto | `.env` |
| `REDIS_URL` | Caché de horarios y transporte de los trabajos de arq (ADR-0008) | variable | `.env` |
| `DATABASE_URL_ADMIN` | Conexión de la **consola interna** con el rol `agenda_admin`. Es una tercera conexión y no un `SET ROLE`: con una sola, un fallo de autorización en un endpoint del panel correría con los permisos del equipo interno. El rol tampoco tiene `BYPASSRLS`: accede por políticas propias | secreto | `.env` / SOPS |
| `DATABASE_URL_PUBLICO` | Conexión del **marketplace** con el rol `agenda_publico`, que solo lee y **solo lo que tiene política de publicable**. Cuarta conexión por lo mismo que la anterior: un endpoint público que compartiera conexión con el panel tendría sus permisos | secreto | `.env` / SOPS |
| `ORIGENES_PERMITIDOS` | Los orígenes que pueden llamar a la API desde un navegador, separados por comas. **Explícitos y nunca `*`**: con credenciales, un comodín regala las sesiones de todo el mundo. `localhost` y `127.0.0.1` no son el mismo origen para el navegador, y faltando uno la pantalla carga pero ninguna petición sale | variable | `.env` |
| `GRANULARIDAD_MINUTOS` · `ANTELACION_MINIMA_HORAS` · `ANTELACION_MAXIMA_DIAS` · `VENTANA_CANCELACION_HORAS` · `VENTANA_REVIEW_DIAS` | Los valores por defecto de negocio que el brief deja configurables. **Cada salón guarda los suyos**: esto es solo la semilla con la que nace uno nuevo, y se cambian desde el back-office sin desplegar | variable | `.env` |
| `DATABASE_URL_TRABAJOS` | Conexión de los trabajos en segundo plano, con el rol auditado `agenda_admin`. El planificador necesita **enumerar** negocios antes de saber en cuál trabajar, y sin tenant fijado el rol de la API no ve ninguno; el trabajo concreto sí corre con el negocio fijado | secreto | `.env` / SOPS |
| `AGENDA_BUZON_NOTIFICACIONES` | Archivo donde el proveedor de desarrollo escribe los mensajes (OTP, recordatorios) mientras no hay canal real | variable | `.env` |
| `SECRET_KEY` | Firma de los tokens de acceso. Rotarla invalida todas las sesiones | secreto | `.env` / SOPS |
| `ENTORNO` | `local` \| `staging` \| `produccion`. Decide qué implementación de proveedor se usa | variable | `.env` |
| `ZONA_HORARIA_DEFECTO` | Zona IANA que se propone al dar de alta un negocio. Default `America/Panama` (ADR-0003) | variable | `.env` |
| `MONEDA_DEFECTO` | Código de moneda de los importes. Default `USD`; el símbolo que se pinta es `$` (D12) | variable | `.env` |
| `URL_PUBLICA_WEB` | Base de las URL absolutas del sitemap, los enlaces de las notificaciones y los enlaces profundos | variable | `.env` |
| `URL_BASE_MEDIA` | Prefijo de las URL de fotos de negocio y de reseña. En local apunta al MinIO del `docker-compose`. Una clave que ya empieza por `/` o por `http` se sirve tal cual, así que las fotos de la semilla siguen funcionando sin tocar una fila | variable | `.env` |
| `ACCESO_ADMIN_MINUTOS` | Duración del token de acceso de la consola interna. Más corta que la de un cliente a propósito (default 30) | variable | `.env` |
| `REFRESCO_ADMIN_HORAS` | Duración del refresco de la consola interna (default 8) | variable | `.env` |
| `CONSOLA_EMAIL_INICIAL` | Correo de la **primera cuenta** de la consola, que crea `python -m agenda.consola_alta`. Sin valor en el repositorio | variable | `.env` |
| `CONSOLA_PASSWORD_INICIAL` | Contraseña de esa primera cuenta. Si se deja vacía, el comando **genera una al azar y la enseña una sola vez** junto con la URI `otpauth://` del segundo factor. Ni la contraseña ni el secreto del 2FA se vuelven a mostrar | secreto | `.env` / Bitwarden |
| `SEMILLA_CONTRASENA` | Contraseña común de las cuentas de ejemplo de `python -m agenda.semilla`. **No es un secreto y no debe tratarse como tal**: la semilla se niega a correr fuera de local y esas cuentas se rehacen en cada carga. Existe para poder cambiarla sin tocar el código | variable | `.env` |
| `NOMBRE_COMERCIAL` | Nombre comercial de la plataforma. Llega a la web como `NEXT_PUBLIC_NOMBRE_COMERCIAL` y es **el único sitio donde se escribe**: cabecera, pie, textos legales y títulos del navegador salen de aquí. Está sin decidir (D1) y `Bukeo` es el codename | variable | `.env` |

### Mensajería y notificaciones

| Nombre | Para qué | Tipo | Dónde se define |
|---|---|---|---|
| `WHATSAPP_TOKEN` | Token de Meta WhatsApp Cloud API: OTP de acceso y notificaciones (NTF-1). **No existe todavía** | secreto | SOPS |
| `WHATSAPP_PHONE_ID` | Identificador del número emisor en Meta | secreto | SOPS |
| `WHATSAPP_WEBHOOK_TOKEN` | Verificación del webhook de estados de entrega de Meta | secreto | SOPS |
| `SMS_API_KEY` | Proveedor de SMS, **solo como respaldo del OTP** (D14). Vigilar coste: es el vector clásico de fraude por tarificación | secreto | SOPS |
| ~~`EMAIL_API_KEY`~~ | **Retirada.** El correo se manda por SMTP (ADR-0024), no contra la API de un proveedor: lo hablan todos, así que la elección es de `SMTP_*` y no de código | — | — |
| `PUSH_CREDENCIALES` | Credenciales de FCM y APNs para las notificaciones de la app (Fase 5) | secreto | SOPS |

### Mapas, almacenamiento y pagos

| Nombre | Para qué | Tipo | Dónde se define |
|---|---|---|---|
| `MAPAS_TOKEN` | Token del proveedor de mapas y geocoding. **D8: Mapbox por defecto, pendiente de confirmar por coste.** Con el geocoding cacheado por texto normalizado (ADR-0005) | secreto | SOPS |
| `S3_ENDPOINT` | Dirección del almacén **que usa la API**: firma los permisos y borra archivos. En local es `http://almacen:9000`, el nombre del servicio dentro de la red de Docker | variable | `.env` |
| `S3_ENDPOINT_PUBLICO` | Dirección del almacén **que usa el navegador**, que sube directo. En local es `http://localhost:9000`. **Son dos y no una**: `almacen:9000` no existe fuera de Docker y `localhost:9000` no existe dentro; con una sola, o no firma la API o no sube el navegador, y el fallo no se parece a su causa. En un entorno publicado las dos son la misma | variable | `.env` |
| `S3_REGION` | La región del cubo. Los almacenes compatibles que no tienen regiones aceptan `us-east-1` | variable | `.env` |
| `S3_BUCKET` | El cubo. En local `m2g-agenda-media-dev`, que crea el propio `docker-compose` con lectura pública | variable | `.env` |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | Las credenciales del almacén. En local abren un MinIO que vive en el portátil: **no son un secreto y no lo pretenden**. En un entorno publicado se generan en la consola del proveedor y **la secreta se enseña una sola vez** | secreto | SOPS |
| `S3_PERMISO_MINUTOS` | Cuánto vale un permiso de subida. Cinco por defecto: lo que tarda alguien en elegir una foto con una conexión mala, y poco para que un permiso filtrado sirva de algo | variable | `.env` |
| `S3_TAMANO_MAXIMO_BYTES` | El tope de una foto. Cinco megas: una foto de móvil sin recortar. El límite viaja **dentro de la firma**, así que lo impone el almacén y no la buena voluntad de quien sube | variable | `.env` |
| `SMTP_HOST`, `SMTP_PUERTO` | El servidor de correo. En local `correo:1025`, el buzón del `docker-compose`, que enseña lo que se manda en `http://localhost:8025` y **no le manda nada a nadie** | variable | `.env` |
| `SMTP_USUARIO`, `SMTP_CONTRASENA` | Credenciales del proveedor. Vacías en local; un relé de la propia red tampoco las pide | secreto | SOPS |
| `SMTP_DESDE` | El remitente. En un entorno publicado tiene que ser una dirección del **dominio verificado, con SPF y DKIM puestos**, o el correo acaba en la carpeta de basura de todo el mundo — que se parece mucho a no llegar | variable | `.env` |
| `SMTP_TLS` | `STARTTLS`. Falso **solo** en local, donde el buzón de desarrollo no cifra. Verdadero en cualquier otro sitio: sin esto el usuario y la contraseña viajan en claro | variable | `.env` |
| `RETENCION_AUDITORIA_MESES` | Cuánto se guarda el rastro de acciones internas antes de que un trabajo diario lo borre. Doce por defecto: cubre una reclamación sin volverse un archivo histórico de la vida privada de nadie (Ley 81 · ADR-0025) | variable | `.env` |
| `RETENCION_FACTURAS_ANOS` | El plazo fiscal. **No lo decide el producto: lo dice la DGI y hay que confirmarlo con la asesoría.** Cinco por defecto, y mientras tanto **nada borra una factura** — hay una prueba que lo fija. Se prefiere guardar de más a tener un problema con Hacienda | variable | `.env` |
| `PASARELA_API_KEY` | Credencial de la pasarela de pago. **D5 sin decidir**: la elige Luis. Solo se guarda el **token** del método de pago, jamás datos de tarjeta (PAY-3) | secreto | SOPS |
| `PASARELA_WEBHOOK_SECRET` | Verificación de los webhooks de cobro | secreto | SOPS |

### Observabilidad

| Nombre | Para qué | Tipo | Dónde se define |
|---|---|---|---|
| `SENTRY_DSN` | Errores de API, worker y web | secreto | SOPS |
| `NIVEL_LOG` | Verbosidad de los registros. Los registros **no llevan teléfonos, correos ni datos de tarjeta** | variable | `.env` |

> Cuando un agente añade una variable o secreto, **añade una fila aquí y la entrada correspondiente en `.env.example`** antes de cerrar la tarea. Nombre y propósito, **nunca el valor**. Y antes de commitear se escanea el diff **en español y en inglés** (`contraseña` y `password`).
