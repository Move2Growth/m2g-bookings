'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { Marca } from '@/componentes/marca'
import { API, conSesion, guardarSesion, leerSesion, type Sesion } from '@/lib/sesion'
import type { CategoriaGlobal, InvitacionCreada } from '@/lib/dueno'

/**
 * El alta del local, **en tres pasos**: crear el local, decir quién trabaja allí y cargar los
 * servicios. Es el punto 4 del encargo del 7 de septiembre, con estas palabras.
 *
 * Tres decisiones que vienen de ahí y no del gusto de nadie:
 *
 * · **El precio del servicio es opcional**, y la pantalla lo ofrece con las palabras de siempre:
 *   «A consultar». Obligar a poner un número hace que se invente uno, y un precio inventado en
 *   una ficha pública es peor que no tener precio.
 * · **El paso de las personas se puede saltar.** Un salón de una persona es el caso normal en
 *   Panamá, y obligarle a invitar a alguien para poder seguir es pedirle que se invente un
 *   compañero.
 * · **Cada paso guarda al terminarlo**, no al final. Si el teléfono se queda sin batería en el
 *   paso tres, el local existe y las personas están invitadas; solo faltan los servicios, y se
 *   entra por la puerta normal a ponerlos.
 *
 * No lleva pestañas: son tres pasos seguidos, y una barra de navegación en medio solo invita a
 * abandonarlos.
 *
 * **El mapa no está aquí y es a propósito.** Dibujar un mapa necesita un proveedor y su clave
 * (decisión D8, abierta). Mientras no la haya, la ubicación se pone con las coordenadas o con el
 * botón de «usar dónde estoy» del propio teléfono, que no depende de nadie.
 */

type Paso = 1 | 2 | 3 | 4

/** El centro de Ciudad de Panamá. Es un punto de partida, no una respuesta: se cambia siempre. */
const PANAMA = { longitud: -79.5199, latitud: 8.9936 }

export default function AltaDelLocal() {
  const router = useRouter()
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [paso, setPaso] = useState<Paso>(1)
  const [local, setLocal] = useState<{ id: string; slug: string; nombre: string } | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  return (
    <main className="contenedor" style={{ paddingBottom: 'var(--espacio-8)' }}>
      <p style={{ paddingTop: 'var(--espacio-4)' }}>
        <Link href="/" aria-label="Inicio">
          <Marca alto={20} />
        </Link>
      </p>

      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>
          {paso === 4 ? 'Tu local está dado de alta' : 'Dar de alta un local'}
        </h1>
      </div>

      {paso < 4 && (
        // El indicador de paso es texto, no tres bolitas: «Paso 2 de 3 · Personas» se entiende
        // sin mirar, y tres bolitas grises no dicen ni cuántas quedan ni de qué van.
        <p className="etiqueta">
          Paso {paso} de 3 ·{' '}
          {paso === 1 ? 'El local' : paso === 2 ? 'Las personas' : 'Los servicios'}
        </p>
      )}

      {!sesion && (
        <p className="aviso aviso--info">
          Para dar de alta un local hace falta entrar antes.{' '}
          <Link href="/entrar?volver=%2Fpanel%2Falta">Entrar o crear una cuenta</Link>
        </p>
      )}

      {sesion && paso === 1 && (
        <PasoDelLocal
          sesion={sesion}
          onCreado={(creado, nueva) => {
            setLocal(creado)
            setSesion(nueva)
            setPaso(2)
          }}
        />
      )}

      {sesion && paso === 2 && local && (
        <PasoDeLasPersonas sesion={sesion} onSeguir={() => setPaso(3)} />
      )}

      {sesion && paso === 3 && local && (
        <PasoDeLosServicios sesion={sesion} onSeguir={() => setPaso(4)} />
      )}

      {sesion && paso === 4 && local && (
        <section className="bloque-panel">
          <p className="aviso aviso--exito">
            <strong>{local.nombre}</strong> ya existe y estás dentro de él. Todavía está en
            borrador: no lo ve nadie en el buscador hasta que lo publiques.
          </p>
          <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
            Lo que falta para publicarlo —el horario, una foto— te lo va diciendo la pantalla de
            la ficha, punto por punto.
          </p>
          <div className="acciones" style={{ marginTop: 'var(--espacio-4)' }}>
            <button
              type="button"
              className="boton boton--primario"
              onClick={() => router.push('/panel/local')}
            >
              Ir a mi local
            </button>
            <button
              type="button"
              className="boton boton--secundario"
              onClick={() => router.push('/panel/ficha')}
            >
              Ver qué falta para publicar
            </button>
          </div>
        </section>
      )}
    </main>
  )
}

/* ── Paso 1 · El local ─────────────────────────────────────────────────────── */

function PasoDelLocal({
  sesion,
  onCreado,
}: {
  sesion: Sesion
  onCreado: (local: { id: string; slug: string; nombre: string }, sesion: Sesion) => void
}) {
  const [nombre, setNombre] = useState('')
  const [categoria, setCategoria] = useState('')
  const [categorias, setCategorias] = useState<CategoriaGlobal[]>([])
  const [direccion, setDireccion] = useState('')
  const [punto, setPunto] = useState(PANAMA)
  const [ubicando, setUbicando] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/api/v1/catalogo/categorias`)
      .then((r) => (r.ok ? r.json() : []))
      .then((lista: CategoriaGlobal[]) => {
        setCategorias(lista)
        setCategoria((previa) => previa || lista[0]?.slug || '')
      })
      .catch(() => setCategorias([]))
  }, [])

  function usarMiUbicacion() {
    if (!navigator.geolocation) {
      setFallo('Este navegador no sabe dónde estás. Pon las coordenadas a mano.')
      return
    }
    setUbicando(true)
    navigator.geolocation.getCurrentPosition(
      (posicion) => {
        setPunto({
          longitud: Number(posicion.coords.longitude.toFixed(6)),
          latitud: Number(posicion.coords.latitude.toFixed(6)),
        })
        setUbicando(false)
      },
      () => {
        setFallo('No se pudo leer tu ubicación. Pon las coordenadas a mano.')
        setUbicando(false)
      },
      { timeout: 8000 },
    )
  }

  async function crear(evento: React.FormEvent) {
    evento.preventDefault()
    setGuardando(true)
    setFallo(null)
    try {
      const creado = await conSesion<{ id: string; slug: string; estado: string }>(
        '/api/v1/negocios',
        {
          metodo: 'POST',
          token: sesion.acceso,
          cuerpo: {
            nombre: nombre.trim(),
            categoria,
            direccion: direccion.trim(),
            longitud: punto.longitud,
            latitud: punto.latitud,
          },
        },
      )

      // Cambiar de contexto es **pedir otro token**, no mandar un parámetro distinto: sin esto,
      // los pasos dos y tres irían al negocio anterior de esta persona, si tenía otro.
      const conNegocio = await fetch(`${API}/api/v1/auth/modo-negocio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${sesion.acceso}` },
        body: JSON.stringify({ negocio_id: creado.id }),
      }).then((r) => (r.ok ? r.json() : null))
      if (!conNegocio) throw new Error('El local se creó, pero no se pudo entrar en él.')

      const nueva: Sesion = {
        ...conNegocio,
        negocio_nombre: nombre.trim(),
        negocio_rol: 'dueno',
      }
      guardarSesion(nueva)
      onCreado({ id: creado.id, slug: creado.slug, nombre: nombre.trim() }, nueva)
    } catch (error) {
      setFallo(error instanceof Error ? error.message : 'No se pudo crear el local.')
      setGuardando(false)
    }
  }

  return (
    <form onSubmit={crear} className="formulario">
      <label className="campo">
        <span>Cómo se llama</span>
        <input
          className="entrada"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Barbería El Cangrejo"
          required
          autoFocus
        />
      </label>

      <label className="campo">
        <span>A qué se dedica</span>
        <select
          className="entrada"
          value={categoria}
          onChange={(e) => setCategoria(e.target.value)}
          required
        >
          {categorias.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.nombre}
            </option>
          ))}
        </select>
        <span className="campo-ayuda">
          Es la categoría principal. Luego se pueden añadir más desde la ficha.
        </span>
      </label>

      <label className="campo">
        <span>Dónde está</span>
        <input
          className="entrada"
          value={direccion}
          onChange={(e) => setDireccion(e.target.value)}
          placeholder="Calle 53 Este, Obarrio"
          required
        />
      </label>

      <fieldset className="grupo">
        <legend className="campo-etiqueta">El punto en el mapa</legend>
        <p className="campo-ayuda">
          Es lo que hace que salgas cuando alguien busca «cerca de mí». Si estás en el local, con
          el botón se pone solo.
        </p>
        <div className="pareja" style={{ marginTop: 'var(--espacio-3)' }}>
          <label className="campo">
            <span>Latitud</span>
            <input
              className="entrada cifras"
              inputMode="decimal"
              value={punto.latitud}
              onChange={(e) => setPunto((p) => ({ ...p, latitud: Number(e.target.value) }))}
              required
            />
          </label>
          <label className="campo">
            <span>Longitud</span>
            <input
              className="entrada cifras"
              inputMode="decimal"
              value={punto.longitud}
              onChange={(e) => setPunto((p) => ({ ...p, longitud: Number(e.target.value) }))}
              required
            />
          </label>
        </div>
        <button
          type="button"
          className="boton boton--secundario"
          onClick={usarMiUbicacion}
          disabled={ubicando}
        >
          {ubicando ? 'Buscando dónde estás…' : 'Usar dónde estoy ahora'}
        </button>
      </fieldset>

      {fallo && (
        <p role="alert" className="aviso aviso--error">
          {fallo}
        </p>
      )}

      <div className="acciones acciones--separadas">
        <button type="submit" className="boton boton--primario boton--ancho" disabled={guardando}>
          {guardando ? 'Creando el local…' : 'Crear el local y seguir'}
        </button>
      </div>
    </form>
  )
}

/* ── Paso 2 · Las personas ─────────────────────────────────────────────────── */

function PasoDeLasPersonas({ sesion, onSeguir }: { sesion: Sesion; onSeguir: () => void }) {
  const [correo, setCorreo] = useState('')
  const [rol, setRol] = useState<'dueno' | 'profesional'>('profesional')
  const [invitadas, setInvitadas] = useState<{ correo: string; rol: string; enlace?: string }[]>([])
  const [enviando, setEnviando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  async function invitar(evento: React.FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setFallo(null)
    try {
      const creada = await conSesion<InvitacionCreada>('/api/v1/negocio/miembros/invitaciones', {
        metodo: 'POST',
        token: sesion.acceso,
        cuerpo: { correo: correo.trim(), rol },
      })
      setInvitadas((previas) => [
        ...previas,
        { correo: correo.trim(), rol, enlace: creada.enlace_de_desarrollo ?? undefined },
      ])
      setCorreo('')
    } catch (error) {
      setFallo(error instanceof Error ? error.message : 'No se pudo invitar a esa persona.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <>
      <p className="tenue medida">
        Quien trabaje contigo entra con su propio correo y ve lo que le toca. Si trabajas sola,
        salta este paso: no hace falta invitar a nadie.
      </p>

      <form onSubmit={invitar} className="formulario">
        <label className="campo">
          <span>Su correo</span>
          <input
            className="entrada"
            type="email"
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            placeholder="nombre@correo.com"
          />
        </label>

        <fieldset className="grupo">
          <legend className="campo-etiqueta">Qué papel tiene</legend>
          <div className="tira tira--envuelve">
            <button
              type="button"
              className="ficha"
              aria-pressed={rol === 'profesional'}
              onClick={() => setRol('profesional')}
            >
              Profesional
            </button>
            <button
              type="button"
              className="ficha"
              aria-pressed={rol === 'dueno'}
              onClick={() => setRol('dueno')}
            >
              Dueño
            </button>
          </div>
          <p className="campo-ayuda" style={{ marginTop: 'var(--espacio-2)' }}>
            {rol === 'profesional'
              ? 'Ve su propia agenda y su horario, nada más.'
              : 'Ve y cambia todo el local, como tú.'}
          </p>
        </fieldset>

        {fallo && (
          <p role="alert" className="aviso aviso--error">
            {fallo}
          </p>
        )}

        <button
          type="submit"
          className="boton boton--secundario"
          disabled={enviando || correo.trim() === ''}
        >
          {enviando ? 'Invitando…' : 'Invitar a esta persona'}
        </button>
      </form>

      {invitadas.length > 0 && (
        <ul className="filas" style={{ marginTop: 'var(--espacio-5)' }}>
          {invitadas.map((i) => (
            <li key={i.correo} className="fila">
              <div className="fila__boton" style={{ cursor: 'default' }}>
                <span className="fila__principal">
                  <span className="fila__nombre">{i.correo}</span>
                  <span className="fila__detalle">
                    Invitación enviada como {i.rol === 'dueno' ? 'dueño' : 'profesional'}
                  </span>
                  {i.enlace && (
                    <span className="fila__detalle" style={{ wordBreak: 'break-all' }}>
                      Sin correo real en este entorno; pásale este enlace: {i.enlace}
                    </span>
                  )}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="acciones acciones--separadas">
        <button type="button" className="boton boton--primario boton--ancho" onClick={onSeguir}>
          {invitadas.length === 0 ? 'Trabajo sola, seguir' : 'Seguir con los servicios'}
        </button>
      </div>
    </>
  )
}

/* ── Paso 3 · Los servicios ────────────────────────────────────────────────── */

type ServicioNuevo = {
  nombre: string
  duracion_minutos: number
  precio_centavos: number | null
  tipo_de_precio: string
}

function PasoDeLosServicios({ sesion, onSeguir }: { sesion: Sesion; onSeguir: () => void }) {
  const [categorias, setCategorias] = useState<CategoriaGlobal[]>([])
  const [categoria, setCategoria] = useState('')
  const [nombre, setNombre] = useState('')
  const [duracion, setDuracion] = useState('45')
  const [tipoDePrecio, setTipoDePrecio] = useState('fijo')
  const [precioTexto, setPrecioTexto] = useState('')
  const [creados, setCreados] = useState<ServicioNuevo[]>([])
  const [guardando, setGuardando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/api/v1/catalogo/categorias`)
      .then((r) => (r.ok ? r.json() : []))
      .then((lista: CategoriaGlobal[]) => {
        setCategorias(lista)
        setCategoria((previa) => previa || lista[0]?.slug || '')
      })
      .catch(() => setCategorias([]))
  }, [])

  async function anadir(evento: React.FormEvent) {
    evento.preventDefault()
    setGuardando(true)
    setFallo(null)
    // «A consultar» manda sobre lo escrito: si alguien tecleó un precio y luego eligió «a
    // consultar», lo que vale es lo último que dijo.
    const centavos =
      tipoDePrecio === 'consultar' || precioTexto.trim() === ''
        ? null
        : Math.round(Number(precioTexto.replace(',', '.')) * 100)
    try {
      await conSesion('/api/v1/negocio/servicios', {
        metodo: 'POST',
        token: sesion.acceso,
        cuerpo: {
          nombre: nombre.trim(),
          categoria,
          duracion_minutos: Number(duracion),
          precio_centavos: centavos,
          tipo_de_precio: tipoDePrecio,
        },
      })
      setCreados((previos) => [
        ...previos,
        {
          nombre: nombre.trim(),
          duracion_minutos: Number(duracion),
          precio_centavos: centavos,
          tipo_de_precio: tipoDePrecio,
        },
      ])
      setNombre('')
      setPrecioTexto('')
    } catch (error) {
      setFallo(error instanceof Error ? error.message : 'No se pudo dar de alta el servicio.')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <>
      <p className="tenue medida">
        Con uno basta para que se pueda reservar. El resto se añaden cuando quieras.
      </p>

      <form onSubmit={anadir} className="formulario">
        <label className="campo">
          <span>Cómo se llama</span>
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
          <span>De qué es</span>
          <select
            className="entrada"
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
          >
            {categorias.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>

        <label className="campo">
          <span>Cuánto dura</span>
          <select
            className="entrada"
            value={duracion}
            onChange={(e) => setDuracion(e.target.value)}
          >
            {[15, 20, 30, 45, 60, 75, 90, 120, 150, 180, 240].map((m) => (
              <option key={m} value={m}>
                {m} min
              </option>
            ))}
          </select>
        </label>

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
          {/* El encargo dice que el precio es opcional, así que la pantalla lo dice con todas
              las letras y en el sitio donde se decide, no en una ayuda al final. */}
          <p className="campo-ayuda" style={{ marginTop: 'var(--espacio-2)' }}>
            {tipoDePrecio === 'consultar'
              ? 'En tu ficha saldrá «A consultar». No hace falta inventarse un número.'
              : tipoDePrecio === 'desde'
                ? 'Se enseña «Desde $X». Sirve para lo que cambia según el pelo o el trabajo.'
                : 'Se enseña el precio tal cual. Si todavía no lo sabes, elige «A consultar».'}
          </p>
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

        {fallo && (
          <p role="alert" className="aviso aviso--error">
            {fallo}
          </p>
        )}

        <button type="submit" className="boton boton--secundario" disabled={guardando}>
          {guardando ? 'Guardando…' : 'Añadir este servicio'}
        </button>
      </form>

      {creados.length > 0 && (
        <ul className="filas" style={{ marginTop: 'var(--espacio-5)' }}>
          {creados.map((s, i) => (
            <li key={`${s.nombre}-${i}`} className="fila">
              <div className="fila__boton" style={{ cursor: 'default' }}>
                <span className="fila__principal">
                  <span className="fila__nombre">{s.nombre}</span>
                  <span className="fila__detalle">{s.duracion_minutos} min</span>
                </span>
                <span className="fila__cifra cifras">
                  {s.tipo_de_precio === 'consultar' || s.precio_centavos === null
                    ? 'A consultar'
                    : `${s.tipo_de_precio === 'desde' ? 'Desde ' : ''}$${(s.precio_centavos / 100).toFixed(2)}`}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="acciones acciones--separadas">
        <button
          type="button"
          className="boton boton--primario boton--ancho"
          onClick={onSeguir}
          disabled={creados.length === 0}
        >
          Terminar
        </button>
        {creados.length === 0 && (
          <p className="campo-ayuda">
            Hace falta al menos un servicio: sin ninguno, tu ficha no se puede reservar. Añade el
            que más hagas y sigue.
          </p>
        )}
      </div>
    </>
  )
}
