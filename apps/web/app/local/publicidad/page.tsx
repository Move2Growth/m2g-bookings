import { NavLocal } from '@/componentes/nav-local';
import { SoloDueno } from '@/componentes/en-el-salon';
import { Publicidad } from '@/componentes/portal-dueno';

export const metadata = { title: 'Publicidad', description: 'Una línea tuya, encima de tu ficha, escrita y quitada desde aquí.' };

/** Publicidad · una de las seis piezas del portal del dueño (encargo §6). */
export default function Pantalla() {
  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tu salón</span>
        <h1 className="rotulo rotulo--grande">Publicidad</h1>
        <NavLocal />
        <SoloDueno>
          <Publicidad />
        </SoloDueno>
      </div>
    </div>
  );
}
