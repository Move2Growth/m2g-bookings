# ADR-0018 · Donde no hay foto va un rótulo

- **Estado:** aceptada
- **Fecha:** 2026-09-02
- **Complementa a:** ADR-0016 y ADR-0017, que fijaron el color y la forma y no dijeron qué se
  enseña cuando no hay imagen

## Contexto

En todo el repositorio hay **dos fotografías**: `unas.webp` y `spa.webp`. Los otros nueve salones
del seed se pintaban con **la inicial del nombre sobre un rectángulo de color**, con el color
rotando por posición en la lista, o sea el color sin significar nada.

Luis dijo que no le vale que haya cosas sin imágenes. Y **no se pueden generar**: la cuenta de
Higgsfield está en plan ultra con 0,25 créditos y una imagen cuesta 2. Comprobado intentando una
generación real, no leyendo el saldo:

```
{"error_type":"not_enough_credits","plan_type":"ultra","billing_period":"monthly"}
```

La pregunta, entonces, no es «qué imagen ponemos» sino **qué se enseña cuando no hay ninguna y no
puede haberla**.

## Decisión

**[decisión] Donde no hay fotografía va un rótulo, y el rótulo no es un sustituto: es la forma
por defecto de presentar un salón.** Cuando hay foto, la foto manda. Cuando no la hay, el rótulo
es la pieza normal del sistema, no un hueco tapado.

Sale del brandbook y no del gusto de nadie: del apartado 03, que dice que el lenguaje de esta
marca es «el del rótulo pintado de un local, no el de una aplicación»; del moodboard, que ya
nombraba el rótulo pintado y la rejilla de horas; y del apartado 06, que tenía la tipografía a
tamaño de cartel sin usar fuera de la portada.

**[decisión] El rótulo tiene tres ingredientes:**

1. **El nombre entero** a tamaño de cartel, en versales y ancho de rótulo. **El nombre, no la
   inicial**: una inicial es un avatar y un nombre grande es un rótulo. Y es lo único que
   distingue de verdad a un salón de otro.
2. **La trama del oficio**, dibujada a trazo y aplicada **como máscara**, así que hereda el color
   del bloque igual que el logotipo hereda con `currentColor`. Un mismo archivo sirve sobre azul,
   sobre tinta y sobre naranja.
3. **Un par de colores** de la paleta, elegido por la posición en la lista.

**[decisión] La trama distingue el oficio, no el negocio.** Dos barberías del barrio comparten el
poste rojiblanco y nadie las confunde. Con seis tramas y cuatro pares hay veinticuatro
combinaciones para once salones, y aun con la trama repetida el rótulo nunca lo está.

**[decisión] El par de colores vive en el elemento que lleva el texto, no en el rótulo.** Si
viviera en un hermano, el nombre se quedaría sin fondo real: bastaría con que el rótulo no
pintara para que el texto desapareciera. Lo cazó el verificador de contraste en pantalla.

**[decisión] Tres tallas y ninguna más:** cartel para la cabecera de una ficha, sello para la
lista, y fondo para las celdas donde el nombre ya está escrito encima.

## Alternativas consideradas

- **Fotografía de banco.** Prohibida por el encargo y ya rechazada en `DECISION-DE-MARCA.md`.
  Además miente sobre cómo es el sitio, y este producto vende precisamente que la hora que se ve
  es la hora que existe.
- **Imágenes generadas.** No se pueden hacer, comprobado arriba.
- **Ilustración a color.** Dos o tres se ven bien y once se ven repetidas, y cada una son
  kilobytes que en 3G se notan.
- **Seguir con la inicial sobre un rectángulo.** Es el parche que había que quitar.

## Consecuencias

- **Todo el sistema, con sus seis tramas, pesa 1.369 bytes comprimido**: el 2,4 % de una sola
  fotografía servida a 640 px, y **sin una petición de red más**.
- **Habilita** que la portada, el buscador y la ficha hablen el mismo idioma: la celda de
  categoría y la presentación de un salón son la misma pieza.
- **Obliga** a que cada salón tenga una categoría asignada, que ya la tiene, y a añadir una trama
  el día que se abra una familia de servicio nueva.
- **No cierra la puerta a la fotografía**: el día que haya crédito o un salón suba su foto, la
  foto ocupa el sitio del rótulo sin tocar una línea de componente.
