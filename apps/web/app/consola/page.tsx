import { ComoVa, PuertaDeConsola } from '@/componentes/consola';

export const metadata = { title: 'Consola de M2G', robots: { index: false, follow: false } };

/**
 * La consola interna. **Otra superficie**: otro acceso, otro rol de base de datos y segundo
 * factor obligatorio. No se indexa.
 */
export default function PantallaDeConsola() {
  return (
    <div className="contenido" data-superficie="trastienda">
      <div className="seccion pila aparece">
        <span className="etiqueta">M2G</span>
        <h1 className="rotulo rotulo--grande">Cómo va</h1>
        <PuertaDeConsola>
          <ComoVa />
        </PuertaDeConsola>
      </div>
    </div>
  );
}
