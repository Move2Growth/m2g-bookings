import { NavLocal } from '@/componentes/nav-local';
import { ElDinero } from '@/componentes/portal-dueno';

export const metadata = { title: 'El dinero', description: 'Lo que has facturado, por día, por semana o por mes.' };

/** El dinero · una de las seis piezas del portal del dueño (encargo §6). */
export default function Pantalla() {
  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tu salón</span>
        <h1 className="rotulo rotulo--grande">El dinero</h1>
        <NavLocal />
        <ElDinero />
      </div>
    </div>
  );
}
