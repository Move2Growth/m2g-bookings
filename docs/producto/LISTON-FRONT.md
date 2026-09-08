# El listón del frontend · Estado: en proceso

> **Escrito el 8 de septiembre de 2026, antes de ver una sola propuesta.** Si se escribe después,
> se escribe a la medida de lo que salió y no sirve para nada.
>
> El frontend anterior se borró entero (punto 0 del encargo). Esto no es un rediseño: es
> construir de cero. Tres direcciones compiten **a ciegas**, cada una con un **prototipo
> navegable de verdad**, y después las critican tres críticos cruzados. La ganadora **se implanta
> tal cual**; lo que se critica luego es el producto, no la propuesta.

---

## Lo que NO se decide aquí

La marca. **Es Tanda** (ADR-0022) y no se toca: hueso, tinta, cobalto que abre e informa, fucsia
que cierra, amarillo que solo avisa, Familjen Grotesk de rótulo y Public Sans de texto. Los
colores y la letra salen de `packages/tokens` y **no se escribe ni un hexadecimal**.

Lo que se compite es **el producto**: qué ve la clienta primero, cómo se llega a una hora, qué
pasa en la mano de quien lo usa. Tres maneras distintas de resolver las mismas pantallas.

## Los descartes (falla uno, fuera)

**D1 · Ni un hexadecimal, ni una familia tipográfica escrita a mano.** Todo sale de los tokens.
Esto ya se rompió una vez: la hoja anterior importaba los tokens y acto seguido los tapaba con
cuarenta líneas de color a mano, así que el verificador medía una paleta y la pantalla pintaba
otra. `grep -E "#[0-9a-fA-F]{3,6}" ` sobre el CSS de la propuesta tiene que dar **cero**.

**D2 · Nada a medias.** Un botón se entrega con sus **seis estados** (reposo, encima, pulsado,
cargando, inhabilitado, foco de teclado). Una pantalla se entrega **entera**, con su cabecera y
su pie. «Los botones están incompletos» ya fue textual una vez.

**D3 · Cero redondeo decorativo y cero degradado decorativo.** Un degradado solo se admite si
*significa* algo. Tarjetas con esquinas de 12 px por defecto es exactamente lo rechazado.

**D4 · Se navega de verdad contra la API local.** Nada de datos inventados en el componente:
las pantallas piden a `http://localhost:8000` y enseñan lo que responda. Una propuesta con datos
falsos no se puede juzgar, porque el problema siempre aparece con los datos de verdad.

**D5 · 390 px primero.** Si desborda a lo ancho a 390, está fuera. Se comprueba con
`scrollWidth`, no a ojo.

**D6 · Movimiento con motivo.** Todo lo que se mueve dice de dónde sale algo, confirma que se ha
tocado o tapa una espera. Nada en bucle. Todo se apaga con `prefers-reduced-motion`.

**D7 · AA de verdad.** Ninguna combinación por debajo de 4,5:1 en texto y 3:1 en elementos de
interfaz, medida **en la pantalla renderizada** y no en la paleta.

## Lo que cada dirección tiene que entregar navegable

No es una maqueta: es la aplicación. Cinco caminos completos, con sus estados de carga, de vacío
y de error:

| # | Camino | Qué tiene que poder hacerse de punta a punta |
|---|---|---|
| 1 | **Descubrir** | Portada → buscar → resultados → ficha de un salón |
| 2 | **Elegir persona** | Desde la ficha, ver a quién atiende y su perfil: años, reseñas, servicios que hace |
| 3 | **Reservar** | Elegir servicio → elegir día y hora → confirmar → verla en «mis citas» |
| 4 | **Entrar** | Correo y contraseña, con su error cuando la contraseña no vale |
| 5 | **El salón** | Entrar como dueño y ver su agenda del día |

Quien no entregue los cinco **navegables** no compite: se queda fuera sin críticos.

## Cómo se juzga

Cada crítico recibe **una sola dirección que no es la suya** y responde tres cosas:

1. **¿Pasa los siete descartes?** Uno a uno, con la prueba de cómo lo comprobó. Un descarte
   fallado es un rechazo, por bonita que sea.
2. **¿Los cinco caminos se recorren enteros?** Con lo que vio en cada uno.
3. **¿Qué es lo que esta dirección hace mejor que nadie, y qué es lo que hace peor?** Una frase
   cada una, concreta.

**Un crítico que proponga mejoras a su dirección invalida la ronda entera.** El trabajo del
crítico es decir si pasa el listón y qué la distingue, no rediseñarla.

## Y después

La ganadora **se implanta tal cual**, sin mezclar piezas de las otras: mezclar es como se llega
a un producto que no es de nadie. Una vez implantada, se critica **el producto** —lo que falla
usándolo— y eso ya es trabajo normal, no otra ronda.
