# ADR-0009 · El ranking es una fórmula con pesos en base de datos; el rating es bayesiano

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

MKT-3 y MKT-4. El encargo es tajante: *«que sea una fórmula con pesos configurables desde el back-office, no reglas repartidas por el código»*. Y ADM-4 exige poder ajustar esos pesos **sin desplegar**.

El riesgo de negocio es doble. Si el ranking premia solo lo que ya funciona, **el marketplace nace bloqueado para los negocios nuevos** — que son todos, el primer día. Y si una sola review de 5 estrellas adelanta a un negocio con ochenta de 4,7, el orden pierde toda credibilidad.

## Decisión

**[decisión]** Una **puntuación única** por (negocio, consulta), suma ponderada de señales normalizadas a 0–1:

| Señal | Qué mide | Nota |
|---|---|---|
| `distancia` | Cercanía al punto de búsqueda | Decae con la distancia; a partir de un radio configurable aporta 0 |
| `rating` | Rating **bayesiano**, no la media simple | Ver abajo |
| `reservas_recientes` | Reservas completadas en los últimos N días | Con techo: un negocio grande no puede dominarlo todo |
| `tasa_completado` | Completadas ÷ (completadas + no-shows + canceladas por el negocio) | Castiga al que confirma y no atiende |
| `completitud` | Fotos, descripción, servicios, horario, atributos (ONB-7) | Es la palanca que el negocio controla |
| `actividad` | Cuándo tocó por última vez su agenda | Un perfil abandonado baja |
| `boost_nuevo` | Impulso temporal decreciente durante los primeros N días | **Sin esto el marketplace nace cerrado** |

- **[decisión]** Los pesos, el radio, las ventanas y la duración del boost viven en **`ranking_weights`**, una fila por versión con fecha de vigencia. Cambiarlos es un `UPDATE` desde el back-office. **No hay ningún número de ranking en el código.**
- **[decisión]** Las señales caras (reservas recientes, tasa de completado, completitud, actividad) se **precalculan** en un trabajo periódico y se guardan por negocio. En la consulta solo se combinan con la distancia, que sí depende de quién busca. Es lo que hace posible el p95 < 500 ms.
- **[decisión]** El rating agregado usa **media bayesiana** (REV-5): `(C·m + Σ notas) / (C + n)`, donde `m` es la media global de la plataforma y `C` el número de reviews de confianza, ambos configurables. Con `n` pequeño el negocio se parece a la media; solo con volumen se separa de ella.
- **[decisión]** Los **patrocinados no entran en la fórmula**. Se resuelven en una consulta aparte y se **intercalan** después: máximo 2 de cada 10, etiquetados «Patrocinado», y **nunca desplazan a un orgánico fuera de la página** — se insertan, no sustituyen. **El patrocinio no toca el rating ni las reviews.**
- **[decisión]** Cada resultado guarda **por qué salió**: la contribución de cada señal se puede consultar en el back-office. Un ranking que nadie puede explicar es un ranking que nadie puede ajustar, y la primera llamada de un dueño enfadado va a ser «¿por qué salgo el noveno?».
- **[decisión]** Impresiones y clics (MKT-8) se registran **agregados por día y negocio**, no fila por evento: 5.000 negocios en portada generan mucho ruido y lo que se necesita es la serie.

## Alternativas consideradas

- **Orden por distancia y ya.** Descartado: premia al que está cerca aunque tenga el perfil vacío y nunca conteste.
- **Pesos en un archivo de configuración.** Descartado: cambiarlos sería desplegar, y ADM-4 lo prohíbe explícitamente.
- **Aprendizaje automático desde el principio.** Descartado: no hay datos, no se puede explicar y no se puede ajustar a mano. Cuando haya volumen, se supera con otro ADR.
- **Media aritmética de reviews.** Descartado por REV-5 y por sentido común: una review de 5 no vale ochenta de 4,7.

## Consecuencias

- Hay que **sembrar la media global `m`** con un valor razonable mientras no haya reviews; si no, el primer negocio con una review de 5 se dispara. Va en la configuración inicial.
- El precálculo introduce un desfase (de minutos) entre la realidad y el orden. Es aceptable y hay que decirlo: una reserva de hace un minuto no reordena la portada.
- La explicabilidad cuesta guardar el desglose. Vale la pena: es lo que permite responder a soporte y a los negocios.
- Cuando lleguen los ads (Fase 4), el intercalado ya está definido: los ads compran **posiciones intercaladas**, no puntos en la fórmula.
