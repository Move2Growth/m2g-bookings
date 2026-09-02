/**
 * El cliente de la API.
 *
 * Todo lo que la web sabe del servidor pasa por aquí. Dos razones: que el sobre de error
 * (`{error: {codigo, mensaje}}`) se traduzca en un solo sitio, y que la web no invente
 * caminos alternativos a los datos — no hay acceso directo a la base ni desde el servidor de
 * Next (ADR-0011).
 *
 * Los tipos de este archivo son **provisionales**: se sustituyen por los de
 * `@agenda/api-types`, generados del OpenAPI, en cuanto ese paquete se genere. Hasta entonces
 * viven aquí en vez de en un archivo de tipos aparte, para que se note que son deuda y no un
 * contrato paralelo.
 */

const BASE = process.env.API_URL ?? 'http://localhost:8000'

export type Servicio = {
  id: string
  nombre: string
  duracion_minutos: number
  precio_centavos: number | null
  tipo_de_precio: 'fijo' | 'desde' | 'consultar'
}

export type Profesional = { id: string; nombre: string }

export type NegocioEnLista = {
  slug: string
  nombre: string
  zona: string | null
  direccion: string | null
  servicios_desde_centavos: number | null
}

export type Perfil = NegocioEnLista & {
  id: string
  zona_horaria: string
  servicios: Servicio[]
  equipo: Profesional[]
}

export type Slot = { inicio: string; fin: string; profesional_id: string | null }

export type Disponibilidad = {
  zona: string
  duracion_minutos: number
  slots: Slot[]
}

/** Un error que la interfaz puede enseñar tal cual, con el código estable para ramificar. */
export class ErrorDeApi extends Error {
  constructor(
    readonly codigo: string,
    mensaje: string,
    readonly estado: number,
  ) {
    super(mensaje)
  }
}

type Opciones = {
  /** Segundos que la respuesta se puede reutilizar. El perfil cambia poco; los huecos, mucho. */
  revalidar?: number
  claveDeIdempotencia?: string
  metodo?: 'GET' | 'POST'
  cuerpo?: unknown
}

async function pedir<T>(ruta: string, opciones: Opciones = {}): Promise<T> {
  const cabeceras: Record<string, string> = { Accept: 'application/json' }
  if (opciones.cuerpo) cabeceras['Content-Type'] = 'application/json'
  // La app y la web reintentan solas con red inestable, y un reintento no puede crear dos
  // citas: la clave viaja en la cabecera y el servidor devuelve la misma respuesta (ADR-0012).
  if (opciones.claveDeIdempotencia) cabeceras['Idempotency-Key'] = opciones.claveDeIdempotencia

  const respuesta = await fetch(`${BASE}${ruta}`, {
    method: opciones.metodo ?? 'GET',
    headers: cabeceras,
    body: opciones.cuerpo ? JSON.stringify(opciones.cuerpo) : undefined,
    next: opciones.revalidar === undefined ? undefined : { revalidate: opciones.revalidar },
  })

  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null)
    const error = cuerpo?.error
    throw new ErrorDeApi(
      error?.codigo ?? 'ERROR',
      error?.mensaje ?? 'No se pudo completar la operación. Vuelve a intentarlo.',
      respuesta.status,
    )
  }

  return (await respuesta.json()) as T
}

export type ResultadoDeBusqueda = {
  slug: string
  nombre: string
  direccion: string | null
  zona: string | null
  distancia_metros: number | null
  rating: number | null
  servicios_desde_centavos: number | null
  patrocinado: boolean
}

/** La búsqueda del marketplace. Cada combinación de filtros tiene su propia URL indexable. */
export function buscarNegocios(filtros: {
  texto?: string
  zona?: string
  categoria?: string
}): Promise<ResultadoDeBusqueda[]> {
  const parametros = new URLSearchParams()
  if (filtros.texto) parametros.set('texto', filtros.texto)
  if (filtros.zona) parametros.set('zona', filtros.zona)
  if (filtros.categoria) parametros.set('categoria', filtros.categoria)
  const cadena = parametros.toString()
  return pedir<ResultadoDeBusqueda[]>(
    `/api/v1/publico/buscar${cadena ? `?${cadena}` : ''}`,
    { revalidar: 60 },
  )
}

export function listarNegocios(): Promise<NegocioEnLista[]> {
  // Un minuto: el listado cambia cuando alguien publica un negocio, no cada segundo.
  return pedir<NegocioEnLista[]>('/api/v1/publico/negocios', { revalidar: 60 })
}

export function verPerfil(slug: string): Promise<Perfil> {
  return pedir<Perfil>(`/api/v1/publico/negocios/${encodeURIComponent(slug)}`, { revalidar: 60 })
}

export function verDisponibilidad(
  slug: string,
  servicios: string[],
  desde: Date,
  hasta: Date,
): Promise<Disponibilidad> {
  const parametros = new URLSearchParams()
  for (const servicio of servicios) parametros.append('servicios', servicio)
  parametros.set('desde', desde.toISOString())
  parametros.set('hasta', hasta.toISOString())

  // **Sin caché**: un hueco que se ofrece y ya está cogido es la peor mentira que puede
  // contar esta pantalla. Mirar no aparta nada, pero al menos que lo que se mire sea de ahora.
  return pedir<Disponibilidad>(
    `/api/v1/publico/negocios/${encodeURIComponent(slug)}/disponibilidad?${parametros}`,
    { revalidar: 0 },
  )
}

/** Formatea centavos como se leen en Panamá: `$18.00`. El símbolo es configuración (D12). */
export function precio(centavos: number | null): string {
  if (centavos === null) return 'A consultar'
  return `$${(centavos / 100).toFixed(2)}`
}

/** «45 min», «3 h», «1 h 15». Nunca «180 minutos», que nadie dice. */
export function duracion(minutos: number): string {
  if (minutos < 60) return `${minutos} min`
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  return resto === 0 ? `${horas} h` : `${horas} h ${resto}`
}
