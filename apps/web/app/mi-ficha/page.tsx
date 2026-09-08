import { NavProfesional } from '@/componentes/nav-profesional';
import { MiFicha } from '@/componentes/mi-agenda';

export const metadata = { title: 'Mi ficha', description: 'Lo que ve de ti quien te está eligiendo.' };

/** El portal del profesional: su ficha pública, editada por quien la protagoniza. */
export default function PantallaDeMiFicha() {
  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tu trabajo</span>
        <h1 className="rotulo rotulo--grande">Mi ficha</h1>
        <NavProfesional />
        <MiFicha />
      </div>
    </div>
  );
}
