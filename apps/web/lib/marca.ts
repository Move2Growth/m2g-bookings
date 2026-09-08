/**
 * El único archivo del front donde puede aparecer escrito el nombre comercial.
 *
 * ADR-0022: el nombre vive en `NOMBRE_COMERCIAL` y llega a la web como
 * `NEXT_PUBLIC_NOMBRE_COMERCIAL`. `scripts/comprobar-variables.py` falla si el nombre aparece
 * en cualquier otro `.ts`/`.tsx` de `app/`, `componentes/` o `lib/`. El valor de aquí es el
 * respaldo para cuando se arranca sin `.env`, no una constante de producto.
 */
export const NOMBRE_COMERCIAL = process.env.NEXT_PUBLIC_NOMBRE_COMERCIAL ?? 'Tanda';

/**
 * Qué significa el nombre. Se pinta en el pie y en la portada, y por eso también sale de aquí:
 * la frase menciona el nombre y no puede vivir en un componente.
 */
export const LEMA = `Una ${NOMBRE_COMERCIAL.toLowerCase()} es el turno que vuelve. Reserva el tuyo.`;
