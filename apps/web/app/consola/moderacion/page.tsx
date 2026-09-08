import { Moderacion, PuertaDeConsola } from '@/componentes/consola';

export const metadata = { title: 'Moderación · Consola', robots: { index: false, follow: false } };

/** Las reseñas reportadas y las fotos por revisar, en la misma pantalla: es la misma cola. */
export default function PantallaDeModeracion() {
  return (
    <div className="contenido" data-superficie="trastienda">
      <div className="seccion pila aparece">
        <span className="etiqueta">M2G</span>
        <h1 className="rotulo rotulo--grande">Moderación</h1>
        <PuertaDeConsola>
          <Moderacion />
        </PuertaDeConsola>
      </div>
    </div>
  );
}
