# Revisión 3 — Estado: en proceso

> **Por qué hay una tercera revisión.** La segunda no fue adversarial: fueron tres críticos
> parcheando **la misma dirección**, y lo que salió, por mucho que midiera bien, seguía siendo
> la dirección rechazada con otro CSS encima. El director la rechazó entera, paleta incluida, y
> tenía razón en el método: competir no es maquillar.
>
> Esta ronda vuelve al procedimiento que sí produjo una decisión: **tres direcciones a ciegas,
> cada una con su propia paleta, su propia tipografía y su propio movimiento**, en prototipos
> navegables y comparables; después tres críticos con lentes distintas que rechazan por defecto;
> y una elección **medida contra este listón**, no contra el gusto.

## Las tres direcciones

| | Dirección | Encargo |
|---|---|---|
| **1** | Noche de barrio panameño | Oscura por defecto, un solo neón que no sea naranja ni azul, luz cálida de interior. El movimiento es un letrero que se enciende |
| **2** | Revista de oficio | Clara, editorial, papel con cuerpo y tipografía con personalidad. Paleta que no sea beige+latón ni naranja+azul. El movimiento pasa páginas |
| **3** | Cinética de app | Clara, densa, alto contraste, cifras tabulares grandes. Un neutro con carácter y un solo saturado que no sea naranja ni azul. El movimiento es la estructura |

Cada una entrega un solo HTML que navega entre **cinco pantallas** (portada, resultados, ficha
con reserva, agenda del panel, lista de la consola) con datos reales de Panamá, y un `.md` con
paleta, fuentes y reglas de movimiento.

## El listón, escrito antes de ver ninguna

Se puntúa cada una de 0 a 3 en cada fila. **Una puntuación de 0 en una fila marcada con ★
descalifica** aunque el resto sea perfecto.

| | Criterio | Cómo se mide |
|---|---|---|
| ★ | **No parece generada.** Ni un componente reconocible como Material, Tailwind UI, shadcn, iOS por defecto, Squarespace o Webflow | El crítico de tells lo compara a ciegas y nombra el parecido si lo hay |
| ★ | **Tiene movimiento con propósito.** Entre pantallas y dentro de ellas; nada en bucle; todo se apaga con `prefers-reduced-motion` | Se cuenta: transiciones de pantalla, gestos de control, entradas de lista. Y se comprueba el apagado |
| ★ | **Cabe a 390 px y se ve espectacular a 1440.** Cero desplazamiento horizontal medido con `scrollWidth`, no con rectángulos | Playwright con `viewport` bien puesto, que la última vez se midió mal |
| ★ | **Contraste AA en todo texto**, medido con el color calculado y el fondo real | Fórmula WCAG en el DOM vivo |
| | **La paleta es suya**, no la de una plantilla ni la rechazada. Un solo saturado, racionado, con una regla de dónde sale | Se lee el `.md` y se cuenta dónde aparece el saturado |
| | **La tipografía tiene carácter y está justificada**, y explota algo (ancho, cifras, contraste de tamaños) más allá de «titular grande» | Se lee y se mira |
| | **Los estados existen**: vacío, carga y error en cada pantalla | Se buscan en el prototipo |
| | **Es Panamá y es verdad**: nombres, precios y barrios reales; cero cifras de escala inventadas | El crítico de negocio lo lee línea a línea |
| | **Resuelve la falta de foto con diseño**, no con un gris ni con una inicial | Se mira la ficha de un salón sin foto |
| | **Densidad y jerarquía cuidadas**: una agenda con siete citas se lee de un vistazo | El crítico de UX la usa |

## Los tres críticos

Reciben las tres a la vez, con la orden de **rechazar por defecto** y de justificar con fichero,
línea o captura cualquier cosa que aprueben:

1. **Tells de plantilla y de IA.** ¿A qué se parece? Que lo nombre.
2. **UX y UI de cerca.** Estados, jerarquía, densidad, objetivos táctiles, ritmo, propósito del
   movimiento. Que la use de pie, a 390 px.
3. **Negocio, marca y verdad.** ¿Se entiende en cinco segundos qué es? ¿Suena a Panamá? ¿Aguanta
   el marketplace con tres salones? ¿Miente en algo?

## Lo que cambia respecto de las rondas anteriores

- **La ganadora se implanta tal cual.** La vez anterior se eligió una dirección y la
  implementación se alejó sin que nadie lo midiera. Esta vez el HTML ganador es el contrato
  visual: el producto se compara contra él pantalla a pantalla, y **se vuelve a criticar el
  producto implementado**, no solo el prototipo.
- **Ninguna de las tres puede ser la rechazada con otro nombre.** Los tres agentes tienen
  prohibido leer la paleta, los componentes y el brandbook anteriores.
