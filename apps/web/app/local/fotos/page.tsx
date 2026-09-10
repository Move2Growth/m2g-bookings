import { EnElSalon } from '@/componentes/en-el-salon';
import { FotosDelSalon } from '@/componentes/fotos-del-salon';
import { NavLocal } from '@/componentes/nav-local';

export const metadata = {
  title: 'Tus fotos',
  description: 'La portada que se ve en la búsqueda y las fotos que se ven dentro de tu ficha.',
};

/** Las fotos del salón. Sin una, el salón no se puede publicar (D11). */
export default function PantallaDeFotos() {
  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tu salón</span>
        <h1 className="rotulo rotulo--grande">Tus fotos</h1>
        <NavLocal />
        <EnElSalon soloDueno>
          <FotosDelSalon />
        </EnElSalon>
      </div>
    </div>
  );
}
