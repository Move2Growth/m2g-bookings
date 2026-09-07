import Link from 'next/link'

/**
 * El interruptor entre las dos búsquedas: **locales** o **personas**.
 *
 * El encargo pide buscar personas «sin sustituir» la búsqueda de siempre, así que son dos
 * listas con dos URL, no una lista con un filtro escondido. Se separan porque lo que devuelven
 * no se parece: un salón tiene dirección, categorías y precio desde; una persona tiene oficio,
 * años y el salón donde está. Meterlas en la misma fila obligaría a que una de las dos mienta.
 *
 * Son enlaces y no botones: cada modo es una dirección que se comparte y que indexa Google.
 *
 * El mapa va aquí y no en otro sitio porque es **la tercera forma de buscar lo mismo**: quien no
 * sabe el nombre de nada pero sabe por dónde va a pasar. Escondido en un menú no lo encuentra
 * nadie.
 */
export function ModoDeBusqueda({
  modo,
  consulta,
}: {
  modo: 'locales' | 'personas'
  /** Lo escrito en el buscador, para no perderlo al cambiar de modo. */
  consulta?: string
}) {
  const cola = consulta ? `?texto=${encodeURIComponent(consulta)}` : ''
  return (
    <div className="tira" role="tablist" aria-label="Buscar locales o personas">
      <Link
        href={`/buscar${cola}`}
        role="tab"
        aria-selected={modo === 'locales'}
        className="ficha ficha--modo"
      >
        Locales
      </Link>
      <Link
        href={`/buscar/personas${cola}`}
        role="tab"
        aria-selected={modo === 'personas'}
        className="ficha ficha--modo"
      >
        Personas
      </Link>
      {/* El mapa no lleva la consulta: enseña lo que hay **donde se está mirando**, y arrastrar
          un texto escrito para una lista lo dejaría vacío sin explicar por qué. */}
      <Link href="/mapa" role="tab" aria-selected={false} className="ficha ficha--modo">
        Mapa
      </Link>
    </div>
  )
}
