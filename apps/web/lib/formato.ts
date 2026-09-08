/**
 * Cómo se escriben las horas, los días y el dinero.
 *
 * Regla de la casa: **la hora que se pinta es la del salón, no la del navegador**. La API
 * devuelve la zona horaria de cada negocio (`America/Panama` en los datos de ejemplo) y aquí
 * se usa siempre esa; si se usara la del dispositivo, alguien que abra desde España vería una
 * cita a las 10 que en el local es a las 3.
 */

const ZONA_POR_DEFECTO = 'America/Panama';

export function hora(iso: string, zona: string = ZONA_POR_DEFECTO): string {
  return new Intl.DateTimeFormat('es-PA', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
    timeZone: zona,
  })
    .format(new Date(iso))
    .replace(/\s/g, ' ');
}

export function horaCorta(iso: string, zona: string = ZONA_POR_DEFECTO): string {
  return new Intl.DateTimeFormat('es-PA', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: zona,
  }).format(new Date(iso));
}

export function diaLargo(iso: string, zona: string = ZONA_POR_DEFECTO): string {
  return new Intl.DateTimeFormat('es-PA', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: zona,
  }).format(new Date(iso));
}

export function diaCorto(iso: string, zona: string = ZONA_POR_DEFECTO): string {
  return new Intl.DateTimeFormat('es-PA', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    timeZone: zona,
  }).format(new Date(iso));
}

/** «hoy», «mañana» o el día escrito, para no obligar a leer una fecha cuando no hace falta. */
export function cuandoEs(iso: string, zona: string = ZONA_POR_DEFECTO): string {
  const dia = fechaLocal(new Date(iso), zona);
  const hoy = fechaLocal(new Date(), zona);
  const manana = fechaLocal(new Date(Date.now() + 86_400_000), zona);
  if (dia === hoy) return 'hoy';
  if (dia === manana) return 'mañana';
  return diaCorto(iso, zona);
}

/** Lo mismo, pero para empezar una etiqueta: «Hoy», «Mañana», «Jue, 10 sept». */
export function cuandoEsEnMayuscula(iso: string, zona: string = ZONA_POR_DEFECTO): string {
  const texto = cuandoEs(iso, zona);
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** El día natural (AAAA-MM-DD) tal y como se vive en esa zona horaria. */
export function fechaLocal(fecha: Date, zona: string = ZONA_POR_DEFECTO): string {
  const partes = new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: zona,
  }).format(fecha);
  return partes;
}

/** Suma días naturales a un AAAA-MM-DD sin que el cambio de mes lo estropee. */
export function sumarDias(dia: string, cuantos: number): string {
  const [ano, mes, numero] = dia.split('-').map(Number);
  const fecha = new Date(Date.UTC(ano, mes - 1, numero + cuantos));
  return fecha.toISOString().slice(0, 10);
}

/** Los dos extremos ISO de un día natural en la zona del salón. */
export function extremosDelDia(dia: string, zona: string = ZONA_POR_DEFECTO): { desde: string; hasta: string } {
  const desfase = desfaseDe(zona, new Date(`${dia}T12:00:00Z`));
  return {
    desde: `${dia}T00:00:00${desfase}`,
    hasta: `${sumarDias(dia, 1)}T00:00:00${desfase}`,
  };
}

function desfaseDe(zona: string, referencia: Date): string {
  const formato = new Intl.DateTimeFormat('en-US', { timeZone: zona, timeZoneName: 'longOffset' });
  const parte = formato.formatToParts(referencia).find((p) => p.type === 'timeZoneName')?.value ?? 'GMT+00:00';
  return parte.replace('GMT', '') || '+00:00';
}

/** El dinero de Panamá es el dólar y se escribe con dos decimales, siempre. */
export function dinero(centavos: number | null | undefined): string {
  if (centavos === null || centavos === undefined) return 'A consultar';
  // `narrowSymbol` a propósito: por defecto `es-PA` escribe «USD 12.00», y en un salón de
  // Panamá el precio se escribe «$12.00». El código de moneda es para una factura, no para una
  // carta de servicios.
  return new Intl.NumberFormat('es-PA', {
    style: 'currency',
    currency: 'USD',
    currencyDisplay: 'narrowSymbol',
  }).format(centavos / 100);
}

export function precioDeServicio(servicio: { precio_centavos: number | null; tipo_de_precio: string }): string {
  if (servicio.precio_centavos === null) return 'A consultar';
  if (servicio.tipo_de_precio === 'desde') return `desde ${dinero(servicio.precio_centavos)}`;
  return dinero(servicio.precio_centavos);
}

export function duracion(minutos: number): string {
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto === 0 ? `${horas} h` : `${horas} h ${resto} min`;
}

/** Los minutos desde medianoche, en la zona del salón. Es lo que coloca un bloque en el riel. */
export function minutosDelDia(iso: string, zona: string = ZONA_POR_DEFECTO): number {
  const partes = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: zona,
  }).format(new Date(iso));
  const [h, m] = partes.split(':').map(Number);
  return h * 60 + m;
}

export const FRANJAS = [
  { clave: 'manana', rotulo: 'Mañana', desde: 0, hasta: 12 * 60 },
  { clave: 'tarde', rotulo: 'Tarde', desde: 12 * 60, hasta: 18 * 60 },
  { clave: 'noche', rotulo: 'Noche', desde: 18 * 60, hasta: 24 * 60 },
] as const;

/**
 * Los seis estados que sirve la API —en minúsculas y con guion bajo, tal cual llegan— y cómo se
 * escriben en pantalla. `cancelada_cliente` y `cancelada_negocio` son dos estados distintos
 * para el negocio, pero **el mismo color**: los tokens solo definen la familia `cancelada`, así
 * que `familiaDeEstado` traduce el estado al token y `ROTULO_DE_ESTADO` al castellano.
 *
 * Esto no es un detalle: pintar `CANCELADA_CLIENTE` en crudo dentro de un bloque sin color es
 * exactamente lo que pasa cuando el front no mira el contrato.
 */
export const ROTULO_DE_ESTADO: Record<string, string> = {
  pendiente: 'Pendiente',
  confirmada: 'Confirmada',
  completada: 'Completada',
  no_show: 'No vino',
  cancelada_cliente: 'Cancelada por la clienta',
  cancelada_negocio: 'Cancelada por el salón',
};

export function rotuloDeEstado(estado: string): string {
  return ROTULO_DE_ESTADO[estado] ?? estado.replace(/_/g, ' ');
}

/** El token de color que le toca a ese estado. Las dos cancelaciones comparten familia. */
export function familiaDeEstado(estado: string): string {
  return estado.startsWith('cancelada') ? 'cancelada' : estado;
}

export function estaCancelada(estado: string): boolean {
  return estado.startsWith('cancelada');
}

/** Nota media con una decimal; sin nota se dice, no se pinta un cero. */
export function nota(valor: number | null | undefined): string | null {
  if (valor === null || valor === undefined) return null;
  return valor.toFixed(1).replace('.', ',');
}
