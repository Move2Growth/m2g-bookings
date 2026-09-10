'use client';

/**
 * Subir una foto del salón (NEG-1, D11 · ADR-0023).
 *
 * Es lo último que le faltaba a un salón para poder publicarse: sin una foto no se publica, y
 * hasta ahora la pantalla del alta pedía disculpas —«falta decidir dónde se guardan las
 * imágenes»— porque el registro existía y el sitio donde dejar el archivo, no.
 *
 * ## El archivo no pasa por nuestra API
 *
 * Van tres pasos y el de en medio no toca el servidor: se pide **permiso**, el navegador sube
 * **directo al almacén**, y solo entonces se **registra** la clave en la ficha. Una foto de
 * cinco megas subiendo por una conexión de Panamá ocuparía un trabajador de la API un minuto;
 * con diez salones a la vez, la agenda deja de responder por culpa de unas fotos.
 *
 * ## Lo que se comprueba aquí y por qué se comprueba igual allí
 *
 * El tipo y el tamaño se miran **antes de empezar**, para poder decirlo con palabras en vez de
 * dejar que el almacén conteste un XML. Pero los límites de verdad viajan dentro de la firma y
 * los impone el almacén: esto es cortesía, no la puerta.
 *
 * ## La barra dice bytes, no una animación
 *
 * En 3G una foto tarda. Una rueda girando no distingue «va lento» de «se colgó», y la
 * diferencia es si la persona espera o cierra la pantalla a medias — dejando la foto subida y
 * sin registrar. Aquí se enseña el porcentaje de verdad, que sale de `XMLHttpRequest`: `fetch`
 * todavía no sabe contar lo que sube.
 */

import { useRef, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { api, comoMensaje, type FotoDelSalon } from '@/lib/api';
import { conSesion } from '@/lib/sesion';

/** Lo que el navegador ofrece en el selector. Es el mismo juego que acepta la API. */
const ACEPTADOS = 'image/jpeg,image/png,image/webp,image/avif';

function enMegas(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Sube al almacén contando lo que va. `fetch` no sabe hacerlo todavía. */
function subirContando(
  url: string,
  forma: FormData,
  alAvanzar: (porcentaje: number) => void,
): Promise<void> {
  return new Promise((listo, falla) => {
    const peticion = new XMLHttpRequest();
    peticion.open('POST', url);
    peticion.upload.onprogress = (evento) => {
      if (evento.lengthComputable) alAvanzar(Math.round((evento.loaded / evento.total) * 100));
    };
    peticion.onload = () =>
      // El almacén contesta 204 sin cuerpo cuando acepta. Cualquier otra cosa trae un XML con
      // el motivo, y se enseña el código —`EntityTooLarge`, `AccessDenied`— porque es lo único
      // de ese XML que le sirve a alguien.
      peticion.status >= 200 && peticion.status < 300
        ? listo()
        : falla(
            new Error(
              peticion.responseText.match(/<Code>([^<]+)<\/Code>/)?.[1] ??
                `El almacén respondió ${peticion.status}.`,
            ),
          );
    peticion.onerror = () => falla(new Error('No se pudo llegar al almacén de fotos.'));
    peticion.send(forma);
  });
}

export function SubirFoto({
  clase = 'galeria',
  rotulo = 'Añadir una foto',
  alSubir,
}: {
  clase?: 'portada' | 'galeria';
  rotulo?: string;
  alSubir: (foto: FotoDelSalon) => void;
}) {
  const campo = useRef<HTMLInputElement>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [porcentaje, setPorcentaje] = useState(0);
  const [fallo, setFallo] = useState<string | null>(null);

  async function elegida(evento: React.ChangeEvent<HTMLInputElement>) {
    const archivo = evento.target.files?.[0];
    // El campo se vacía siempre: sin esto, elegir **el mismo archivo** dos veces seguidas no
    // dispara nada, y parece que el botón se ha roto.
    evento.target.value = '';
    if (!archivo) return;

    setFallo(null);
    setPorcentaje(0);
    setSubiendo(true);
    try {
      const permiso = await conSesion((acceso) => api.permisoDeSubida(archivo.type, acceso));

      if (archivo.size > permiso.tamano_maximo_bytes) {
        // Se dice antes de gastar la subida entera. El almacén lo rechazaría igual, pero
        // después de haber mandado los megas por una conexión que se paga.
        setFallo(
          `Esa foto pesa ${enMegas(archivo.size)} y el tope son ${enMegas(permiso.tamano_maximo_bytes)}. Hazle una copia más pequeña.`,
        );
        return;
      }

      const forma = new FormData();
      for (const [nombre, valor] of Object.entries(permiso.campos)) forma.append(nombre, valor);
      // El archivo va **el último**: el almacén deja de leer en cuanto lo encuentra, así que
      // todo lo que vaya detrás lo ignora.
      forma.append('file', archivo);

      await subirContando(permiso.url, forma, setPorcentaje);

      const foto = await conSesion((acceso) =>
        api.registrarFoto(
          { clave: permiso.clave, clase, texto_alternativo: archivo.name.replace(/\.[^.]+$/, '') },
          acceso,
        ),
      );
      alSubir(foto);
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setSubiendo(false);
      setPorcentaje(0);
    }
  }

  return (
    <div className="pila pila--apretada">
      <input
        className="solo-lectores"
        ref={campo}
        type="file"
        accept={ACEPTADOS}
        onChange={elegida}
        aria-hidden="true"
        tabIndex={-1}
      />
      {/* El botón es el botón de la casa y no el del navegador: el nativo no se puede pintar,
          no dice qué acepta y en móvil se lee a 11 px. */}
      <Boton
        tono={clase === 'portada' ? 'cierra' : 'abre'}
        onClick={() => campo.current?.click()}
        cargando={subiendo}
        rotuloCargando={porcentaje > 0 ? `Subiendo ${porcentaje} %` : 'Preparando'}
        hijos={rotulo}
      />
      {subiendo ? (
        <p className="menor tenue" role="status">
          {porcentaje > 0 ? `Va por el ${porcentaje} %.` : 'Pidiendo permiso al almacén…'} No cierres esta pantalla.
        </p>
      ) : (
        <p className="menor tenue">JPG, PNG, WebP o AVIF. Hasta 5 MB.</p>
      )}
      {fallo ? (
        <p className="campo__fallo" role="alert">
          {fallo}
        </p>
      ) : null}
    </div>
  );
}
