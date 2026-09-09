'use client';

/**
 * El QR y el enlace del salón, para pegarlos donde estén sus clientas (NEG-4).
 *
 * Un salón no reparte una URL: reparte un cartel en el mostrador, una pegatina en el espejo y
 * una línea en la bio de Instagram. Las tres cosas salen del mismo sitio y por eso están en la
 * misma pantalla: el enlace corto para copiar y el mismo enlace hecho código para imprimir.
 *
 * ## Se dibuja en el navegador, y eso es una decisión
 *
 * La alternativa era un endpoint que devolviera una imagen. Se descarta por dos razones que no
 * son de comodidad. La primera: un QR es **determinista** —de este enlace sale exactamente este
 * dibujo, siempre—, así que guardarlo en un servidor es guardar algo que se puede recalcular en
 * un milisegundo. La segunda pesa más: generar imágenes en el servidor arrastra dónde
 * guardarlas, y dónde se guardan las imágenes de este producto es justo la decisión que sigue
 * abierta. Montar el QR encima de esa deuda sería atarlo a algo que aún puede cambiar.
 *
 * ## Se descarga en SVG, no en PNG
 *
 * Porque lo que el salón va a hacer con esto es **imprimirlo**, y a tamaños que no sabemos:
 * una tarjeta de visita y un cartel A3 salen del mismo archivo. Un PNG de 512 px vale para el
 * mostrador y se ve roto en el escaparate; el vector no tiene ese problema, y cualquier
 * imprenta de Panamá acepta un SVG.
 *
 * El dibujo va en **negro sobre blanco** y no en los colores de la marca. No es falta de gusto:
 * un lector de códigos necesita contraste alto entre módulos, y el cobalto sobre hueso —que
 * cumple de sobra para leer texto— empieza a fallar con la cámara de un móvil viejo en un salón
 * con poca luz. La marca está alrededor, en el cartel, no dentro del código.
 */

import { useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';

/** Cuántos píxeles se piden por módulo. Cuatro da un SVG legible y un dibujo compacto. */
const ESCALA = 4;

/*
 * Los dos únicos colores de todo el producto que **no** salen de los tokens, y por eso van
 * marcados: los módulos de un código no son color de interfaz, son datos. Un lector necesita
 * el contraste máximo, y el cobalto sobre hueso —que cumple de sobra para leer texto— empieza
 * a fallar con la cámara de un móvil viejo en un salón con poca luz.
 *
 * Además viajan **dentro** del SVG que el salón se descarga: si el fondo lo pusiera el CSS, el
 * archivo saldría transparente y la imprenta lo pondría sobre lo que le diera la gana.
 */
const NEGRO = '#000000'; // fuera-de-marca: módulo de código, no interfaz
const BLANCO = '#ffffff'; // fuera-de-marca: zona de silencio del código, no interfaz

export function QrDelSalon({ slug, nombre }: { slug: string; nombre: string }) {
  const [dibujo, setDibujo] = useState<string | null>(null);
  const [enlace, setEnlace] = useState('');
  const [copiado, setCopiado] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  useEffect(() => {
    // El origen se lee del navegador y no de una variable: el enlace que el salón reparte
    // tiene que ser el mismo por el que ha entrado, no el que alguien configuró una vez.
    const url = `${window.location.origin}/salon/${slug}`;
    setEnlace(url);

    let vivo = true;
    // La librería del código entra solo aquí, y solo en el navegador: es peso que no tiene por
    // qué viajar en ninguna otra pantalla.
    import('qrcode')
      .then((qr) =>
        qr.toString(url, {
          type: 'svg',
          errorCorrectionLevel: 'M',
          margin: 2,
          scale: ESCALA,
          color: { dark: NEGRO, light: BLANCO },
        }),
      )
      .then((svg) => {
        if (vivo) setDibujo(svg);
      })
      .catch(() => {
        if (vivo) setFallo('No se pudo dibujar el código. Recarga la pantalla.');
      });
    return () => {
      vivo = false;
    };
  }, [slug]);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(enlace);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2500);
    } catch {
      // Sin permiso de portapapeles no se finge que salió bien: se dice qué hacer.
      setFallo('Tu navegador no deja copiar solo. Selecciona el enlace y cópialo a mano.');
    }
  }

  function descargar() {
    if (!dibujo) return;
    const archivo = new Blob([dibujo], { type: 'image/svg+xml' });
    const temporal = URL.createObjectURL(archivo);
    const ancla = document.createElement('a');
    ancla.href = temporal;
    // El nombre del archivo lleva el del salón: en la carpeta de descargas de un móvil,
    // «qr.svg» es indistinguible de los otros catorce que hay ahí.
    ancla.download = `qr-${slug}.svg`;
    document.body.appendChild(ancla);
    ancla.click();
    ancla.remove();
    URL.revokeObjectURL(temporal);
  }

  return (
    <section className="pila" aria-label="El código y el enlace de tu salón">
      <div className="pila pila--apretada">
        <span className="etiqueta">Tu enlace</span>
        {/* Se enseña entero y se puede seleccionar: es lo que se pega en la bio de Instagram
            y en el estado de WhatsApp, y un enlace recortado con puntos suspensivos no sirve
            para eso. */}
        <p className="enlace-del-salon">{enlace || `…/salon/${slug}`}</p>
        <div className="tira">
          <Boton tono="abre" onClick={() => void copiar()} hijos={copiado ? 'Copiado' : 'Copiar el enlace'} />
          <a className="boton boton--secundario" href={`/salon/${slug}`} target="_blank" rel="noreferrer">
            Ver mi ficha
          </a>
        </div>
      </div>

      <div className="pila pila--apretada">
        <span className="etiqueta">Tu código</span>
        {fallo ? (
          <p className="campo__fallo" role="alert">
            {fallo}
          </p>
        ) : dibujo ? (
          <>
            {/* El dibujo va dentro de un cuadro blanco con aire alrededor: un QR pegado al
                borde de un fondo de color no lo lee ninguna cámara. */}
            <div
              className="qr"
              role="img"
              aria-label={`Código de ${nombre}. Al leerlo se abre la ficha del salón.`}
              dangerouslySetInnerHTML={{ __html: dibujo }}
            />
            <Boton tono="cierra" onClick={descargar} hijos="Descargar para imprimir" />
            <p className="menor tenue">
              Sale en vector: vale igual para una tarjeta que para un cartel grande.
            </p>
          </>
        ) : (
          <p className="menor cargando">Dibujando el código…</p>
        )}
      </div>
    </section>
  );
}
