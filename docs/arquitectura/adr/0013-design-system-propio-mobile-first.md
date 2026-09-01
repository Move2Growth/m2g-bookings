# ADR-0013 · Design system propio, mobile-first, con tokens como fuente única

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

El brief §8 pide design system propio y mobile-first. El encargo pone límites explícitos: **modo claro por defecto**, nada de tarjetas y botones redondeados por todas partes, ni degradados decorativos, ni scrollytelling, y **ni Inter, ni Fraunces, ni Bricolage, ni General Sans**. Se valida **a 390 px**, que es donde vive el producto.

Hay además una restricción física que manda sobre la estética: **teléfono de gama media con 3G**, y una persona con las manos ocupadas mirando la pantalla a un brazo de distancia dentro de un salón con luz fuerte.

## Decisión

**[decisión]** Design system propio, con **`packages/tokens` como fuente única**: un JSON de tokens del que se generan variables CSS para web y back-office y un módulo TypeScript para React Native. Ningún color, ninguna medida y ningún tamaño de letra se escribe suelto en un componente.

**Tipografía.** **IBM Plex Sans** como única familia, con **cifras tabulares** en horas, precios y duraciones — en una agenda las columnas de horas tienen que alinearse. Es abierta, tiene buen dibujo a tamaños pequeños y no está entre las vetadas. Escala de un solo eje, mínimo **16 px** en cuerpo de texto: por debajo, iOS hace zoom en los campos de formulario y el diseño se descuadra solo.

**Color.** Paleta de modo claro como base, definida por función y no por tono (`superficie`, `superficie-elevada`, `borde`, `texto`, `texto-suave`, `acento`, `peligro`, `aviso`, `exito`), y los estados de una reserva con color propio y **estable en las tres superficies**: pendiente, confirmada, completada, no-show, cancelada. Contraste **AA** verificado, incluidos los estados: un color de estado que no se lee al sol no informa de nada.

**Forma.** Radios contenidos y consistentes; sombras solo donde comunican elevación real (una hoja modal, un menú), nunca como decoración. Sin degradados decorativos.

**Densidad y toque.** Objetivo táctil mínimo de **44 px**; en la agenda, donde se toca mucho y con prisa, la fila de cita es el objetivo entero. Separación entre acciones destructivas y frecuentes: cancelar una cita no puede estar pegado a moverla.

- **[decisión]** **Se diseña a 390 px primero** y se ensancha después. No al revés: un diseño de escritorio comprimido siempre acaba con la acción principal fuera de pantalla.
- **[decisión]** El modo oscuro **se prepara con tokens desde el día uno** pero no es la Fase 1. Lo que no se hace es cablear colores: eso convertiría el modo oscuro en un rediseño.
- **[decisión]** **Todos los textos externalizados desde el primer componente** (§6 del brief), aunque solo haya español. Recorrer la interfaz después buscando cadenas es el trabajo que nadie hace.
- **[decisión]** Los componentes compartidos viven en `packages/ui` y **no dependen de la lógica de negocio**. Móvil no consume ese paquete (ADR-0001): comparte tokens, no componentes.
- **[decisión]** Ninguna pantalla se da por hecha sin verla **en el navegador a 390 px**. «Build verde» no es evidencia.

## Alternativas consideradas

- **Una librería de componentes ya hecha (MUI, Chakra, shadcn/ui).** Descartado como base: arrastran su propio lenguaje visual y este producto tiene vetos estéticos explícitos; adaptarlas cuesta más que partir de tokens. Piezas sueltas sin estilo (menús, diálogos, calendarios accesibles) sí se pueden usar como base de comportamiento.
- **Tailwind sin capa de tokens.** Descartado: la escala de utilidades acaba siendo la fuente de verdad y el móvil no la comparte. Tailwind sí se usa **consumiendo los tokens**, no definiéndolos.
- **Sistema tipográfico de dos familias.** Descartado para v1: una familia bien usada rinde más que dos mal combinadas, y pesa la mitad en 3G.

## Consecuencias

- Hay una tarea real de diseño antes de las pantallas (Fase 0), con el **Mockuper por delante del frontend**.
- El presupuesto de fuentes es limitado: se cargan **los pesos que se usan y nada más**, en formato variable, y se sirven desde el propio dominio.
- Cambiar la identidad cuando se decida el nombre comercial (D1) es cambiar tokens, no pantallas. Por eso el nombre tampoco se mete a fuego en la interfaz.
