/**
 * El único sitio por donde se habla con la API.
 *
 * Todo lo que se pinta en esta web sale de `http://localhost:8000`. No hay ni un dato de
 * ejemplo escrito dentro de un componente: si la API no responde, la pantalla enseña su estado
 * de error, que es justo lo que hay que poder juzgar.
 */

/**
 * **Dos direcciones para la misma API, y hacen falta las dos.**
 *
 * Dentro de Docker el servidor de Next y la API son dos contenedores: el servidor la alcanza en
 * `http://api:8000` y el navegador en `http://localhost:8000`. Usando la del navegador en los
 * dos sitios, el pintado en servidor falla con `ECONNREFUSED`, la página **se sirve vacía** y el
 * navegador la rellena después. No se ve ningún error: la pantalla funciona y lo único que se
 * pierde es lo que Google necesita, que es justo lo que esta dirección hace mejor que las otras.
 * Se cazó con `curl`: la ficha de un salón volvía sin su nombre.
 */
export const BASE_API =
  typeof window === 'undefined'
    ? (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000')
    : (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000');

/** El sobre de error que devuelve la API: `{"error": {"codigo", "mensaje"}}`. */
export type ErrorDeApi = {
  codigo: string;
  mensaje: string;
  estado: number;
};

export class FalloDeApi extends Error {
  codigo: string;
  estado: number;

  constructor(fallo: ErrorDeApi) {
    super(fallo.mensaje);
    this.name = 'FalloDeApi';
    this.codigo = fallo.codigo;
    this.estado = fallo.estado;
  }
}

/** Mensaje presentable para cualquier cosa que salga mal, incluida la red caída. */
export function comoMensaje(error: unknown): string {
  if (error instanceof FalloDeApi) return error.message;
  if (error instanceof Error && error.message.includes('fetch')) {
    return 'No se pudo hablar con el servidor. Comprueba que la API está levantada en el puerto 8000.';
  }
  return 'Algo se rompió por el camino. Vuelve a intentarlo.';
}

type Opciones = {
  metodo?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  cuerpo?: unknown;
  acceso?: string | null;
  cabeceras?: Record<string, string>;
  /** En el servidor no cacheamos: una agenda cacheada es una agenda mentirosa. */
  revalidar?: number;
};

export async function pedir<T>(camino: string, opciones: Opciones = {}): Promise<T> {
  const { metodo = 'GET', cuerpo, acceso, cabeceras = {}, revalidar } = opciones;

  const respuesta = await fetch(`${BASE_API}${camino}`, {
    method: metodo,
    headers: {
      ...(cuerpo === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(acceso ? { Authorization: `Bearer ${acceso}` } : {}),
      ...cabeceras,
    },
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    ...(revalidar === undefined ? { cache: 'no-store' as const } : { next: { revalidate: revalidar } }),
  });

  if (!respuesta.ok) {
    let codigo = 'ERROR';
    let mensaje = `La API respondió ${respuesta.status}.`;
    try {
      const cuerpoError = await respuesta.json();
      if (cuerpoError?.error?.mensaje) {
        codigo = cuerpoError.error.codigo ?? codigo;
        mensaje = cuerpoError.error.mensaje;
      } else if (typeof cuerpoError?.detail === 'string') {
        mensaje = cuerpoError.detail;
      }
    } catch {
      /* La API no siempre contesta JSON cuando revienta de verdad. */
    }
    throw new FalloDeApi({ codigo, mensaje, estado: respuesta.status });
  }

  if (respuesta.status === 204) return undefined as T;
  return (await respuesta.json()) as T;
}

/* ── Los tipos que esta web usa, recortados del contrato ──────────────────────────────────── */

export type ResultadoDeBusqueda = {
  negocio_id: string;
  slug: string;
  nombre: string;
  direccion: string | null;
  zona: string | null;
  distancia_metros: number | null;
  rating: number | null;
  servicios_desde_centavos: number | null;
  foto_portada: string | null;
  numero_reviews: number;
  categorias: string[];
  abierto_ahora: boolean | null;
  proxima_hora: string | null;
  patrocinado: boolean;
};

export type ServicioPublico = {
  id: string;
  nombre: string;
  duracion_minutos: number;
  precio_centavos: number | null;
  tipo_de_precio: string;
  trabajos: { id: string; url: string; profesional: string; profesional_id: string; descripcion: string | null }[];
};

export type ProfesionalDelEquipo = {
  id: string;
  slug: string | null;
  nombre: string;
  titular: string | null;
  foto: string | null;
  anos_de_experiencia: number | null;
  nota: number | null;
  numero_resenas: number;
  servicios: string[];
  negocio_slug: string | null;
  negocio: string | null;
  zona: string | null;
  citas_atendidas: number;
  clientes_atendidos: number;
};

export type ResenaPublica = {
  id: string;
  nota: number;
  texto: string | null;
  fecha: string;
  autor: string;
  profesional: string | null;
  fotos: { id: string; url: string }[];
  respuesta: { texto: string; fecha: string } | null;
};

export type ResenasDelPerfil = {
  resumen: {
    total: number;
    media: number | null;
    puntuacion: number | null;
    reparto: Record<string, number>;
  };
  resenas: ResenaPublica[];
};

export type PerfilPublico = {
  id: string;
  slug: string;
  nombre: string;
  zona: string | null;
  direccion: string | null;
  descripcion: string | null;
  zona_horaria: string;
  fotos: string[];
  foto_portada: string | null;
  rating: number | null;
  numero_reviews: number;
  atributos: string[];
  horario: { dia: number; abre: string; cierra: string }[];
  abierto_ahora: boolean | null;
  tiene_whatsapp: boolean;
  servicios_desde_centavos: number | null;
  servicios: ServicioPublico[];
  equipo: { id: string; nombre: string; slug: string | null; titular: string | null; foto: string | null }[];
  anuncio: { texto: string; hasta: string | null } | null;
};

export type PerfilDelProfesional = ProfesionalDelEquipo & {
  descripcion: string | null;
  redes: {
    instagram: string | null;
    instagram_url: string | null;
    facebook: string | null;
    facebook_url: string | null;
    x: string | null;
    x_url: string | null;
  };
  negocio_id: string;
  zona_horaria: string;
  direccion: string | null;
  catalogo: ServicioPublico[];
  galeria: { id: string; url: string; descripcion: string | null; servicio: string | null }[];
  trabajos: { id: string; url: string; descripcion: string | null; servicio: string | null }[];
  resenas: ResenaPublica[];
};

export type Slot = { inicio: string; fin: string; profesional_id: string | null };

export type RespuestaDisponibilidad = {
  zona: string;
  duracion_minutos: number;
  slots: Slot[];
};

export type MiCita = {
  id: string;
  negocio: string;
  negocio_slug: string;
  inicio: string;
  fin: string;
  estado: string;
  zona_horaria: string;
  servicios: { nombre: string; duracion_minutos: number; precio_centavos: number | null }[];
  total_centavos: number;
  se_puede_cancelar: boolean;
  se_puede_resenar: boolean;
  ya_resenada: boolean;
};

export type Credenciales = {
  acceso: string;
  refresco: string;
  expira_en_segundos: number;
  usuario_id: string;
  negocio_activo: string | null;
};

export type NegocioDeLaPersona = { id: string; nombre: string; slug: string; rol: string };

export type CitaEnColumna = {
  id: string;
  inicio: string;
  fin: string;
  estado: string;
  cliente: string;
  servicios: string[];
  importe_centavos: number;
};

export type ColumnaDelDia = {
  profesional_id: string;
  nombre: string;
  foto: string | null;
  activo: boolean;
  citas: CitaEnColumna[];
  bloqueos: { id: string; inicio: string; fin: string; motivo: string | null }[];
};

export type DiaEnColumnas = {
  dia: string;
  zona: string;
  inicio: string;
  fin: string;
  columnas: ColumnaDelDia[];
};

export type CategoriaGlobal = { id: string; slug: string; nombre: string; padre_slug: string | null };

export type MiPerfil = {
  id: string;
  nombre: string;
  telefono: string | null;
  telefono_verificado: boolean;
  correo: string | null;
  idioma: string;
};

/* ── Llamadas con nombre, para que las pantallas no construyan URLs a mano ────────────────── */

export type FiltrosDeBusqueda = {
  texto?: string;
  categoria?: string;
  zona?: string;
  cuando?: 'cualquiera' | 'ahora' | 'hoy' | 'fecha';
  dia?: string;
  orden?: string;
  pagina?: number;
};

export function consultaDeBusqueda(filtros: FiltrosDeBusqueda): string {
  const parametros = new URLSearchParams();
  if (filtros.texto) parametros.set('texto', filtros.texto);
  if (filtros.categoria) parametros.set('categoria', filtros.categoria);
  if (filtros.zona) parametros.set('zona', filtros.zona);
  if (filtros.cuando && filtros.cuando !== 'cualquiera') {
    parametros.set('disponibilidad', filtros.cuando);
    if (filtros.cuando === 'fecha' && filtros.dia) parametros.set('dia', filtros.dia);
  }
  if (filtros.orden && filtros.orden !== 'relevancia') parametros.set('orden', filtros.orden);
  if (filtros.pagina && filtros.pagina > 1) parametros.set('pagina', String(filtros.pagina));
  // La próxima hora libre cuesta una consulta de agenda por resultado. Se pide **siempre**
  // porque en esta dirección la hora ES el resultado: sin ella la lista no dice nada.
  parametros.set('con_proxima_hora', 'true');
  return parametros.toString();
}

export const api = {
  buscar: (filtros: FiltrosDeBusqueda) =>
    pedir<ResultadoDeBusqueda[]>(`/api/v1/publico/buscar?${consultaDeBusqueda(filtros)}`),

  // El catálogo de categorías es de la plataforma y cambia de higos a brevas: se guarda cinco
  // minutos. Es lo ÚNICO que se cachea en toda la web; las agendas y los huecos, nunca.
  categorias: () => pedir<CategoriaGlobal[]>('/api/v1/catalogo/categorias', { revalidar: 300 }),

  ficha: (slug: string) => pedir<PerfilPublico>(`/api/v1/publico/negocios/${encodeURIComponent(slug)}`),

  equipo: (slug: string) =>
    pedir<ProfesionalDelEquipo[]>(`/api/v1/publico/negocios/${encodeURIComponent(slug)}/profesionales`),

  profesional: (slug: string, persona: string) =>
    pedir<PerfilDelProfesional>(
      `/api/v1/publico/negocios/${encodeURIComponent(slug)}/profesionales/${encodeURIComponent(persona)}`,
    ),

  resenas: (slug: string) =>
    pedir<ResenasDelPerfil>(`/api/v1/publico/negocios/${encodeURIComponent(slug)}/reviews`),

  /**
   * Los huecos del salón entero. Cada hueco viene con la persona que lo puede atender, así que
   * «me da igual con quién» se puede resolver sin inventar nada: se reserva con quien traiga el
   * hueco elegido.
   */
  horasDelNegocio: (slug: string, servicios: string[], desde: string, hasta: string) => {
    const parametros = new URLSearchParams();
    servicios.forEach((servicio) => parametros.append('servicios', servicio));
    parametros.set('desde', desde);
    parametros.set('hasta', hasta);
    return pedir<RespuestaDisponibilidad>(
      `/api/v1/publico/negocios/${encodeURIComponent(slug)}/disponibilidad?${parametros.toString()}`,
    );
  },

  horasDelProfesional: (profesionalId: string, servicios: string[], desde: string, hasta: string) => {
    const parametros = new URLSearchParams();
    servicios.forEach((servicio) => parametros.append('servicios', servicio));
    parametros.set('desde', desde);
    parametros.set('hasta', hasta);
    return pedir<RespuestaDisponibilidad>(
      `/api/v1/publico/profesionales/${profesionalId}/disponibilidad?${parametros.toString()}`,
    );
  },

  entrar: (correo: string, contrasena: string) =>
    pedir<Credenciales>('/api/v1/auth/entrar', { metodo: 'POST', cuerpo: { correo, contrasena, superficie: 'web' } }),

  modoNegocio: (negocioId: string, acceso: string) =>
    pedir<Credenciales>('/api/v1/auth/modo-negocio', {
      metodo: 'POST',
      cuerpo: { negocio_id: negocioId, superficie: 'web' },
      acceso,
    }),

  misNegocios: (acceso: string) => pedir<NegocioDeLaPersona[]>('/api/v1/mi/negocios', { acceso }),

  miPerfil: (acceso: string) => pedir<MiPerfil>('/api/v1/mi/perfil', { acceso }),

  misCitas: (acceso: string, pagina = 1) =>
    pedir<MiCita[]>(`/api/v1/mi/reservas${pagina > 1 ? `?pagina=${pagina}` : ''}`, { acceso }),

  cancelar: (citaId: string, acceso: string) =>
    pedir<MiCita>(`/api/v1/mi/reservas/${citaId}/cancelar`, { metodo: 'POST', acceso }),

  reservar: (
    datos: { negocio_slug: string; servicios: string[]; inicio: string; profesional_id: string; nota?: string | null },
    acceso: string,
    llave: string,
  ) =>
    pedir<MiCita>('/api/v1/mi/reservas', {
      metodo: 'POST',
      cuerpo: datos,
      acceso,
      cabeceras: { 'Idempotency-Key': llave },
    }),

  diaEnColumnas: (acceso: string, dia?: string) =>
    pedir<DiaEnColumnas>(`/api/v1/negocio/agenda/columnas${dia ? `?dia=${dia}` : ''}`, { acceso }),

  /* ── El alta del local, en tres pasos (encargo §4) ────────────────────────────────────── */

  crearNegocio: (datos: AltaDeNegocio, acceso: string) =>
    pedir<NegocioCreado>('/api/v1/negocios', { metodo: 'POST', cuerpo: datos, acceso }),

  ponerHorario: (horario: TramoDeHorario[], acceso: string) =>
    pedir<TramoDeHorario[]>('/api/v1/negocio/horario', { metodo: 'PUT', cuerpo: horario, acceso }),

  invitar: (datos: { correo: string; rol: 'dueno' | 'profesional'; nombre?: string }, acceso: string) =>
    pedir<InvitacionCreada>('/api/v1/negocio/miembros/invitaciones', { metodo: 'POST', cuerpo: datos, acceso }),

  crearServicio: (datos: AltaDeServicio, acceso: string) =>
    pedir<string>('/api/v1/negocio/servicios', { metodo: 'POST', cuerpo: datos, acceso }),

  checklist: (acceso: string) => pedir<Checklist>('/api/v1/negocio/checklist', { acceso }),

  publicar: (acceso: string) => pedir<NegocioCreado>('/api/v1/negocio/publicar', { metodo: 'POST', acceso }),

  /* ── El portal del dueño, sus seis piezas (encargo §6) ─────────────────────────────────── */

  finanzas: (acceso: string, desde: string, hasta: string, agrupacion: 'dia' | 'semana' | 'mes') =>
    pedir<Finanzas>(
      `/api/v1/negocio/finanzas?desde=${desde}&hasta=${hasta}&agrupacion=${agrupacion}`,
      { acceso },
    ),

  mejorDelMes: (acceso: string, criterio: 'importe' | 'servicios', categoria?: string) =>
    pedir<EnElPodio[]>(
      `/api/v1/negocio/mejor-del-mes?criterio=${criterio}${categoria ? `&categoria=${encodeURIComponent(categoria)}` : ''}`,
      { acceso },
    ),

  profesionalesDelLocal: (acceso: string) =>
    pedir<ProfesionalEnPanel[]>('/api/v1/negocio/profesionales', { acceso }),

  /** El fichaje es **por persona** (encargo §6): el dueño lo enciende a quien quiere. */
  ponerFichaje: (profesionalId: string, activo: boolean, acceso: string) =>
    pedir<ProfesionalEnPanel>(`/api/v1/negocio/profesionales/${profesionalId}/fichaje`, {
      metodo: 'PUT',
      cuerpo: { activo },
      acceso,
    }),

  fichajes: (acceso: string) => pedir<Fichaje[]>('/api/v1/negocio/fichajes', { acceso }),

  anuncios: (acceso: string) => pedir<AnuncioDelSalon[]>('/api/v1/negocio/anuncios', { acceso }),

  crearAnuncio: (texto: string, acceso: string) =>
    pedir<AnuncioDelSalon>('/api/v1/negocio/anuncios', { metodo: 'POST', cuerpo: { texto }, acceso }),

  cambiarAnuncio: (id: string, cambio: { texto?: string; activo?: boolean }, acceso: string) =>
    pedir<AnuncioDelSalon>(`/api/v1/negocio/anuncios/${id}`, { metodo: 'PATCH', cuerpo: cambio, acceso }),

  borrarAnuncio: (id: string, acceso: string) =>
    pedir<AnuncioDelSalon>(`/api/v1/negocio/anuncios/${id}`, { metodo: 'DELETE', acceso }),

  /* ── El portal del profesional ─────────────────────────────────────────────────────────── */

  miAgenda: (acceso: string, desde?: string, hasta?: string) =>
    pedir<MiAgenda>(
      `/api/v1/mi/agenda${desde && hasta ? `?desde=${desde}&hasta=${hasta}` : ''}`,
      { acceso },
    ),

  miPerfilProfesional: (acceso: string) =>
    pedir<MiPerfilProfesional>('/api/v1/mi/perfil-profesional', { acceso }),

  cambiarMiPerfilProfesional: (cambio: Partial<MiPerfilProfesional>, acceso: string) =>
    pedir<MiPerfilProfesional>('/api/v1/mi/perfil-profesional', { metodo: 'PATCH', cuerpo: cambio, acceso }),

  /* ── La clienta: opinar, guardar y repetir ─────────────────────────────────────────────── */

  opinar: (
    citaId: string,
    resena: { nota: number; texto?: string | null; profesional_id?: string | null; nota_al_profesional?: number | null },
    acceso: string,
  ) => pedir<{ id: string }>(`/api/v1/mi/reservas/${citaId}/review`, { metodo: 'POST', cuerpo: resena, acceso }),

  favoritos: (acceso: string) => pedir<NegocioFavorito[]>('/api/v1/mi/favoritos', { acceso }),

  guardarFavorito: (negocioId: string, acceso: string) =>
    pedir<NegocioFavorito>('/api/v1/mi/favoritos', { metodo: 'POST', cuerpo: { negocio_id: negocioId }, acceso }),

  quitarFavorito: (negocioId: string, acceso: string) =>
    pedir<void>(`/api/v1/mi/favoritos/${negocioId}`, { metodo: 'DELETE', acceso }),

  repetir: (citaId: string, acceso: string) =>
    pedir<ReservaDeNuevo>(`/api/v1/mi/reservas/${citaId}/repetir`, { acceso }),

  /* ── La consola interna. Otro sistema de acceso entero (ADR-0006). ─────────────────────── */

  entrarEnConsola: (email: string, password: string, codigo_2fa: string) =>
    pedir<{ acceso: string; refresco: string }>('/api/v1/consola/entrar', {
      metodo: 'POST',
      cuerpo: { email, password, codigo_2fa },
    }),

  metricas: (acceso: string) => pedir<Metricas>('/api/v1/consola/metricas', { acceso }),

  negociosEnConsola: (acceso: string, buscar?: string, estado?: string) =>
    pedir<NegocioEnConsola[]>(
      `/api/v1/consola/negocios?${buscar ? `buscar=${encodeURIComponent(buscar)}&` : ''}${estado ? `estado=${estado}` : ''}`,
      { acceso },
    ),

  suspender: (negocioId: string, motivo: string, acceso: string) =>
    pedir<NegocioEnConsola>(`/api/v1/consola/negocios/${negocioId}/suspender`, {
      metodo: 'POST',
      cuerpo: { motivo },
      acceso,
    }),

  reactivar: (negocioId: string, acceso: string) =>
    pedir<NegocioEnConsola>(`/api/v1/consola/negocios/${negocioId}/reactivar`, { metodo: 'POST', acceso }),

  resenasReportadas: (acceso: string) =>
    pedir<ReporteEnCola[]>('/api/v1/consola/moderacion/resenas', { acceso }),

  resolverReporte: (reporteId: string, accion: 'ocultar' | 'mantener', nota: string | null, acceso: string) =>
    pedir<ReporteEnCola>(`/api/v1/consola/moderacion/resenas/${reporteId}`, {
      metodo: 'POST',
      cuerpo: { accion, nota },
      acceso,
    }),

  fotosEnCola: (acceso: string) => pedir<FotoEnCola[]>('/api/v1/consola/moderacion/fotos', { acceso }),

  decidirFoto: (fotoId: string, accion: 'aprobar' | 'rechazar', nota: string | null, acceso: string) =>
    pedir<FotoEnCola>(`/api/v1/consola/moderacion/fotos/${fotoId}`, {
      metodo: 'POST',
      cuerpo: { accion, nota },
      acceso,
    }),

  /** El mapa **por rectángulo**: lo que se ve es lo que se pregunta (encargo §5). */
  mapa: (rect: { oeste: number; sur: number; este: number; norte: number }) =>
    pedir<{ salones: SalonEnMapa[] }>(
      `/api/v1/publico/mapa?oeste=${rect.oeste}&sur=${rect.sur}&este=${rect.este}&norte=${rect.norte}`,
    ),
};

/* ── El portal del profesional ───────────────────────────────────────────────────────────── */

export type CitaEnMiAgenda = {
  id: string;
  inicio: string;
  fin: string;
  estado: string;
  cliente: string | null;
  telefono: string | null;
  servicios: string[];
  duracion_minutos: number;
  total_centavos: number;
  nota_del_cliente: string | null;
};

export type MiAgenda = {
  profesional_id: string;
  profesional: string;
  negocio: string;
  zona_horaria: string;
  citas: CitaEnMiAgenda[];
  bloqueos: { inicio: string; fin: string; motivo: string | null }[];
};

export type MiPerfilProfesional = {
  id: string;
  slug: string | null;
  nombre: string;
  titular: string | null;
  descripcion: string | null;
  foto: string | null;
  anos_de_experiencia: number | null;
  instagram: string | null;
  facebook: string | null;
  x: string | null;
  citas_atendidas: number;
  clientes_atendidos: number;
  activo: boolean;
  visible_en_marketplace: boolean;
};

export type NegocioFavorito = {
  negocio_id: string;
  slug: string;
  nombre: string;
  zona: string | null;
  direccion: string | null;
  rating: number | null;
  numero_reviews: number;
  servicios_desde_centavos: number | null;
  abierto_ahora: boolean | null;
  categorias: string[];
};

export type ReservaDeNuevo = {
  negocio_slug: string;
  negocio_nombre: string;
  profesional: string | null;
  profesional_id: string | null;
  profesional_disponible: boolean;
  se_puede_repetir: boolean;
  servicios: { id: string; nombre: string; duracion_minutos: number; precio_centavos: number | null; sigue_disponible: boolean }[];
};

/* ── La consola interna de M2G ───────────────────────────────────────────────────────────── */

export type Metricas = {
  negocios_totales: number;
  negocios_publicados: number;
  negocios_suspendidos: number;
  reportes_abiertos: number;
  reservas_por_dia: { dia: string; valor: number }[];
  impresiones_por_dia: { dia: string; valor: number }[];
  clics_por_dia: { dia: string; valor: number }[];
};

export type NegocioEnConsola = {
  id: string;
  slug: string;
  nombre: string;
  estado: string;
  direccion: string | null;
  creado: string;
  publicado: string | null;
  suspendido: string | null;
  motivo_suspension: string | null;
  reservas: number;
  clientes: number;
  reviews: number;
  rating: number | null;
};

export type ReporteEnCola = {
  reporte_id: string;
  resena_id: string;
  negocio: string;
  negocio_slug: string;
  nota: number;
  texto: string | null;
  motivo: string;
  reportado_por: string;
  estado_resena: string;
  estado_reporte: string;
  fecha: string;
};

export type FotoEnCola = {
  foto_id: string;
  profesional_id: string;
  profesional: string;
  negocio: string;
  negocio_slug: string;
  url: string;
  descripcion: string | null;
  servicio: string | null;
  estado: string;
  fecha: string;
};

export type SalonEnMapa = {
  negocio_id: string;
  slug: string;
  nombre: string;
  longitud: number;
  latitud: number;
  rating: number | null;
  numero_reviews: number;
};

/* ── Tipos del portal del dueño ──────────────────────────────────────────────────────────── */

export type Finanzas = {
  zona: string;
  moneda: string;
  agrupacion: string;
  citas: number;
  importe_centavos: number;
  ticket_medio_centavos: number;
  /** Cuántas de esas citas no llevaban precio. Sin este número la media miente. */
  citas_sin_precio: number;
  periodos: { inicio: string; citas: number; importe_centavos: number }[];
};

export type EnElPodio = {
  profesional_id: string;
  nombre: string;
  servicios: number;
  importe_centavos: number;
};

export type ProfesionalEnPanel = {
  id: string;
  nombre: string;
  slug: string | null;
  titular: string | null;
  foto: string | null;
  anos_de_experiencia: number | null;
  activo: boolean;
  visible_en_marketplace: boolean;
  tiene_cuenta: boolean;
  fichaje_activo: boolean;
  citas_futuras: number;
};

export type Fichaje = {
  id: string;
  profesional_id: string;
  profesional: string;
  entrada: string;
  salida: string | null;
};

export type AnuncioDelSalon = {
  id: string;
  texto: string;
  activo: boolean;
  vigente: boolean;
  desde: string | null;
  hasta: string | null;
};

/* ── Tipos del alta ──────────────────────────────────────────────────────────────────────── */

export type AltaDeNegocio = {
  nombre: string;
  categoria: string;
  direccion: string;
  longitud: number;
  latitud: number;
};

export type NegocioCreado = { id: string; slug: string; estado: string };

export type TramoDeHorario = { dia: number; abre: string; cierra: string };

export type InvitacionCreada = {
  miembro: { correo: string | null; rol: string; estado: string };
  /** Solo en local: el enlace que en producción viaja al correo. */
  enlace_de_desarrollo: string | null;
};

export type AltaDeServicio = {
  nombre: string;
  categoria: string;
  duracion_minutos: number;
  /** Opcional a propósito (encargo §4): hay servicios cuyo precio no se sabe de antemano. */
  precio_centavos: number | null;
  tipo_de_precio: 'fijo' | 'desde' | 'consultar';
};

export type Checklist = {
  tiene_servicio_activo: boolean;
  tiene_horario: boolean;
  tiene_ubicacion: boolean;
  tiene_foto: boolean;
  listo_para_publicar: boolean;
  completitud: number;
};
