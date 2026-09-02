'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Hoja } from '@/componentes/hoja'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * El catálogo del salón.
 *
 * La lista se lee como una carta: **nombre, duración y precio**, en ese orden, porque es el
 * orden en que se le canta a una clienta por teléfono.
 *
 * Un servicio no se borra si tiene citas: se desactiva. Borrarlo dejaría citas pasadas
 * apuntando a un servicio que ya no existe, y ese es el tipo de agujero que aparece meses
 * después en la contabilidad. Eso lo decide el servidor; aquí solo se enseña la consecuencia.
 */

type Variante = {
  id: string
  nombre: string
  duracion_minutos: number
  precio_centavos: number | null
  tipo_de_precio: string
  activa: boolean
}

type Servicio = {
  id: string
  nombre: string
  descripcion: string | null
  categoria_slug: string
  categoria_nombre: string
  duracion_minutos: number
  precio_centavos: number | null
  tipo_de_precio: string
  moneda: string
  buffer_antes_min: number
  buffer_despues_min: number
  foto: string | null
  activo: boolean
  orden: number
  profesionales: number
  variantes: Variante[]
}

type Categoria = { id: string; slug: string; nombre: string; padre_slug: string | null }

function precio(s: { precio_centavos: number | null; tipo_de_precio: string }) {
  if (s.tipo_de_precio === 'consultar' || s.precio_centavos === null) return 'A consultar'
  const cifra = `$${(s.precio_centavos / 100).toFixed(2)}`
  return s.tipo_de_precio === 'desde' ? `Desde ${cifra}` : cifra
}

export default function Servicios() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [servicios, setServicios] = useState<Servicio[] | null>(null)
  const [categorias, setCategorias] = useState<Categoria[]>([])
  const [error, setError] = useState<string | null>(null)
  const [editando, setEditando] = useState<Servicio | 'nuevo' | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      const [lista, cats] = await Promise.all([
        conSesion<Servicio[]>('/api/v1/negocio/servicios', { token: actual.acceso }),
        conSesion<Categoria[]>('/api/v1/catalogo/categorias', { token: actual.acceso }),
      ])
      setServicios(lista)
      setCategorias(cats)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar tus servicios.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  const activos = (servicios ?? []).filter((s) => s.activo)
  const apagados = (servicios ?? []).filter((s) => !s.activo)

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Servicios</h1>
        <button type="button" className="boton boton--primario" onClick={() => setEditando('nuevo')}>
          Añadir servicio
        </button>
      </div>

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      )}

      {servicios === null && !error && <Esqueleto filas={4} alto={72} etiqueta="Cargando tus servicios" />}

      {servicios !== null && servicios.length === 0 && (
        <Vacio
          icono={Iconos.servicios}
          titulo="Todavía no tienes servicios"
          texto="Con uno basta para que se pueda reservar. Puedes añadir el resto cuando quieras."
        />
      )}

      {activos.length > 0 && (
        <ul className="filas escalona">
          {activos.map((s) => (
            <FilaDeServicio key={s.id} servicio={s} onEditar={() => setEditando(s)} />
          ))}
        </ul>
      )}

      {apagados.length > 0 && (
        <>
          <h2 className="etiqueta" style={{ marginTop: 'var(--espacio-6)' }}>
            Desactivados
          </h2>
          <p className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
            No se pueden reservar y no salen en tu ficha. Las citas que ya tenían se respetan.
          </p>
          <ul className="filas filas--apagadas">
            {apagados.map((s) => (
              <FilaDeServicio key={s.id} servicio={s} onEditar={() => setEditando(s)} />
            ))}
          </ul>
        </>
      )}

      {editando && sesion && (
        <FormularioDeServicio
          servicio={editando === 'nuevo' ? null : editando}
          categorias={categorias}
          sesion={sesion}
          onCerrar={() => setEditando(null)}
          onGuardado={() => {
            setEditando(null)
            void cargar(sesion)
          }}
        />
      )}
    </div>
  )
}

function FilaDeServicio({ servicio, onEditar }: { servicio: Servicio; onEditar: () => void }) {
  return (
    <li className="fila">
      <button type="button" className="fila__boton" onClick={onEditar}>
        <span className="fila__principal">
          <span className="fila__nombre">{servicio.nombre}</span>
          <span className="fila__detalle">
            {servicio.categoria_nombre} · {servicio.duracion_minutos} min
            {servicio.profesionales === 0 && (
              /* Un servicio que no hace nadie no se puede reservar aunque esté activo. Es el
                 fallo silencioso más común al montar el catálogo. */
              <span className="fila__alerta"> · nadie lo hace todavía</span>
            )}
          </span>
        </span>
        <span className="fila__cifra cifras">{precio(servicio)}</span>
      </button>
    </li>
  )
}

/**
 * El formulario, en una hoja.
 *
 * En hoja y no en otra página porque editar un precio es un gesto de veinte segundos entre dos
 * clientas: al cerrarla se vuelve a la lista en el mismo sitio.
 */
function FormularioDeServicio({
  servicio,
  categorias,
  sesion,
  onCerrar,
  onGuardado,
}: {
  servicio: Servicio | null
  categorias: Categoria[]
  sesion: Sesion
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [nombre, setNombre] = useState(servicio?.nombre ?? '')
  const [categoria, setCategoria] = useState(servicio?.categoria_slug ?? categorias[0]?.slug ?? '')
  const [duracion, setDuracion] = useState(String(servicio?.duracion_minutos ?? 30))
  const [tipoDePrecio, setTipoDePrecio] = useState(servicio?.tipo_de_precio ?? 'fijo')
  const [precioTexto, setPrecioTexto] = useState(
    servicio?.precio_centavos != null ? (servicio.precio_centavos / 100).toFixed(2) : '',
  )
  const [bufferDespues, setBufferDespues] = useState(String(servicio?.buffer_despues_min ?? 0))
  const [activo, setActivo] = useState(servicio?.activo ?? true)
  const [guardando, setGuardando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault()
    setGuardando(true)
    setFallo(null)
    const centavos =
      tipoDePrecio === 'consultar' || precioTexto.trim() === ''
        ? null
        : Math.round(Number(precioTexto.replace(',', '.')) * 100)
    try {
      if (servicio) {
        await conSesion(`/api/v1/negocio/servicios/${servicio.id}`, {
          metodo: 'PATCH',
          token: sesion.acceso,
          cuerpo: {
            nombre: nombre.trim(),
            categoria,
            duracion_minutos: Number(duracion),
            precio_centavos: centavos,
            tipo_de_precio: tipoDePrecio,
            buffer_despues_min: Number(bufferDespues),
            activo,
          },
        })
      } else {
        await conSesion('/api/v1/negocio/servicios', {
          metodo: 'POST',
          token: sesion.acceso,
          cuerpo: {
            nombre: nombre.trim(),
            categoria,
            duracion_minutos: Number(duracion),
            precio_centavos: centavos,
            tipo_de_precio: tipoDePrecio,
            buffer_despues_min: Number(bufferDespues),
          },
        })
      }
      onGuardado()
    } catch (error) {
      setFallo(error instanceof Error ? error.message : 'No se pudo guardar.')
      setGuardando(false)
    }
  }

  return (
    <Hoja titulo={servicio ? 'Editar servicio' : 'Nuevo servicio'} onCerrar={onCerrar}>
      <form onSubmit={guardar} className="formulario">
        <label className="campo">
          <span>Nombre</span>
          <input
            className="entrada"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Corte + barba"
            required
            autoFocus
          />
        </label>

        <label className="campo">
          <span>Categoría</span>
          <select className="entrada" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
            {categorias.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>

        <div className="pareja">
          <label className="campo">
            <span>Duración</span>
            <select className="entrada" value={duracion} onChange={(e) => setDuracion(e.target.value)}>
              {[10, 15, 20, 30, 45, 60, 75, 90, 120, 150, 180, 240].map((m) => (
                <option key={m} value={m}>
                  {m} min
                </option>
              ))}
            </select>
          </label>

          <label className="campo">
            <span>Descanso después</span>
            <select
              className="entrada"
              value={bufferDespues}
              onChange={(e) => setBufferDespues(e.target.value)}
            >
              {[0, 5, 10, 15, 20, 30].map((m) => (
                <option key={m} value={m}>
                  {m === 0 ? 'Ninguno' : `${m} min`}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)', marginTop: 'calc(var(--espacio-3) * -1)' }}>
          El descanso es tuyo: se reserva después de la cita para limpiar o recoger, y nadie
          puede ocuparlo.
        </p>

        <fieldset className="grupo">
          <legend className="campo-etiqueta">Precio</legend>
          <div className="tira tira--envuelve">
            {[
              ['Fijo', 'fijo'],
              ['Desde', 'desde'],
              ['A consultar', 'consultar'],
            ].map(([texto, valor]) => (
              <button
                key={valor}
                type="button"
                className="ficha"
                aria-pressed={tipoDePrecio === valor}
                onClick={() => setTipoDePrecio(valor)}
              >
                {texto}
              </button>
            ))}
          </div>
        </fieldset>

        {tipoDePrecio !== 'consultar' && (
          <label className="campo">
            <span>Cuánto cuesta</span>
            <input
              className="entrada cifras"
              inputMode="decimal"
              value={precioTexto}
              onChange={(e) => setPrecioTexto(e.target.value)}
              placeholder="18.00"
            />
          </label>
        )}

        {servicio && (
          <label className="interruptor">
            <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
            <span>Se puede reservar</span>
          </label>
        )}

        {fallo && (
          <p role="alert" className="aviso aviso--error">
            {fallo}
          </p>
        )}

        <div className="hoja__pie">
          <button type="button" className="boton boton--llano" onClick={onCerrar}>
            Cancelar
          </button>
          <button type="submit" className="boton boton--cierra" disabled={guardando}>
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </form>
    </Hoja>
  )
}
