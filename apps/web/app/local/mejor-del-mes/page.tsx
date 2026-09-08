import { NavLocal } from '@/componentes/nav-local';
import { MejorDelMes } from '@/componentes/portal-dueno';

export const metadata = { title: 'Mejor del mes', description: 'Quién va por delante este mes, por dinero o por servicios.' };

/** Mejor del mes · una de las seis piezas del portal del dueño (encargo §6). */
export default function Pantalla() {
  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tu salón</span>
        <h1 className="rotulo rotulo--grande">Mejor del mes</h1>
        <NavLocal />
        <MejorDelMes />
      </div>
    </div>
  );
}
