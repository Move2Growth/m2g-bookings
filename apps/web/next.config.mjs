/**
 * Configuración de Next.
 *
 * `transpilePackages` hace falta porque `@agenda/tokens` se consume como TypeScript sin
 * compilar dentro del workspace: es la fuente de la verdad del color y de la letra, y tener
 * una copia compilada aparte sería tener dos verdades.
 */
/** @type {import('next').NextConfig} */
const configuracion = {
  reactStrictMode: true,
  transpilePackages: ['@agenda/tokens'],
  // El chivato flotante de desarrollo de Next se apaga: es una pastilla redonda encima de la
  // pantalla que no es del producto y que ensucia cualquier captura o revisión.
  devIndicators: false,
  // El monorepo tiene dos lockfiles (el del repositorio y el del árbol de trabajo). Sin esto,
  // Next avisa en cada arranque de que ha adivinado la raíz.
  outputFileTracingRoot: import.meta.dirname,
  eslint: { ignoreDuringBuilds: true },
};

export default configuracion;
