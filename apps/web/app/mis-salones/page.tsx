import { MisSalones } from '@/componentes/mis-salones';

export const metadata = { title: 'Mis salones', description: 'Los salones que has guardado, para volver sin buscar.' };

/** Los favoritos de la clienta: volver a donde ya fuiste sin tener que acordarte del nombre. */
export default function PantallaDeFavoritos() {
  return (
    <div className="contenido" data-superficie="calle">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tuyos</span>
        <h1 className="rotulo rotulo--grande">Mis salones</h1>
        <MisSalones />
      </div>
    </div>
  );
}
