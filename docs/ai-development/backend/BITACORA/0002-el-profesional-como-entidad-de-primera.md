# 0002 · El profesional como entidad de primera, y elegirlo antes que el salón

- **Agente:** Backend · **Tareas:** BE-T032 y BE-T033 (secciones **A** y **B** de [`ESPEC-PROFESIONAL-Y-DUENO.md`](../../../producto/ESPEC-PROFESIONAL-Y-DUENO.md), §3 del [encargo del 7 de septiembre](../../../producto/ENCARGO-2026-09-07.md)) · **Fecha:** 2026-09-07
- **Estado al cerrar:** hecha (pendiente de QA)
- **Árbol de trabajo:** `.claude/worktrees/agent-a76a4bb9adfd93f57`, rama `worktree-agent-a76a4bb9adfd93f57`. **Sin push ni merge**: el merge lo hace el director.

## Qué hice

Hasta hoy el profesional era **una fila del equipo de un salón**: un nombre, una bio y una foto
que solo existían dentro de la ficha del negocio. Luis lo señaló como «el fallo de fondo». Ahora
es una entidad con perfil propio, URL propia, portafolio propio y su propia puerta de reserva.

**A · El profesional como entidad pública.** `staff_profiles` gana `slug` —único **por negocio**,
no global—, `headline`, `instagram`, `facebook`, `x` y `years_experience`. Tabla nueva
`staff_media` con `service_id` **nulable**: atada a un servicio significa «esto lo hizo esta
persona», suelta es su galería. Cuatro rutas públicas nuevas —el perfil, el equipo de un salón,
la búsqueda de profesionales sueltos y sus huecos— y ocho del panel para que la persona edite
su ficha y suba fotos, y para que el dueño haga lo mismo con su equipo.

**B · Elegir profesional primero.** El camino de siempre —negocio → servicio → profesional—
sigue exactamente igual. Al lado hay uno nuevo: **buscar persona → ver su perfil → elegir uno de
sus servicios → hora**, con `GET /publico/profesionales/{id}/disponibilidad`, que resuelve el
salón a partir de la ficha. **El motor de disponibilidad no cambió ni una línea**, y hay una
prueba que lo demuestra comparando las dos rutas hueco a hueco.

Y una cosa pequeña que llevaba tiempo vacía: `ResenaPublica.profesional` existía en el contrato
y **siempre venía nulo**. Ahora dice quién atendió, que es la mitad del dato en una reseña que
dice «me encantó el color».

## Decisiones tomadas

**El slug es único por negocio, no global.** La misma persona puede trabajar en dos salones y
ser `yaris` en los dos. Un único global obligaría a la segunda Yaris a llamarse `yaris-2` en un
salón donde no hay ninguna otra, y eso no hay forma de explicárselo a nadie. El índice es
parcial: solo entre los **vivos**, para que quien se va no se quede ocupando el nombre bonito
de quien llega.

**El slug admite nulo en la base y lo pone la aplicación.** Hacerlo obligatorio convertiría cada
alta —dos segundos desde el mostrador— en una transacción con reintentos por colisión. A cambio
se cierra el agujero por tres sitios: la migración **rellena** los existentes, el alta desde el
panel lo asigna, y el perfil público acepta **slug o identificador**, así que un nulo no deja a
nadie sin URL. Además, la primera vez que alguien guarda su perfil se le asigna uno si no lo
tenía.

**Las tres redes guardan el usuario y no la URL, y lo defiende una restricción.** El endpoint
normaliza las tres formas en que la gente rellena de verdad ese campo (`yaris.nails`,
`@yaris.nails` y la URL copiada del navegador) y rechaza una dirección de otro dominio. Pero
**el endpoint es lo que un compañero futuro puede olvidar escribir**, así que la defensa de
verdad está en `CHECK`: en esos patrones no cabe ni una barra ni dos puntos. Hay cinco pruebas
que lo comprueban escribiendo directo en la base.

**Ni el número de atendidos ni la nota se guardan en una columna.** Se calculan al leer, con una
consulta agrupada por profesional —una para la lista entera, no una por persona—. Un contador
guardado se desincroniza el primer día que alguien cancela una cita a mano en la base, y hay una
prueba que hace exactamente eso y comprueba que el número baja.

**Son dos números, no uno:** `citas_atendidas` (trabajo hecho) y `clientes_atendidos` (personas
distintas). Una clienta que vuelve cada mes cuenta doce veces en el primero y una en el segundo,
y las dos preguntas son legítimas. Solo cuentan las citas `completada`.

**La nota del profesional es bayesiana**, con los mismos pesos configurables que la del negocio
(REV-5, ADR-0009). Y cuando no tiene reseñas es `null`, no la media global: enseñarle la media
de la plataforma como si fuera suya sería inventarle una reputación que nadie le dio.

**`bookings` sigue sin ser pública, y lo atendido se cuenta abriendo una sesión con el negocio
fijado** — el mismo movimiento que ya hacía la disponibilidad del salón, y por el mismo motivo:
abrirle las reservas al rol del marketplace sería una puerta que después no se cierra. La
consecuencia se asume por escrito: **la búsqueda de profesionales no trae ese número**, porque
ahí cada resultado es de un salón distinto y contarlo costaría una conexión por negocio en la
ruta que más se va a repetir. Está en el perfil, que es donde alguien lo mira de verdad.

**La 0009 abre un recorte de la 0006, y solo un poco.** La migración 0006 cerró la escritura de
`staff_profiles` para el profesional; el encargo pide que cada quien edite **la suya**. La
política restrictiva de `UPDATE` pasa de «ningún profesional escribe aquí» a «cada profesional
escribe su propia fila». `INSERT` y `DELETE` **se quedan cerrados**: dar de alta y de baja es del
dueño, y una ficha borrada por su titular se llevaría por delante su historial de agenda.

Qué **campos** puede cambiar de su propia fila lo decide la aplicación, no la base: PostgreSQL no
distingue columnas dentro de una fila para un mismo rol. Por eso `CambioDeMiPerfil` sencillamente
**no tiene** `activo`, `visible_en_marketplace` ni `orden`, en vez de tenerlos y descartarlos.

**`staff_media` nace con moderación `aprobada`, como `business_media`.** Se consideró
`pendiente`, y se descartó: no hay cola de moderación de fotos en la consola (solo de reseñas),
así que el default habría dejado toda galería invisible hasta que alguien tocara la base a mano.
La columna está y la política pública exige `aprobada`, así que rechazar una foto la apaga en el
acto — el día que exista la cola, no hay que migrar nada.

**Las fotos del seed son solo las dos que la web sirve de verdad.** Sembrar rutas que no existen
llenaría los perfiles de imágenes rotas, que es peor que un perfil sin fotos.

## Archivos / recursos creados o tocados

**Migración** (zona serializada; nadie más la tocó):
- `apps/api/migraciones/versions/20260907_0009_profesional_entidad.py` — `revision = "0009_profesional_entidad"`, `down_revision = "0008_acceso_contrasena"`, como se pidió. Seis columnas, el relleno de slugs, el único parcial, cinco `CHECK`, la tabla `staff_media` con sus cuatro políticas, `staff_services` abierta al rol público y el recorte de la 0006 sustituido. **Con `downgrade` probado.**

**Modelo:** `agenda/modelos/equipo.py` (columnas nuevas y `StaffMedia`), `agenda/modelos/__init__.py`.

**Dominio nuevo:** `agenda/dominio/textos.py` — `slug_desde`, `usuario_de_red` y `url_de_red`.
Lo comparten el slug del negocio y el del profesional: si cada uno tuviera el suyo, un día uno
transliteraría las tildes y el otro no.

**Servicio nuevo:** `agenda/servicios/profesionales.py` — `slug_libre`, `atendidos`, `notas`.

**Rutas nuevas:** `agenda/api/publico_profesionales.py` (4 públicas) y
`agenda/api/perfil_profesional.py` (8 del panel).

**Tocados:** `agenda/api/publico.py` (los trabajos por servicio y el equipo con slug y titular),
`agenda/api/negocio_equipo.py` (el dueño edita el perfil público del equipo),
`agenda/api/onboarding.py` (el alta nace con slug; `_slug` delega en el dominio),
`agenda/api/resenas.py` (`pintar_publicas` pasa a pública y rellena `profesional`),
`agenda/main.py`, `agenda/semilla.py`.

**Pruebas nuevas:** `pruebas/dominio/test_textos.py`, `pruebas/bd/escenario_profesional.py`,
`pruebas/bd/test_profesional_rls.py`, `pruebas/bd/test_perfil_profesional.py`,
`pruebas/bd/test_panel_del_profesional.py`. **Ninguna prueba existente se modificó.**

**Contrato:** `packages/api-types/openapi.json` y `tipos.ts` regenerados — **77 rutas, 98
operaciones, 98 esquemas** (eran 65 / 81 / 84). Comprobado que **no desaparece ni una operación
ni un esquema**: solo se añade.

## Cómo verificar que funciona

Base propia `agenda_pruebas_w1`, para no chocar con el otro agente. Desde el árbol de trabajo:

```bash
# Migrar desde cero (se probó con la base recién creada, y también downgrade → upgrade)
docker compose -f infra/local/docker-compose.yml run --rm \
  -v "$PWD/apps/api:/app" \
  -e DATABASE_URL_MIGRACIONES="postgresql+psycopg://agenda_owner:agenda@db:5432/agenda_pruebas_w1" \
  api alembic upgrade head

# Lint (ruff 0.8.4, el del proyecto) y las pruebas
docker compose -f infra/local/docker-compose.yml run --rm \
  -v "$PWD/apps/api:/app" \
  -e DATABASE_URL_PRUEBAS="postgresql+asyncpg://agenda_api:agenda@db:5432/agenda_pruebas_w1" \
  -e DATABASE_URL_PRUEBAS_DUENO="postgresql+psycopg://agenda_owner:agenda@db:5432/agenda_pruebas_w1" \
  -e DATABASE_URL_PRUEBAS_SISTEMA="postgresql+asyncpg://agenda_admin:agenda@db:5432/agenda_pruebas_w1" \
  -e DATABASE_URL_DUENO_ASYNC="postgresql+asyncpg://agenda_owner:agenda@db:5432/agenda_pruebas_w1" \
  api sh -c "ruff check agenda/ pruebas/ && ruff format --check agenda/ pruebas/ && pytest"
```

**229 pruebas pasan** (eran 172). Lint y formato limpios.

### Y en vivo, que es donde se comprueba de verdad

Con el seed cargado en `agenda_pruebas_w1` y la API levantada en el 8099:

```bash
curl -s .../publico/negocios/salon-obarrio/profesionales
curl -s .../publico/negocios/spa-costa-del-este/profesionales/ivonne-saavedra
curl -s '.../publico/profesionales?servicio=barberia&orden=nota'
curl -s '.../publico/profesionales/{id}/disponibilidad?servicios={id}&desde=…Z&hasta=…Z'
```

Lo comprobado a mano, con datos del seed:

- El equipo de Salón Obarrio sale con titular, años, **nota bayesiana** (4,27 / 4,23 / 4,42) y
  citas atendidas.
- El perfil de Ivonne Saavedra trae bio, Instagram compuesto como URL, su catálogo, **una foto
  de trabajo atada al masaje relajante** y sus cinco reseñas con el autor acortado.
- Buscar `servicio=barberia&orden=nota` devuelve tres barberos de tres salones distintos
  ordenados por nota.
- Los huecos de Kevin salen con `zona: America/Panama` y **21 huecos**, todos a su nombre.
- **Entrando como profesional** (`pro.barberia-el-cangrejo@demo.pa`): leo mi perfil, lo edito
  pegando `https://www.instagram.com/kevin.fade/` y se guarda `kevin.fade`; pegar
  `https://sitio-cualquiera.com/promo` devuelve `DATO_INVALIDO` diciendo qué campo falla; subo
  una foto atada a «Corte + barba» y **aparece en la ficha pública del salón con mi nombre al
  lado**.
- Intentar editar a la compañera o subirle una foto desde esa sesión: **403 `NO_AUTORIZADO`**,
  no un 500.
- El JSON del perfil, del equipo y de la búsqueda **no contiene ningún teléfono**.

### Las pruebas se rompieron a propósito

Cada prueba delicada se validó **reintroduciendo el fallo** y comprobando que falla:

| Lo que se rompió | Qué falló |
|---|---|
| Quitar `visible_in_marketplace` de la política de `staff_media` | 2 pruebas |
| Borrar la política restrictiva `staff_media_profesional` | 2 pruebas |
| Borrar el único parcial del slug y los cinco `CHECK` | 6 pruebas |
| Meter un teléfono en el serializador público | 1 prueba |
| Cambiar `profesional_id=ficha.id` por `None` en la disponibilidad | 1 prueba |

La última **no falló al primer intento** y hubo que reforzarla: el escenario solo tenía horario
para una persona, así que «los huecos de Kevin» y «los huecos de cualquiera» daban lo mismo. Se
añadió horario para las dos y un bloqueo solo de Kevin dentro del horario de apertura. Es
exactamente la clase de prueba que pasa en verde sin comprobar nada.

## Pendiente o bloqueado

1. **No hay subida de archivos tampoco para las fotos del profesional.** `POST
   /mi/perfil-profesional/fotos` recibe **una clave**, no un fichero, igual que
   `POST /negocio/fotos`. Es la misma deuda ya anotada (BE-T029) y no se resuelve sin decidir el
   almacenamiento de objetos.
2. **No hay cola de moderación para `staff_media`.** La columna está y la política pública la
   respeta, pero **nadie modera**: hoy una foto entra `aprobada`. Anotado como deuda nueva.
3. **La búsqueda de profesionales no ordena por distancia.** `distancia_metros` viaja en la
   respuesta y siempre es `null`. Hacerlo bien es meter PostGIS en esta consulta, y eso es
   trabajo suyo, no un añadido de esta tarea.
4. **Las citas atendidas no salen en la búsqueda de profesionales.** Decidido y explicado arriba.
5. **Los errores de validación no llevan la forma única del error.** Un `desde` mal escrito
   devuelve el `{"detail": [...]}` de FastAPI en vez de `{"error": {"codigo": …}}` (ADR-0012).
   **Es anterior a esta tarea** —pasa igual en `/publico/negocios/{slug}/disponibilidad`— pero se
   encontró aquí y se anota, porque la forma única del error es contrato.
6. **La sección C (el portal del dueño) y las D y E no se han tocado**: no eran de esta tarea.

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **La migración es `0009_profesional_entidad` sobre `0008_acceso_contrasena`**, como pidió el
  director. No se renumeró nada.
- **La base `agenda` y `agenda_pruebas` no se han tocado.** Todo se hizo contra
  `agenda_pruebas_w1`, que se borró y se recreó a mitad para probar las migraciones desde cero.
  **La base de desarrollo sigue en 0008: hay que migrarla y resembrarla tras el merge**, o los
  perfiles saldrán sin slug.
- **`packages/api-types` está regenerado.** Si choca en el merge con lo del otro agente, **no se
  resuelve a mano**: se mergea el código y se vuelve a ejecutar
  `python -m agenda.contrato > packages/api-types/openapi.json` y después
  `npx openapi-typescript openapi.json --output tipos.ts --alphabetize`.
- **Lo que no hay que hacer:** añadir una política nueva sobre `staff_media` o sobre la ficha del
  profesional **sin `AS RESTRICTIVE`** cuando la intención sea recortar — una permisiva se crea,
  se aplica, no falla y no restringe nada. Y no convertir `citas_atendidas` en una columna: se
  desincroniza el primer día, y hay una prueba escrita para recordarlo.
- **El fichero clave** para entender el bloque es la propia migración 0009: ahí está escrito por
  qué cada política dice lo que dice y por qué el slug es por negocio.
