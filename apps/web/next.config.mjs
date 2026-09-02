/** @type {import('next').NextConfig} */
const nextConfig = {
  // El paquete de tokens se publica como fuente TypeScript, no compilado: es una sola
  // fuente de verdad y no un artefacto que haya que reconstruir a mano cada vez.
  transpilePackages: ['@agenda/tokens'],
  images: {
    // Hoy las fotos son locales. Cuando los salones suban las suyas, aquí entra el dominio del
    // almacenamiento y nada más.
    formats: ['image/avif', 'image/webp'],
  },
  reactStrictMode: true,
  // Cabeceras mínimas de seguridad. La CSP se afina cuando entre el mapa; lo que no se
  // hace es dejarla para el final, que es como se rompe un login en producción sin que
  // ningún build verde avise.
  async headers() {
    return [
      {
        source: '/:ruta*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ]
  },
}

export default nextConfig
