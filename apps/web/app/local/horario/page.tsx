import { Horario } from '@/componentes/horario';
import { NavLocal } from '@/componentes/nav-local';
import { SoloDueno } from '@/componentes/en-el-salon';

export const metadata = {
  title: 'Horario',
  description: 'Cuándo abre el local, la jornada de cada persona y los ratos bloqueados.',
};

/** El horario del salón, el de cada persona y los bloqueos: la misma pregunta a tres escalas. */
export default function PantallaDeHorario() {
  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tu salón</span>
        <h1 className="rotulo rotulo--grande">Horario</h1>
        <NavLocal />
        <SoloDueno>
          <Horario />
        </SoloDueno>
      </div>
    </div>
  );
}
