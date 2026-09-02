/**
 * Todos los textos de interfaz de los componentes compartidos, externalizados desde el primer
 * componente (ADR-0013). Hoy solo hay español de Panamá; el día que entre otro idioma esto se
 * convierte en el diccionario por defecto y no hay que recorrer el JSX buscando cadenas.
 *
 * Regla del design system §6.7: el texto dice **qué pasó y qué hacer ahora**, en ese orden, y
 * nunca culpa a la persona.
 */
export const textos = {
  boton: {
    cargando: 'Un momento…',
    /** Se anuncia al lector de pantalla mientras la petición está en vuelo. */
    cargandoAccesible: 'Enviando, espera un momento',
  },
  campo: {
    opcional: 'opcional',
    caracteresRestantes: (restantes: number) =>
      restantes === 1 ? 'Queda 1 carácter' : `Quedan ${restantes} caracteres`,
    caracteresPasados: (pasados: number) =>
      pasados === 1 ? 'Te pasaste por 1 carácter' : `Te pasaste por ${pasados} caracteres`,
  },
  selector: {
    tituloDias: 'Elige el día',
    tituloHoras: 'Elige la hora',
    honestidad: 'Estos son los huecos ahora mismo.',
    hayHuecos: 'con huecos',
    sinHuecos: 'sin huecos',
    franjas: {
      manana: 'Mañana',
      tarde: 'Tarde',
      noche: 'Noche',
    },
    diaSinHuecos: 'No quedan huecos este día.',
    saltarAPrimerHueco: (cuando: string) => `El primer hueco es el ${cuando}`,
    nadaEnSesentaDias:
      'Este salón no tiene huecos en los próximos 60 días. No está roto: está lleno.',
    escribirPorWhatsapp: 'Escribir por WhatsApp',
    cargando: 'Buscando huecos…',
    rejillaAccesible: 'Horas disponibles. Usa las flechas para moverte entre horas.',
  },
  cita: {
    servicios: 'Servicios',
    profesional: 'Profesional',
    notas: 'Notas',
    total: 'Total',
    duracionTotal: 'Duración',
  },
  agenda: {
    huecoLibre: (duracion: string) => `${duracion} libres`,
    reservarEnHueco: 'Reservar aquí',
    sinEnviar: 'Sin enviar',
    sinEnviarExplicacion: 'Esta acción todavía no llegó al servidor.',
    filaAccesible: (hora: string, cliente: string, servicio: string) =>
      `${hora}, ${cliente}, ${servicio}. Toca para ver el detalle.`,
  },
  hoja: {
    cerrar: 'Cerrar',
    arrastrarParaCerrar: 'Arrastra hacia abajo para cerrar',
  },
  error: {
    tituloBloque: 'No se pudo completar',
  },
  estados: {
    pendiente: 'Pendiente',
    confirmada: 'Confirmada',
    completada: 'Completada',
    no_show: 'No vino',
    cancelada: 'Cancelada',
    cancelada_cliente: 'Cancelada por el cliente',
    cancelada_negocio: 'Cancelada por el salón',
    desconocido: 'Estado desconocido',
  },
  carga: {
    enCurso: 'Cargando…',
  },
} as const;

export type Textos = typeof textos;
