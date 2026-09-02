# Restricciones — Bukeo

> Las reglas duras del encargo y los requisitos no funcionales (§6 del brief). **Un choque con algo de aquí se para y se escala**, no se resuelve por cuenta propia.

## 1. Vocabulario (usar siempre estos términos)

| Término | Significa | No decir |
|---|---|---|
| **Negocio** | La unidad de tenencia: salón, barbería, spa o profesional independiente | «tienda», «local», «cuenta» |
| **Profesional** | Quien presta el servicio y tiene agenda propia (staff) | «empleado», «recurso» |
| **Servicio** | Lo que se reserva: nombre, duración, precio, buffers | «producto», «tratamiento» |
| **Reserva** | La cita de un cliente con un profesional para uno o más servicios | «booking», «turno» |
| **Slot** | Hueco reservable según la granularidad del negocio | «franja», «hora» |
| **Zona** | Nivel de la taxonomía geográfica: provincia → distrito → corregimiento → barrio | «área», «región» |
| **Patrocinado** | Resultado pagado del marketplace, siempre etiquetado | «destacado», «premium» |

## 2. Lo que no es de este equipo

**No se monta CI/CD, ni Docker de producción, ni gitops, ni servidores, ni dominios. No se despliega a ningún entorno.** Eso lo hace Luis.

Lo que sí hay que dejar impecable para que él despliegue sin adivinar nada:

- Un `docker-compose.yml` que levante el stack completo (API, Postgres con PostGIS, Redis, worker, web) con **un solo comando** y datos de ejemplo cargados.
- **Migraciones que corran de cero** contra una base limpia, sin pasos manuales.
- `.env.example` con todas las variables, cada una con una línea explicando para qué sirve, y el inventario en `docs/operacion/SECRETOS-Y-VARIABLES.md`. **Nombre y propósito, nunca el valor.**
- Un README de arranque en pasos numerados: si al leerlo hay que adivinar algo, no está terminado.
- **Las pruebas corriendo en local con un comando, y que pasen.**

Si hace falta un servicio externo para avanzar —clave de WhatsApp, pasarela, token de mapas— **se para y se pide**. No se inventan credenciales ni se monta un apaño.

## 3. Reglas duras de ingeniería

- **Multi-tenant desde la primera migración.** Tenant = negocio, autorización a nivel de fila en **todos** los endpoints. Ningún dato de un negocio es accesible desde otro. Meterlo después toca todas las consultas.
- **Ningún secreto en git.** Todo secreto nuevo se documenta en el acto y el diff se escanea **en español y en inglés** antes de commitear (`contraseña` y `password`).
- **Datos de tarjeta: nunca.** Solo el token de la pasarela (PAY-3).
- **Los teléfonos no se exponen.** El click-to-chat se resuelve en servidor; los listados no llevan el número en claro.
- **Jobs idempotentes.** Un recordatorio duplicado a las 7 de la mañana es una queja.
- **Migraciones probadas contra un Postgres real** antes de darlas por buenas.
- **`America/Panama` no tiene horario de verano**, pero se guarda en UTC con la zona del negocio: el modelo tiene que aguantar España después.

## 4. Legal — Ley 81 de 2019 de Panamá

Consentimiento, derechos del titular, política de privacidad, retención, y **borrado de cuenta desde dentro de la app**. Sin eso, Apple rechaza la publicación. Términos separados para negocios y clientes, política de reviews, y política de cancelación visible **antes** de reservar.

## 5. Rendimiento y escala (§6 del brief)

| Métrica | Objetivo |
|---|---|
| Búsqueda del marketplace | p95 < 500 ms |
| Cálculo de disponibilidad | p95 < 300 ms |
| Lighthouse móvil (web pública) | ≥ 90 |
| Escala v1 sin rediseño | 5.000 negocios · 100.000 clientes · 50.000 reservas/mes |
| Fiabilidad | 99,5 %, backups diarios con restauración probada |

El panel tiene que ser usable **en un teléfono de gama media con 3G**. Mobile-first aquí no es «responsive»: es el caso principal.

## 6. Diseño

- **Modo claro por defecto.**
- **Se valida en navegador a 390 px de ancho**, no con «build verde»: la CSP, el runtime y el diseño no salen ahí.
- Nada de tarjetas y botones redondeados por todas partes, degradados decorativos ni scrollytelling.
- **Fuentes vetadas:** Inter, Fraunces, Bricolage, General Sans.
- Español (Panamá) en v1, pero **strings externalizados desde el día uno**; inglés es v2.
- WCAG AA básico en los flujos de reserva.

## 7. Datos de ejemplo

**Nunca «Servicio 1 · 100,00».** Un salón panameño de verdad: «Corte + barba, 45 min, $18», «Balayage, 3 h, desde $120». Con datos de mentira no se ve que una reserva de tres horas no cabe en el hueco de las cinco de la tarde.

## 8. Lo que no decide el equipo

1. **El dominio** todavía. El nombre ya es **Bukeo** (ADR-0015), pero nunca a fuego: sale de configuración.
2. **La pasarela concreta** (D5) — default Yappy + tarjetas, pero la elección y las credenciales son de Luis.
3. **Mapas** (D8) — Mapbox por defecto, tiene coste y hay que confirmarlo.
4. **Cualquier cosa que cobre dinero de verdad** a un negocio o a un cliente.

Las 18 decisiones del §10 del brief **ya vienen con su valor por defecto: se usan**. Lo que no esté ahí, se pregunta.
