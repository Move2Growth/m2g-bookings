import { AltaDeLocal } from '@/componentes/alta';

export const metadata = {
  title: 'Dar de alta un local',
  description: 'Crea tu salón en tres pasos: el local, las personas y los servicios. Gratis.',
};

/**
 * El alta de un local (encargo §4).
 *
 * Vive bajo `/local` porque es la puerta de la zona del salón, no una pantalla de clienta: quien
 * llega aquí viene de «Tengo un salón y quiero mi agenda».
 */
export default function PantallaDeAlta() {
  return <AltaDeLocal />;
}
