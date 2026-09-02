# Brief de producto — Bukeo

> Resumen operativo de §3–§5 del [brief](../docs/BRIEF-PRODUCTO.md). Los códigos (ONB-1, RSV-3, MKT-4…) son la trazabilidad: **toda tarea y todo endpoint citan el suyo**.

## Actores

| Actor | Qué hace | Dónde |
|---|---|---|
| Cliente | Busca y reserva | App (modo cliente), web pública |
| Profesional independiente | Negocio de una sola persona | Panel de negocio |
| Dueño / admin de negocio | Servicios, staff, agenda, ads, facturación | Panel de negocio |
| Profesional (staff) | Solo su agenda y sus clientes; sin finanzas ni configuración | Panel de negocio, sobre todo en app |
| Recepción | Agenda de todos sin finanzas | **v2** |
| Equipo M2G | Configuración, moderación, planes, ads, métricas, soporte | Back-office |
| Sistema | Jobs: recordatorios, ranking, billing, métricas | — |

**Una misma cuenta puede ser cliente y tener rol en uno o varios negocios** (ONB-3), con cambio de contexto explícito ("modo negocio").

## Superficies

| # | Superficie | Stack | Por qué |
|---|---|---|---|
| W1 | Web pública: marketplace + reserva + panel de negocio | **Next.js con SSR** | Los perfiles y las páginas categoría × zona **tienen que indexarse** en Google (MKT-7, D6). |
| W2 | Web interna M2G | React + Vite (SPA) | Solo cuenta interna, no necesita SEO. |
| A1 | App nativa iOS + Android | Expo / React Native (D7) | Modo cliente y modo negocio. Fase 5. |

Un único backend y una única API REST versionada sirven a las tres.

## Los dos criterios de "hecho" que importan

- **Fase 1 (núcleo):** un salón real puede operar su agenda entera **desde un teléfono**. No «los endpoints responden».
- **Fase 2 (marketplace):** un cliente encuentra un negocio y reserva **sin que nadie le ayude**, y Google indexa los perfiles.

## Las dos piezas donde se juega el producto

### Motor de disponibilidad (AGD)

```
slot libre = horario del negocio ∩ horario del profesional
             − bloqueos − reservas existentes − buffers
```

Granularidad configurable por negocio (default 15 min), antelación mínima 1 h y máxima 60 días. **La imposibilidad de doble reserva es transaccional, no un `if`** (AGD-4). Detalle y casos límite en [`../docs/arquitectura/fase-3-motor-disponibilidad.md`](../docs/arquitectura/fase-3-motor-disponibilidad.md).

### Ranking del marketplace (MKT-3, MKT-4)

**Una fórmula con pesos configurables desde el back-office**, no reglas repartidas por el código. Entran: distancia, rating ponderado, reservas recientes, tasa de completado, completitud del perfil y actividad reciente, más un **boost temporal para negocios nuevos** — sin él, el marketplace nace bloqueado para los que llegan. El rating agregado va con **ponderación bayesiana**: una review de 5 estrellas no adelanta a un negocio con ochenta de 4,7 (REV-5).

## Flujo de reserva (RSV-1)

negocio → servicio(s) → profesional (o «cualquiera») → fecha y hora → confirmar.
**Máximo 3 pantallas tras elegir servicio.** Reserva como invitado: **no**; teléfono verificado obligatorio (D9). Auto-confirmación por defecto, configurable (D10).

Estados (RSV-3): `pendiente` → `confirmada` → `completada` | `no_show` | `cancelada_cliente` | `cancelada_negocio`. **La reprogramación es un evento, no un estado final.**

## Lo que es v2 y NO se construye

Recepción, multi-sede, recursos físicos, profesional en varios negocios, depósitos y cobro al cliente final, paquetes y promociones, lista de espera, reservas recurrentes, Google Calendar, inglés, factura DGI, override de servicios por profesional.

**Pero el modelo de datos les deja sitio** cuando es barato: una columna hoy no cuesta nada; una migración con datos vivos, mucho.
