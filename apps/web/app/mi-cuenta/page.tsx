import { MiCuenta } from '@/componentes/mi-cuenta';

export const metadata = {
  title: 'Mi cuenta',
  description: 'Tus datos y la puerta de salida: darte de baja se hace aquí, no por correo.',
};

/** Mi cuenta. Aquí vive el derecho de supresión de la Ley 81, ejercible en la propia pantalla. */
export default function PantallaDeMiCuenta() {
  return (
    <div className="contenido" data-superficie="calle">
      <div className="seccion pila aparece">
        <span className="etiqueta">Tuyo</span>
        <h1 className="rotulo rotulo--grande">Mi cuenta</h1>
        <MiCuenta />
      </div>
    </div>
  );
}
