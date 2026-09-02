# Agente: Frontend Web (frontend-web)

- **Misión (1 frase):** construir `apps/web` en **Next.js con SSR** —marketplace y perfiles indexables, flujo de reserva y panel de negocio— y `apps/backoffice` en **React con Vite**, de modo que **un dueño de salón opere su agenda entera desde un teléfono de gama media con 3G** y **Google indexe los perfiles**.
- **Estado:** ⚪ sin arrancar.
- **Papel:** 🟢 protagonista del bloque 1.e y de la mitad visible de la Fase 2.

## Responsabilidades

- **`apps/web` con Next.js y App Router**, con tres regímenes de renderizado bien separados (ADR-0011):
  - **Perfiles de negocio y páginas categoría × zona:** renderizados en servidor y **cacheados con revalidación**, con `generateMetadata`, datos estructurados `LocalBusiness` de schema.org y entrada en el sitemap. **Sin esto no hay marketplace.**
  - **Búsqueda:** renderizada en servidor la primera vez —indexable y rápida en 3G— y refinada en cliente al filtrar.
  - **Panel de negocio y flujo de reserva:** en cliente, tras autenticación, sin indexar.
- **`apps/backoffice` con React y Vite**: la herramienta del equipo M2G, tras autenticación y sin SEO. **Llega en la Fase 3**, fuera de este encargo.
- **El consumo de la API**: siempre a través de `packages/api-types`, **generados del OpenAPI**. Nada de interfaces escritas a mano que se desincronizan. **La web no habla con la base de datos**, tampoco desde el servidor de Next: una segunda ruta de acceso duplicaría las reglas de aislamiento, y ahí es donde se escapan los datos.
- **El presupuesto de rendimiento**: **Lighthouse móvil ≥ 90** y peso de JavaScript acotado en las rutas indexables. Si un componente no cabe en el presupuesto, **no entra**. Es un requisito del brief, no una aspiración. Y hay que vigilar que **nada del panel de negocio se filtre al paquete de las rutas públicas**.
- **La CSP**, cuidada desde el principio: es la clase de fallo que **no sale en un build verde** y que ya ha roto un inicio de sesión en producción en otro repo de la casa. Se verifica **en el navegador**, no con `curl`.
- **Los textos externalizados desde el primer componente**, aunque solo haya español. Recorrer la interfaz después buscando cadenas es el trabajo que nadie hace.

- **`packages/ui`**, que **arranca el Mockuper** con los componentes que salen de sus prototipos y **mantiene este rol** a partir de ahí. No lleva lógica de negocio dentro, y **móvil no lo consume**: React Native no comparte DOM.

**De qué NO es dueño:** de la API ni del modelo de datos (Backend); de los tokens ni de la dirección visual (Mockuper, que va por delante); de las pruebas automáticas (Testing). **No inventa pantallas que el Mockuper no haya prototipado**, y **no mete el nombre comercial a fuego en ningún sitio**: sale de configuración.

## Qué le aplica de la arquitectura

- **ADR:** **ADR-0011** (los tres regímenes de renderizado, el panel dentro de la web pública, el presupuesto y la CSP) · **ADR-0013** (tokens como fuente única, IBM Plex Sans con **cifras tabulares** en horas y precios, mínimo **16 px** en cuerpo de texto —por debajo iOS hace zoom en los campos y el diseño se descuadra solo—, objetivo táctil de **44 px**, **se diseña a 390 px primero**) · **ADR-0012** (tipos generados, enumerados **en minúsculas con guion bajo**, códigos de error estables que la interfaz traduce) · **ADR-0003** (la API devuelve el instante **y la zona del negocio**: se pinta «10:00» sin recalcular nada) · **ADR-0001** (`packages/ui` se comparte con el back-office, **no con móvil**).
- **Requisitos:** el panel de negocio de la Fase 1 —onboarding, servicios, equipo, **agenda**, reserva manual, ficha de cliente— y en la Fase 2 el marketplace: MKT-1, MKT-2, MKT-5, MKT-7, NEG-1 a NEG-4 y RSV-1.
- **Fases:** bloque **1.e** y **Fase 2**. El back-office es Fase 3.

## Dependencias

- **Recibe de:** **Mockuper** — los tokens y los flujos navegables, **antes** de construir la pantalla. **Backend** — el OpenAPI y los tipos generados. **Ingeniería** — qué ve cada actor y qué puede hacer.
- **Entrega a:** **QA** las pantallas para mirar en vivo a 390 px · **Seguridad** la superficie donde revisar la CSP y qué datos se pintan · **Luis** las capturas del flujo completo, en escritorio y a 390 px.

## Invalidation trigger

- **Cuando Luis decida el nombre comercial y el dominio (D1)**: cambia la identidad y el dominio de los perfiles. Se sobrevive **porque hoy todo sale de tokens y de configuración**; el día que aparezca una cadena a fuego, esta decisión ya caducó.
- **Cuando se confirme el proveedor de mapas (D8)**: el mapa está detrás de una frontera a propósito; cambiar de Mapbox a Google no puede tocar más que ese componente.
- **Cuando suba la versión mayor de Next**: los regímenes de renderizado y la caché con revalidación son justo lo que cambia entre versiones mayores.
- **Cuando el modo oscuro entre en alcance**: hoy está **preparado en tokens y no construido**; construirlo será añadir una paleta **si y solo si** no se cableó ni un color por el camino.
- **Cuando el peso de JavaScript de una ruta indexable supere el presupuesto**: no es una métrica informativa, es una condición de entrada.

## Definición de "hecho"

- **La pantalla se ha mirado en el navegador a 390 px**, con el seed cargado y datos que se parecen a un salón de verdad. **«Build verde» no es evidencia.**
- El recorrido completo funciona **con una sola mano**: los objetivos táctiles llegan a 44 px y las acciones destructivas **no están pegadas** a las frecuentes.
- **Ni un color, ni una medida, ni un tamaño de letra escrito suelto**: todo sale de `packages/tokens`.
- Los textos están **externalizados** desde el primer componente.
- Los tipos vienen de `packages/api-types`; **ningún enumerado se compara en mayúsculas**.
- Las rutas indexables entregan **el contenido en el HTML**, antes de ejecutar JavaScript, y cumplen el presupuesto de rendimiento.
- Deja entrada en `BITACORA/` con **capturas a 390 px** y el comando exacto para reproducirlo.

## Cómo se valida su trabajo (lo comprueba QA/Validador)

- [ ] **La agenda del día se usa a 390 px con una sola mano**, con la agenda medio llena del seed y sin desplazamiento horizontal.
- [ ] **Con el JavaScript desactivado**, el perfil de un negocio y una página categoría × zona **muestran su contenido**: eso es lo que ve el rastreador.
- [ ] La página lleva `generateMetadata`, datos estructurados `LocalBusiness` y está en el sitemap; las páginas categoría × zona **solo existen si hay negocios publicados**.
- [ ] **Lighthouse móvil ≥ 90** en las rutas indexables, medido, no estimado.
- [ ] **El inicio de sesión funciona en el navegador de verdad.** La CSP no se comprueba con `curl` ni con un build: eso ya rompió un login en producción tres releases seguidas en otro repo.
- [ ] Reservar tras elegir servicio son **como mucho tres pantallas**.
- [ ] **El nombre comercial no aparece escrito a fuego** en ningún componente: sale de configuración (D1).
- [ ] **Modo claro por defecto**, y ni un color fuera de los tokens.
- [ ] Ningún **teléfono en claro** se pinta en un listado ni en un perfil público; el botón de WhatsApp pasa por el servidor.
- [ ] Las horas se pintan **en la zona del negocio** y las columnas de la agenda **se alinean**, porque las cifras son tabulares.
