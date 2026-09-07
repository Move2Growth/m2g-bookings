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

export type Profesional = {
  id: string
  nombre: string
  /** Su URL pública. Nulo mientras nadie le haya puesto uno: entonces se enlaza por `id`. */
  slug?: string | null
  titular?: string | null
  foto?: string | null
}

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
  /* Lo que la ficha pública enseña además de servicios y equipo. Va opcional porque el perfil
     se sirve igual mientras un salón no lo haya rellenado: una ficha a medias tiene que salir,
     no romperse. */
  descripcion?: string | null
  rating?: number | null
  numero_reviews?: number
  /** Rutas o URL de las fotos, la portada primero. Son cadenas y no objetos: la API compone
   *  la URL a partir de la clave guardada, y el texto alternativo todavía no viaja. */
  fotos?: string[]
  categorias?: string[]
  atributos?: { slug: string; nombre: string; grupo: string }[]
  horario?: { dia: number; abre: string; cierra: string }[]
  /** Si tiene WhatsApp configurado. **Nunca llega el número**: solo si existe el botón, y el
   *  salto lo resuelve el servidor. */
  tiene_whatsapp?: boolean
}

export type ResenaPublica = {
  id: string
  nota: number
  texto: string | null
  fecha: string
  autor: string
  profesional: string | null
  fotos: { id: string; url: string }[]
  respuesta: { texto: string; fecha: string } | null
}

export type ResenasDelPerfil = {
  resumen: { total: number; media: number | null; reparto: Record<string, number> }
  resenas: ResenaPublica[]
}

/** Las reseñas de un salón. Si el salón no tiene ninguna, la ficha sale igual y lo dice. */
export function verResenas(slug: string): Promise<ResenasDelPerfil> {
  return pedir<ResenasDelPerfil>(`/api/v1/publico/negocios/${slug}/reviews`, { revalidar: 300 })
}

export type Slot = { inicio: string; fin: string; profesional_id: string | null }

export type Disponibilidad = {
  zona: string
  duracion_minutos: number
  slots: Slot[]
}

/* ── El profesional como entidad de primera (encargo 2026-09-07 §3) ──────────────────────── */

/** Una foto de trabajo. Cuando lleva `servicio`, es lo que hace visible **quién hizo qué**. */
export type FotoDeProfesional = {
  id: string
  url: string
  descripcion: string | null
  servicio: string | null
  servicio_id: string | null
}

export type RedesDelProfesional = {
  instagram?: string | null
  instagram_url?: string | null
  facebook?: string | null
  facebook_url?: string | null
  x?: string | null
  x_url?: string | null
}

/** Un profesional tal y como sale en una lista: el suyo, su salón y su nota. */
export type ProfesionalEnLista = {
  id: string
  slug: string | null
  nombre: string
  titular: string | null
  foto: string | null
  anos_de_experiencia: number | null
  nota: number | null
  numero_resenas: number
  /** Los identificadores de los servicios que hace. Sirven para pedirle sus horas libres. */
  servicios: string[]
  negocio: string | null
  negocio_slug: string | null
  zona: string | null
  distancia_metros: number | null
  /** **No viene de la API**: lo compone la página sondeando el motor de disponibilidad. */
  proxima_hora?: string | null
}

/** Un servicio del catálogo de esa persona, con las fotos que ella ató a ese servicio. */
export type ServicioDelProfesional = Servicio & {
  trabajos: { id: string; url: string; descripcion: string | null }[]
}

export type PerfilDeProfesional = ProfesionalEnLista & {
  descripcion: string | null
  citas_atendidas: number
  clientes_atendidos: number
  redes: RedesDelProfesional
  negocio_id: string
  zona_horaria: string
  direccion: string | null
  catalogo: ServicioDelProfesional[]
  /** Las fotos sueltas, sin servicio atado. */
  galeria: FotoDeProfesional[]
  /** Todas sus fotos, con y sin servicio. */
  trabajos: FotoDeProfesional[]
  resenas: ResenaPublica[]
}

/** La búsqueda de personas. Convive con la de salones: son dos listas, no una con un filtro. */
export function buscarProfesionales(
  filtros: Record<string, string | undefined>,
): Promise<ProfesionalEnLista[]> {
  const ADMITIDOS = ['texto', 'servicio', 'zona', 'negocio', 'orden', 'pagina']
  const parametros = new URLSearchParams()
  for (const clave of ADMITIDOS) {
    const valor = filtros[clave]
    if (valor) parametros.set(clave, valor)
  }
  const cadena = parametros.toString()
  return pedir<ProfesionalEnLista[]>(
    `/api/v1/publico/profesionales${cadena ? `?${cadena}` : ''}`,
    { revalidar: 60 },
  )
}

/** El perfil de una persona. `quien` admite su slug o, si todavía no tiene, su identificador. */
export function verPerfilDeProfesional(
  slug: string,
  quien: string,
): Promise<PerfilDeProfesional> {
  return pedir<PerfilDeProfesional>(
    `/api/v1/publico/negocios/${encodeURIComponent(slug)}/profesionales/${encodeURIComponent(quien)}`,
    { revalidar: 60 },
  )
}

/** Las horas libres **de esa persona**, no las del salón. */
export function verDisponibilidadDeProfesional(
  profesionalId: string,
  servicios: string[],
  desde: Date,
  hasta: Date,
  /**
   * Segundos de caché. **Cero en la pantalla donde se reserva**: ofrecer un hueco ya cogido es
   * la peor mentira que puede contar esta pantalla. En una lista, donde la hora es un reclamo
   * y no un botón de reservar, un minuto de retraso no engaña a nadie y ahorra una petición
   * por fila en cada visita.
   */
  revalidar = 0,
): Promise<Disponibilidad> {
  const parametros = new URLSearchParams()
  for (const servicio of servicios) parametros.append('servicios', servicio)
  parametros.set('desde', desde.toISOString())
  parametros.set('hasta', hasta.toISOString())

  return pedir<Disponibilidad>(
    `/api/v1/publico/profesionales/${encodeURIComponent(profesionalId)}/disponibilidad?${parametros}`,
    { revalidar },
  )
}

/**
 * La próxima hora libre de cada persona de la lista.
 *
 * **No viene de la API**: `ProfesionalEnLista` no la trae, así que se sondea el motor una vez
 * por persona con su servicio más corto y dos días de ventana. Se hace en paralelo y **para
 * toda la página**, no para las primeras: media lista con hora y media sin ella se lee como si
 * a las de abajo no les quedara ninguna, que es justo lo contrario de lo que pasa.
 *
 * Sale a cuenta porque cada sonda se cachea un minuto: la primera visita del minuto paga las
 * veinte peticiones —medido en local, 432 ms para doce en paralelo— y el resto no paga nada.
 * Quien falla se queda sin hora y la fila dice «ver horas»; ni una sola persona desaparece de
 * la lista por eso.
 */
export async function conProximaHora(
  personas: ProfesionalEnLista[],
): Promise<ProfesionalEnLista[]> {
  const desde = new Date()
  const hasta = new Date(desde.getTime() + 2 * 24 * 60 * 60 * 1000)

  const horas = await Promise.all(
    personas.map(async (persona) => {
      if (persona.servicios.length === 0) return null
      try {
        const libre = await verDisponibilidadDeProfesional(
          persona.id,
          [persona.servicios[0]],
          desde,
          hasta,
          60,
        )
        return libre.slots[0]?.inicio ?? null
      } catch {
        return null
      }
    }),
  )

  return personas.map((persona, indice) => ({ ...persona, proxima_hora: horas[indice] }))
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
  /** El identificador del negocio, que es con lo que se guarda en favoritos. */
  negocio_id?: string
  slug: string
  nombre: string
  direccion: string | null
  zona: string | null
  distancia_metros: number | null
  rating: number | null
  /** Cuántas reseñas sostienen esa nota. Una nota de 5 con una reseña no es una nota de 5, y
   *  enseñarla sin el número engaña. */
  numero_reviews?: number
  servicios_desde_centavos: number | null
  foto_portada?: string | null
  categorias?: string[]
  abierto_ahora?: boolean | null
  proxima_hora?: string | null
  patrocinado: boolean
}

/** La búsqueda del marketplace. Cada combinación de filtros tiene su propia URL indexable. */
export function buscarNegocios(
  filtros: Record<string, string | undefined>,
): Promise<ResultadoDeBusqueda[]> {
  // Se pasan tal cual los filtros que la API conoce. La lista está escrita aquí y no se manda
  // el objeto entero porque un parámetro inventado en la URL no puede llegar al servidor.
  const ADMITIDOS = [
    'texto',
    'zona',
    'categoria',
    'precio_min',
    'precio_max',
    'rating_min',
    'disponibilidad',
    'dia',
    'abierto_ahora',
    'orden',
    'pagina',
  ]
  const parametros = new URLSearchParams()
  for (const clave of ADMITIDOS) {
    const valor = filtros[clave]
    if (valor) parametros.set(clave, valor)
  }
  // La próxima hora libre es opcional en la API porque cuesta: son diez sondas al motor de
  // disponibilidad. Medido en local, ~70 ms para los diez resultados de una página, y es el
  // dato que convierte una lista en algo que se puede tocar. Se pide siempre.
  parametros.set('con_proxima_hora', 'true')
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
