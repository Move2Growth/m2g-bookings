# Encargo común a las tres direcciones · revisión 4

Lo lee cada dirección entero. Lo que cambia entre una y otra es **una sola línea**: su semilla
estratégica. Todo lo demás es idéntico, para que la comparación sea honesta.

## Qué es el producto

Una **plataforma de reservas y marketplace de belleza y bienestar en Panamá**: peluquerías,
barberías, uñas, pestañas, depilación, spa. Tres cosas la definen y ninguna es negociable:

1. **Es gratis para el salón.** No se le cobra por gestionar su agenda. El dinero sale de
   posicionamiento pagado, no de una cuota.
2. **El cliente elige a una persona, no a un local.** Ve al profesional, su perfil, sus fotos,
   cuánta gente ha atendido, sus reseñas y su calendario, y reserva con él o con ella.
3. **Es de Panamá y para Panamá.** Ciudad de Panamá, teléfono en la mano, datos móviles.

Quien lo usa: una clienta buscando una hora esta tarde, y una profesional que trabaja de pie
todo el día y mira esto entre cliente y cliente. **No es un SaaS de escritorio.**

## Qué hay que entregar

**Un brandbook en PDF**, apaisado, diez páginas, en la estructura y con los descartes de
[`LISTON.md`](LISTON.md) — que se lee antes de empezar y manda sobre este documento.

Y con él, **un nombre**. El nombre es tuyo y es parte de la propuesta: no hay marca previa, la
anterior se descartó. Que se pueda decir por teléfono en Panamá sin deletrearlo.

## Lo que se entrega, archivo por archivo

Todo dentro de tu carpeta `direcciones/<TU-LETRA>-<tu-slug>/`, y **solo ahí**:

| Archivo | Qué es |
|---|---|
| `libro.html` | El brandbook. Una `<section class="pagina">` por página, de 1122.5×793.7 px exactos |
| `marca.json` | Las tintas con su hex y su ratio de contraste, las familias tipográficas y sus pesos |
| `logo/` | Los SVG que devuelva Higgsfield, con el elegido como `logo/principal.svg` |
| `fuentes/` | Lo que deje el descargador de tipografías |
| `NOTAS.md` | Por qué cada decisión. Corto. Lo que no sabrías defender en voz alta, fuera |

## La maquinaria

Tipografías (se bajan a tu carpeta, no compartas nada):

```bash
node pipeline/fuentes.mjs direcciones/<TU-CARPETA>/fuentes "Familia:wght@400;700"
```

En el `libro.html`, `<link rel="stylesheet" href="./fuentes/fuentes.css">`.

Montar el PDF:

```bash
node pipeline/libro.mjs direcciones/<TU-CARPETA>/libro.html salida/<Nombre>_BrandBook.pdf
```

**El renderizador falla a propósito** si una página se desborda o si una tipografía declarada no
cargó. Un libro que no pasa el renderizador no está entregado.

## El logotipo

Sale de Higgsfield, en vectorial, y **no se dibuja con CSS**:

```bash
higgsfield generate create recraft_v4_1 --model_type vector --aspect_ratio 1:1 \
  --resolution 1k --background_color '#TU_FONDO' --wait --json < prompt.txt
```

Devuelve un `result_url` con un `.svg`: se descarga con `curl` a `logo/`. Cuesta **2,5 créditos**
por intento y tienes **ocho como máximo**. No es una restricción de estilo, es que la última vez
se fundieron los créditos generando cosas que no hacían falta.

Pide **símbolo solo, sin letras**: los logotipos con texto salen con las letras deformadas
siempre. El nombre lo compones tú con la tipografía elegida, al lado del símbolo.

**Nada de fotos.** Ni de servicios, ni de salones, ni de moodboard. Las seis piezas del moodboard
se dibujan con CSS y SVG, como hace el brandbook de RŪTA que es la referencia.

## Cómo se juzga

Contra el listón, por un crítico que no eres tú y que no sabe de quién es el libro. Después
elige el director entre las tres. **Una dirección que falle un descarte no llega a enseñarse.**

## Reglas de la partida

- **Vas a ciegas.** No abras las carpetas de las otras letras, ni `docs/marca/revision-2` o
  `revision-3`, ni `BRANDBOOK-BUKEO.md`. Si copias, se nota, y las dos rondas anteriores se
  rechazaron precisamente por parecer todas la misma cosa.
- **No toques nada fuera de tu carpeta.** Ni `packages/tokens`, ni `apps/`, ni el pipeline.
- **No hagas commit.** Ni `git add`, ni `git commit`, ni `git push`. De eso me encargo yo.
- Escribe en español, con sus tildes, y con la ñ donde toca.
