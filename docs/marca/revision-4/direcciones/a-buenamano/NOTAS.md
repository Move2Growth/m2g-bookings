# Buenamano · por qué cada cosa · Estado: completado

Dirección A. Semilla: **lo que se reserva es una persona, no un local.**

## El nombre

**Buenamano.** Sale de lo que ya se dice en Panamá cuando se recomienda a alguien: *«esa muchacha
tiene buena mano pa' las trenzas»*. Es la frase con la que una clienta describe exactamente lo que
esta plataforma vende, y no la inventé yo.

Por qué aguanta:

- **Nombra a una persona, no a un sitio.** Un local no tiene manos. Una peluquera, sí. El nombre
  ya excluye el «directorio de negocios» que no queremos ser.
- **Se dice por teléfono sin deletrear.** Nueve letras, todas del castellano común, sin ñ, sin
  tilde, sin dígrafo raro, sin anglicismo. «Buenamano, todo junto.»
- **Es de aquí.** «Buena mano» no se dice en Berlín ni en un SaaS de agendas. Un panameño lo
  entiende antes de que le expliquen el producto.
- **Deja sitio al elogio.** El nombre es lo que la clienta ya piensa de su profesional, así que la
  marca se pone del lado de ella y no del sistema.

Se escribe siempre en minúscula y en una sola palabra: `buenamano`. Con mayúscula inicial se
convierte en una empresa; en minúscula sigue siendo una manera de hablar.

## Los dos signos

**El sello** es una huella dactilar de tres anillos atravesada por una barra recta. Los anillos son
la persona (única, irrepetible); la barra es la marca en la regla de horas. *Una persona, marcada a
una hora* — que es literalmente la transacción del producto. Sale de Higgsfield en vectorial y no
se retocó más que el color y el encuadre.

**La cinta de horas** es el segundo signo y hace el trabajo que un logotipo no puede hacer: enseña
que lo que se compra es el hueco. Lo ocupado se pinta en tinta maciza y el hueco se deja en papel,
para que la vista caiga en el blanco. El próximo libre lleva un aro de achiote.

De la unión de los dos sale la única regla de forma del sistema: **todo va a cero de radio menos el
círculo del retrato.** Un círculo, en Buenamano, quiere decir «aquí hay alguien».

## Los tres casos difíciles de la semilla

Están resueltos en la página 02 y usados de verdad en las pantallas de la 09, no mencionados:

1. **No ha subido foto.** Se le calcula una **huella** a partir de su nombre: número de anillos,
   huecos, giro y tinta salen de un hash del nombre, así que es determinista, suya y no se repite.
   El código que la dibuja está en el propio `libro.html` y es el mismo que iría en producto. Un
   monigote gris habría dicho «falta algo»; la huella dice «es ella».
2. **Sola o en equipo de seis.** La independiente lleva su retrato y el sello «Trabaja sola». El
   equipo se pinta como retratos apilados con «+3 más», y cada cara abre su propia agenda: en la
   pantalla C el día del salón son cuatro columnas, una por persona, no una sola agenda del local.
3. **Recién llegada.** Aro de achiote alrededor del retrato, «Nueva · sin reseñas» escrito tal
   cual, y la columna de su agenda casi vacía. No se inventan estrellas ni se esconde el cero.

## Las tintas

Papel crudo, tinta casi negra, un **añil** de bordado de pollera y un **achiote** —el rojo de la
semilla con la que se cocina aquí—. No es la paleta de un SaaS: es la de un cuaderno de citas de
un salón panameño.

Los ratios están medidos, no estimados, y los que no pasan están escritos como prohibidos:
`bruma` no es color de texto (1,28:1) y `ceniza` no se usa sobre `bruma` (4,24:1). Por eso el
estado inhabilitado se dibuja con **papel y trama**, no con relleno gris: así el texto sigue a
5,42:1 y no hay que refugiarse en la excepción que WCAG da a los controles apagados.

El añil tiene tope: 8 % de la superficie. El achiote, uno por pantalla.

## Las tipografías

**Alegreya** (Huerta Tipográfica, Buenos Aires) y **Archivo** (Omnibus-Type, Buenos Aires). Las
dos están dibujadas en Latinoamérica y para textos en español, con la ñ y las tildes resueltas de
origen y no como parche. Ninguna es de la lista de fuentes delatoras.

La regla que las reparte no es estética, es de producto: **si tiene nombre y apellido, va en
Alegreya; todo lo demás, en Archivo.** La serifa es la persona; el palo seco es el sistema. Así,
en cualquier pantalla, la mirada encuentra a quién antes que a qué.

Archivo entra con su eje de ancho (62–125 %) para que los rótulos del sistema puedan ensancharse
sin cambiar de familia.

## El botón

El botón tiene una anatomía propia y no la de una biblioteca: cero de radio, alto 44, holgura 18
y un **canto** de 2 px más oscuro por debajo. El canto es la línea de la regla de horas metida en
el control. Al pasar por encima el canto crece a 4 px; **al pulsar desaparece y el botón baja 2 px**,
como si se apoyara en el papel. Cargando conserva el color de pulsado y cambia el canto por una
barra segmentada. El foco es un contorno de 2,5 px separado 3 px, cuadrado, nunca un halo.

Los seis estados están dibujados de verdad en la página 08, para los cuatro tipos, y debajo van el
campo de texto con sus seis estados, el selector de hora y los chips.

## Lo que no me gusta de mi propia propuesta

- **El retrato de quien sí tiene foto está fingido.** No se admiten fotografías en el libro, así
  que la foto se representa con una silueta sobre los anillos de la huella. Funciona como sistema,
  pero nadie ha visto todavía cómo queda el conjunto con caras reales encima, que es el 70 % de
  las pantallas.
- **La huella depende del nombre, y los nombres se repiten.** Dos «María González» en la misma
  ciudad tendrían la misma huella. Habría que sembrar el hash con el identificador, no con el
  nombre, y eso rompe la promesa de «se calcula de tu nombre».
- **Buenamano no dice «reservar».** Dice quién, no qué. Cuesta un cartel más en la calle explicar
  que esto es una agenda y no un directorio de recomendaciones.
- **El achiote está muy cerca del rojo de error.** Aquí significa «tu próximo hueco», que es una
  buena noticia, y a la vez tiñe «cancelar». Es la decisión más frágil de la paleta.
- **Alegreya en cifras grandes.** Sus números son elegantes pero de estilo antiguo en algunos
  pesos; toda la numeración se ha empujado a Archivo tabular, y eso deja a la serifa haciendo un
  solo trabajo. Defendible, pero es una familia entera para los nombres.

## Créditos gastados

Tres intentos de logotipo en Higgsfield (`recraft_v4_1`, vectorial), **7,5 créditos** de los 20
del presupuesto. El elegido es el tercero. Los otros dos quedan en `logo/intento-1.svg` y
`logo/intento-2.svg` por si el director prefiere la huella sin barra.
