/* Generado por generar.mjs a partir de tokens.json. No editar a mano. */

export const tokens = {
  "_marca": [
    "Tanda — tokens de marca, dirección «bloques de color» elegida por Luis el 7 de septiembre.",
    "El producto abre en CLARO: hueso, tinta, y tres saturados con el trabajo repartido.",
    "",
    "LA REGLA QUE NO SE ROMPE: el COBALTO —`acento`— ABRE e informa (buscar, crear, publicar,",
    "enlaces) y el FUCSIA —`cierra`— CIERRA (elegir hora, confirmar la cita). Nunca compiten en",
    "el mismo botón. El token se llama `cierra` y no `abre` porque antes se llamaba así y era",
    "mentira: la clase que lo usa es `.boton--cierra`.",
    "",
    "El AMARILLO —`aviso`— es solo superficie, con tinta encima: nunca es color de texto, porque",
    "sobre claro no llega a AA. Esa es justo la razón de la regla.",
    "",
    "Ninguno de los tres es color de texto largo: el texto es tinta, y la tinta-tenue lo secundario.",
    "El porqué de cada decisión está en docs/marca/revision-5/direcciones/c-tanda/ y en ADR-0022."
  ],
  "color": {
    "claro": {
      "_nota": "La superficie por defecto. Hueso y no blanco puro: el blanco se reserva para lo que se levanta.",
      "papel": "#FBFBF9",
      "lienzo": "#FFFFFF",
      "arena": "#F1F1EE",
      "borde": "#D8D8D2",
      "borde-fuerte": "#6E6E68",
      "tinta": "#101014",
      "tinta-suave": "#3A3A42",
      "tinta-tenue": "#5C5C66",
      "acento": "#1B34C4",
      "acento-hover": "#14289C",
      "acento-suave": "#E6E9FB",
      "acento-texto": "#FFFFFF",
      "cierra": "#C81E64",
      "cierra-hover": "#A3184F",
      "cierra-suave": "#FCE7EF",
      "cierra-texto": "#FFFFFF",
      "exito": "#0F6B4F",
      "exito-suave": "#E2F2EC",
      "aviso": "#7A5A00",
      "aviso-suave": "#FFF3C4",
      "peligro": "#B3123A",
      "peligro-suave": "#FCE4EA",
      "foco": "#101014",
      "velo": "rgba(16, 16, 20, 0.62)"
    },
    "oscuro": {
      "_nota": "El tema alternativo (Fase 6). Mismos papeles semánticos: los tres saturados suben de luz para poder vivir sobre tinta, y el amarillo sigue sin ser color de texto.",
      "papel": "#0C0C10",
      "lienzo": "#121218",
      "arena": "#17171F",
      "borde": "#2A2A34",
      "borde-fuerte": "#7A7A88",
      "tinta": "#F7F7F4",
      "tinta-suave": "#C6C6CE",
      "tinta-tenue": "#9A9AA6",
      "acento": "#8FA0FF",
      "acento-hover": "#AFBBFF",
      "acento-suave": "#141B3A",
      "acento-texto": "#0C0C10",
      "cierra": "#FF5C93",
      "cierra-hover": "#FF83AC",
      "cierra-suave": "#3A1024",
      "cierra-texto": "#0C0C10",
      "exito": "#49D9A2",
      "exito-suave": "#0E2A20",
      "aviso": "#F5C400",
      "aviso-suave": "#2E2400",
      "peligro": "#FF6B81",
      "peligro-suave": "#33101A",
      "foco": "#F7F7F4",
      "velo": "rgba(0, 0, 0, 0.68)"
    }
  },
  "estado-reserva": {
    "_nota": "Los cinco estados de una cita, iguales en la web, el panel y la app. Ninguno usa el azul ni el naranja de marca: un estado no es una acción, y confundirlos hace que la gente toque lo que no debe.",
    "pendiente": {
      "fondo": "#FBEDD6",
      "texto": "#6B4105",
      "borde": "#DBA646"
    },
    "confirmada": {
      "fondo": "#E1EFE7",
      "texto": "#0F4E2D",
      "borde": "#5A9C77"
    },
    "completada": {
      "fondo": "#E6E9EF",
      "texto": "#2C3A52",
      "borde": "#7C89A3"
    },
    "no_show": {
      "fondo": "#E7E9E2",
      "texto": "#4A5163",
      "borde": "#AEB3A8"
    },
    "cancelada": {
      "fondo": "#FAE7E7",
      "texto": "#8A1216",
      "borde": "#D49A9A"
    }
  },
  "tipografia": {
    "_nota": "Familjen Grotesk para rótulo: grotesca con carácter en las diagonales, que aguanta un titular muy grande sin parecer una plantilla. Public Sans para texto y cifras: neutra, de lectura larga y con cifras tabulares de verdad, que en una agenda no es un detalle. Las dos autoalojadas.",
    "familia-display": "\"Familjen Grotesk\", \"Helvetica Neue\", Arial, sans-serif",
    "familia": "\"Public Sans\", \"Helvetica Neue\", Arial, sans-serif",
    "cifras-tabulares": "tabular-nums",
    "pesos": {
      "normal": 400,
      "medio": 500,
      "fuerte": 600,
      "display": 700
    },
    "tamano": {
      "micro": "0.75rem",
      "menor": "0.875rem",
      "cuerpo": "1rem",
      "mayor": "1.125rem",
      "titulo-4": "1.25rem",
      "titulo-3": "1.5rem",
      "titulo-2": "2rem",
      "titulo-1": "2.75rem",
      "cartel": "4.25rem"
    },
    "interlineado": {
      "apretado": 0.94,
      "titulo": 1.08,
      "normal": 1.5,
      "suelto": 1.65
    },
    "espaciado": {
      "titular": "-0.02em",
      "normal": "0",
      "etiqueta": "0.08em"
    }
  },
  "espacio": {
    "0": "0",
    "1": "0.25rem",
    "2": "0.5rem",
    "3": "0.75rem",
    "4": "1rem",
    "5": "1.5rem",
    "6": "2rem",
    "7": "3rem",
    "8": "4rem",
    "9": "6.5rem",
    "_nota": "Escala de 4 px. Objetivo táctil mínimo de 44 px; en la agenda, la fila entera es el objetivo.",
    "toque-minimo": "44px"
  },
  "radio": {
    "_nota": "Una sola escala de radio en todo el producto: 4 px en cualquier cosa que se toque y 0 en superficies y bloques de color. La pildora se retira con la direccion B: en un lenguaje de rotulo de local no hay nada redondeado salvo el avatar.",
    "superficie": "0",
    "control": "4px",
    "pildora": "999px"
  },
  "sombra": {
    "_nota": "Casi ninguna. En una dirección de bloques planos, la sombra rompe el plano; lo que separa es el cambio de color.",
    "ninguna": "none",
    "menu": "0 2px 10px rgba(13, 21, 38, 0.16)",
    "hoja": "0 -2px 24px rgba(13, 21, 38, 0.22)",
    "elevada": "0 1px 2px rgba(13, 21, 38, 0.08)"
  },
  "pantalla": {
    "_nota": "Se diseña a 390 px primero y se ensancha después.",
    "movil": "390px",
    "tableta": "768px",
    "escritorio": "1024px",
    "ancho": "1160px"
  },
  "movimiento": {
    "_nota": "Contenido a proposito: esto se usa en 3G y en gama media. La regla no es «poco «movimiento», es que TODO movimiento tenga un motivo: decir de donde sale algo, confirmar que se ha tocado o tapar una espera. Nada se mueve solo en bucle. Todo se apaga con prefers-reduced-motion.",
    "instante": "90ms",
    "rapido": "120ms",
    "normal": "240ms",
    "lento": "340ms",
    "curva": "cubic-bezier(0.2, 0.85, 0.25, 1)",
    "curva-salida": "cubic-bezier(0.4, 0, 1, 1)",
    "curva-empuje": "cubic-bezier(0.34, 1.3, 0.64, 1)",
    "escalonado": "34ms"
  },
  "canto": {
    "_nota": "El zocalo macizo que llevan dentro las cosas que se tocan. Su grosor ES la jerarquia: 4 px la accion que abre o cierra, 3 px la secundaria, 2 px la de texto, 0 lo que no se toca. Al pasar por encima crece a 6 px, la chapa se levanta, y al pulsar se lo traga. La mordida es lo que le falta por la derecha: la muesca calada del icono de la marca.",
    "principal": "4px",
    "secundario": "3px",
    "menor": "2px",
    "alzado": "6px",
    "mordida": "14px"
  },
  "filo": {
    "_nota": "La barra maciza que dice «estas aqui» o «esto esta elegido». Misma medida que el filo de bloque del brandbook y distinto color a proposito: el naranja se reserva para cortar la pagina entre bloques, o dejaria de significar «abre».",
    "grosor": "6px"
  },
  "foco": {
    "_nota": "No es del color de marca (ADR-0016): tinta sobre claro y cal dentro de bloques oscuros, resuelto con una variable y no con una lista de selectores.",
    "grosor": "3px",
    "separacion": "2px"
  },
  "_direccion": "Dirección C de la revisión 5, «Tanda», elegida por Luis el 7 de septiembre de 2026. Claro por defecto. El color va en BLOQUES, no en degradados: cada bloque es una decisión. Cobalto lo que informa y abre, fucsia lo que se toca y cierra, amarillo lo que avisa. El nombre viene del turno que rota: la clienta que vuelve cada tres semanas.",
  "superficie": {
    "_nota": "Los tres ambientes. No son grises: dicen DÓNDE estás. La CALLE es lo público, el LOCAL es donde se trabaja —panel del salón y área de la clienta— y la TRASTIENDA es la consola de M2G. En Tanda los tres son claros y se distinguen por temperatura, no por oscuridad: la calle es hueso, el local es blanco puro y la trastienda tira a frío.",
    "calle": "#FBFBF9",
    "calle-media": "#F4F4F1",
    "calle-alta": "#EDEDE9",
    "calle-borde": "#DCDCD6",
    "local": "#FFFFFF",
    "local-media": "#F7F7F5",
    "local-alta": "#EFEFEC",
    "local-borde": "#D8D8D2",
    "trastienda": "#F2F3F5",
    "trastienda-media": "#EAECEF",
    "trastienda-alta": "#E1E4E8",
    "trastienda-borde": "#CBD0D6"
  },
  "neon": {
    "_nota": "Medidas del filete macizo que marca lo que se puede tocar y lo que está elegido. Conserva el nombre porque toda la hoja de estilo lo usa; en Tanda no es un tubo de neón sino el canto de un bloque de color.",
    "tubo": "3px",
    "golpe": "4px"
  }
} as const;

export type Tokens = typeof tokens;
