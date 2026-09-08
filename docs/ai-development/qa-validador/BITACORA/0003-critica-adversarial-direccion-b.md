# 0003 · Crítica adversarial de la DIRECCIÓN B del frontend

- **Agente:** QA / Validador (en papel de **crítico cruzado**) · **Tarea:** ronda adversarial del listón del frontend · **Fecha:** 2026-09-08
- **Estado al cerrar:** hecha

## Qué hice

Juzgué **una sola** dirección de frontend, la **B («El tablón»)**, contra
`docs/producto/LISTON-FRONT.md`. No he visto las otras dos ni sé qué proponen. **No es una
validación de tarea**: nada pasa a `validada` con esto; es la crítica de una propuesta que compite.

Lo que hice, en concreto:

1. **Los siete descartes, medidos por mí.** No ejecuté ni uno de los verificadores de la propuesta
   (`apps/web/verificacion/*.mjs`): escribí instrumentos propios con Playwright y Chromium a 390 px
   y también a 1440. Barrí **20 pantallas × 2 anchos = 40 combinaciones**, más los estados que solo
   se alcanzan tocando (servicio/persona/día/hora elegidos, dos servicios encadenados, día sin
   hueco, error de contraseña), más el recorrido completo del teclado con el tabulador en 9
   pantallas.
2. **Los cinco caminos, a base de clics**, entrando de verdad con las cuentas de demostración.
   Creé **una reserva real** en el camino 3 y dos más para probar aristas.
3. **Limpié la base**, que es compartida: las tres reservas quedaron canceladas y comprobadas por
   la API.

**Resultado: la dirección B NO pasa el listón.** Falla **D7**: el anillo de foco de teclado de los
tres enlaces de la navegación principal (Horas / Salones / Personas) se pinta `#FBFBF9` sobre
`#FFFFFF` = **1,04:1**, contra el 3:1 que D7 exige para elementos de interfaz, y ocurre en **9 de 9
pantallas** (27 apariciones). Lo probé con píxeles de una captura a `deviceScaleFactor: 3`, no solo
con `getComputedStyle`. Los otros **seis descartes los pasa**, varios con holgura. Los **cinco
caminos se recorren enteros**.

## Decisiones tomadas

- **No ejecutar la verificación de la propia propuesta.** El encargo lo pedía explícitamente y
  además es la regla de la casa: «build verde» —o «verificador propio en verde»— no es evidencia.
  Acertó: su `contraste.mjs` no contiene la palabra `focus` (`grep -c` = 0), así que su D7 en verde
  es cierto para lo que mide y ciego para el indicador de foco, que es donde se cae.
- **Medir D5 tres veces y no fiarme de `scrollWidth`.** La hoja pone `overflow-x: hidden` en el
  `body`, lo cual *fabrica* un `scrollWidth` correcto aunque se recortara contenido. Además de la
  medida normal, quité el recorte en caliente y volví a medir, y busqué desbordes elemento a
  elemento comprobando si colgaban de un carril con scroll (legítimo) o de un `hidden` (recorte).
  Pasa las tres.
- **No proponer ni una mejora.** El listón dice que un crítico que propone mejoras invalida la
  ronda entera. La crítica describe y demuestra; no arregla ni sugiere cómo arreglar.
- **No tocar el código de la dirección**, ni `apps/api`, ni `packages/`, ni `scripts/`.
- **Corregí en caliente dos falsas alarmas mías** antes de escribirlas como defecto, porque un
  rechazo sin reproducción no sirve: (a) «a La carta le falta un servicio» era el zócalo pegajoso
  en una captura de página completa —comprobado con `elementFromPoint` y con un barrido de oclusión
  al fondo del documento: nada queda tapado de forma permanente—; y (b) «el botón Cancelar no hace
  nada» era mi selector buscando un `[role=dialog]` cuando la confirmación es **inline dentro de la
  fila**; al confirmar dispara el `POST` y cancela de verdad.

## Archivos / recursos creados o tocados

- **Creado:** `/Users/luisgomez/Desktop/kraken/m2g-bookings/docs/producto/criticas-front/critica-b.md`
  (la crítica, con las tres respuestas que pide el listón).
- **Creado:** este archivo.
- **Instrumentos de medida** (fuera del repositorio, en el scratchpad de la sesión):
  `/private/tmp/claude-501/-Users-luisgomez-Desktop-kraken-m2g/1376160a-a936-466a-bcb6-7086a3fd95ea/scratchpad/qa/`
  — `medir.mjs` (contraste, desbordes, radios, degradados, familias), `barrido.mjs` (20×2),
  `d5-crudo.mjs`, `d2-estados.mjs` (seis estados por CDP), `d6-movimiento.mjs`, `d4-api.mjs`,
  `d7-extra.mjs`, `focos.mjs`, `oclusion.mjs`, `enlaces.mjs`, `estres.mjs`, `camino123.mjs`,
  `camino3-reserva.mjs`, `camino4-entrar.mjs`, `camino5.mjs`, `cancelar.mjs`; capturas en `shots/`.
- **No toqué** el worktree de la dirección B ni ningún archivo de otro agente.

## Cómo verificar que funciona

Con la API local levantada (`make arriba`) y el servidor de la dirección B en `http://localhost:3300`:

1. **El fallo de D7, en treinta segundos y a mano:** abre `http://localhost:3300/` en el navegador,
   pulsa **Tab** cuatro veces hasta que el foco llegue a **«Salones»** en la barra blanca de
   secciones. El anillo no se ve. Con la consola abierta:
   ```js
   getComputedStyle(document.activeElement).outlineColor   // "rgb(251, 251, 249)"
   getComputedStyle(document.querySelector('.secciones')).backgroundColor  // "rgb(255, 255, 255)"
   ```
   `#FBFBF9` sobre `#FFFFFF` = **1,04:1**. Se repite en las nueve pantallas.
2. **El resto de descartes:** los guiones del scratchpad son reproducibles tal cual con
   `node <guion>.mjs` usando el Playwright de `/Users/luisgomez/Desktop/kraken/m2g-bookings/node_modules`.
3. **Los cinco caminos:** están narrados paso a paso en `critica-b.md`, con la URL y lo que se ve en
   cada paso.

## Pendiente o bloqueado

Nada que dependa de mí. La decisión de qué dirección gana **es de Luis**, no de QA: yo solo digo si
esta pasa el listón, y **no pasa**.

**Sí escribí en `ESTADO-GLOBAL.md`**, una fila en la tabla «Avisos entre agentes», detrás de la que
ya había dejado el crítico de la dirección C. Es el sitio que ese aviso ya había establecido y es un
reemplazo de una sola cadena, que es lo menos que puede chocar con los otros críticos que corren en
paralelo sobre el mismo repositorio (el tablero es zona serializada, §9 del README).

**Lo que NO metí en la tabla de deuda viva, y por qué:** lo encontrado es de **una propuesta que
todavía no está elegida**, no del producto. Si la B gana, ese mismo día entran a la tabla, con dueño:
(a) el fallo de D7 del anillo de foco, y (b) el `404 /fotos/spa.webp`. Queda dicho en el propio aviso
del tablero para que no viva solo en prosa.

**Aviso ajeno que confirmo, no arreglo:** `ESTADO-GLOBAL.md` sigue teniendo una marca de conflicto de
git sin resolver (`>>>>>>> worktree-agent-abb50ac3d35f2882e`) dentro de la tabla «Estado de los
agentes». Ya la había señalado el crítico de la dirección C. **No la toco**: es el resto de un merge
ajeno y borrarla puede tapar una fila perdida.

## Qué necesita saber el siguiente que llegue (HANDOFF)

- **Estado real:** dirección B criticada y **rechazada por D7**. Seis descartes pasados, cinco
  caminos completos. El detalle con pruebas está en `docs/producto/criticas-front/critica-b.md`.
- **Si la B resulta elegida**, tres cosas hay que apuntar el primer día, todas verificadas:
  el anillo de foco de la navegación (D7), el `404 /fotos/spa.webp` que pinta una imagen rota en
  `/salon/spa-costa-del-este/ivonne-saavedra` —el origen es la **semilla**, no el frontend—, y que
  el aviso del tope de 30 citas le habla a la clienta de cómo pagina la API.
- **Qué NO hacer:** no dar por bueno el D7 de una dirección porque su propio verificador esté en
  verde. Ninguno de los tres verificadores de contraste que he visto en esta casa mide el indicador
  de foco; hay que recorrer con el **tabulador** y medir el `outlineColor` contra el fondo real.
- **La base de datos de la demostración es compartida.** Cualquier reserva que se cree probando se
  cancela al terminar por `POST /api/v1/mi/reservas/{id}/cancelar` y se comprueba leyendo
  `GET /api/v1/mi/reservas`. Yo creé tres y las tres están canceladas.
