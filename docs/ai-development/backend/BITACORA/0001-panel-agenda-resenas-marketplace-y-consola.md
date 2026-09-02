# 0001 · El panel del salón, la agenda del profesional, las reseñas, los filtros y la consola

- **Agente:** Backend · **Tareas:** BE-T006, BE-T007, BE-T011, BE-T014 (parcial), BE-T017, BE-T019, BE-T020 (parcial) y el back-office ADM-1 a ADM-6 · **Fecha:** 2026-09-02
- **Estado al cerrar:** hecha (pendiente de QA)

## Qué hice

La API pasa de **23 endpoints a 81 operaciones sobre 65 rutas**. Lo que había era el camino
mínimo —crear un negocio, crear un servicio, crear un profesional, poner horario y agendar—; lo
que faltaba era todo lo que un salón hace **después del primer día**: cambiar un precio, dar de
baja a alguien, cerrar por vacaciones, editar su ficha y mirar a sus clientes.

En seis bloques:

1. **Panel del salón.** Listar, editar y retirar servicios con sus variantes; listar, editar y
   dar de baja profesionales, con qué servicios hace cada uno y su horario propio; leer el
   horario del negocio y sus ajustes; ausencias y cierres puntuales; feriados sugeridos; la
   ficha pública editable con categorías, atributos, pin y fotos; y la lista de clientes con su
   historial, sus notas y el bloqueo del reincidente.
2. **Agenda del profesional.** `GET /mi/agenda` y, sobre todo, **la migración 0006**: un
   profesional ve y gestiona su agenda y nada más, y lo impide PostgreSQL, no un `if`.
3. **Reseñas** enteras: dejar una (solo con cita completada, una por reserva, dentro de la
   ventana del negocio), leerlas en el perfil con el agregado bayesiano, la respuesta única del
   salón y el reporte a moderación.
4. **Favoritos**, perfil de la persona y **«reservar de nuevo»**.
5. **Filtros reales del marketplace**: precio, rating, disponibilidad real («ahora», «hoy»,
   una fecha), abierto ahora y cinco criterios de orden; y la tarjeta con foto de portada,
   rating, número de reseñas, categorías y la próxima hora libre.
6. **La consola interna de M2G**, con su propio login con segundo factor, su propio rol de base
   de datos y su propia tabla de cuentas.

## Decisiones tomadas

**La agenda del profesional se resuelve con políticas RESTRICTIVAS, no permisivas.** Es el
detalle que decide si esto funciona o solo lo parece: en PostgreSQL las políticas normales se
suman con `OR`, así que añadir una nunca quita acceso. Para *recortar* lo que ya concede la
política de tenant hace falta `AS RESTRICTIVE`, que se combina con `AND`. Escritas como
permisivas se habrían creado, aplicado, no fallado y **no restringido nada**.

**Aparece `app.current_staff_id`**, hermano de `app.current_business_id` y de
`app.current_user_id`. La dependencia de sesión lo declara a partir del rol del token, y todas
las políticas nuevas tienen la misma forma: `app_profesional_actual() IS NULL OR <condición>`.
El `IS NULL` deja intactos al dueño y a los trabajos en segundo plano.

**Además de la política, el filtro de aplicación** (ADR-0002). Los endpoints que escriben
configuración llaman a `exigir_dueno`. No es redundancia decorativa: sin él, la política deja
leer y bloquea el `UPDATE`, el `UPDATE` no toca ninguna fila, el ORM lanza `StaleDataError` y
el usuario ve un **500 en vez de un «no tienes permiso»**. Se descubrió probando en vivo. Por
si algún endpoint futuro se olvida, hay además dos traductores globales en `main.py`: `42501`
(«permiso insuficiente») y `StaleDataError` salen como `NO_AUTORIZADO` con 403.

**El teléfono sigue sin salir nunca.** El perfil público devuelve `tiene_whatsapp: true|false`,
nunca el número, y `GET /publico/negocios/{slug}/chat` **resuelve el salto en servidor**:
apunta el clic agregado por día y responde con la redirección a `wa.me`. Verificado con `curl`:
el cuerpo de la respuesta no contiene el número.

**El nombre completo de quien reseña tampoco.** Se sirve «Abdiel H.». El rol del marketplace
**no tiene permiso sobre `users`** y eso se mantiene: para los nombres se abre una segunda
sesión con el rol de la aplicación y se leen solo el identificador y el nombre.

**Reportar una reseña exige sesión.** El documento de contratos preveía
`POST /publico/reviews/{id}/reporte`, y no se ha hecho así: el rol público es de solo lectura
por diseño y reportar sin identificarse es regalar una herramienta para tumbar a un competidor
con un guion. Queda en `/mi/reviews/{id}/reportar` y `/negocio/reviews/{id}/reportar`.

**El filtro de disponibilidad usa el motor de reservas, no una copia.** Es el filtro más caro
del producto —varias consultas de agenda por negocio— así que se aplica al final, sobre los
candidatos ya ordenados, y se recorre hasta llenar la página con un techo de 40 agendas por
petición. La sonda es **el servicio activo más corto** de cada salón: si el más corto no cabe,
no cabe ninguno.

**`proxima_hora` es opcional y se pide.** Ponerlo siempre convertiría la portada en la pantalla
más cara del producto. Viene relleno cuando se filtra por disponibilidad —ahí ya está
calculado— y cuando se pide con `con_proxima_hora=true`.

**El segundo factor de la consola está escrito con la biblioteca estándar** en vez de traer una
dependencia más. No se inventa criptografía: TOTP es HMAC-SHA1 con el truncamiento que el RFC
6238 especifica byte a byte, y la prueba lo contrasta con **los vectores publicados en el
propio RFC**.

**Los bloqueos recurrentes con vigencia (`time_block_rules`) no se han expuesto.** El descanso
recurrente —el almuerzo de todos los días— ya funciona como `staff_hours` de clase `descanso`,
que es lo que el motor lee. `time_block_rules` necesita un trabajo que materialice las reglas
en ocupación y **ese trabajo no existe todavía**: exponerlo sin él daría reglas que no bloquean
nada. Queda anotado como deuda.

## Archivos / recursos creados o tocados

**Migraciones** (zona serializada, nadie más las tocó):
- `apps/api/migraciones/versions/20260902_0006_agenda_del_profesional.py` — `app_profesional_actual()` y 60 políticas restrictivas.
- `apps/api/migraciones/versions/20260902_0007_resenas_y_ficha_publica.py` — horario y fotos de reseña públicos, lectura de reseñas publicadas para el rol de la aplicación, índice parcial de reseñas.

**Endpoints nuevos** en `apps/api/agenda/api/`: `negocio_catalogo.py`, `negocio_equipo.py`,
`negocio_agenda.py`, `negocio_ficha.py`, `negocio_clientes.py`, `profesional.py`, `resenas.py`,
`favoritos.py`, `consola.py`, `comunes.py`.

**Servicios**: `agenda/servicios/resenas.py`, `tarjetas.py`, `pesos.py`, `consola.py`;
`agenda/dominio/totp.py`; `agenda/contrato.py`; `agenda/consola_alta.py`.

**Tocados**: `agenda/main.py` (routers y dos traductores de error), `agenda/api/dependencias.py`
(`app.current_staff_id`, sesiones de consola), `agenda/bd.py` (motor de consola y contexto del
marketplace), `agenda/ajustes.py`, `agenda/errores.py`, `agenda/api/publico.py`,
`agenda/api/negocio.py`, `agenda/api/onboarding.py`, `agenda/servicios/busqueda.py`,
`agenda/semilla.py`.

**Contrato**: `packages/api-types/openapi.json` y `tipos.ts` regenerados (65 rutas, 81
operaciones, 84 esquemas).

**Documentación**: `.env.example` y `docs/operacion/SECRETOS-Y-VARIABLES.md` con
`DATABASE_URL_ADMIN`, `URL_BASE_MEDIA`, `ACCESO_ADMIN_MINUTOS`, `REFRESCO_ADMIN_HORAS`,
`CONSOLA_EMAIL_INICIAL` y `CONSOLA_PASSWORD_INICIAL`. **Ningún valor, solo el nombre y para qué.**

## Cómo verificar que funciona

```bash
cd apps/api
./.venv/bin/ruff check agenda/ && ./.venv/bin/ruff format --check agenda/
AGENDA_DATABASE_URL="postgresql+asyncpg://agenda_owner:agenda@127.0.0.1:5433/agenda_pruebas" \
  ./.venv/bin/python -m pytest        # 161 pruebas (eran 107)
```

Y **en vivo**, que es donde salieron los cuatro fallos que las pruebas no habrían visto:

```bash
DATABASE_URL_MIGRACIONES="postgresql+psycopg://agenda_owner:agenda@127.0.0.1:5433/agenda" \
  ./.venv/bin/python -m alembic upgrade head
DATABASE_URL_MIGRACIONES="postgresql+psycopg://agenda_owner:agenda@127.0.0.1:5433/agenda" \
  ./.venv/bin/python -m agenda.semilla
CONSOLA_EMAIL_INICIAL=admin@m2g.dev DATABASE_URL_MIGRACIONES="postgresql+psycopg://agenda_owner:agenda@127.0.0.1:5433/agenda" \
  ./.venv/bin/python -m agenda.consola_alta      # imprime la contraseña y el QR UNA vez

curl -s 'http://localhost:8000/api/v1/publico/buscar?disponibilidad=hoy&con_proxima_hora=true'
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  'http://localhost:8000/api/v1/publico/negocios/spa-costa-del-este/chat'
```

Lo comprobado a mano, con datos reales del seed: el dueño entra, cambia un precio, bloquea dos
días de vacaciones, sube una foto y ve sus clientes; el profesional entra y ve **cuatro citas,
todas suyas**, y recibe `403 NO_AUTORIZADO` al intentar tocar un servicio; la clienta reseña su
cita completada, la segunda reseña sale `409 YA_EXISTE`, el perfil público enseña **4,36
bayesiano frente a 5,00 de media simple**; y la consola entra con 2FA, suspende un negocio —que
desaparece del marketplace y **conserva sus 24 citas**—, lo reactiva, cambia un peso del ranking
creando la versión 2 y exporta el CSV.

## Pendiente o bloqueado

1. **`AGENDA_DATABASE_URL` no la lee nadie.** El comando de pruebas del encargo la fija, pero
   `Ajustes` no tiene `env_prefix`, así que el motor global de `agenda.bd` usa el valor por
   defecto —la base de **desarrollo**—. No importaba mientras ninguna prueba tocara ese motor;
   ahora el filtro de disponibilidad sí lo toca, y se ha resuelto con una fixture que lo
   redirige. **Hay que decidir el nombre bueno de la variable** en vez de arrastrar dos.
2. **Los feriados de Panamá siguen sin datos.** `GET /negocio/feriados` funciona y devuelve una
   lista vacía porque la tabla está vacía; es la deuda ya anotada del Arquitecto.
3. **`time_block_rules` sin materializador**: el bloqueo recurrente con vigencia no se expone.
4. **No hay subida de archivos.** `POST /negocio/fotos` recibe una **clave**, no un fichero:
   sin almacenamiento de objetos decidido (S3 no está en el compose ni tiene credenciales), un
   endpoint de subida sería mentir. Hoy la clave es una ruta servible o una URL absoluta.
5. **El secreto TOTP se guarda sin cifrar en reposo.** El modelo lo anota como «cifrado en
   reposo» y **no lo está**: cifrarlo sin un gestor de claves de verdad sería teatro.
6. **Impersonar (ADM-2) no se ha construido**: sin caducidad corta, aviso al negocio y
   auditoría de las tres cosas a la vez, no se hace (ADR-0006).

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **La API la reinicié dos veces** con el mismo comando
  (`./.venv/bin/python -m uvicorn agenda.main:app --host 127.0.0.1 --port 8000`) porque no
  corre con `--reload` y había que verificar los arreglos en vivo. Está levantada y sirviendo.
- **La base de desarrollo estaba dos migraciones por detrás.** Ya está en `head`, y el seed
  recargado: ahora los salones tienen `published_at`, dos tienen portada, hay plan Gratis, hay
  pesos de ranking vigentes y **el primer profesional de cada salón tiene cuenta** (teléfonos
  `+50762000001`…`+50762000011`) para poder probar la agenda del profesional.
- **Lo que no hay que hacer:** exponer `time_block_rules` sin escribir antes el trabajo que las
  materializa en `staff_occupancy`; y añadir una política nueva sobre la agenda del profesional
  **sin `AS RESTRICTIVE`**, porque no restringiría nada y no fallaría nada.
- **El fichero clave** para entender el bloque 2 es
  `migraciones/versions/20260902_0006_agenda_del_profesional.py`: ahí está escrito por qué cada
  tabla cae en «su agenda», «solo lectura» o «ni existe».
