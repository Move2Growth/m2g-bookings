import { NavLocal } from '@/componentes/nav-local';
import { SoloDueno } from '@/componentes/en-el-salon';
import { ElEquipo } from '@/componentes/portal-dueno';

export const metadata = { title: 'El equipo', description: 'Quién trabaja en tu salón, y a quién le pides fichaje.' };

/** El equipo · una de las seis piezas del portal del dueño (encargo §6). */
export default function Pantalla() {
  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tu salón</span>
        <h1 className="rotulo rotulo--grande">El equipo</h1>
        <NavLocal />
        <SoloDueno>
          <ElEquipo />
        </SoloDueno>
      </div>
    </div>
  );
}
