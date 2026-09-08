import Link from 'next/link';

/** La pantalla de «aquí no hay nada». También lleva cabecera y pie: las pone el armazón. */
export default function NoHayNada() {
  return (
    <div className="contenido seccion">
      <div className="hueco bloque bloque--arena relleno--grande">
        <span className="etiqueta">Error 404</span>
        <h1 className="hueco__titulo">Esta dirección no lleva a ningún sitio</h1>
        <p className="parrafo">
          Puede que el enlace esté mal escrito o que el salón ya no esté publicado. Desde la búsqueda se llega a todo.
        </p>
        <div className="tira">
          <Link className="boton boton--abre" href="/buscar">
            Ir a la búsqueda
          </Link>
          <Link className="boton boton--secundario" href="/">
            Volver a la portada
          </Link>
        </div>
      </div>
    </div>
  );
}
