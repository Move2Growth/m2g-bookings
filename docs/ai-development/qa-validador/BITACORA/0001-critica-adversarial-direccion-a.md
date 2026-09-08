# 0001 · Crítica adversarial de la dirección A de frontend

- **Agente:** QA / Validador · **Tarea:** crítica de ronda adversarial (encargada por el director; no es una tarea de `TAREAS.md`) · **Fecha:** 2026-09-08
- **Estado al cerrar:** hecha

## Qué hice

Juzgué **una sola** dirección de frontend, la **A** («Te toca»), contra
`docs/producto/LISTON-FRONT.md`: sus **siete descartes** y sus **cinco caminos**. Es una crítica
de ronda a ciegas: no vi las otras dos direcciones ni las busqué, y **no propuse ni una mejora**
—proponerlas invalida la ronda—.

Todo se midió por mí, en Playwright a 390 px (y también a 768 y 1440), contra `:3200` con la API
en `:8000` y la semilla cargada. **No acepté como prueba nada de `apps/web/verificacion/`**: cada
descarte se volvió a medir con guiones propios, escritos fuera del repositorio.

**Resultado: rechazada por fallar D7.** Seis descartes limpios; el séptimo falla en su mitad de
«elementos de interfaz», que es justo la mitad que su propio verificador nunca mide. De los cinco
caminos, cuatro enteros y el de reservar roto en su último paso para 4 de los 7 días que ofrece.

## Decisiones tomadas

- **Medir los seis estados del botón recortando una región fija de pantalla**, no la caja del
  botón. Con la caja móvil, «encima» y «pulsado» salían idénticos (22 px de 89.760) porque el
  recorte se mueve con el `transform` y anula la diferencia. Con región fija, los diez pares
  difieren. Lo apunto porque la próxima validación de botones debe hacerse así.
- **Medir el contraste de elementos de interfaz con barrido de píxeles** sobre la captura, no con
  `getComputedStyle`: los bordes de esta dirección son `box-shadow: inset`, y un medidor que solo
  mire `border-width` da falsos positivos (marca como fallo botones que sí tienen anillo) y
  falsos negativos a la vez.
- **No cancelar reservas que no eran mías.** Aparecieron dos que ninguno de mis guiones creó;
  con tres críticos sobre la misma base de datos, cancelarlas podía romper el trabajo de otro.
  Van avisadas en la crítica. Acerté: una la canceló su dueño solo.
- **No toqué `ESTADO-GLOBAL.md`.** Es zona serializada y hay otros dos críticos trabajando a la
  vez sobre la misma ronda; escribirlo desde aquí era el conflicto garantizado. Queda escalado al
  director en el informe (ver «Pendiente»).

## Archivos / recursos creados o tocados

- `docs/producto/criticas-front/critica-a.md` — la crítica (creada; la carpeta también).
- `docs/ai-development/qa-validador/BITACORA/0001-critica-adversarial-direccion-a.md` — esta entrada.
- **No se tocó** el código de la dirección, ni `apps/api`, ni `packages/`, ni `scripts/`, ni
  `ESTADO-GLOBAL.md`.
- Guiones de medida y capturas, fuera del repositorio, en el scratchpad de la sesión.

## Cómo verificar que funciona

Con la API en `:8000` con la semilla y la dirección A servida en `:3200`:

- **D1:** `grep -rnE "#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?\b" --include="*.css" --include="*.tsx" --include="*.ts" apps/web` → 0.
  Y la tabla `name` de `apps/web/fuentes/*.woff2` con `fontTools` → «Familjen Grotesk» y «Public Sans».
- **D5:** `document.documentElement.scrollWidth` en cada parada a 390 px → 390 en las 18.
- **D7 (a):** captura de la portada a 390 px; barrido vertical de píxeles por el centro del botón
  «Buscar» cruzando su borde superior → `(27,52,196)` seguido de `(200,30,100)`, sin nada en
  medio: **1,64:1**.
- **D7 (b):** captura de `/salon/barberia-el-cangrejo/kevin-ortega/reservar` a 390 px; barrido
  horizontal cruzando el borde izquierdo de una opción de servicio no elegida →
  `(251,251,249)` → 6 px de `(216,216,210)` → `(255,255,255)`: **1,38:1** y **1,04:1**.
- **Camino 3 roto:** reservar cualquier hueco posterior al 10 de septiembre y pulsar «Ver mis
  citas»; la cita no está. La causa está en la API: `GET /api/v1/mi/reservas` devuelve 30 futuras
  y 30 pasadas **sin paginación** (su `openapi.json` no declara ni un parámetro de página) y la
  semilla ya llena las 30 hasta el 10 de septiembre.
- **Sin SSR:** `curl http://localhost:3200/salon/barberia-el-cangrejo | grep -c "Barbería El Cangrejo"` → 0.

## Pendiente o bloqueado

- **`ESTADO-GLOBAL.md` sin actualizar, a propósito.** Lo escribe quien serialice la ronda —el
  director o el orquestador— cuando estén las tres críticas. Si esta ronda deja deuda que
  sobreviva a la elección (por ejemplo, que el verificador de contraste de la casa **no mide
  elementos de interfaz**), tiene que entrar en la tabla de deuda viva con dueño; hoy no está.
- **Reservas ajenas en la agenda de Barbería El Cangrejo.** Aparecieron dos que no creé
  (07:43:01 y 08:01:11 UTC, esta última con mis pruebas ya terminadas). No las toqué. La primera
  la canceló su dueño mientras yo escribía la crítica: hay **otro crítico trabajando a la vez
  sobre la misma base de datos local**. Mis 6 reservas están las 6 canceladas.

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **La ronda no la cierra QA.** Yo solo emito la crítica de la dirección A; quién gana lo decide
  el director con las tres.
- **Si esta dirección se implanta pese al rechazo, hay dos deudas que nacen con ella y hay que
  escribirlas antes de que se olviden:** el contraste de elementos de interfaz (D7) y la ausencia
  total de contenido en el HTML antes del JavaScript, que choca de frente con el criterio de la
  Fase 2 («el HTML del perfil trae el contenido antes de ejecutar JavaScript» y «Lighthouse móvil
  ≥ 90»). La segunda no es un descarte del listón, pero es la que se paga cara.
- **Qué NO hacer:** no reaprovechar `apps/web/verificacion/contraste.mjs` como guardián de AA sin
  ampliarlo; hoy solo mide texto y da verde con dos fallos de interfaz delante.
- La base de datos local es **compartida** entre críticos: antes de reservar, apunta el
  identificador y cancela por la API al terminar.
