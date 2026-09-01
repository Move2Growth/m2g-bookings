# M2G Agenda — Brief de producto y requisitos funcionales

**Versión:** 0.1 · 1 sep 2026 · Redactado a partir de la nota de voz de Luis
**Nombre comercial:** por definir (codename interno: *M2G Agenda*)

> Este es el brief de producto **tal como lo entregó Luis**. Es la fuente de verdad de QUÉ hay que
> construir. El encargo de desarrollo —el cómo, el orden y las reglas— está en
> [`PROMPT-CONSTRUCTOR.md`](../PROMPT-CONSTRUCTOR.md), que se apoya en este documento y no lo
> sustituye. Los códigos (ONB-1, RSV-3…) son la trazabilidad entre los dos.

---

## 1. Visión

**One-liner:** Plataforma de reservas + marketplace para belleza y bienestar en Panamá, **gratis para el negocio**. Los negocios gestionan su agenda y su equipo sin pagar; los clientes descubren, comparan y reservan; M2G monetiza con **posicionamiento pagado** y, cuando toque, con una **suscripción cuyo precio es un parámetro** (0 al lanzamiento).

**Referencias:** Booksy (Europa / EE. UU.), AgendaPro (LatAm), Fresha (modelo "software gratis + marketplace").
- Tomamos: agenda multi-profesional, catálogo de servicios con duración y precio, marketplace con búsqueda y reviews.
- Cambiamos: $0/mes para el negocio (sin tarjeta para registrarse), ranking pagado transparente, producto hecho para Panamá (WhatsApp, Yappy, español, zonas de la ciudad).

**Tesis:** el salón, barbería o spa pequeño en Panamá no paga $30–60/mes por software. Si es gratis y funciona desde el teléfono, se llena de negocios; la densidad de negocios atrae clientes; los negocios que quieren más clientes pagan por visibilidad.

**Vertical v1:** barberías, peluquerías y salones, uñas, pestañas y cejas, maquillaje, depilación, spa y masajes, estética facial y corporal. Taxonomía administrable.

**Alcance geográfico v1:** Panamá (todo el país, foco en Ciudad de Panamá). Modelo preparado para multi-país (España después).

## 2. Modelo de negocio

### 2.1 Suscripción del negocio (parametrizable)
- Al lanzamiento: plan "Gratis" con precio **0**. Sin tarjeta para registrarse.
- Requisito clave: el **motor de planes y billing existe desde v1** aunque cobre 0. Pasar el precio a $1 o $2/mes debe ser un cambio de configuración en el back-office, no un desarrollo.
- Soporta: precio, moneda, periodicidad, límites y features por plan, fecha efectiva de cambio, aviso previo, *grandfathering* configurable, periodo de gracia y suspensión por impago.
- Unidad de cobro: por negocio (default), modelo preparado para cobrar por profesional (D3).

### 2.2 Posicionamiento pagado (ingreso principal a corto plazo)
- El negocio compra visibilidad: destacado en (categoría × zona) durante un periodo.
- v1: precio fijo por slot y periodo (7 / 30 días), inventario limitado por combinación, etiqueta "Patrocinado".
- v2: subasta / CPC, destacados en home, push a clientes cercanos (opt-in).
- Pago inmediato con tarjeta o Yappy.

### 2.3 Lo que NO cobramos en v1
- Comisión por reserva: no (D4).
- Cobro al cliente final (depósitos, pago anticipado): no en v1; modelo preparado.

### 2.4 Palancas futuras (no diseñar ahora, no bloquear)
Depósito anti no-show; planes premium; comisión por "cliente nuevo" del marketplace.

## 3. Actores y roles

| Actor | Descripción | Superficie |
|---|---|---|
| Cliente | Busca y reserva servicios | App (modo cliente), web pública |
| Profesional independiente | Negocio de una sola persona | Panel de negocio (web / app) |
| Dueño / admin de negocio | Servicios, staff, agenda, ads, facturación | Panel de negocio (web / app) |
| Profesional (staff) | Ve y gestiona solo su agenda | Panel de negocio (sobre todo app) |
| Recepción | Agenda de todos sin finanzas ni configuración | **v2** |
| M2G superadmin / soporte / finanzas / moderación | Equipo interno | Back-office |
| Sistema | Jobs: recordatorios, ranking, billing, métricas | — |

Una misma cuenta puede ser cliente y tener rol en uno o varios negocios.

## 4. Superficies: 2 webs + 1 app

| # | Superficie | Usuarios | Contenido | Notas |
|---|---|---|---|---|
| W1 | **Web pública** | Clientes y negocios | Marketplace + reserva + panel de negocio | Perfiles y páginas categoría × zona **indexables** (SSR). Mobile-first. |
| W2 | **Web interna M2G** | Equipo M2G | Configuración, moderación, planes, ads, métricas, soporte | Solo cuenta interna. |
| A1 | **App nativa** iOS + Android | Clientes y negocios | Modo cliente y modo negocio | Ver §5.13 y D2. |

Un único backend / API sirve a las tres.

## 5. Requisitos funcionales

### 5.1 Cuentas y onboarding (ONB)
- **ONB-1** Registro y login de cliente por teléfono con OTP (WhatsApp; SMS fallback según D14) o email; login social Google y Apple (Apple obligatorio en iOS si hay login social).
- **ONB-2** Registro de negocio 100 % self-service, sin intervención de M2G ni tarjeta: datos básicos, categorías, ubicación con pin, horario, tipo, primer servicio. Objetivo: **operativo en menos de 10 minutos desde el móvil**.
- **ONB-3** Una cuenta puede ser cliente y negocio; cambio de contexto explícito ("modo negocio").
- **ONB-4** Invitación de profesionales por WhatsApp o email; el dueño puede crear profesionales "sin cuenta" y convertirlos después.
- **ONB-5** v1: teléfono verificado; **v2** sello "Verificado" con documento o RUC.
- **ONB-6** Estados: borrador → publicado → suspendido (solo admin). Solo "publicado" aparece en el marketplace. Mínimo para publicar: 1 servicio activo, horario, ubicación, 1 foto (D11).
- **ONB-7** Checklist de progreso del perfil, con impacto en el ranking.

### 5.2 Perfil público del negocio (NEG)
- **NEG-1** Nombre, descripción, categorías, portada + galería, dirección + geolocalización, horario semanal, WhatsApp click-to-chat (número no expuesto en texto plano), Instagram y redes.
- **NEG-2** Atributos filtrables como **catálogo administrable** (no hardcode): tipo de cabello, técnicas, público atendido, accesibilidad, estacionamiento, métodos de pago, idiomas.
- **NEG-3** Servicios con precio y duración, equipo, reviews, mapa, botón "Reservar" siempre visible.
- **NEG-4** URL amigable (slug) para SEO y bio de Instagram; QR descargable.
- **NEG-5** v1: una ubicación por negocio. Preparado para multi-sede (**v2**).

### 5.3 Catálogo de servicios (SRV)
- **SRV-1** Servicio: nombre, categoría global, descripción, duración, precio (fijo / "desde" / a consultar), buffer antes y después, activo, foto, orden.
- **SRV-2** Variantes con precio y duración propios. v1 lista simple; **v2** opciones combinables.
- **SRV-3** Asignación de servicios a profesionales. Override por profesional: **v2**.
- **SRV-4** Categorías globales administradas por M2G para filtros consistentes.
- **SRV-5** Recursos físicos como restricción de capacidad: **v2**.
- **SRV-6** Paquetes, combos y promociones: **v2**.

### 5.4 Profesionales y recursos (STF)
- **STF-1** Profesional: nombre, foto, bio, servicios, horario propio, descansos, días libres, vacaciones, bloqueos.
- **STF-2** Activo / inactivo; visible u oculto en el marketplace.
- **STF-3** Permisos: dueño (todo); profesional (su agenda y sus clientes, sin finanzas ni configuración); recepción (**v2**).
- **STF-4** Profesional en varios negocios: **v2** (D17).
- **STF-5** Reserva "cualquier profesional disponible", balanceando carga.

### 5.5 Motor de disponibilidad y agenda (AGD)
- **AGD-1** Slots = horario del negocio ∩ horario del profesional − bloqueos − reservas − buffers. Granularidad configurable (default 15 min). Antelación mínima (1 h) y máxima (60 días) configurables.
- **AGD-2** Vista día y semana por profesional; reserva manual (walk-in / teléfono) con cliente registrado o "cliente rápido"; mover y reprogramar con drag & drop en web.
- **AGD-3** Bloqueos puntuales y recurrentes.
- **AGD-4** **Imposibilidad de doble reserva**: control de concurrencia transaccional.
- **AGD-5** Zona horaria `America/Panama` (sin DST). Almacenar en UTC + tz del negocio.
- **AGD-6** Feriados de Panamá precargados (sugeridos, no impuestos).
- **AGD-7** Google Calendar: **v2**.

### 5.6 Reservas (RSV)
- **RSV-1** Flujo: negocio → servicio(s) → profesional (o cualquiera) → fecha y hora → confirmar. **Máximo 3 pantallas** tras elegir servicio. Reserva como invitado: no; teléfono verificado obligatorio (D9).
- **RSV-2** Varios servicios encadenados con el mismo profesional (D13). Distintos profesionales: **v2**.
- **RSV-3** Estados: `pendiente` → `confirmada` → `completada` | `no_show` | `cancelada_cliente` | `cancelada_negocio`. La reprogramación es un evento, no un estado final. Auto-confirmar por default (D10).
- **RSV-4** Cancelación y reprogramación por el cliente hasta X horas antes (default 2 h); después solo el negocio.
- **RSV-5** No-show: lo marca el negocio; contador por cliente; puede bloquear reincidentes. Depósito: **v2**.
- **RSV-6** Notas del cliente; ficha de cliente por negocio. Datos de salud: **v2** con consentimiento.
- **RSV-7** Historial; "reservar de nuevo" en un tap; añadir al calendario (.ics).
- **RSV-8** Lista de espera: **v2**. · **RSV-9** Reservas recurrentes: **v2**.

### 5.7 Marketplace (MKT)
- **MKT-1** Home con búsqueda por texto, categoría y ubicación (GPS, dirección o zona). Lista y mapa.
- **MKT-2** Filtros: distancia, categoría, servicio, precio, rating, atributos, disponibilidad real ("ahora", "hoy", fecha), abierto ahora, métodos de pago.
- **MKT-3** Ranking orgánico documentado y ajustable desde back-office: distancia, rating ponderado, reservas recientes, tasa de completado, completitud, actividad. **Boost temporal para negocios nuevos.**
- **MKT-4** Patrocinados intercalados y etiquetados, máximo N por página (default 2 de 10). **Nunca ocultan a los orgánicos.**
- **MKT-5** Favoritos; compartir perfil (deep link); "reservar de nuevo".
- **MKT-6** Taxonomía de zonas administrable y jerárquica (provincia → distrito → corregimiento → barrio).
- **MKT-7** SEO: perfiles y páginas categoría × zona con SSR, metadatos, schema.org LocalBusiness, sitemap.
- **MKT-8** Tracking de impresiones y clics por negocio.

### 5.8 Reviews (REV)
- **REV-1** Solo con reserva **completada**, una por reserva, ventana de X días (default 14).
- **REV-2** Rating 1–5 + texto + fotos; al negocio y opcionalmente al profesional.
- **REV-3** Respuesta pública del negocio (una por review).
- **REV-4** Reporte y moderación en back-office; política pública.
- **REV-5** Rating agregado con **ponderación bayesiana**.
- **REV-6** Solicitud automática tras la cita.

### 5.9 Publicidad (ADS)
- **ADS-1** El negocio elige categoría × zona × periodo, ve precio, inventario y vista previa, y paga.
- **ADS-2** Inventario limitado (default 3 slots); si está lleno, siguiente periodo o lista de espera.
- **ADS-3** Pago inmediato, recibo, renovación automática opcional con aviso.
- **ADS-4** Métricas: impresiones, clics, reservas atribuidas, comparación con orgánico.
- **ADS-5** Precios, inventario y reglas administrables; cupones y promociones.
- **ADS-6** **v2**: subasta / CPC, destacados en home, push a cercanos.
- **ADS-7** **El patrocinio nunca altera el rating ni oculta reviews.**

### 5.10 Notificaciones (NTF)
- **NTF-1** WhatsApp (Meta Cloud API) principal; push; email. SMS solo fallback de OTP (D14).
- **NTF-2** Eventos: reserva creada / confirmada / cancelada / reprogramada, recordatorio 24 h y 2 h, "¿cómo te fue?", invitación de staff, ads por vencer, cambios de plan, resumen diario opcional.
- **NTF-3** Preferencias por usuario y negocio; plantillas administrables y aprobadas en Meta; español v1, i18n preparado.
- **NTF-4** Cola con reintentos, registro de entregas, control de costes.

### 5.11 Pagos y facturación (PAY)
- **PAY-1** Motor de planes y suscripciones: estado por negocio, cambio de precio con fecha efectiva y aviso, grandfathering, gracia y suspensión. **Al lanzamiento cuesta 0; el flujo de cobro debe existir y estar probado.**
- **PAY-2** Cobro de ads y suscripciones por pasarela panameña (D5): Yappy + tarjetas; webhooks, conciliación, reintentos, recibos.
- **PAY-3** Tokenización de la pasarela; **nunca almacenar datos de tarjeta**.
- **PAY-4** Datos fiscales (RUC / DV) en el recibo; factura DGI: **v2** (D16).
- **PAY-5** Cobro al cliente final: **v2**; el modelo debe soportarlo.
- **PAY-6** USD / PAB. Símbolo según D12. Modelo multi-moneda.

### 5.12 Back-office M2G (ADM)
- **ADM-1** Dashboard: negocios registrados / publicados / activos, reservas por día, clientes, ingresos, funnel de onboarding, retención por cohortes.
- **ADM-2** Gestión de negocios: ver, editar, publicar / suspender, verificar, impersonar con auditoría y aviso.
- **ADM-3** Moderación: reviews reportadas, fotos, perfiles.
- **ADM-4** **Configuración sin desplegar código**: planes y precios, ads, taxonomías, pesos del ranking, plantillas, feature flags.
- **ADM-5** Roles internos: superadmin, soporte, finanzas, moderación.
- **ADM-6** Auditoría de acciones; exportaciones CSV.
- **ADM-7** Soporte: buscar usuario / negocio / reserva, reenviar notificación, forzar cancelación, ver log.

### 5.13 App nativa (APP)
- **APP-1** iOS + Android desde una única base de código (D7).
- **APP-2** Modo cliente: marketplace, reservas, favoritos, historial, push, ubicación.
- **APP-3** Modo negocio: agenda día / semana, gestionar reservas, reserva manual, bloquear tiempo, ficha de cliente, push. Configuración avanzada puede quedar en web en v1 (D2).
- **APP-4** Deep links universales.
- **APP-5** Tolerancia a red inestable: caché de la agenda del día, reintentos, estados optimistas.
- **APP-6** Publicación con cuentas de M2G (D18).

## 6. Requisitos no funcionales

- **Multi-tenant lógico:** tenant = negocio; autorización a nivel de fila en todos los endpoints.
- **Idioma:** español (Panamá) v1; strings externalizados desde el día 1; inglés **v2**.
- **Localización:** `America/Panama`, USD / PAB; listo para multi-país.
- **Rendimiento:** búsqueda p95 < 500 ms; disponibilidad p95 < 300 ms; Lighthouse móvil ≥ 90; panel usable en gama media con 3G / 4G.
- **Escala v1:** 5.000 negocios, 100.000 clientes, 50.000 reservas / mes sin rediseño.
- **Seguridad:** OAuth2 / JWT con refresh y revocación; OTP con rate limiting; RBAC; cifrado en tránsito y de datos sensibles en reposo; protección de teléfonos frente a scraping; OWASP Top 10; dependencias auditadas.
- **Privacidad y legal:** Ley 81 de 2019 de Panamá: consentimiento, derechos del titular, política de privacidad, retención y **borrado de cuenta desde la app**; términos separados para negocios y clientes; política de reviews; política de cancelación visible antes de reservar.
- **Fiabilidad:** 99,5 %; backups diarios con restauración probada; **jobs idempotentes**.
- **Observabilidad:** logs estructurados, métricas, alertas, Sentry, health checks.
- **Calidad:** unitarios e integración en el motor de disponibilidad y el ciclo de reservas; E2E de: registrar negocio, publicar, reservar, cancelar, review, comprar ads.
- **Accesibilidad:** WCAG AA básico en los flujos de reserva.
- **Mobile-first en toda la web.**

## 7. Modelo de datos (entidades núcleo)

Orientativo; el esquema final lo define el constructor.

- **Identidad:** `users`, `auth_identities`, `sessions`, `otp_codes`.
- **Negocio:** `businesses`, `locations`, `business_categories`, `business_attributes`, `business_hours`, `business_settings`, `business_media`.
- **Equipo:** `memberships`, `staff_profiles`, `staff_hours`, `time_blocks`, `staff_services`.
- **Catálogo:** `service_categories`, `services`, `service_variants`.
- **Clientes:** `client_profiles`, `business_clients`, `favorites`.
- **Reservas:** `bookings`, `booking_items`, `booking_events`.
- **Reviews:** `reviews`, `review_media`, `review_replies`, `review_reports`.
- **Marketplace:** `zones`, `attributes`, `listing_impressions`, `listing_clicks`, `ranking_weights`.
- **Monetización:** `plans`, `subscriptions`, `subscription_events`, `ad_products`, `ad_inventory`, `ad_campaigns`, `ad_metrics_daily`, `coupons`.
- **Pagos:** `payment_methods`, `payments`, `invoices`, `payment_provider_events`.
- **Notificaciones:** `notification_templates`, `notification_preferences`, `notifications`.
- **Interno:** `admin_users`, `audit_logs`, `feature_flags`, `moderation_queue`.
- Geo con PostGIS (`geography(Point)` + índice GiST).

## 8. Arquitectura y stack propuestos

- **Backend:** FastAPI (Python 3.12, uv), PostgreSQL 16 + PostGIS, Redis, workers (arq / Celery), S3-compatible con procesado de imágenes, API REST versionada con OpenAPI, webhooks de pasarela y WhatsApp.
- **Web pública (W1):** Next.js / React con SSR. El template M2G (FastAPI + React/Vite) es SPA: sirve para panel y back-office, no para páginas públicas indexables (D6).
- **Back-office (W2):** React (Vite) SPA.
- **App (A1):** Expo (React Native), EAS Build, OTA (D7).
- **Monorepo** con paquetes compartidos: tipos desde OpenAPI, design tokens, componentes.
- **Infra:** Docker, Hetzner, CI/CD, entornos dev / staging / prod, Alembic, backups.
- **Integraciones:** Meta WhatsApp Cloud API; pasarela (D5); mapas (D8); FCM / APNs; email; Sentry.
- **Design system propio**, mobile-first.

## 9. Fases

| Fase | Entrega | Criterio de "hecho" |
|---|---|---|
| 0 | Diseño: flujos, design system, modelo de datos, contratos; cierre de decisiones | Aprobado por Luis |
| 1 | Núcleo: auth, onboarding, servicios, staff, agenda, disponibilidad, reservas manuales, notificaciones, ficha de cliente | **Un salón real opera su agenda 100 % desde la web móvil** |
| 2 | Marketplace: perfiles SEO, búsqueda, filtros, mapa, reserva, reviews, favoritos, ranking | **Un cliente encuentra y reserva sin ayuda; Google indexa** |
| 3 | Back-office + planes y billing (precio 0), taxonomías, moderación, métricas, flags | M2G cambia precios y taxonomías sin desplegar |
| 4 | Ads + pasarela | Un negocio compra un destacado, paga y aparece como "Patrocinado" |
| 5 | App: modo cliente + negocio, push, deep links, stores | Aprobadas en App Store y Google Play |
| 6 | Crecimiento: depósitos, Google Calendar, multi-sede, inglés, lista de espera, España | Según prioridad |

Orden de 4 y 5 según D15.

## 10. Decisiones (con valor por defecto)

| # | Decisión | Default | Alternativa |
|---|---|---|---|
| D1 | Nombre comercial y dominio | Codename *M2G Agenda* | — |
| D2 | Alcance de la app | Dos modos; configuración avanzada solo en web | App solo clientes |
| D3 | Unidad de cobro futura | Por negocio; preparado por profesional | Por profesional |
| D4 | Comisión por reserva | No en v1 | — |
| D5 | Pasarela | Yappy + tarjetas vía pasarela local | Solo tarjetas |
| D6 | Web pública | Next.js con SSR | Vite SPA (peor SEO) |
| D7 | App | Expo / React Native | Flutter |
| D8 | Mapas | Mapbox | Google Maps |
| D9 | Reserva como invitado | No; teléfono verificado | Sí, con OTP |
| D10 | Confirmación | Auto-confirmar (configurable) | Manual |
| D11 | Mínimo para publicar | 1 servicio, horario, ubicación, 1 foto | Solo servicio + horario |
| D12 | Símbolo de moneda | "$" | "B/." |
| D13 | Multi-servicio | Sí en v1, mismo profesional | Uno por reserva |
| D14 | SMS | Solo fallback de OTP | Sin SMS |
| D15 | Orden de fases | Ads (4) antes que app (5) | App antes |
| D16 | Factura DGI | v2 | v1 |
| D17 | Profesional en varios negocios | v2 | v1 |
| D18 | Cuentas de stores | De M2G | — |

## 11. Fuera de alcance v1

POS / caja e inventario; nómina y comisiones; email marketing; fidelidad y gift cards; venta de productos; multi-sede; Google Calendar; cobro al cliente final; inglés; recepción; recursos físicos; paquetes; lista de espera; reservas recurrentes.

## 12. Riesgos y mitigaciones

- **Arranque en frío:** lanzar por barrios piloto; la agenda vale aunque el marketplace esté vacío; captación manual de los primeros 100.
- **No-shows sin depósito:** teléfono verificado, recordatorios, contador y bloqueo; depósito en Fase 6.
- **Coste de WhatsApp y mapas:** control por mensaje, plantillas eficientes, caché de geocoding.
- **Dependencia de Meta:** email y push como respaldo.
- **Revisión de stores:** login con Apple, política de privacidad, borrado de cuenta en la app.
- **Scraping:** rate limiting, números no expuestos, términos de uso.
- **Cambio de precio:** comunicación y grandfathering previstos (PAY-1).
