/**
 * Tipos de presentación de los componentes compartidos. **No son los tipos de la API**: aquí no
 * entra lógica de negocio (ADR-0013). Los tipos del contrato viven en `@agenda/api-types`, se
 * generan del OpenAPI y los consume `apps/web`, que traduce de aquéllos a éstos.
 */

/**
 * Los seis estados de una reserva, tal y como los serializa la API: **minúsculas con guion bajo**
 * (ADR-0012). El componente de estado normaliza igualmente lo que reciba, porque en la casa ya se
 * ha roto un front por comparar en minúsculas lo que llegaba en mayúsculas.
 */
export type EstadoReserva =
  | 'pendiente'
  | 'confirmada'
  | 'completada'
  | 'no_show'
  | 'cancelada_cliente'
  | 'cancelada_negocio';

/** Las cinco familias de color: `cancelada_cliente` y `cancelada_negocio` comparten la suya. */
export type FamiliaEstado = 'pendiente' | 'confirmada' | 'completada' | 'no_show' | 'cancelada';

/** Franja del día por la que se agrupan los huecos en el selector de hora. */
export type FranjaDelDia = 'manana' | 'tarde' | 'noche';

/** Un día de la tira horizontal del selector de fecha. */
export interface DiaDisponible {
  /** Fecha local del negocio en formato `AAAA-MM-DD`. */
  fecha: string;
  /** Abreviatura del día: «lun», «mar»… Se formatea fuera del componente. */
  diaSemana: string;
  /** Número del día del mes, ya formateado. */
  diaMes: string;
  /**
   * Derivado de la respuesta de disponibilidad, **nunca adivinado**: la API dice si hay huecos.
   */
  hayHuecos: boolean;
}

/**
 * Un hueco. No lleva identificador reservable ni bloqueo temporal: el slot no se aparta, se compite
 * por él al confirmar (ADR-0004).
 */
export interface HuecoDisponible {
  /** Instante de comienzo en ISO-8601 con desplazamiento explícito. Es la clave de la lista. */
  comienzo: string;
  /** La hora ya formateada en la zona del negocio: «09:15». La interfaz no hace aritmética de husos. */
  hora: string;
  franja: FranjaDelDia;
  /** Nombre del profesional, cuando el modo es «cualquiera disponible» y hace falta decirlo. */
  profesional?: string;
}

/** Una línea de servicio dentro de una tarjeta de cita. */
export interface LineaDeServicio {
  nombre: string;
  /** «45 min», «3 h». Formateado fuera. */
  duracion: string;
  /** «$18», «desde $120», «A consultar». Formateado fuera, con su moneda. */
  precio: string;
}
