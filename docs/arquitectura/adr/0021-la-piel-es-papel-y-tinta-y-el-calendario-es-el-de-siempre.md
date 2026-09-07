# ADR-0021 · La piel es papel y tinta, y el calendario es el de siempre

- **Estado:** aceptada
- **Fecha:** 2026-09-07
- **Supera:** ADR-0016 (la dirección visual es el bloque de color) en lo visual, y la tira de
  siete días como único selector de fecha.

## Contexto

Luis vio las tres direcciones de la revisión 4 y ninguna le convenció. La que más se acercaba era
**Buenamano**. Su reproche fue en dos planos, y conviene no mezclarlos:

1. **De producto.** «Esa vista del calendario y de las horas no la estás haciendo estándar (…)
   tiene que ser fácil de entender.» El selector era una tira de siete días con desplazamiento
   horizontal —así está escrito en el propio CSS: *«sin vista de mes»*— y en el brandbook aparecía
   además una «cinta de horas» con regla de tiempo. Quien quería hora para dentro de tres semanas
   no tenía por dónde pedirla.
2. **De piel.** El producto se estaba pintando con la dirección «Noche de barrio panameño»:
   fondo casi negro, rosa neón y `data-tema="oscuro"` forzado en el `<html>`. Eso incumplía el
   **descarte D1 del listón** («el producto arranca en claro»), que es exactamente lo que ya había
   matado una ronda anterior.

## Decisión

**[decisión] El selector de fecha es un calendario de mes corriente.** Rejilla de siete columnas
de lunes a domingo, flechas de mes, hoy señalado, el día elegido con tres señales (fondo, borde y
peso) y **los días sin hueco apagados a la vista, no escondidos**: si desaparecen, quien mira no
sabe si es que no hay hora o si la web se rompió. Encima quedan tres atajos —hoy, mañana y pasado—,
que es lo que se pide el 80 % de las veces.

**[decisión] Las horas van agrupadas en mañana, tarde y noche**, en rejilla de botones. Veinte
horas seguidas no se leen, y «por la tarde» es como pide la hora todo el mundo.

**[decisión] Aquí no se innova.** La mecánica de elegir día y hora es la que la gente ya sabe usar.
Lo original se paga en clientas que no reservan. La marca entra en el color, en la letra y en el
resto de la pantalla; en este control, no.

**[decisión] La piel del producto pasa a «papel y tinta»**, sobre la dirección Buenamano: papel
crudo `#F7F2E9`, tinta `#14100D`, ceniza `#6B6157`, y los dos saturados con su trabajo repartido —
**achiote `#B23320` abre** (buscar, crear, publicar) y **añil `#1D3FB0` cierra** (elegir hora,
confirmar). Ninguno de los dos es color de texto largo.

**[decisión] Se quita `data-tema="oscuro"` del `<html>`.** El producto abre en claro. El tema
oscuro sigue existiendo en los tokens como alternativa, que es lo que el listón permite.

**[decisión] Se cambia la piel, no el esqueleto.** Los nombres de las variables CSS no cambian, así
que ningún componente se entera: se reescribe el bloque `:root` de `globales.css` y la paleta clara
de `packages/tokens/tokens.json`.

## Consecuencias

- `verificar-contraste.mjs`: **41 combinaciones, todas AA**.
- El nombre sigue siendo **Bukeo** y sigue viviendo en configuración, no escrito en las pantallas.
- **Queda pendiente el logotipo.** El sello de huella dactilar era de Buenamano y no vale para
  Bukeo; hace falta uno nuevo, generado en vectorial, y ahora mismo no hay créditos para ello.
  Hasta que lo haya, la cabecera lleva el nombre compuesto en tipografía.
- El lenguaje de «tubo de neón» sobrevive como **filete de 2 px** en añil: en papel, 3 px de trazo
  es un subrayado gordo.
