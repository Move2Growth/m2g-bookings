# M2G Agenda — encargo de construcción

Vas a construir **M2G Agenda**: una plataforma de reservas y marketplace para belleza y bienestar
en Panamá, **gratis para el negocio**. Trabajas en la Mac de Luis, en
`/Users/luisgomez/Desktop/kraken/m2g-bookings` — el repo **ya existe** (remoto
`Move2Growth/m2g-bookings`) y hoy solo tiene un README y el brief. **No crees otro repo, no hagas
`git init`.**

---

## Lo primero, antes de escribir una línea

**Lee `docs/BRIEF-PRODUCTO.md` entero.** Es el brief de Luis y la **fuente de verdad de qué hay
que construir**: trece secciones con los requisitos funcionales codificados (ONB-1, RSV-3, MKT-4…),
el modelo de datos orientativo, las fases y dieciocho decisiones ya tomadas con su valor por
defecto.

Este documento es el **cómo**: el orden, las reglas y lo que no puedes decidir tú. Cuando los dos
digan cosas distintas, **manda el brief** y me lo dices.

---

## La tesis, para que entiendas qué estás construyendo

El salón, la barbería o el spa pequeño de Panamá **no paga 30–60 dólares al mes por software**. Si
es gratis y funciona desde el teléfono, se llena de negocios; la densidad atrae clientes; y los
negocios que quieren más clientes pagan por visibilidad.

Eso tiene tres consecuencias que gobiernan cada decisión técnica:

1. **Todo se usa desde un teléfono de gama media con 3G.** El dueño del salón no tiene un
   escritorio: tiene un móvil y las manos ocupadas. «Mobile-first» aquí no es responsive: es el
   caso principal.
2. **El motor de planes y billing existe desde el día uno aunque cobre 0.** Pasar el precio a un
   dólar tiene que ser cambiar un número en el back-office, no un desarrollo. Si lo dejas para
   después, ese cambio será un proyecto.
3. **Las páginas públicas las tiene que indexar Google.** La mitad del negocio llega buscando
   «barbería en San Francisco», no el nombre del salón. Sin SSR no hay marketplace.

---

## Lo que NO es tuyo: infraestructura y despliegue

**No montes CI/CD, ni Docker de producción, ni gitops, ni servidores, ni dominios. No despliegues
nada, a ningún entorno.** De eso me encargo yo.

**Tú desarrollas y validas en local.** Y para que yo pueda desplegar sin adivinar nada, lo que sí
tienes que dejar impecable es esto:

- Un **`docker-compose.yml`** que levante el stack completo —API, Postgres con PostGIS, Redis,
  worker, web— con **un solo comando** y datos de ejemplo cargados.
- **Migraciones** que corran de cero contra una base limpia. Sin pasos manuales, sin «y luego
  ejecuta este SQL a mano».
- **`.env.example`** con todas las variables, cada una con una línea explicando para qué sirve, y
  el inventario en `docs/operacion/SECRETOS-Y-VARIABLES.md`. **Nombre y propósito, nunca el valor.**
- Un **README de arranque** en pasos numerados: cómo se levanta esto en una máquina nueva. Si al
  leerlo hay que adivinar algo, no está terminado.
- **Las pruebas corriendo en local con un comando**, y que pasen.

Si necesitas un servicio externo para avanzar —una clave de WhatsApp, una pasarela, un token de
mapas— **para y pídemelo**. No inventes credenciales ni te montes un apaño.

---

## Cómo se trabaja aquí

**Copia el método que ya usan los demás repos de M2G:**

```bash
cp -R /Users/luisgomez/Desktop/kraken/m2g-development/plantilla-proyecto/docs .
```

Trae el tablero, las convenciones y las definiciones de agente. **Adáptalo a este proyecto y borra
lo que no aplique** en vez de dejar carpetas vacías.

- **La arquitectura antes que el código.** Cada decisión que tomes se escribe como ADR en
  `docs/arquitectura/adr/`. **Un ADR decidido no se edita: se supera con otro.**
- **El tablero** (`docs/ai-development/ESTADO-GLOBAL.md`) es el primer sitio que mira cualquiera.
  Se actualiza en la misma sesión en que terminas algo, no al final de la semana.
- **Nada pendiente solo en prosa.** Lo que quede a medias va al tablero con su estado al lado del
  título: `sin iniciar` | `en proceso` | `completado`.
- **Todo entra por la rama `development`.** `main` no recibe commits directos.

---

## El stack, ya decidido

No lo re-discutas salvo que encuentres un impedimento real; si lo encuentras, escribe el ADR
explicando por qué y avisa.

| Pieza | Qué |
|---|---|
| **Backend** | FastAPI · Python 3.12 · uv |
| **Base de datos** | PostgreSQL 16 + **PostGIS** (búsqueda por distancia con índice GiST) |
| **Caché y colas** | Redis + workers para notificaciones, recordatorios, ranking, billing y métricas |
| **Web pública (W1)** | **Next.js con SSR** — obligatorio: los perfiles y las páginas categoría × zona tienen que indexarse |
| **Back-office (W2)** | React + Vite (SPA) |
| **App (A1)** | Expo / React Native, una base de código para iOS y Android |
| **Monorepo** | Paquetes compartidos: tipos generados desde OpenAPI, design tokens, componentes |
| **API** | REST versionada con OpenAPI, la misma para las tres superficies |

**El template de M2G (FastAPI + React/Vite) es SPA y no sirve para las páginas públicas.** Sirve
para el panel de negocio y el back-office. Esa distinción es la decisión D6 del brief y está tomada.

---

## Por dónde empezar, y en qué orden

El brief tiene siete fases (§9). **Constrúyelas en ese orden** y no empieces una sin cerrar la
anterior. Lo que se te pide en este encargo son las **fases 0, 1 y 2**; las demás se encargan
después.

### Fase 0 · Diseño

Flujos, design system, modelo de datos y contratos de API. **Termina cuando Luis lo apruebe**, no
cuando tú lo des por bueno.

### Fase 1 · El núcleo, y es lo que de verdad importa

Auth, onboarding, servicios, staff, agenda, **motor de disponibilidad**, reservas manuales,
notificaciones y ficha de cliente.

**Está hecha cuando un salón real puede operar su agenda entera desde un teléfono.** Ese es el
criterio, no «los endpoints responden».

### Fase 2 · El marketplace

Perfiles con SEO, búsqueda, filtros, mapa, reserva por cliente, reviews, favoritos y ranking
orgánico.

**Está hecha cuando un cliente encuentra un negocio y reserva sin que nadie le ayude, y Google
indexa los perfiles.**

---

## Las dos piezas donde se juega el producto

Casi todo lo demás es CRUD. Estas dos no, y quiero que les dediques el tiempo que se merecen.

### El motor de disponibilidad (AGD)

Un slot libre es:

```
horario del negocio ∩ horario del profesional
  − bloqueos − reservas existentes − buffers
```

Granularidad configurable por negocio (default 15 min), antelación mínima 1 h y máxima 60 días.

**Escribe las pruebas de estos casos antes que el código.** Son los que rompen este tipo de motor:

- Dos clientes confirmando **el mismo slot a la vez**. Bajo carga, no en teoría. Que no haya doble
  reserva es transaccional, no un `if`.
- Un buffer que **cruza el final de la jornada**.
- Un profesional con **horario distinto del negocio** — que es el caso normal, no la excepción.
- **Cambiar el horario del negocio cuando ya hay reservas dentro** de lo que se elimina.
- Un servicio **más largo que el hueco** que queda antes del cierre.
- Reserva **multi-servicio encadenada** (D13): tres servicios seguidos con el mismo profesional
  necesitan un bloque continuo, no tres huecos sueltos.
- Bloqueos **recurrentes** (el almuerzo de cada día) contra bloqueos puntuales.
- **`America/Panama` no tiene horario de verano**, pero guarda en UTC con la zona del negocio: el
  modelo tiene que aguantar España después.

### El ranking del marketplace (MKT-3, MKT-4)

Que sea **una fórmula con pesos configurables desde el back-office**, no reglas repartidas por el
código. Entran: distancia, rating ponderado, reservas recientes, tasa de completado, completitud
del perfil y actividad reciente. Más un **boost temporal para negocios nuevos**, o el marketplace
nace bloqueado para los que llegan.

Tres reglas que no se negocian:

- Los patrocinados van **intercalados y etiquetados «Patrocinado»**, máximo 2 de cada 10.
- **Nunca ocultan a los orgánicos.**
- **El patrocinio no toca el rating ni las reviews.** Jamás.

Y el rating agregado va con **ponderación bayesiana**: una sola review de 5 estrellas no puede
adelantar a un negocio con ochenta reviews de 4,7.

---

## Reglas duras

- **Multi-tenant desde la primera migración.** Tenant = negocio, autorización a nivel de fila en
  **todos** los endpoints. Ningún dato de un negocio es accesible desde otro. Meterlo después toca
  todas las consultas: es lo más caro que puedes dejar para luego.
- **Ningún secreto en git.** Todo secreto nuevo se documenta en el acto y se escanea el diff en
  español y en inglés antes de commitear (`contraseña` y `password`).
- **Datos de tarjeta: nunca.** Solo el token de la pasarela (PAY-3).
- **Los teléfonos no se exponen.** El click-to-chat se resuelve en servidor y los listados no
  llevan el número en claro: si no, alguien raspa la base entera de negocios en una tarde.
- **Ley 81 de Panamá** (protección de datos): consentimiento, derechos del titular, política de
  privacidad, retención, y **borrado de cuenta desde dentro de la app** — sin eso, Apple rechaza.
- **Jobs idempotentes.** Un recordatorio duplicado a las 7 de la mañana es una queja.
- **Lo de UI se valida en navegador**, no con «build verde»: la CSP, el runtime y el diseño no
  salen ahí. Y a **390 px** de ancho, que es donde va a vivir esto.
- **Migraciones probadas contra un Postgres real** antes de darlas por buenas.
- **Modo claro por defecto.**
- Nada de tarjetas y botones redondeados por todas partes, degradados decorativos ni
  scrollytelling. Ni Inter, ni Fraunces, ni Bricolage, ni General Sans.

---

## Cómo quiero que trabajes

- **No preguntes si sigues.** Encadena el trabajo. Párate solo ante un bloqueo real: una credencial
  que no tengas, una decisión de negocio que sea de Luis, o algo que pueda tocar datos reales.
- **Enseña pronto.** Cuando tengas el **motor de disponibilidad con sus pruebas en verde**, para y
  enséñalo antes de montar pantallas encima. Si ese motor está mal, todo lo que construyas encima
  hay que rehacerlo.
- **Rutas absolutas siempre** (`/Users/luisgomez/…`) cuando hables de archivos.
- Si algo falla, **dilo con lo que salió por pantalla**. No lo escondas ni lo des por bueno.
- **Datos realistas, nunca «Servicio 1 · 100,00».** Un salón panameño de verdad: «Corte + barba,
  45 min, $18», «Balayage, 3 h, desde $120». Con datos de mentira no se ve que una reserva de tres
  horas no cabe en el hueco de las cinco de la tarde.

---

## Lo que NO puedes decidir tú

El brief trae dieciocho decisiones ya tomadas (§10) **con su valor por defecto: úsalas**. Si te
topas con algo que no está resuelto ahí, **para y pregunta**; no elijas por Luis. En particular:

1. **El nombre comercial y el dominio** (D1). Usa el codename *M2G Agenda* mientras tanto y no
   metas el nombre a fuego en ningún sitio: que salga de configuración.
2. **La pasarela de pago concreta** (D5). El default es Yappy + tarjetas vía pasarela local, pero
   la elección final y sus credenciales son de Luis.
3. **Mapas** (D8): Mapbox por defecto, pero tiene coste y hay que confirmarlo.
4. Cualquier cosa que **cobre dinero de verdad** a un negocio o a un cliente.

Y lo marcado **v2** en el brief **no se construye**, pero el modelo de datos lo deja preparado
cuando sea barato. En concreto, deja sitio para: multi-sede, recursos físicos, profesional en
varios negocios, depósitos y cobro al cliente final, y el rol de recepción. Una columna hoy cuesta
nada; una migración con datos vivos, mucho.

---

## Cuando termines cada fase

Deja en el tablero qué está hecho, qué quedó fuera y por qué, y avisa con:

- **Cómo levantarlo** y con qué credenciales de prueba.
- **Capturas del flujo completo**, no de pantallas sueltas: registrar un negocio, publicarlo,
  reservar, cancelar y dejar una review. En escritorio y a 390 px.
- **Las pruebas del motor de disponibilidad en verde**, con la lista de casos que cubren.
- Lo que necesites de mí para desplegarlo.
