import { Cabecera } from '@/componentes/cabecera'
import { Vacio } from '@/componentes/estados'
import { Iconos } from '@/componentes/pestanas'
import { Pie } from '@/componentes/pie'

/**
 * La página que sale cuando la dirección no existe.
 *
 * Hasta ahora era la de Next: fondo en blanco y «This page could not be found», en inglés y sin
 * salida. Se nota más desde que el perfil de una persona vive en `/[salón]/[persona]`, porque
 * **cualquier dirección de dos tramos mal escrita cae aquí**: un enlace de WhatsApp cortado, un
 * salón que se despublicó, una persona que se fue del salón.
 *
 * Es un estado vacío como los demás y sigue su misma regla: dice qué pasó y **por dónde salir**.
 * Un callejón sin salida en la página a la que llega la gente desde fuera es tráfico tirado.
 */
export default function NoExiste() {
  return (
    <>
      <Cabecera />
      <main className="contenedor seccion">
        <Vacio
          icono={Iconos.buscar}
          titulo="Esta página ya no está aquí"
          texto={
            <>
              Puede que el salón ya no esté publicado, que esa persona se haya ido, o que el
              enlace llegara cortado. Búscalo y lo encuentras.
            </>
          }
          accion={{ href: '/buscar', texto: 'Buscar salones y personas' }}
        />
      </main>
      <Pie />
    </>
  )
}
