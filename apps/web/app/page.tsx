import Link from 'next/link'
import { NOMBRE } from '@/lib/marca'
import { ErrorDeApi, listarNegocios, precio, type NegocioEnLista } from '@/lib/api'

/**
 * La portada del marketplace.
 *
 * Se renderiza **en servidor** (ADR-0011): la mitad de la clientela llega buscando «barbería
 * en San Francisco», y una página que llega vacía y se rellena con JavaScript no la indexa
 * nadie. Aquí no hay ni un `useEffect` cargando datos.
 */
export default async function Portada() {
  let negocios: NegocioEnLista[] = []
  let fallo: string | null = null

  try {
    negocios = await listarNegocios()
  } catch (error) {
    // Si la API no responde, la página **sale igual** y lo dice. Una pantalla en blanco no
    // informa de nada y una excepción sin capturar tumba el servidor de renderizado.
    fallo = error instanceof ErrorDeApi ? error.message : 'No pudimos cargar los negocios.'
  }

  return (
    <main className="contenido">
      <header style={{ marginBottom: 'var(--espacio-6)' }}>
        <p
          style={{
            color: 'var(--color-acento)',
            fontWeight: 'var(--tipografia-pesos-medio)',
            marginBottom: 'var(--espacio-2)',
          }}
        >
          {NOMBRE}
        </p>
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-1)' }}>
          Reserva en salones y barberías de Panamá
        </h1>
        <p style={{ color: 'var(--color-texto-suave)', marginTop: 'var(--espacio-3)' }}>
          Sin llamar, sin esperar respuesta por WhatsApp. Eliges servicio, profesional y hora.
        </p>
      </header>

      {fallo ? (
        <p
          role="status"
          style={{
            background: 'var(--color-peligro-suave)',
            color: 'var(--color-peligro)',
            padding: 'var(--espacio-4)',
            borderRadius: 'var(--radio-grande)',
          }}
        >
          {fallo} Comprueba que la API está levantada con <code>make arriba</code>.
        </p>
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--espacio-3)' }}>
          {negocios.map((negocio) => (
            <li key={negocio.slug}>
              <Link
                href={`/${negocio.slug}`}
                style={{
                  display: 'block',
                  background: 'var(--color-superficie)',
                  border: '1px solid var(--color-borde)',
                  borderRadius: 'var(--radio-grande)',
                  padding: 'var(--espacio-4)',
                  textDecoration: 'none',
                  color: 'inherit',
                  // 44 px de objetivo táctil: la tarjeta entera se toca, no solo el nombre.
                  minHeight: 'var(--espacio-toque-minimo)',
                }}
              >
                <h2 style={{ fontSize: 'var(--tipografia-tamano-mayor)' }}>{negocio.nombre}</h2>
                {negocio.direccion && (
                  <p
                    style={{
                      color: 'var(--color-texto-suave)',
                      fontSize: 'var(--tipografia-tamano-menor)',
                      marginTop: 'var(--espacio-1)',
                    }}
                  >
                    {negocio.direccion}
                  </p>
                )}
                {negocio.servicios_desde_centavos !== null && (
                  <p
                    className="cifras"
                    style={{
                      marginTop: 'var(--espacio-2)',
                      fontSize: 'var(--tipografia-tamano-menor)',
                    }}
                  >
                    Desde {precio(negocio.servicios_desde_centavos)}
                  </p>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}

      {!fallo && negocios.length === 0 && (
        <p style={{ color: 'var(--color-texto-suave)' }}>
          Todavía no hay negocios publicados. Carga los datos de ejemplo con{' '}
          <code>make semilla</code>.
        </p>
      )}
    </main>
  )
}
