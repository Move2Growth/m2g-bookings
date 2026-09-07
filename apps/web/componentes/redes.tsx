import type { RedesDelProfesional } from '@/lib/api'

/**
 * Las redes de una persona (encargo 2026-09-07 §3): Instagram, Facebook y X.
 *
 * La API manda dos campos por red: el usuario (`instagram`) y la dirección ya montada
 * (`instagram_url`). **Se enlaza la que monta el servidor**, nunca una compuesta aquí: si un
 * día cambia el dominio de una red, se cambia en un sitio y no en tres frontales.
 *
 * Se escribe el usuario y no «Instagram» a secas porque en este oficio el usuario *es* la
 * carta de presentación: quien mira quiere ver el arroba antes de decidir si toca.
 *
 * `rel="me nofollow"` a propósito: `me` dice que ese perfil es de esta persona, y `nofollow`
 * evita que un salón nos use de escalera de posicionamiento para su Instagram.
 */
export function Redes({ redes, de }: { redes: RedesDelProfesional; de: string }) {
  const enlaces = [
    { red: 'Instagram', usuario: redes.instagram, url: redes.instagram_url },
    { red: 'Facebook', usuario: redes.facebook, url: redes.facebook_url },
    { red: 'X', usuario: redes.x, url: redes.x_url },
  ].filter((e) => e.url)

  if (enlaces.length === 0) return null

  return (
    <ul className="pastillas" style={{ marginTop: 'var(--espacio-4)' }} aria-label={`Redes de ${de}`}>
      {enlaces.map((e) => (
        <li key={e.red}>
          <a
            href={e.url as string}
            className="boton boton--secundario"
            target="_blank"
            rel="me nofollow noopener noreferrer"
          >
            {e.red}
            {e.usuario ? <span className="tenue"> @{e.usuario}</span> : null}
          </a>
        </li>
      ))}
    </ul>
  )
}
