/**
 * Las zonas y las categorías que se enseñan en el producto.
 *
 * Vive en un módulo **neutro**, sin `'use client'`, porque lo leen las dos orillas: el buscador
 * en el navegador y la página del marketplace en el servidor, que necesita el nombre de la zona
 * para el título que sale en Google. Un dato exportado desde un módulo de cliente no cruza:
 * Next lo sustituye por una referencia y en el servidor deja de ser un array.
 *
 * Es una lista provisional escrita a mano. La taxonomía de verdad es jerárquica y administrable
 * (MKT-6) y vive en la tabla `zones`; cuando esté cargada, esto se borra y se lee de la API.
 */

export const ZONAS: [string, string][] = [
  ['Bella Vista', 'bella-vista'],
  ['El Cangrejo', 'el-cangrejo'],
  ['Obarrio', 'obarrio'],
  ['San Francisco', 'san-francisco'],
  ['Costa del Este', 'costa-del-este'],
  ['Juan Díaz', 'juan-diaz'],
]

export const CATEGORIAS: [string, string][] = [
  ['Barbería', 'barberia'],
  ['Peluquería', 'peluqueria'],
  ['Uñas', 'unas'],
  ['Pestañas y cejas', 'pestanas-cejas'],
  ['Maquillaje', 'maquillaje'],
  ['Depilación', 'depilacion'],
  ['Spa y masajes', 'spa-masajes'],
  ['Estética', 'estetica'],
]

export function nombreDeZona(slug: string | undefined) {
  return ZONAS.find(([, s]) => s === slug)?.[0]
}
