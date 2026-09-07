# 0002 · El portal del dueño, el mapa y las personas del local

- **Agente:** Backend · **Tareas:** BE-T036, BE-T037, BE-T038 y BE-T039 (secciones C, D y E de
  `docs/producto/ESPEC-PROFESIONAL-Y-DUENO.md`) · **Fecha:** 2026-09-07
- **Estado al cerrar:** hecha (pendiente de QA)

## Qué hice

Las tres secciones que me tocaban del encargo del 7 de septiembre: **el portal del dueño**, **el
mapa** y **asignar personas al local**. La API pasa de **65 rutas y 81 operaciones** a **81 rutas
y 101 operaciones**, con **una sola migración** y **dos tablas nuevas**.

Las seis piezas del portal del dueño, una por una:

1. **Todos los calendarios.** `GET /negocio/agenda/columnas` devuelve el día del salón con una
   columna por persona: sus citas —con cliente, servicios e importe— y sus bloqueos. El día se
   recorta **en hora local del negocio**, no en UTC.
2. **Lista de profesionales.** Ya existía; solo se le añadió `fichaje_activo` a cada ficha.
3. **Finanzas.** `GET /negocio/finanzas`, agregado por día, semana o mes sobre citas
   `completada`, con el **importe guardado en la cita** y agrupado en la zona del negocio.
4. **Publicidad flash.** Tabla `business_banners` y su CRUD, más el anuncio vigente colgado de
   la ficha pública.
5. **Fichaje.** `staff_profiles.clock_in_enabled` —apagado por defecto, encendido persona a
   persona— y `staff_clock_events` con entrada, salida y el parte de horas.
6. **Mejor del mes.** `GET /negocio/mejor-del-mes`, ordenable por **importe facturado** o por
   **número de servicios**, y filtrable por categoría de servicio.

**El mapa** es `GET /publico/mapa`: los salones dentro de un rectángulo, con su punto, su nota
bayesiana y su número de reseñas, con tope de resultados y avisando cuando recorta.

**Asignar personas** es invitar por correo con su papel y aceptar la invitación, con la regla de
que un salón no se queda sin dueño por ninguna de las tres puertas que había.

Y **un agujero de seguridad real que apareció por el camino**, contado abajo.

## Decisiones tomadas

**Ni una tabla de agregados para las finanzas.** Un total guardado se desincroniza el primer día
que alguien cancela una cita a mano, y un panel de dinero que miente sin fallar es peor que no
tener panel. Las finanzas y el mejor del mes son consultas; el día que el volumen lo pida, se
precalculan en un trabajo periódico y eso será una decisión con su ADR, no un descuido de hoy.

**El importe es `bookings.total_amount_minor`, la copia congelada al reservar.** Hay prueba, y
se comprobó rompiéndola: sustituyendo el agregado por el precio de hoy del catálogo, la prueba
pasa de 1.800 a 9.900 y falla. Es exactamente el fallo que no se ve hasta que un salón sube la
tarifa y su histórico entero cambia solo.

**Se agrupa `AT TIME ZONE` la zona del negocio, no en UTC.** Panamá está a cinco horas: agrupar
en UTC parte el sábado por la mitad y le manda las cinco últimas horas al domingo. También
comprobado rompiéndolo: con la agrupación en UTC, el periodo empieza a las 19:00 locales en vez
de a medianoche y la prueba falla.

**`business_banners` no es `ad_campaigns`, y no se mezclan.** `ad_campaigns` es el
posicionamiento pagado del marketplace, con su inventario, su factura y su tope de 2 de cada 10
(ADR-0009, ADR-0010). Esto es el salón escribiendo en su propia página: gratis, sin competir con
nadie y sin tocar el ranking. Y **no lleva enlace**: un campo de URL libre en superficie pública
es un redirector abierto y un vector de spam, y no hacía falta para lo que se pidió.

**Un anuncio activo a la vez, y lo impone la base.** Restricción de exclusión sobre el rango de
vigencia, la misma herramienta que la no doble reserva (ADR-0004). Así la ficha pública no tiene
que elegir entre dos y el dueño se entera al guardar, no al mirar.

**La vigencia del anuncio vive en la política de seguridad por fila, no en el serializador.**
Patrón B de ADR-0002 al pie de la letra: activo, dentro de fecha y de un negocio publicado, las
tres cosas juntas. Despublicar un salón apaga su anuncio sin que nadie tenga que acordarse.

**El interruptor del fichaje está dentro de la política de escritura.** No basta con que la
pantalla no ofrezca el botón: si `clock_in_enabled` está apagado, PostgreSQL **rechaza la fila**.
Se probó insertando a mano, sin pasar por el servicio, y se comprobó quitando el `EXISTS` de la
política: la prueba se pone en rojo. El servicio comprueba lo mismo antes, pero solo para que el
mensaje se entienda — un `403` de PostgreSQL no explica de quién depende encenderlo.

**`staff_clock_events` es append-only y no es pública jamás.** `SELECT` e `INSERT` para el rol de
la aplicación y nada más, como `booking_events`: un registro horario que se puede reescribir no
prueba nada, ni a favor del salón ni a favor de quien trabaja allí. Y lleva `REVOKE` explícito
del rol público, porque los privilegios por defecto del entorno conceden `SELECT` a
`agenda_publico` sobre **toda** tabla nueva.

**La puerta de la invitación es `app.current_invite`**, hermano de `app.current_business_id`,
`app.current_user_id` y `app.current_staff_id`. El problema de fondo es real: quien acepta una
invitación **todavía no está dentro de ningún negocio**, así que la política de tenant no le deja
ni ver su propia fila; y no puede estar dentro antes, porque aceptar es lo que le mete. Se
resuelve declarando con qué se pregunta, y lo que se compara es **el hash del token**. La
caducidad y el estado se comprueban **en la política**, no solo en el código: hay prueba que
intenta el `UPDATE` por SQL directo con una invitación vencida y no toca ninguna fila.

**Al aceptar se declara además `app.current_user_id`, y no es cosmético.** PostgreSQL exige que,
tras un `UPDATE`, la fila resultante siga siendo visible para quien la escribió. Al borrar el
token, la política que la dejaba ver deja de aplicar y el `UPDATE` sale con «new row violates
row-level security policy». Con el usuario declarado, quien la ve es `memberships_propias`. Costó
un rato entenderlo y por eso está escrito en el código.

**Una cuenta que ya tiene contraseña exige estar dentro con ella para aceptar.** Un token de
correo no puede dar acceso a una cuenta que ya tiene dueño: quien interceptara el enlace entraría
en la cuenta de otra persona y no solo en el salón. Si la cuenta la creó la propia invitación
—sin contraseña, imposible de usar para entrar— entonces sí se elige la contraseña ahí mismo, y
el correo queda verificado, porque haber recibido el enlace es justamente la prueba.

**El token viaja en el cuerpo y no en la URL**, y las dos rutas de invitación son `POST` aunque
una solo lea. Un secreto en la ruta acaba en el registro de accesos, en el historial del
navegador y en la cabecera `Referer` de la primera imagen que cargue la página.

**La regla del último dueño se cierra por las tres puertas.** Cambiarle el papel, revocarlo y
—la que no era evidente— **darlo de baja del equipo**, que revoca la membresía por detrás. En un
salón de barrio el dueño corta el pelo, así que tiene ficha de equipo: antes de esto, darse de
baja a sí mismo dejaba el salón sin nadie que pudiera invitar a nadie, sin un solo error por el
camino. Comprobado rompiéndolo: sin la comprobación, las dos pruebas caen.

**El mapa recorta por el centro del rectángulo y avisa.** Ordenar por distancia al centro deja
los pines donde está mirando quien mueve el mapa; recortar por identificador dejaría huecos
justo en el sitio que se está viendo. Y cuando recorta lo dice (`truncado`), porque una muestra
silenciosa es peor que un recorte: la pantalla enseñaría quince salones donde hay cuatrocientos.

### 🔴 El agujero que apareció escribiendo la prueba del mapa

Escribí una prueba que decía «el rol del marketplace no tiene permiso sobre las tablas con
teléfonos» — que es lo que afirma el comentario de la migración 0002 y lo que daba por hecho la
bitácora 0001. **Falló.**

`infra/local/init/01-roles.sql` fija `ALTER DEFAULT PRIVILEGES … GRANT SELECT ON TABLES TO
agenda_publico`, así que el rol del marketplace acabó con `SELECT` sobre **las 68 tablas del
esquema**. En las que llevan seguridad por fila no se nota —sin política, cero filas—, pero en
las que **no** la llevan porque no son de ningún negocio, sí. Medido en la base de desarrollo:

```
$ psql -U agenda_publico -d agenda -c "select count(*) from users"
 34
$ ... -c "select full_name, phone_e164, email, left(password_hash,12) from users limit 2"
 Zuleika Rodríguez | +50761230002 | zuleika@demo.pa | $argon2id$v=
```

Teléfonos, correos y hashes de contraseña legibles por el rol público. Lo mismo con
`auth_identities`, `otp_codes`, `sessions`, `admin_users` y `admin_sessions`. Ningún endpoint lo
consultaba —los serializadores son explícitos—, pero la garantía 3 de la constitución no puede
depender de que ningún endpoint futuro escriba la consulta equivocada.

Lo cierra `_cerrar_el_rol_publico()` en la migración 0010, con una regla que cabe en una frase y
por eso se puede vigilar con una prueba: **si una tabla no tiene política para el rol público,
tampoco tiene por qué tener permiso**. La excepción, explícita, es el catálogo global. Después
del barrido, `agenda_publico` lee 30 tablas en vez de 68, y las 221 pruebas siguen en verde.

## Archivos / recursos creados o tocados

**Migración** (zona serializada, nadie más la tocó):
- `apps/api/migraciones/versions/20260907_0010_portal_del_dueno.py` — `revision =
  "0010_portal_del_dueno"`, `down_revision = "0008_acceso_contrasena"`. **Encadenada a la 0008 a
  propósito**: hay otra rama escribiendo la 0009 en paralelo y el reencadenado lo hace el
  director al fusionar.

**Modelos:** `agenda/modelos/dueno.py` (`BusinessBanner`, `StaffClockEvent`);
`agenda/modelos/equipo.py` (+ `clock_in_enabled`); `agenda/modelos/__init__.py`.

**Servicios nuevos:** `agenda/servicios/finanzas.py`, `fichaje.py`, `anuncios.py`, `mapa.py`,
`miembros.py`.

**Endpoints nuevos:** `agenda/api/negocio_dueno.py`, `negocio_miembros.py`, `invitaciones.py`,
`publico_mapa.py`.

**Tocados:** `agenda/main.py` (cuatro routers), `agenda/api/dependencias.py`
(`identidad_si_la_hay`), `agenda/api/publico.py` (el anuncio en la ficha),
`agenda/api/negocio_equipo.py` (`fichaje_activo` y la regla del último dueño en la baja),
`agenda/errores.py` (`SinDueno` → `NEGOCIO_SIN_DUENO`), `agenda/notificaciones/cola.py`
(`Hecho.INVITACION_AL_EQUIPO`), `agenda/servicios/identidad.py` (`revisar_contrasena` deja de ser
privada).

**Pruebas nuevas (49):** `pruebas/bd/escenario_dueno.py`, `test_portal_del_dueno.py`,
`test_anuncios.py`, `test_fichaje.py`, `test_miembros.py`, `test_mapa.py`,
`test_permisos_del_rol_publico.py` y `pruebas/dominio/test_fichaje.py`. **No se modificó ninguna
prueba existente.**

**Contrato:** `packages/api-types/openapi.json` y `tipos.ts` regenerados — **81 rutas, 101
operaciones, 112 esquemas**.

**Variables de entorno:** ninguna nueva. La invitación usa `URL_PUBLICA_WEB`, que ya existía.

## Cómo verificar que funciona

Pruebas, con la base propia de este árbol de trabajo:

```bash
docker compose -f infra/local/docker-compose.yml run --rm \
  -v "$PWD/apps/api:/app" \
  -e DATABASE_URL_PRUEBAS="postgresql+asyncpg://agenda_api:agenda@db:5432/agenda_pruebas_w2" \
  -e DATABASE_URL_PRUEBAS_DUENO="postgresql+psycopg://agenda_owner:agenda@db:5432/agenda_pruebas_w2" \
  -e DATABASE_URL_PRUEBAS_SISTEMA="postgresql+asyncpg://agenda_admin:agenda@db:5432/agenda_pruebas_w2" \
  -e DATABASE_URL_DUENO_ASYNC="postgresql+asyncpg://agenda_owner:agenda@db:5432/agenda_pruebas_w2" \
  api pytest            # 221 pruebas (eran 172)

docker compose -f infra/local/docker-compose.yml run --rm -v "$PWD/apps/api:/app" \
  api sh -c "ruff check agenda/ pruebas/ && ruff format --check agenda/ pruebas/"
```

**Y en vivo**, que es donde se vio que todo esto se usa de verdad. Se levantó una base aparte
(`agenda_vivo_w2`) migrada desde cero y sembrada, con la API en el puerto 8099 — **sin tocar
`agenda` ni `agenda_pruebas`**:

```bash
docker compose -f infra/local/docker-compose.yml run --rm -d --name w2-api-vivo -p 8099:8000 \
  -v "$PWD/apps/api:/app" \
  -e DATABASE_URL="postgresql+asyncpg://agenda_api:agenda@db:5432/agenda_vivo_w2" \
  -e DATABASE_URL_PUBLICO="postgresql+asyncpg://agenda_publico:agenda@db:5432/agenda_vivo_w2" \
  -e DATABASE_URL_ADMIN="postgresql+asyncpg://agenda_admin:agenda@db:5432/agenda_vivo_w2" \
  api python -m uvicorn agenda.main:app --host 0.0.0.0 --port 8000
```

Lo comprobado a mano, con los datos del seed:

- **Finanzas** de la Barbería El Cangrejo: 24 citas completadas, **276,00 USD**, ticket medio
  11,50, dos semanas que empiezan el lunes a las **05:00 UTC** — es decir, medianoche en Panamá.
- **Mejor del mes**: Kevin Ortega 140,00 en 12 servicios, Yaritza Beitía 136,00 en 12. Los dos
  criterios devuelven listas distintas cuando los números difieren.
- **Agenda en columnas** del 8 de septiembre: dos columnas, dos citas cada una, con cliente,
  servicio e importe, y el día recortado entre `2026-09-08T00:00:00-05:00` y el mismo instante
  del día siguiente.
- **Anuncio**: se crea, sale en `GET /publico/negocios/barberia-el-cangrejo` y el segundo que se
  solapa devuelve **409 `YA_EXISTE`**. En el cuerpo de la ficha pública **no aparece ningún
  `+507`**.
- **Fichaje**: fichar con el interruptor apagado devuelve **403** con «El fichaje no está
  activado para esta persona»; encendido, la entrada se guarda; una segunda entrada seguida
  devuelve **422** «Ya hay una entrada sin cerrar».
- **Invitación entera**: el dueño invita a `Yaris.Vega@correo.pa`, `POST /invitaciones/ver`
  **sin sesión** describe el salón y el papel, `POST /invitaciones/aceptar` con contraseña
  devuelve credenciales **ya en modo negocio**, y después esa persona **entra con su correo**
  por la puerta normal.
- **Último dueño**: `PATCH` y `DELETE` sobre el único dueño devuelven **422
  `NEGOCIO_SIN_DUENO`**.
- **Mapa**: 10 salones dentro del rectángulo de Ciudad de Panamá, `truncado: false`; con
  `limite=2`, dos salones y `truncado: true`; un rectángulo en el mar devuelve cero; uno al revés
  devuelve **422**. Sin teléfonos en la respuesta.
- **Como profesional**: la agenda en columnas trae **una sola columna, la suya**; finanzas, mejor
  del mes, miembros y escribir el anuncio devuelven **403**; su propio fichaje sí, y el parte
  solo enseña el suyo.

**Las tres pruebas delicadas se comprobaron reintroduciendo el fallo a propósito**, y las tres se
pusieron en rojo: el importe leído del catálogo de hoy, la agrupación en UTC y la regla del
último dueño. La del interruptor del fichaje se comprobó recreando la política sin el `EXISTS`.

## Pendiente o bloqueado

1. **La invitación llega al buzón de desarrollo, no a un correo de verdad.**
   `POST /negocio/miembros/invitaciones` encola la notificación con canal `email` y plantilla
   `invitacion_equipo`, y en local el proveedor de desarrollo la entrega: comprobado ejecutando
   `cola.entregar` sobre la fila, que pasó a `enviada` y dejó el mensaje con su enlace en el
   buzón. Fuera de local hace falta **credencial de correo** (`EMAIL_API_KEY`), que no existe:
   `ProveedorCorreo` sin clave lanza `ProveedorNoConfigurado` y la notificación se reintenta
   hasta quedar `fallida`. Mientras tanto, **solo en local la respuesta devuelve el token y el
   enlace**, igual que hace el código de un solo uso. **Hace falta decidir proveedor de correo.**
2. **La plantilla `invitacion_equipo` no existe como fila** en `notification_templates`. Hoy no
   estorba —el proveedor de desarrollo escribe lo que recibe—, pero cuando haya canal real hay
   que cargarla.
3. **`ad_campaigns` sigue sin construirse.** Es Fase 4 y no entraba aquí; queda dicho para que
   nadie confunda el anuncio del salón con el posicionamiento pagado.
4. **El anuncio no admite foto ni enlace.** Lo primero espera al almacenamiento de objetos
   (BE-T029); lo segundo se descartó a propósito y está explicado arriba.
5. **El fichaje no se puede corregir.** Es append-only y no hay endpoint de corrección: una marca
   equivocada se arregla con otra marca. Si el uso real pide corregir, hará falta decidir **quién
   puede** y que quede auditado; hacerlo editable sin eso vaciaría el registro de sentido.
6. **El barrido de permisos del rol público es de esta migración, no del entorno.** Sigue vivo el
   `ALTER DEFAULT PRIVILEGES` de `infra/local/init/01-roles.sql`, así que **cualquier tabla nueva
   volverá a nacer con `SELECT` para `agenda_publico`**. La prueba
   `test_permisos_del_rol_publico.py` lo detecta, pero el arreglo de raíz es de DevOps: quitar
   `agenda_publico` de los privilegios por defecto y conceder tabla a tabla.

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **La migración es `0010_portal_del_dueno` y cuelga de la `0008`.** Hay una `0009` en otra rama.
  Al fusionar hay que **reencadenar una de las dos**, no renombrar la mía.
- **Bases usadas y no usadas.** Este trabajo corrió sobre `agenda_pruebas_w2` (pruebas) y
  `agenda_vivo_w2` (verificación en vivo). **`agenda` y `agenda_pruebas` no se tocaron**, así que
  la base de desarrollo compartida sigue en la migración 0008 y **le falta el arreglo de
  permisos del rol público**: mientras no se migre, ahí los teléfonos siguen siendo legibles por
  `agenda_publico`.
- **Lo que NO hay que hacer:** añadir una tabla nueva y darle política para `agenda_publico`
  «por si acaso» —si no es pública, lo que se le quita es el permiso—; y añadir una política
  sobre la agenda o el fichaje del profesional **sin `AS RESTRICTIVE`**, porque no restringiría
  nada y no fallaría nada.
- **Los ficheros clave** para entender esto son la migración 0010 —donde están las cuatro
  políticas y el barrido de permisos— y `agenda/servicios/miembros.py`, donde está escrito por
  qué la invitación necesita declarar dos ajustes de sesión y no uno.
