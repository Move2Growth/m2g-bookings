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
| `DATABASE_URL_TRABAJOS` | Conexión de los trabajos en segundo plano, con el rol auditado `agenda_admin`. El planificador necesita **enumerar** negocios antes de saber en cuál trabajar, y sin tenant fijado el rol de la API no ve ninguno; el trabajo concreto sí corre con el negocio fijado | secreto | `.env` / SOPS |
| `AGENDA_BUZON_NOTIFICACIONES` | Archivo donde el proveedor de desarrollo escribe los mensajes (OTP, recordatorios) mientras no hay canal real | variable | `.env` |
| `SECRET_KEY` | Firma de los tokens de acceso. Rotarla invalida todas las sesiones | secreto | `.env` / SOPS |
| `ENTORNO` | `local` \| `staging` \| `produccion`. Decide qué implementación de proveedor se usa | variable | `.env` |
| `ZONA_HORARIA_DEFECTO` | Zona IANA que se propone al dar de alta un negocio. Default `America/Panama` (ADR-0003) | variable | `.env` |
| `MONEDA_DEFECTO` | Código de moneda de los importes. Default `USD`; el símbolo que se pinta es `$` (D12) | variable | `.env` |
| `URL_PUBLICA_WEB` | Base de las URL absolutas del sitemap, los enlaces de las notificaciones y los enlaces profundos | variable | `.env` |
| `URL_BASE_MEDIA` | Prefijo de las URL de fotos de negocio y de reseña. **Vacía por defecto**: entonces la clave guardada se sirve tal cual, que hoy es una ruta de la web (`/fotos/spa.webp`) o una URL absoluta. Cuando exista almacenamiento de objetos se rellena aquí y no se toca ni una fila | variable | `.env` |
| `ACCESO_ADMIN_MINUTOS` | Duración del token de acceso de la consola interna. Más corta que la de un cliente a propósito (default 30) | variable | `.env` |
| `REFRESCO_ADMIN_HORAS` | Duración del refresco de la consola interna (default 8) | variable | `.env` |
| `CONSOLA_EMAIL_INICIAL` | Correo de la **primera cuenta** de la consola, que crea `python -m agenda.consola_alta`. Sin valor en el repositorio | variable | `.env` |
| `CONSOLA_PASSWORD_INICIAL` | Contraseña de esa primera cuenta. Si se deja vacía, el comando **genera una al azar y la enseña una sola vez** junto con la URI `otpauth://` del segundo factor. Ni la contraseña ni el secreto del 2FA se vuelven a mostrar | secreto | `.env` / Bitwarden |

### Mensajería y notificaciones

| Nombre | Para qué | Tipo | Dónde se define |
|---|---|---|---|
| `WHATSAPP_TOKEN` | Token de Meta WhatsApp Cloud API: OTP de acceso y notificaciones (NTF-1). **No existe todavía** | secreto | SOPS |
| `WHATSAPP_PHONE_ID` | Identificador del número emisor en Meta | secreto | SOPS |
| `WHATSAPP_WEBHOOK_TOKEN` | Verificación del webhook de estados de entrega de Meta | secreto | SOPS |
| `SMS_API_KEY` | Proveedor de SMS, **solo como respaldo del OTP** (D14). Vigilar coste: es el vector clásico de fraude por tarificación | secreto | SOPS |
| `EMAIL_API_KEY` | Correo transaccional: respaldo de notificaciones e invitaciones de equipo | secreto | SOPS |
| `PUSH_CREDENCIALES` | Credenciales de FCM y APNs para las notificaciones de la app (Fase 5) | secreto | SOPS |

### Mapas, almacenamiento y pagos

| Nombre | Para qué | Tipo | Dónde se define |
|---|---|---|---|
| `MAPAS_TOKEN` | Token del proveedor de mapas y geocoding. **D8: Mapbox por defecto, pendiente de confirmar por coste.** Con el geocoding cacheado por texto normalizado (ADR-0005) | secreto | SOPS |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Almacenamiento compatible con S3 para fotos de negocio, servicios y reviews | secreto | SOPS |
| `PASARELA_API_KEY` | Credencial de la pasarela de pago. **D5 sin decidir**: la elige Luis. Solo se guarda el **token** del método de pago, jamás datos de tarjeta (PAY-3) | secreto | SOPS |
| `PASARELA_WEBHOOK_SECRET` | Verificación de los webhooks de cobro | secreto | SOPS |

### Observabilidad

| Nombre | Para qué | Tipo | Dónde se define |
|---|---|---|---|
| `SENTRY_DSN` | Errores de API, worker y web | secreto | SOPS |
| `NIVEL_LOG` | Verbosidad de los registros. Los registros **no llevan teléfonos, correos ni datos de tarjeta** | variable | `.env` |

> Cuando un agente añade una variable o secreto, **añade una fila aquí y la entrada correspondiente en `.env.example`** antes de cerrar la tarea. Nombre y propósito, **nunca el valor**. Y antes de commitear se escanea el diff **en español y en inglés** (`contraseña` y `password`).
