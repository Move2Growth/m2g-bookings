import { PuertaDeConsola, Salones } from '@/componentes/consola';

export const metadata = { title: 'Salones · Consola', robots: { index: false, follow: false } };

/** Buscar un salón, y suspenderlo o reactivarlo. Suspender pide motivo: la auditoría lo guarda. */
export default function PantallaDeSalones() {
  return (
    <div className="contenido" data-superficie="trastienda">
      <div className="seccion pila aparece">
        <span className="etiqueta">M2G</span>
        <h1 className="rotulo rotulo--grande">Salones</h1>
        <PuertaDeConsola>
          <Salones />
        </PuertaDeConsola>
      </div>
    </div>
  );
}
