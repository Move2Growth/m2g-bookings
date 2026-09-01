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

Si los dos dicen cosas distintas, **manda el brief**.

## Las tres cosas que gobiernan cada decisión

1. **Todo se usa desde un teléfono de gama media con 3G.** El dueño del salón no tiene escritorio.
2. **El motor de planes y billing existe desde el día uno aunque cobre 0.** Subir el precio tiene
   que ser cambiar un número, no un desarrollo.
3. **Las páginas públicas las indexa Google.** Media clientela llega buscando «barbería en San
   Francisco», no el nombre del salón. Sin SSR no hay marketplace.

## Reparto del trabajo

- **Quien desarrolla:** construye y valida **en local**. Deja `docker-compose` que levante todo con
  un comando, migraciones que corran de cero, `.env.example` documentado y README de arranque.
- **Infraestructura, CI/CD y despliegues:** los lleva el equipo de plataforma de M2G. **Quien
  desarrolla no despliega a ningún entorno.**

## Estado

**Fase 0 — sin iniciar.** El repo tiene el brief y el encargo; falta el diseño (flujos, design
system, modelo de datos y contratos de API), que se cierra con la aprobación de Luis.
