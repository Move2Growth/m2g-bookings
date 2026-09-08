# ADR-0022 · La marca es Tanda

- **Estado:** aceptada
- **Fecha:** 2026-09-07
- **Supera:** [ADR-0015](0015-la-marca-es-bukeo.md), que fijaba el nombre en «Bukeo»
- **Afecta a:** [ADR-0013](0013-tokens-de-marca.md) (tokens) y [ADR-0021](0021-la-piel-es-papel-y-tinta-y-el-calendario-es-el-de-siempre.md) (la piel anterior)

## Contexto

«Bukeo» lo descartó Luis el 7 de septiembre: dos rondas de identidad murieron por el mismo
motivo de fondo —«todo me parece IA, reutilizado»—. La revisión 5 se hizo a ciegas con tres
direcciones completas en PDF, cada una con **nombre propio**, y Luis eligió la tercera.

Las tres compitieron con el mismo listón escrito **antes** de ver nada: claro por defecto, cero
tipografías delatoras, cero redondeo y degradado decorativos, contraste AA impreso y calculado,
logotipo generado y no dibujado con CSS, y nada a medias.

## Decisión

**[decisión]** La marca del producto es **Tanda**, en las tres superficies y en todo material.

En Panamá una tanda es el turno que va rotando. Es exactamente lo que hace una clienta que
vuelve cada tres semanas, y por eso la marca es el turno y no el negocio.

**[decisión]** La dirección visual es **bloques de color**, con el trabajo repartido y por
escrito:

| Tinta | Hex | Trabajo |
|---|---|---|
| Cobalto | `#1B34C4` | **Abre e informa**: buscar, crear, publicar, enlaces |
| Fucsia | `#C81E64` | **Cierra**: elegir hora, confirmar la cita |
| Amarillo | `#F5C400` | **Avisa**, y solo como superficie con tinta encima |
| Tinta | `#101014` | Todo el texto |
| Hueso | `#FBFBF9` | El fondo. El producto abre en claro |

- **[decisión]** Ninguno de los tres saturados es color de texto largo. El amarillo **nunca** es
  color de texto: no llega a AA sobre claro y esa es justamente la razón de la regla.
- **[decisión]** Las familias son **Familjen Grotesk** (rótulo) y **Public Sans** (texto y
  cifras), las dos variables y autoalojadas: un archivo por familia, ninguna petición a un
  tercero.
- **[decisión]** El sello es un círculo de seis porciones **al que le falta una**. Esa que falta
  es el turno que viene y **no se rellena nunca**. Va dibujado como geometría —cinco sectores de
  60° con 3° de aire— para que no dependa de que cargue una fuente y aguante a 16 px.

**[decisión]** El nombre **sigue sin escribirse a fuego en ninguna pantalla**, igual que con el
codename. Vive en `NOMBRE_COMERCIAL` y llega a la web como `NEXT_PUBLIC_NOMBRE_COMERCIAL`.
`make variables` **falla** si aparece en cualquier `.ts`/`.tsx` que no sea `lib/marca.ts`, y no
cuenta los comentarios: explicar de qué dirección salió un componente es documentación, no una
pantalla.

## Consecuencias

- **Se cerró un agujero al aplicarla.** `globales.css` importaba los tokens y **acto seguido los
  tapaba** con cuarenta líneas de color escritas a mano. `pnpm contraste` medía entonces una
  paleta y la pantalla pintaba otra. Ya no queda ni un hexadecimal en la hoja: todo sale de
  `@agenda/tokens`, así que cambiar de dirección vuelve a ser cambiar `tokens.json`.
- Las tres superficies con significado —**calle** (lo público), **local** (donde se trabaja) y
  **trastienda** (la consola de M2G)— se conservan con sus nombres, pero ahora se distinguen por
  temperatura y no por oscuridad, porque las tres son claras.
- El modo oscuro sigue definido y sin encender (Fase 6). Sus valores se rehicieron para Tanda y
  pasan AA en las mismas 41 combinaciones que el claro.
- **Queda pendiente el dominio.** El nombre está decidido; `tanda.com` y sus variantes no se han
  comprobado ni registrado, y eso es de Luis.

## Alternativas descartadas

- **Buenamano** (editorial, Archivo + Newsreader, verde savia): la más seria de las tres y la más
  fácil de confundir con una publicación. Descartada por Luis.
- **Cupo** (señalética, Schibsted Grotesk + IBM Plex Mono, un solo naranja): la más disciplinada,
  y la que peor aguantaba un salón que quiere verse alegre. Descartada por Luis.

Los tres libros están en `docs/marca/revision-5/salida/` y se regeneran con
`node pipeline/construir.mjs` más `node pipeline/libro.mjs`.
