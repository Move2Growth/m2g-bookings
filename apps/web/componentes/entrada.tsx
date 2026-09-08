'use client';

/**
 * El formulario de entrada.
 *
 * El error de contraseña **no** es un cartel rojo genérico: se pinta el mensaje que devuelve la
 * API («Correo o contraseña incorrectos.»), el campo se marca con `aria-invalid`, el foco
 * vuelve a la contraseña y el correo se conserva. Escribir otra vez el correo porque fallaste
 * la contraseña es de las cosas que más cabrean en un móvil.
 *
 * Al entrar se mira si la persona trabaja en algún salón. Si trabaja, se le ofrece ir a la
 * agenda del local; si no, se le devuelve a donde estaba. No se decide por ella.
 */

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { api, comoMensaje, type NegocioDeLaPersona } from '@/lib/api';
import { guardarSesion, leerSesion } from '@/lib/sesion';

export function Entrada() {
  const router = useRouter();
  const parametros = useSearchParams();
  const volver = parametros.get('volver');

  const [correo, setCorreo] = useState('');
  const [contrasena, setContrasena] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);
  const [negocios, setNegocios] = useState<NegocioDeLaPersona[] | null>(null);
  const [yaEstaba, setYaEstaba] = useState(false);

  const cajaContrasena = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setYaEstaba(leerSesion() !== null);
  }, []);

  async function entrar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setFallo(null);
    try {
      const credenciales = await api.entrar(correo.trim(), contrasena);
      guardarSesion(credenciales);

      let suyos: NegocioDeLaPersona[] = [];
      try {
        suyos = await api.misNegocios(credenciales.acceso);
      } catch {
        // Que no se sepa si trabaja en un salón no impide entrar como clienta.
      }

      if (suyos.length > 0 && !volver) {
        setNegocios(suyos);
        return;
      }
      router.push(volver ?? '/mis-citas');
    } catch (error) {
      setFallo(comoMensaje(error));
      setContrasena('');
      cajaContrasena.current?.focus();
    } finally {
      setEnviando(false);
    }
  }

  if (negocios) {
    return (
      <div className="contenido" data-superficie="local">
        <div className="seccion pila aparece">
          <span className="etiqueta">Ya estás dentro</span>
          <h1 className="rotulo rotulo--grande">¿A qué vienes hoy?</h1>
          <p className="parrafo">
            Trabajas en {negocios.length === 1 ? 'un salón' : `${negocios.length} salones`}. Puedes entrar a la agenda
            del local o seguir como clienta.
          </p>
          <div className="tira">
            <Link className="boton boton--abre" href="/local">
              La agenda del salón
            </Link>
            <Link className="boton boton--secundario" href="/mis-citas">
              Mis citas como clienta
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Acceso</span>
        <h1 className="rotulo rotulo--grande">Entra con tu correo.</h1>

        {yaEstaba ? (
          <div className="bloque bloque--exito relleno" role="note">
            <p>Ya tienes una sesión abierta. Si entras con otra cuenta, se sustituye.</p>
          </div>
        ) : null}

        <form className="pila" onSubmit={entrar} noValidate>
          <div className="campo">
            <label className="campo__rotulo" htmlFor="correo">
              Correo
            </label>
            <input
              className="campo__caja"
              id="correo"
              name="correo"
              type="email"
              inputMode="email"
              autoComplete="email"
              autoCapitalize="none"
              spellCheck={false}
              required
              value={correo}
              onChange={(evento) => setCorreo(evento.target.value)}
              aria-invalid={fallo ? true : undefined}
              aria-describedby={fallo ? 'fallo-entrada' : undefined}
            />
          </div>

          <div className="campo">
            <label className="campo__rotulo" htmlFor="contrasena">
              Contraseña
            </label>
            <input
              className="campo__caja"
              id="contrasena"
              name="contrasena"
              type="password"
              autoComplete="current-password"
              required
              ref={cajaContrasena}
              value={contrasena}
              onChange={(evento) => setContrasena(evento.target.value)}
              aria-invalid={fallo ? true : undefined}
              aria-describedby={fallo ? 'fallo-entrada' : undefined}
            />
          </div>

          {fallo ? (
            <p className="campo__fallo" id="fallo-entrada" role="alert">
              {fallo}
            </p>
          ) : null}

          <Boton
            tono="cierra"
            bloque
            type="submit"
            cargando={enviando}
            rotuloCargando="Comprobando"
            disabled={correo.trim() === '' || contrasena === ''}
            hijos="Entrar"
          />
        </form>

        <p className="campo__pista">
          El segundo factor y entrar con Google o Apple llegan más adelante. Por ahora, correo y contraseña.
        </p>
      </div>
    </div>
  );
}
