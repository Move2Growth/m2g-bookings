'use client';

/**
 * El mapa de salones (encargo §5).
 *
 * Es la tercera forma de buscar lo mismo: quien no sabe el nombre de nada pero sabe por dónde va
 * a pasar. Por eso vive al lado de la búsqueda y no escondido en un menú.
 *
 * **Las baldosas son de OpenStreetMap y no piden clave.** Es una decisión con consecuencia
 * escrita: el proveedor de mapas de pago sigue sin decidirse por coste, y montar el mapa contra
 * uno que factura sin que nadie lo haya aprobado es gastar dinero de otro. Cambiarlo el día que
 * se decida es cambiar una URL.
 *
 * Se pide **por rectángulo**: lo que se ve es lo que se pregunta. Arrastrar el mapa vuelve a
 * preguntar, y por eso la petición va con freno — sin él, un dedo arrastrando dispara veinte
 * consultas que nadie llega a leer.
 *
 * Su hoja de estilo se **importa del paquete**, no se copia a `public/`. La copia obligaba a
 * mantener a mano una hoja de terceros de seiscientas líneas —con sus propios hexadecimales y su
 * propia tipografía— dentro de un proyecto cuya regla es que todo el color salga de los tokens.
 * Importada, el empaquetador la trae, la regla sigue siendo cierta y no hay dos versiones.
 */

import 'leaflet/dist/leaflet.css';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';

import { Roto } from '@/componentes/estados';
import { Nota } from '@/componentes/piezas';
import { api, comoMensaje, type SalonEnMapa } from '@/lib/api';

/** El centro de Ciudad de Panamá y un zoom en el que se ven los barrios, no el país. */
const CENTRO: [number, number] = [8.9824, -79.5199];
const ZOOM = 14;

export function Mapa() {
  const caja = useRef<HTMLDivElement>(null);
  const mapa = useRef<import('leaflet').Map | null>(null);
  const capa = useRef<import('leaflet').LayerGroup | null>(null);
  const [salones, setSalones] = useState<SalonEnMapa[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const preguntar = useCallback(async (L: typeof import('leaflet'), m: import('leaflet').Map) => {
    const rect = m.getBounds();
    setCargando(true);
    try {
      const respuesta = await api.mapa({
        oeste: rect.getWest(),
        sur: rect.getSouth(),
        este: rect.getEast(),
        norte: rect.getNorth(),
      });
      setSalones(respuesta.salones);
      setFallo(null);

      capa.current?.clearLayers();
      for (const salon of respuesta.salones) {
        // El pin es texto, no una chincheta: a partir de cinco salones juntos, doce chinchetas
        // iguales no dicen nada y el nombre sí.
        const marca = L.marker([salon.latitud, salon.longitud], {
          icon: L.divIcon({
            className: 'pin',
            html: `<span class="pin__caja"><span class="pin__nombre">${salon.nombre.replace(/</g, '&lt;')}</span>${
              salon.rating ? `<span class="pin__nota cifras">${salon.rating.toFixed(1)}</span>` : ''
            }</span>`,
            iconSize: undefined,
            iconAnchor: [0, 0],
          }),
          keyboard: true,
          alt: salon.nombre,
        });
        marca.on('click', () => {
          window.location.href = `/salon/${salon.slug}`;
        });
        marca.addTo(capa.current!);
      }
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    let vivo = true;
    let freno: ReturnType<typeof setTimeout> | undefined;

    // Leaflet toca `window` al importarse, así que entra en el navegador y no en el servidor.
    import('leaflet').then((L) => {
      if (!vivo || !caja.current || mapa.current) return;
      const m = L.map(caja.current, { center: CENTRO, zoom: ZOOM, zoomControl: false });
      L.control.zoom({ position: 'topright' }).addTo(m);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© colaboradores de OpenStreetMap',
      }).addTo(m);
      capa.current = L.layerGroup().addTo(m);
      mapa.current = m;

      const alMover = () => {
        clearTimeout(freno);
        freno = setTimeout(() => void preguntar(L, m), 400);
      };
      m.on('moveend', alMover);
      void preguntar(L, m);
    });

    return () => {
      vivo = false;
      clearTimeout(freno);
      mapa.current?.remove();
      mapa.current = null;
    };
  }, [preguntar]);

  return (
    <div className="pila">
      <div className="mapa">
        <div className="mapa__lienzo" ref={caja} role="application" aria-label="Mapa de salones" />
        <p className="mapa__estado" role="status">
          {cargando
            ? 'Buscando salones en lo que se ve…'
            : salones && salones.length > 0
              ? `${salones.length} ${salones.length === 1 ? 'salón' : 'salones'} en lo que se ve`
              : 'Aquí no hay ninguno. Arrastra el mapa o aleja.'}
        </p>
      </div>

      {fallo ? <Roto mensaje={fallo} /> : null}

      {/* **La lista de debajo no es un adorno.** Un mapa no se puede recorrer con el tabulador ni
          leer con un lector de pantalla; esta lista dice lo mismo y sí se puede. */}
      {salones && salones.length > 0 ? (
        <ul className="pila pila--apretada">
          {salones.map((salon) => (
            <li key={salon.negocio_id}>
              <Link className="fila-mapa" href={`/salon/${salon.slug}`}>
                <span className="pila pila--apretada">
                  <span className="rotulo rotulo--pequeno">{salon.nombre}</span>
                  <Nota valor={salon.rating} resenas={salon.numero_reviews} />
                </span>
                <span className="menor tenue">Ver y reservar</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
