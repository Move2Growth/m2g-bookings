# ADR-0011 · Next.js con SSR para lo público; Vite SPA para el back-office

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

D6 ya está decidida en el brief y el encargo la subraya: *«el template de M2G (FastAPI + React/Vite) es SPA y no sirve para las páginas públicas»*. La razón es de negocio, no de gusto: **la mitad del negocio llega buscando «barbería en San Francisco»**, no el nombre del salón. Una SPA entrega un HTML vacío y deja el contenido a merced de que el rastreador ejecute JavaScript.

Lo que queda por decidir es **dónde cae el panel del negocio**, que no necesita SEO pero sí es la superficie que más se usa desde el móvil.

## Decisión

**[decisión]** Tres aplicaciones, y el panel del negocio va con la web pública:

| App | Stack | Por qué |
|---|---|---|
| `apps/web` — marketplace, perfiles, reserva **y panel de negocio** | **Next.js (App Router), SSR** | Lo público necesita SSR. El panel va aquí para que dueño y cliente compartan sesión, componentes y despliegue: son la misma persona a menudo (ONB-3). |
| `apps/backoffice` — equipo M2G | React + Vite, SPA | Cuenta interna, sin SEO, tras autenticación. Una SPA es más simple y más rápida de construir. |
| `apps/mobile` — clientes y negocios | Expo / React Native (D7) | Fase 5. |

- **[decisión]** En `apps/web` se distinguen tres regímenes de renderizado:
  - **Perfiles de negocio y páginas categoría × zona:** renderizado en servidor y **cacheado con revalidación**, con `generateMetadata`, datos estructurados `LocalBusiness` de schema.org y entrada en el sitemap (MKT-7).
  - **Búsqueda:** renderizada en servidor la primera vez (indexable y rápida en 3G) y refinada en cliente al filtrar.
  - **Panel de negocio y flujo de reserva:** en cliente, tras autenticación, sin indexar.
- **[decisión]** La web **no habla con la base de datos**. Todo pasa por la API, también desde el servidor de Next. Una segunda ruta de acceso a los datos duplicaría las reglas de aislamiento (ADR-0002), y ahí es donde se escapan los datos.
- **[decisión]** Los tipos de la API los consume desde `packages/api-types`, **generados del OpenAPI**. Nada de interfaces escritas a mano que se desincronizan.
- **[decisión]** **Presupuesto de rendimiento explícito** en la web pública: Lighthouse móvil ≥ 90 y un peso de JavaScript acotado en las rutas indexables. Si un componente no cabe en el presupuesto, no entra. Es un requisito del brief §6, no una aspiración.
- **[decisión]** El SSR obliga a **cuidar la CSP desde el principio**: es la clase de fallo que no sale en un build verde y ya ha roto un login en producción en otro repo de la casa. Se verifica en navegador, no con `curl`.

## Alternativas consideradas

- **Todo en Vite SPA.** Descartado por D6: mata el SEO y con él la mitad del canal de adquisición.
- **Todo en Next, incluido el back-office.** Descartado: el back-office no gana nada con SSR y añade complejidad de servidor a una herramienta interna.
- **Panel de negocio como app aparte.** Descartado: duplicaría sesión, componentes y despliegue para el mismo usuario que también es cliente.
- **Generación estática de los perfiles.** Descartado: con 5.000 negocios que cambian horario y servicios a diario, la reconstrucción completa no es viable; el renderizado en servidor con revalidación da el mismo SEO sin ese problema.

## Consecuencias

- `apps/web` es la aplicación más grande y la que más importa. Merece el mejor trabajo de diseño y de rendimiento.
- Hace falta una capa de servidor en Next para el despliegue (no es un sitio estático). **Eso es cosa de Luis**, pero se le avisa: el `docker-compose.yml` local ya la levanta como es.
- El panel de negocio comparte código con lo público: hay que vigilar que **nada del panel se filtre al paquete de las rutas públicas** y engorde el presupuesto.
- Compartir sesión entre marketplace y panel exige que el cambio a «modo negocio» sea explícito (ONB-3, ADR-0006).
