import { EnElSalon } from '@/componentes/en-el-salon';
import { NavProfesional } from '@/componentes/nav-profesional';
import { MiDia } from '@/componentes/mi-agenda';

export const metadata = { title: 'Mi día', description: 'A quién atiendes hoy, a qué hora y con qué servicio.' };

/** El portal del profesional: su día. Aquí no hay dinero del salón ni equipo: no es su zona. */
export default function PantallaDeMiAgenda() {
  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tu trabajo</span>
        <h1 className="rotulo rotulo--grande">Mi día</h1>
        <NavProfesional />
        <EnElSalon>
          <MiDia />
        </EnElSalon>
      </div>
    </div>
  );
}
