import { Mapa } from '@/componentes/mapa';

export const metadata = {
  title: 'Mapa de salones',
  description: 'Los salones de Ciudad de Panamá en el mapa, con su nota y su enlace para reservar.',
};

/**
 * El mapa (encargo §5).
 *
 * Es la tercera puerta a lo mismo: buscar por nombre, buscar por persona o mirar por dónde vas a
 * pasar. Las tres viven al mismo nivel; esconder el mapa en un menú es no tenerlo.
 */
export default function PantallaDelMapa() {
  return (
    <div className="contenido" data-superficie="calle">
      <div className="seccion pila aparece">
        <span className="etiqueta">Por dónde te queda</span>
        <h1 className="rotulo rotulo--grande">Los salones, en el mapa.</h1>
        <Mapa />
      </div>
    </div>
  );
}
