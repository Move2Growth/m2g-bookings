# Brief de negocio — Bukeo

> Resumen operativo de §1–§2 del [brief](../docs/BRIEF-PRODUCTO.md). Si algo aquí contradice al brief, manda el brief.

## La tesis

El salón, la barbería o el spa pequeño de Panamá **no paga 30–60 dólares al mes por software**. Si es gratis y funciona desde el teléfono, se llena de negocios; la densidad de negocios atrae clientes; y los negocios que quieren más clientes pagan por visibilidad.

## Quién paga y por qué

| Fuente | v1 | Notas |
|---|---|---|
| Suscripción del negocio | Plan "Gratis", precio **0**, sin tarjeta para registrarse | El **motor de planes y billing existe desde el día uno aunque cobre 0**. Subir el precio a 1 $ es cambiar un número en el back-office, no un desarrollo. |
| Posicionamiento pagado | **Ingreso principal a corto plazo.** Precio fijo por slot (categoría × zona) y periodo de 7 o 30 días, inventario limitado, etiqueta "Patrocinado" | Fase 4. |
| Comisión por reserva | **No** (D4) | — |
| Cobro al cliente final (depósitos) | **No** en v1 | El modelo de datos lo deja preparado. |

## Las tres reglas del marketplace que no se negocian

1. Los patrocinados van **intercalados y etiquetados «Patrocinado»**, máximo 2 de cada 10.
2. **Nunca ocultan a los orgánicos.**
3. **El patrocinio no toca el rating ni las reviews.** Jamás.

## Referencias

Booksy (Europa / EE. UU.), AgendaPro (LatAm), Fresha (software gratis + marketplace).

- **Tomamos:** agenda multi-profesional, catálogo con duración y precio, marketplace con búsqueda y reviews.
- **Cambiamos:** 0 $/mes para el negocio, ranking pagado transparente, y un producto hecho para Panamá — WhatsApp, Yappy, español, zonas de la ciudad.

## Alcance geográfico

Panamá (foco en Ciudad de Panamá). El modelo queda preparado para multi-país: España después. Zona horaria `America/Panama`, **sin horario de verano**, pero se guarda en UTC con la zona del negocio porque España sí lo tiene.

## Riesgos vivos

- **Arranque en frío:** se lanza por barrios piloto; la agenda vale aunque el marketplace esté vacío.
- **No-shows sin depósito:** teléfono verificado, recordatorios, contador y bloqueo de reincidentes.
- **Coste de WhatsApp y de mapas:** control por mensaje, plantillas eficientes, caché de geocoding.
- **Dependencia de Meta:** email y push como respaldo.
- **Scraping de la base de negocios:** los teléfonos no se exponen; el click-to-chat se resuelve en servidor.
