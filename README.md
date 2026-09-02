# M2G Agenda

Plataforma de reservas y marketplace para belleza y bienestar en **Panamá**, **gratis para el
negocio**. Los negocios gestionan su agenda y su equipo sin pagar; los clientes descubren y
reservan; M2G monetiza con posicionamiento pagado y, cuando toque, con una suscripción cuyo precio
es un parámetro (0 al lanzamiento).

> Codename interno: *M2G Agenda*. **El nombre comercial está por definir** (decisión D1): no lo
> metas a fuego en ningún sitio, que salga de configuración.

## Por dónde empezar

| Documento | Qué es |
|---|---|
| [`docs/BRIEF-PRODUCTO.md`](docs/BRIEF-PRODUCTO.md) | **Qué** hay que construir. El brief de Luis, con los requisitos codificados (ONB-1, RSV-3, MKT-4…), el modelo de datos, las fases y las 18 decisiones ya tomadas. **Es la fuente de verdad.** |
| [`PROMPT-CONSTRUCTOR.md`](PROMPT-CONSTRUCTOR.md) | **Cómo** se construye: el encargo para quien desarrolla, con el orden, las reglas y lo que no puede decidir por su cuenta. |
| [`docs/arquitectura/`](docs/arquitectura/) | **Las decisiones ya tomadas**: catorce ADR, la constitución, el modelo de datos, el motor de disponibilidad y los contratos de API. |
| [`docs/ai-development/ESTADO-GLOBAL.md`](docs/ai-development/ESTADO-GLOBAL.md) | **El tablero.** En qué estado está todo, incluida la deuda viva. |

Si los dos primeros dicen cosas distintas, **manda el brief**.

## Las tres cosas que gobiernan cada decisión

1. **Todo se usa desde un teléfono de gama media con 3G.** El dueño del salón no tiene escritorio.
2. **El motor de planes y billing existe desde el día uno aunque cobre 0.** Subir el precio tiene
   que ser cambiar un número, no un desarrollo.
3. **Las páginas públicas las indexa Google.** Media clientela llega buscando «barbería en San
   Francisco», no el nombre del salón. Sin SSR no hay marketplace.

## Levantarlo en una máquina nueva

Hacen falta **Docker**, **[uv](https://docs.astral.sh/uv/)** para el backend en Python y
**pnpm** para las superficies web. Ninguna credencial de servicio externo es necesaria: en
local, WhatsApp, la pasarela y los mapas usan implementaciones de desarrollo.

1. **Clona el repositorio y sitúate en él.**
   ```bash
   git clone git@github.com:Move2Growth/m2g-bookings.git
   cd m2g-bookings
   ```
2. **Crea tu archivo de entorno** a partir del ejemplo. Cada variable lleva al lado una línea
   explicando para qué sirve; para trabajar en local no hay que rellenar ninguna.
   ```bash
   cp .env.example .env
   ```
3. **Levanta el stack.** Un solo comando: construye las imágenes, arranca PostgreSQL con
   PostGIS y Redis, aplica las migraciones desde cero y carga los datos de ejemplo.
   ```bash
   make arriba
   ```
4. **Comprueba que responde.** La documentación de la API queda en
   <http://localhost:8000/docs> y la base en `postgresql://agenda_api@localhost:5433/agenda`.
5. **Ejecuta las pruebas.** Corren contra un PostgreSQL real, no contra una base de mentira:
   lo que hay que probar son restricciones de exclusión, seguridad por fila y PostGIS, y nada
   de eso existe en SQLite.
   ```bash
   make pruebas
   ```
6. **Cuando termines**, `make abajo` para y libera los puertos. `make reiniciar` borra los datos
   y vuelve a empezar de cero.

`make` sin argumentos lista todos los comandos disponibles.

## Cómo se trabaja aquí

- **Todo entra por la rama `development`.** `main` no recibe commits directos.
- **Las decisiones se escriben como ADR** en `docs/arquitectura/adr/`. Un ADR decidido no se
  edita: se supera con otro.
- **Nada pendiente solo en prosa:** lo que queda abierto va al tablero con su estado.
- **La UI se valida en el navegador y a 390 px**, que es donde vive esto. «Build verde» no es
  evidencia.

## Reparto del trabajo

- **Quien desarrolla:** construye y valida **en local**. Deja `docker-compose` que levante todo
  con un comando, migraciones que corran de cero, `.env.example` documentado y este README.
- **Infraestructura, CI/CD y despliegues:** los lleva el equipo de plataforma de M2G. **Quien
  desarrolla no despliega a ningún entorno.**

## Estado

**Fase 0 — en proceso.** Arquitectura decidida (catorce ADR), modelo de datos, contratos de API,
flujos y design system escritos, y el **motor de disponibilidad con su núcleo puro y sus pruebas
en verde**. Pendiente de la aprobación de Luis para pasar a la Fase 1. El detalle, en
[`docs/ai-development/ESTADO-GLOBAL.md`](docs/ai-development/ESTADO-GLOBAL.md).
