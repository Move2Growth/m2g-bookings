import { Mapa } from '@/componentes/mapa';
import { api, type SalonEnMapa } from '@/lib/api';
import { RECTANGULO_DE_ARRANQUE } from '@/lib/mapa';

export const metadata = {
  title: 'Mapa de salones',
  description: 'Los salones de Ciudad de Panamá en el mapa, con su nota y su enlace para reservar.',
};

/**
 * El mapa (encargo §5).
 *
 * Es la tercera puerta a lo mismo: buscar por nombre, buscar por persona o mirar por dónde vas a
 * pasar. Las tres viven al mismo nivel; esconder el mapa en un menú es no tenerlo.
 *
 * **La lista de salones se pide aquí, en el servidor, y viaja dentro del HTML.** Medido a 3G con
 * el procesador frenado, pedirla desde el navegador la dejaba en 4,8 segundos: no por la
 * consulta, que sale en el primer instante, sino porque antes hay que bajarse el JavaScript de
 * la pantalla. Una lista de nombres y notas no puede depender de eso — y menos siendo lo único
 * de aquí que un lector de pantalla puede leer.
 *
 * Si la API no contesta, la pantalla sale igual y la lista se llena desde el navegador en cuanto
 * el mapa arranque. Un mapa vacío es mejor que un error: lo que se está buscando es «qué hay por
 * aquí», y arrastrar el mapa vuelve a preguntar.
 */
export default async function PantallaDelMapa() {
  let inicial: SalonEnMapa[] = [];
  try {
    inicial = (await api.mapa(RECTANGULO_DE_ARRANQUE)).salones;
  } catch {
    // Se sigue sin lista. Leaflet la pedirá al arrancar.
  }

  return (
    <div className="contenido" data-superficie="calle">
      <div className="seccion pila aparece">
        <span className="etiqueta">Por dónde te queda</span>
        <h1 className="rotulo rotulo--grande">Los salones, en el mapa.</h1>
        <Mapa inicial={inicial} />
      </div>
    </div>
  );
}
