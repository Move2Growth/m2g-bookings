# Fase 2 · Requisitos y MVP — Estado: en proceso

> **Qué es este documento.** La prueba de que **nada del brief se ha perdido por el camino**. Los
> ochenta y tres requisitos del [§5 del brief](../BRIEF-PRODUCTO.md) aparecen aquí uno por uno, con
> su prioridad, la fase en la que se construye y el sitio exacto —ADR, endpoint, tabla— donde deja
> de ser una frase y pasa a ser algo. Después, el **MVP mínimo de la Fase 1** y el de la **Fase 2**
> contra sus criterios de «hecho» literales; la lista de **lo que es v2 y no se construye**; los
> **no funcionales del §6 convertidos en comprobaciones**; y, al final, los requisitos que hoy **no
> cubre ni un ADR ni un endpoint**, dichos en voz alta en vez de disimulados.
>
> **De dónde sale.** Del §5, §6, §9 y §11 del brief, del
> [encargo de construcción](../../PROMPT-CONSTRUCTOR.md), de los catorce [ADR](adr/), del
> [modelo de datos](fase-3-modelo-de-datos.md), de los [contratos de API](fase-3-contratos-api.md) y
> del [plan de sprints](fase-5-plan-de-sprints.md). **Si esto y el brief dicen cosas distintas, manda
> el brief.**

---

## 1. Cómo se lee la tabla

**Prioridad (MoSCoW).** No es una escala de importancia absoluta, sino **dentro de la fase en la que
el requisito se construye**:

| Valor | Qué significa |
|---|---|
| **Debe** | Sin él, la fase **no cumple su criterio de «hecho»**. No hay negociación: si falta, la fase no se cierra. |
| **Debería** | La fase se sostiene sin él, pero el producto queda cojo. Se construye dentro de la fase salvo que el tiempo obligue a moverlo, y entonces se anota en el tablero con dueño. |
| **Puede** | Mejora que entra si sobra tiempo. En las fases 0 a 2 hay muy poco de esto, y es deliberado: lo que no es imprescindible o casi, está en fases posteriores. |

**Fase.** El número del §9 del brief. Cuando un requisito se reparte entre dos fases —lo habitual
cuando el dato se captura en la Fase 1 y se publica en la Fase 2— se escriben las dos con lo que
entra en cada una. **«v2 — no se construye»** significa exactamente eso: no hay tarea, no hay
endpoint, no hay pantalla; solo el hueco en el modelo de datos, si lo tiene.

**Dónde se materializa.** El ADR que lo decide, el endpoint que lo expone y la tabla que lo guarda.
Si una celda dice «sin endpoint todavía» o «sin hueco declarado», eso **no es un olvido de la tabla**:
está recogido en el §8, «Requisitos sin cubrir todavía».

---

## 2. Trazabilidad completa — los 83 requisitos del §5

### 2.1 Cuentas y onboarding (ONB)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **ONB-1** | Registro y login de cliente por teléfono con OTP, correo alternativo y acceso social Google y Apple | Debe | 1 | ADR-0006 · `POST /auth/otp/solicitar`, `/auth/otp/verificar`, `/auth/social/{google\|apple}`, `/auth/refrescar` · `users`, `auth_identities`, `otp_codes`, `sessions` |
| **ONB-2** | Alta de negocio 100 % autoservicio, sin M2G y sin tarjeta, operativa en menos de 10 minutos desde el móvil | Debe | 1 | ADR-0010 · `POST /negocios`, `PUT /negocio/ubicacion`, `PUT /negocio/horario` · `businesses`, `locations`, `business_hours`, `services`, `subscriptions` |
| **ONB-3** | Una cuenta puede ser cliente y tener papel en uno o varios negocios, con cambio de contexto explícito | Debe | 1 | ADR-0006 · `POST /mi/contexto/negocio` · `memberships`, `sessions.active_business_id` |
| **ONB-4** | Invitación de profesionales por WhatsApp o correo; profesional «sin cuenta» convertible después | Debe | 1 | ADR-0006, ADR-0007 · `POST /negocio/profesionales/{id}/invitacion` · `staff_profiles.user_id` nulable, `memberships.invite_token_hash` |
| **ONB-5** | v1: teléfono verificado. Sello «Verificado» con documento o RUC | Debe (parte v1) | 1 (teléfono) · **v2** (sello) | `users.phone_verified_at` (D9) · `businesses.verified_at`, hoy siempre `NULL` |
| **ONB-6** | Estados borrador → publicado → suspendido; solo «publicado» aparece en el marketplace; mínimo para publicar | Debe | 1 (estados y publicación) · 3 (suspender desde el back-office) | D11 · `POST /negocio/publicar` · `businesses.status`, `published_at`, `suspended_at` |
| **ONB-7** | Lista de progreso del perfil, con impacto en el ranking | Debería | 1 (la lista) · 2 (el impacto) | `GET /negocio/checklist` · `businesses.profile_completeness`, `business_ranking_signals.completeness` |

### 2.2 Perfil público del negocio (NEG)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **NEG-1** | Nombre, descripción, categorías, portada y galería, dirección y geolocalización, horario, WhatsApp click-to-chat sin número en claro, redes | Debe | 1 (captura) · 2 (publicación) | ADR-0005 · `PATCH /negocio/perfil`, `PUT /negocio/ubicacion`, `POST /negocio/media`, `GET /publico/negocios/{slug}`, `GET …/chat` · `businesses`, `locations`, `business_media` |
| **NEG-2** | Atributos filtrables como catálogo administrable, no escritos en el código | Debería | 2 (uso y filtro) · 3 (administración) | `attributes`, `attribute_values`, `business_attributes` · `GET /publico/buscar` |
| **NEG-3** | Servicios con precio y duración, equipo, opiniones, mapa y botón «Reservar» siempre visible | Debe | 2 | `GET /publico/negocios/{slug}` · `services`, `staff_profiles`, `reviews`, `business_rating_stats` |
| **NEG-4** | URL amigable (slug) para SEO y bio de Instagram; QR descargable | Debe (slug) · Debería (QR) | 2 | ADR-0011 · `businesses.slug`, `slug_redirects` · **el QR está en el Sprint 10 pero no tiene endpoint en el contrato: §8** |
| **NEG-5** | Una ubicación por negocio; modelo preparado para multi-sede | Debe (parte v1) | 1 · **v2** (multi-sede) | `locations` como tabla propia + `CREATE UNIQUE INDEX locations_una_principal` · hueco §14.1 del modelo |

### 2.3 Catálogo de servicios (SRV)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **SRV-1** | Servicio con nombre, categoría global, descripción, duración, precio (fijo, «desde» o a consultar), buffers antes y después, activo, foto y orden | Debe | 1 | `GET`·`POST`·`PATCH`·`DELETE /negocio/servicios[/{id}]` · `services` |
| **SRV-2** | Variantes con precio y duración propios, en lista simple | Debería | 1 · **v2** (opciones combinables) | `…/servicios/{id}/variantes` · `service_variants` |
| **SRV-3** | Asignación de servicios a profesionales | Debe | 1 · **v2** (override de precio y duración por profesional) | `PUT /negocio/profesionales/{id}/servicios` · `staff_services` |
| **SRV-4** | Categorías globales administradas por M2G, para que los filtros sean consistentes entre negocios | Debe | 1 (uso y semilla) · 3 (administración) | `GET /catalogo/categorias` · `service_categories`, global y sin RLS a propósito |
| **SRV-5** | Recursos físicos como restricción de capacidad | — | **v2 — no se construye** | Hueco §14.2: la forma genérica de `staff_occupancy`, `booking_items` y ADR-0004 admiten `resource_occupancy` sin tocar nada |
| **SRV-6** | Paquetes, combos y promociones | — | **v2 — no se construye** | Sin hueco declarado; `booking_items` (varias líneas por cita) y `coupons` dan base parcial · §8 |

### 2.4 Profesionales y recursos (STF)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **STF-1** | Profesional con nombre, foto, bio, servicios, horario propio, descansos, días libres, vacaciones y bloqueos | Debe | 1 | `GET`·`POST`·`PATCH /negocio/profesionales[/{id}]`, `PUT …/horario`, `/negocio/bloqueos` · `staff_profiles`, `staff_hours`, `time_block_rules`, `staff_occupancy` |
| **STF-2** | Activo o inactivo; visible u oculto en el marketplace | Debe | 1 | `staff_profiles.active`, `staff_profiles.visible_in_marketplace` |
| **STF-3** | Permisos: dueño todo; profesional su agenda y sus clientes, sin finanzas ni configuración | Debe | 1 · **v2** (rol de recepción) | ADR-0006 · matriz (rol × acción) en un solo módulo · `memberships.role`, con `recepcion` ya en el `CHECK` (§14.5) |
| **STF-4** | Un profesional en varios negocios | — | **v2 — no se construye** (D17) | Hueco §14.3: `staff_occupancy.staff_user_id` nulable y la exclusión declarada por `staff_id` y no por `(business_id, staff_id)` |
| **STF-5** | Reserva «cualquier profesional disponible», balanceando carga | Debe | 1 | `GET /publico/negocios/{slug}/disponibilidad` · `staff_profiles.accepts_any_staff`, `staff_services` |

### 2.5 Motor de disponibilidad y agenda (AGD)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **AGD-1** | Slots = horario del negocio ∩ horario del profesional − bloqueos − reservas − buffers; granularidad y antelación mínima y máxima configurables | Debe | 1 (Sprints 4 y 5) | ADR-0003, ADR-0004 · [`fase-3-motor-disponibilidad.md`](fase-3-motor-disponibilidad.md) · `GET …/disponibilidad` · `business_settings`, `business_hours`, `staff_hours`, `services.buffer_*` |
| **AGD-2** | Vista día y semana por profesional; reserva manual con cliente registrado o «cliente rápido»; mover y reprogramar | Debe | 1 | `GET /negocio/agenda`, `POST /negocio/reservas`, `PATCH /negocio/reservas/{id}` · `bookings`, `business_clients.user_id` nulable |
| **AGD-3** | Bloqueos puntuales y recurrentes | Debe | 1 | `GET`·`POST`·`DELETE /negocio/bloqueos[/{id}]` · `time_block_rules` (recurrentes) + `staff_occupancy` con `kind = 'bloqueo'` (puntuales) |
| **AGD-4** | Imposibilidad de doble reserva por control de concurrencia transaccional | Debe | 1 | **ADR-0004** · `staff_occupancy_sin_solape` (`EXCLUDE USING gist`) · `409 SLOT_NO_DISPONIBLE` · garantía 2 de la [constitution](constitution.md) |
| **AGD-5** | Zona horaria `America/Panama`; almacenar en UTC con la zona del negocio | Debe | 0 (modelo) · 1 (motor) | **ADR-0003** · `businesses.timezone`, instantes en `timestamptz`, reglas horarias como día + hora local |
| **AGD-6** | Feriados de Panamá precargados, sugeridos y no impuestos | Debería | 1 | `holidays` (global) → propone `time_block_rules` solo si el negocio acepta |
| **AGD-7** | Sincronización con Google Calendar | — | **v2 — no se construye** | Sin hueco declarado; `booking_events` y el `.ics` de RSV-7 son la base natural · §8 |

### 2.6 Reservas (RSV)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **RSV-1** | Flujo negocio → servicio(s) → profesional o «cualquiera» → fecha y hora → confirmar, en **máximo 3 pantallas** tras elegir servicio; sin reserva de invitado | Debe | 2 (Sprint 13) | D9 · `POST /mi/reservas` con `Idempotency-Key` · `bookings`, `booking_items` |
| **RSV-2** | Varios servicios encadenados con el mismo profesional | Debe | 1 (el motor lo resuelve como bloque continuo) · 2 (el flujo del cliente) | D13 · ADR-0004 · `booking_items`, un único rango en `staff_occupancy` |
| **RSV-3** | Estados `pendiente → confirmada → completada \| no_show \| cancelada_*`; la reprogramación es un evento, no un estado final; auto-confirmar por defecto | Debe | 1 | D10 · `POST /negocio/reservas/{id}/estado`, `POST /mi/reservas/{id}/reprogramar` · `bookings.status`, `booking_events`, disparador de §8.4 del modelo |
| **RSV-4** | Cancelación y reprogramación por el cliente hasta X horas antes (2 h por defecto); después, solo el negocio | Debe | 1 (el parámetro y el lado negocio) · 2 (el lado cliente) | `POST /mi/reservas/{id}/cancelar` · `business_settings` · P10 de [descubrimiento](fase-0-descubrimiento.md) |
| **RSV-5** | No-show marcado por el negocio, contador por cliente y bloqueo de reincidentes | Debe | 1 | `POST /negocio/reservas/{id}/estado` · `business_clients.no_show_count`, `.blocked`, `.blocked_reason` |
| **RSV-6** | Notas del cliente y ficha de cliente por negocio | Debe | 1 · **v2** (datos de salud, con consentimiento) | `GET`·`PATCH /negocio/clientes[/{id}]` · `business_clients.notes`; `client_profiles` deliberadamente flaco (§7 del modelo) |
| **RSV-7** | Historial, «reservar de nuevo» en un toque, añadir al calendario (`.ics`) | Debería | 2 | `GET /mi/reservas`, `GET /mi/reservas/{id}` con `.ics` · `bookings` |
| **RSV-8** | Lista de espera | — | **v2 — no se construye** | Sin hueco declarado · §8 |
| **RSV-9** | Reservas recurrentes | — | **v2 — no se construye** | Sin hueco declarado · §8 |

### 2.7 Marketplace (MKT)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **MKT-1** | Portada con búsqueda por texto, categoría y ubicación (GPS, dirección o zona); resultados en lista y en mapa | Debe | 2 (Sprint 11) | ADR-0005 · `GET /publico/buscar` · `locations.geo` con índice GiST, `zones`, `geocoding_cache` |
| **MKT-2** | Filtros: distancia, categoría, servicio, precio, rating, atributos, **disponibilidad real**, abierto ahora, métodos de pago | Debe | 2 | `GET /publico/buscar` · `business_attributes`, `services.price_minor`, `business_rating_stats` y el motor de AGD-1 |
| **MKT-3** | Ranking orgánico documentado y ajustable desde el back-office, con **boost temporal a los negocios nuevos** | Debe | 2 (fórmula y precálculo) · 3 (ajuste desde el panel) | **ADR-0009** · `ranking_weights` con vigencia, `business_ranking_signals.base_score` y `signals` (el desglose) |
| **MKT-4** | Patrocinados intercalados y etiquetados, máximo N por página (2 de 10), **sin ocultar a los orgánicos** | Debe | 2 (mecanismo, con inventario vacío) · 4 (compras reales) | ADR-0009 · `ranking_weights.sponsored_per_page`, `page_size` · `ad_campaigns` sin ninguna columna que la una a `business_ranking_signals` |
| **MKT-5** | Favoritos; compartir perfil por enlace profundo; «reservar de nuevo» | Debería | 2 | `GET`·`POST`·`DELETE /mi/favoritos[/{id}]` · `favorites` |
| **MKT-6** | Taxonomía de zonas administrable y jerárquica (provincia → distrito → corregimiento → barrio) | Debe | 2 (uso y semilla) · 3 (administración) | ADR-0005 · `GET /publico/zonas` · `zones` con `path` materializado y `boundary` para sugerir la zona de un punto |
| **MKT-7** | SEO: perfiles y páginas categoría × zona con SSR, metadatos, schema.org LocalBusiness y sitemap | Debe | 2 (Sprint 10) | **ADR-0011** · `GET /publico/z/{zona}/{categoria}` · `zones.businesses_count` para no generar páginas vacías |
| **MKT-8** | Tracking de impresiones y clics por negocio | Debería | 2 | `POST /publico/negocios/{slug}/impresion`, `GET …/chat` · `listing_impressions_daily`, `listing_clicks_daily`, agregados por día |

### 2.8 Reviews (REV)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **REV-1** | Solo con reserva **completada**, una por reserva, dentro de la ventana (14 días) | Debe | 2 (Sprint 14) | `POST /mi/reservas/{id}/review` · `reviews` con `UNIQUE (booking_id)`; la ventana y el estado se validan en la aplicación · P11 |
| **REV-2** | Rating 1–5 más texto y fotos; al negocio y opcionalmente al profesional | Debe | 2 | `reviews.rating`, `reviews.staff_rating`, `review_media` |
| **REV-3** | Respuesta pública del negocio, una por opinión | Debería | 2 | `POST /negocio/reviews/{id}/respuesta` · `review_replies` |
| **REV-4** | Reporte y moderación en el back-office; política pública de opiniones | Debe (reporte y política) · Debería (panel) | 2 (reporte y cola) · 3 (panel de moderación) | `POST /publico/reviews/{id}/reporte` · `review_reports`, `moderation_queue` |
| **REV-5** | Rating agregado con **ponderación bayesiana** | Debe | 2 | **ADR-0009** · `business_rating_stats`, `ranking_weights.bayes_m` y `bayes_c` |
| **REV-6** | Solicitud automática de opinión tras la cita | Debería | 1 (el evento en la cola) · 2 (activación, cuando ya hay dónde opinar) | ADR-0007 · `notifications` con clave `peticion_opinion:booking:{id}` |

### 2.9 Publicidad (ADS)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **ADS-1** | El negocio elige categoría × zona × periodo, ve precio, inventario y vista previa, y paga | Debe | 4 | `ad_products`, `ad_inventory`, `ad_campaigns` · sin endpoints todavía, declarado en el §7 del contrato |
| **ADS-2** | Inventario limitado (3 slots por defecto); si está lleno, siguiente periodo o lista de espera | Debe | 4 | `ad_inventory` con `CHECK (slots_taken <= slots_total)` y `UNIQUE (producto, categoría, zona, periodo)` · P12 |
| **ADS-3** | Pago inmediato, recibo, renovación automática opcional con aviso | Debe | 4 | `ad_campaigns.auto_renew`, `ad_campaigns.payment_id`, `payments`, `invoices` · pasarela D5 sin decidir |
| **ADS-4** | Métricas: impresiones, clics, reservas atribuidas y comparación con el orgánico | Debería | 4 | `ad_metrics_daily`, contrastado con `listing_impressions_daily` y `listing_clicks_daily` |
| **ADS-5** | Precios, inventario y reglas administrables; cupones y promociones | Debería | 3 (administración) · 4 (uso) | `ad_products` con vigencia, `coupons`, `coupon_redemptions` |
| **ADS-6** | Subasta / CPC, destacados en la home, push a clientes cercanos | — | **v2 — no se construye** | `ad_products.placement` solo admite `categoria_zona` en v1 |
| **ADS-7** | **El patrocinio nunca altera el rating ni oculta reviews** | Debe | 2 (se garantiza al construir el intercalado) | ADR-0009 · garantía del modelo: no existe ninguna columna que relacione `ad_campaigns` con `business_ranking_signals` ni con `reviews` |

### 2.10 Notificaciones (NTF)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **NTF-1** | WhatsApp (Meta Cloud API) como canal principal; push; correo. SMS solo como respaldo del OTP | Debe | 1 (WhatsApp y correo, con proveedor de desarrollo) · 5 (push) | D14 · **ADR-0007** · `notifications.channel` · **el registro de tokens de dispositivo para push no existe: §8** |
| **NTF-2** | Eventos: reserva creada, confirmada, cancelada, reprogramada, recordatorios de 24 h y 2 h, «¿cómo te fue?», invitación de staff, ads por vencer, cambios de plan, resumen diario | Debe | 1 (los de la fase) · 3 y 4 (plan y ads) | ADR-0007, ADR-0008 · `notifications`, `notification_templates` |
| **NTF-3** | Preferencias por usuario y negocio; plantillas administrables y aprobadas en Meta; español en v1 con i18n preparado | Debe | 1 (datos y preferencias) · 3 (administración) · **v2** (inglés) | `notification_preferences`, `notification_templates.locale` y `.provider_status`, `users.locale` |
| **NTF-4** | Cola con reintentos, registro de entregas y control de costes | Debe | 1 | ADR-0007, ADR-0008 · `notifications` con índice único de idempotencia e índice parcial de pendientes, `notification_deliveries.cost_minor` |

### 2.11 Pagos y facturación (PAY)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **PAY-1** | Motor de planes y suscripciones con estado por negocio, cambio de precio con fecha efectiva y aviso, grandfathering, gracia y suspensión. **Cuesta 0, pero el flujo de cobro existe y está probado** | Debe | 0 (modelo, Sprint 2) · 3 (motor) | **ADR-0010** · `plans` —un cambio de precio es una fila nueva, no un `UPDATE`—, `subscriptions`, `subscription_events` · garantía 7 de la constitution |
| **PAY-2** | Cobro de ads y suscripciones por pasarela panameña, con webhooks, conciliación, reintentos y recibos | Debe | 4 | D5 sin decidir (P2) · `payments`, `payment_provider_events`, `invoices` · **sin ADR de pasarela: §8** |
| **PAY-3** | Tokenización de la pasarela; **nunca almacenar datos de tarjeta** | Debe | 0 (invariante desde la primera migración) · 4 (aplicación) | Garantía 4 de la constitution · `payment_methods` guarda solo el token del proveedor |
| **PAY-4** | Datos fiscales (RUC / DV) en el recibo; factura DGI | Debe (RUC) | 1 (captura) · 4 (recibo) · **v2** (DGI) | D16 · `businesses.tax_id`, `businesses.tax_id_dv`, `invoices` |
| **PAY-5** | Cobro al cliente final (depósitos, pago anticipado) | — | **v2 — no se construye** | Hueco §14.4: `payments.payer_kind`, `payer_user_id`, `booking_id`, `purpose`; `bookings.deposit_*`; `business_settings.deposit_enabled = false` |
| **PAY-6** | USD / PAB, símbolo según D12, modelo multi-moneda | Debe | 0 (modelo) · 1 (uso) | D12 · `currency char(3)` en toda tabla de dinero, importes en unidades menores · `platform_settings` guarda el símbolo |

### 2.12 Back-office M2G (ADM)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **ADM-1** | Cuadro de mando: negocios registrados, publicados y activos, reservas por día, clientes, ingresos, funnel de onboarding, retención por cohortes | Debería | 3 | `businesses`, `bookings`, `subscriptions`, `listing_*_daily` · sin endpoints: `/api/v1/admin/…` es Fase 3 |
| **ADM-2** | Gestión de negocios: ver, editar, publicar y suspender, verificar, impersonar con auditoría y aviso | Debe | 3 | ADR-0006 · `businesses.status`, `.verified_at` · `audit_logs.impersonated_user_id`, `admin_sessions` |
| **ADM-3** | Moderación de reviews reportadas, fotos y perfiles | Debe | 3 | `moderation_queue`, `review_reports`, `reviews.status`, `business_media` |
| **ADM-4** | **Configuración sin desplegar código**: planes y precios, ads, taxonomías, pesos del ranking, plantillas, feature flags | Debe | 3 | ADR-0009, ADR-0010 · `plans`, `ad_products`, `zones`, `service_categories`, `attributes`, `ranking_weights`, `notification_templates`, `feature_flags`, `platform_settings` |
| **ADM-5** | Roles internos: superadmin, soporte, finanzas, moderación | Debe | 3 | `admin_users` con 2FA obligatorio, `admin_sessions`, rol de base de datos propio (§1.8 del modelo) |
| **ADM-6** | Auditoría de acciones; exportaciones CSV | Debe (auditoría) · Debería (CSV) | 3 | `audit_logs`, append-only y sin RLS de negocio · **la exportación CSV no está modelada ni contratada: §8** |
| **ADM-7** | Soporte: buscar usuario, negocio o reserva; reenviar notificación; forzar cancelación; ver el log | Debería | 3 | `notifications`, `notification_deliveries`, `booking_events`, `audit_logs` |

### 2.13 App nativa (APP)

| Código | Enunciado | Prioridad | Fase | Dónde se materializa |
|---|---|---|---|---|
| **APP-1** | iOS y Android desde una única base de código | Debe | 5 | D7 (Expo / React Native) · **sin ADR propio todavía: §8** |
| **APP-2** | Modo cliente: marketplace, reservas, favoritos, historial, push, ubicación | Debe | 5 | Reutiliza `/api/v1/publico/…` y `/api/v1/mi/…` · ADR-0012 (misma API para las tres superficies) |
| **APP-3** | Modo negocio: agenda, gestión de reservas, reserva manual, bloquear tiempo, ficha de cliente, push | Debe | 5 | D2 · reutiliza `/api/v1/negocio/…` |
| **APP-4** | Enlaces profundos universales | Debería | 5 | `businesses.slug`, `slug_redirects` (los enlaces indexados no se rompen) |
| **APP-5** | Tolerancia a red inestable: caché de la agenda del día, reintentos, estados optimistas | Debería | 5 | ADR-0012 (idempotencia en las escrituras) · **sin convenciones de caché ni validadores HTTP: §8** |
| **APP-6** | Publicación con las cuentas de M2G en las tiendas | Debe | 5 | D18 · P9 de descubrimiento (D-U-N-S, se pide con semanas de antelación) |

### 2.14 Recuento

| Corte | Requisitos |
|---|---|
| **Total del §5 del brief** | **83** |
| Se construyen (o empiezan) en las fases 0, 1 y 2 — este encargo | **56** |
| — de ellos, con su núcleo en las fases 0 y 1 | 37 |
| — de ellos, con su núcleo en la Fase 2 | 19 |
| Fase 3 (back-office, planes) | 8 · ADM-1…7 y el motor de PAY-1 |
| Fase 4 (ads y pasarela) | 8 · ADS-1…5, PAY-2, y las mitades de PAY-3 y PAY-4 |
| Fase 5 (app) | 7 · APP-1…6 y el canal push de NTF-1 |
| **v2 — no se construye, íntegros** | **8** · SRV-5, SRV-6, STF-4, AGD-7, RSV-8, RSV-9, ADS-6, PAY-5 |
| **v2 — la mitad de un requisito que sí se construye** | **8** · ONB-5 (sello), NEG-5 (multi-sede), SRV-2 (combinables), SRV-3 (override), STF-3 (recepción), RSV-6 (datos de salud), NTF-3 (inglés), PAY-4 (factura DGI) |

Ningún código del §5 se queda sin fila. Ese era el objetivo de la tabla y es lo único que la
justifica.

---

## 3. El MVP mínimo de la Fase 1

El criterio de la fase es literal y no admite lectura benévola: **«un salón real opera su agenda
entera desde un teléfono»**. No «los endpoints responden», no «la demo funciona». La prueba es que
el salón **tira el cuaderno**, y el cuaderno solo se tira cuando el producto cubre el día completo:
las citas que entran por la puerta, las que entran por teléfono, el almuerzo, el día que Yeimy no
viene, el que no se presentó y el que llamó para cambiar la hora.

De los treinta y siete requisitos que tocan las fases 0 y 1, **estos dieciséis son el mínimo
irreducible**. Quitar cualquiera de ellos no hace la Fase 1 más pequeña: la deja sin cumplir.

| # | Requisito | Por qué es imprescindible | Qué se rompe si falta |
|---|---|---|---|
| 1 | **ONB-1** Identidad por teléfono | Es el suelo de todo lo demás: sin cuenta no hay a quién atribuir el negocio, ni sesión que aislar, ni destinatario para un recordatorio | Sin sesión no hay multi-tenant: cualquier consulta necesita saber quién pregunta. La garantía 1 de la constitution no se puede ni plantear |
| 2 | **ONB-2** Alta autoservicio sin tarjeta | La tesis del producto es la densidad de negocios, y la densidad exige que nadie de M2G intervenga en el alta | Cada salón habría que darlo de alta a mano. El modelo de negocio deja de existir, no la funcionalidad |
| 3 | **ONB-6** Estados y mínimo para publicar | Separa el negocio a medio configurar del que está listo | Un salón sin horario ni servicios aparecería en la Fase 2 con una agenda vacía; el primer cliente que intente reservar se lleva la mala impresión y no vuelve |
| 4 | **NEG-1** (mitad de captura) datos, ubicación y **horario semanal** | El horario del negocio es la **primera entrada** de la fórmula de AGD-1 | Sin horario, el motor no tiene dominio sobre el que restar y devuelve o todo o nada |
| 5 | **SRV-1** Servicio con duración, precio y buffers | La duración y los buffers son la **segunda entrada** del motor; el precio es lo que el cliente compara | Sin duración no hay tamaño de hueco. Sin buffers, la agenda encaja citas pegadas y el peluquero llega tarde a todas desde la segunda |
| 6 | **SRV-3** Asignación servicio ↔ profesional | Es lo que hace que «cualquier profesional» no sea una mentira | Sin ella, el sistema ofrece un balayage con el barbero que solo corta. La primera vez que pasa, el salón deja de usarlo |
| 7 | **STF-1** Profesional con **horario propio**, descansos y vacaciones | El encargo lo dice sin rodeos: el profesional con horario distinto del negocio **es el caso normal, no la excepción** | Se ofrecen huecos en los que no hay nadie. Es el fallo que convierte una agenda en una fuente de reclamaciones |
| 8 | **STF-3** Permisos de dueño y profesional | El profesional ve su agenda; no ve las finanzas ni la configuración | No es una comodidad: es que el empleado vea la facturación del dueño. Se descubre el día que alguien mira, y para entonces ya pasó |
| 9 | **AGD-1** El motor de disponibilidad | Es **la** pieza. Todo lo demás son pantallas encima | Si el motor está mal, todo lo construido sobre él se rehace. Por eso tiene puerta propia y sus pruebas van antes que él |
| 10 | **AGD-3** Bloqueos puntuales y **recurrentes** | El almuerzo de todos los días es la regla, no la excepción | Sin recurrentes, el dueño bloquea el almuerzo a mano cada día. A la tercera semana vuelve al cuaderno |
| 11 | **AGD-4** Imposibilidad de doble reserva | Es garantía transaccional de la base de datos, no un `if` | Dos clientes a la misma hora con el mismo profesional. Una sola vez que ocurra basta para perder al salón: es el fallo que no se perdona |
| 12 | **AGD-5** UTC con la zona del negocio | Se decide una vez y para siempre; cambiarlo después toca todas las consultas | Cambiar el modelo de tiempo con reservas dentro es rehacer el motor. Y España, que ya está prevista, entraría por migración en vez de por configuración |
| 13 | **AGD-2** Vista día y semana **y reserva manual** | Hoy la mayoría de sus citas entran por la puerta y por teléfono, no por internet | Sin reserva manual el salón mantiene el cuaderno en paralelo. Y con dos agendas, la de verdad es siempre el cuaderno: el producto no se adopta |
| 14 | **RSV-2** Multi-servicio encadenado (D13) | Está aquí por una razón de ingeniería, no de producto: tres servicios seguidos exigen **un bloque continuo** de ocupación, no tres huecos sueltos | Si el motor nace pensando «una cita = un hueco», encadenar después no es añadir una función: es rediseñar la concurrencia, que es donde más caro sale equivocarse |
| 15 | **RSV-3** y **RSV-5** Ciclo de estados y no-show con contador | «Completada» es lo que habilita las opiniones y la tasa de completado del ranking; el contador de ausencias es la **única** defensa sin depósito | Sin «completada» la Fase 2 nace sin reputación que mostrar ni señal que ordenar. Sin contador de no-shows, el riesgo declarado del brief se queda sin mitigación |
| 16 | **NTF-1**, **NTF-2** y **NTF-4** Recordatorios sobre cola idempotente | El recordatorio de 24 h y el de 2 h son lo que baja las ausencias, y son también la parte que un salón nota de inmediato | Sin recordatorios sube el no-show y el salón concluye que el producto no le sirve. Y sin idempotencia, el recordatorio duplicado a las siete de la mañana es una queja, no un detalle |

**Lo que además es obligatorio aunque no sea del §5.** El **consentimiento explícito y el borrado de
cuenta desde dentro del producto** (Ley 81, §6 del brief) se construyen en el Sprint 6 y no al final.
No es celo legal anticipado: sin borrado de cuenta Apple rechaza la publicación en la Fase 5, y
retrofitear un borrado correcto sobre veinte tablas con datos vivos es exactamente el trabajo que
nadie quiere hacer con prisa.

**Lo que está en la Fase 1 pero no en el mínimo.** ONB-4 (invitación de profesionales —el hueco
crítico, el profesional «sin cuenta», ya lo cubre STF-1), ONB-7 (lista de progreso), SRV-2
(variantes), SRV-4 (categorías globales, que en la Fase 1 llegan por semilla), STF-2, STF-5, AGD-6
(feriados), RSV-4 en su mitad de negocio, RSV-6 (ficha de cliente) y NTF-3. Todos son **Debería** y
se construyen dentro de la fase; si el tiempo aprieta, se mueven **con dueño y fecha en el tablero**,
nunca en silencio. RSV-6 es el que menos margen tiene: la ficha de cliente es lo que sostiene el
«reservar de nuevo» de la Fase 2 y el contador de RSV-5 vive en ella.

---

## 4. El MVP de la Fase 2

El criterio, otra vez literal: **«un cliente encuentra un negocio y reserva sin que nadie le ayude,
y Google indexa los perfiles»**. Son dos afirmaciones y hay que leerlas por separado. La primera se
comprueba con **una persona ajena al equipo, con su propio teléfono y sin instrucciones**. La segunda
se comprueba mirando el **código fuente sin ejecutar JavaScript**: si el nombre, los servicios, los
precios y el horario no están ahí, Google tampoco los ve.

Estos diez son el mínimo. El resto de la fase es real y se construye, pero no es lo que decide el
criterio.

| # | Requisito | Por qué es imprescindible | Qué se rompe si falta |
|---|---|---|---|
| 1 | **MKT-7** SSR, metadatos, schema.org y sitemap | Es **la mitad literal del criterio**. Sin renderizado en servidor no hay marketplace, y sin marketplace no hay negocio (garantía 8) | La página existe para el usuario y no para Google. La mitad del tráfico —el que busca «barbería en San Francisco» y no el nombre del salón— nunca llega |
| 2 | **MKT-6** Taxonomía de zonas | Es la que da la URL indexable y la que hace que «en Bella Vista» signifique algo consultable | Sin zonas no hay páginas categoría × zona, que son justamente las que capturan la búsqueda genérica. Solo quedarían los perfiles, que capturan la búsqueda por nombre: la que ya te conocía |
| 3 | **NEG-4** Slug estable con redirección | Es la dirección que Google indexa y la que va en la bio de Instagram | Un slug que cambia rompe enlaces ya indexados y ya circulando por WhatsApp. Recuperar posicionamiento perdido cuesta meses |
| 4 | **NEG-1** (mitad pública) y **NEG-3** Perfil completo con botón de reservar siempre visible | Es lo que Google indexa y lo que el desconocido lee antes de decidir | Un perfil sin servicios y precios no convierte: el cliente vuelve a la búsqueda. Y sin botón visible en todo el scroll, la reserva se pierde a mitad de la página |
| 5 | **MKT-1** Búsqueda por texto, categoría y ubicación, en lista y mapa | Es el «encuentra» del criterio | Sin búsqueda, el marketplace es un directorio al que hay que llegar sabiendo la dirección |
| 6 | **MKT-2** Filtros, con **disponibilidad real** | El filtro que decide es «¿tiene hueco hoy?». Y obliga a que búsqueda y motor de la Fase 1 den la misma respuesta | Sin disponibilidad real el cliente entra en cinco perfiles hasta encontrar uno con hueco. Ese es el punto exacto donde abandona |
| 7 | **MKT-3** Ranking con pesos configurables y **boost a los nuevos** | Con 5.000 negocios, un orden arbitrario es ruido; y sin boost, el marketplace **nace cerrado para los que llegan**, que el primer día son todos | Sin orden, la primera página es aleatoria y el cliente no confía. Sin boost, ningún negocio nuevo se ve nunca y la densidad —la tesis entera— no arranca |
| 8 | **RSV-1** Reserva del cliente en **3 pantallas** tras elegir servicio, con teléfono verificado | Es el «reserva sin que nadie le ayude» | Cada pantalla de más es abandono medible. Y sin teléfono verificado (D9) el control de ausencias se queda sin base y habría que pedir depósito, que es v2 |
| 9 | **RSV-4** Cancelación por el cliente con la **política visible antes de reservar** | Es requisito legal —la política de cancelación se muestra **antes**, no después— y es lo que hace que el desconocido se atreva a confirmar | Sin política visible antes, incumplimiento. Sin cancelación propia, cada cambio de hora se convierte en una llamada al salón: exactamente lo que el producto venía a quitar |
| 10 | **ADS-7** y la regla de intercalado de **MKT-4** | La regla se construye **ahora**, con el inventario vacío, aunque la publicidad de pago sea la Fase 4 | Si el intercalado se monta en la Fase 4 sobre un ranking ya escrito, la tentación de «que el patrocinado puntúe un poco más» aparece con dinero de por medio. Con el mecanismo hecho antes, el patrocinio **no puede** tocar el rating: no hay columna que los una |

**Lo que está en la Fase 2 y no en el mínimo, dicho sin adornos.** Las opiniones (REV-1 a REV-5) son
**Debe** de la fase y se enseñan en su puerta, pero el criterio literal se cumple sin ellas: un
cliente encuentra y reserva aunque no haya ninguna opinión escrita, y la valoración bayesiana
degrada limpiamente a la media global sembrada mientras no haya reseñas. Se construyen dentro de la
fase por dos razones concretas: **REV-5 alimenta MKT-3** —sin rating, una de las seis señales del
ranking está muerta— y **REV-1 depende del estado «completada»** que la Fase 1 ya produce, así que el
coste de hacerlo ahora es el más bajo que va a tener. Igual pasa con MKT-5 (favoritos), MKT-8
(tracking), RSV-7 (historial y `.ics`), NEG-2 (atributos filtrables) y REV-6: **Debería**, dentro de
la fase, fuera del mínimo.

**Y una advertencia sobre el orden.** MKT-3 se enuncia como «ajustable desde el back-office», pero el
back-office es la Fase 3. En la Fase 2 el ajuste de los pesos se hace **insertando una fila en
`ranking_weights`**, no desde un panel. Eso cumple el fondo del requisito —ningún número de ranking
en el código— y deja pendiente la forma. Lo mismo vale para las taxonomías de SRV-4 y MKT-6, que en
las fases 1 y 2 llegan por migración y semilla y solo se vuelven administrables en la 3.

---

## 5. Lo que es v2 y NO se construye

Lo marcado v2 en el brief no se construye: **no hay tarea, no hay endpoint, no hay pantalla y no hay
prueba.** Lo único que existe es el hueco en el modelo de datos, y solo donde dejarlo cuesta nada.
La regla que gobierna esto está en el §14 del modelo y es de una línea: **una columna hoy cuesta
nada; una migración con datos vivos, mucho.**

### 5.1 Los cinco huecos que el encargo pidió explícitamente

| Qué es v2 | Requisito | Qué lo prepara hoy | Qué se hace en v2 |
|---|---|---|---|
| **Multi-sede** | NEG-5 | `locations` es **tabla propia** (no columnas dentro de `businesses`), `locations.timezone` nulable, `location_id` nulable en `business_hours`, `staff_hours`, `services` y `bookings`, y el índice `locations_una_principal` que impone «una sede» | Se **elimina el índice único** y se rellenan cuatro columnas. Lo caro que se evita es haber metido dirección, punto geográfico y zona dentro de `businesses` |
| **Recursos físicos** | SRV-5 | Ningún campo nuevo, a propósito: lo que prepara es la **forma**. `staff_occupancy` es genérica (`kind`, buffers copiados, columnas generadas y exclusión GiST), el motor consume «fuentes de ocupación» y no una tabla, y `booking_items` ya existe | Aparece `resource_occupancy` con la misma forma más `resources` y `service_resource_requirements`. Nada de lo existente se toca |
| **Profesional en varios negocios** | STF-4 / D17 | `staff_profiles.user_id` nulable y no clave, `staff_occupancy.staff_user_id` nulable (poblada y hoy sin usar), y la exclusión declarada **por `staff_id` solo**, sin `business_id` | Se añade una segunda exclusión sobre la persona. Sin la columna habría que rellenar millones de filas con bloqueos largos sobre la tabla más caliente; y con la exclusión mal declarada, reconstruirla con datos vivos **falla** y se convierte en un incidente |
| **Depósitos y cobro al cliente final** | PAY-5 | `payments.payer_kind` polimórfico (`negocio` \| `cliente`), `payer_user_id` y `booking_id` nulables, `purpose` con `deposito_reserva`, `payment_methods.user_id`, `bookings.deposit_*`, `services.deposit_amount_minor`, `business_settings.deposit_enabled = false` | Se encienden columnas que ya existen. Lo caro que se evita es tener que **migrar la tabla de dinero** —con historial fiscal, conciliaciones y recibos dentro— para relajar una `NOT NULL` |
| **Rol de recepción** | STF-3 | `recepcion` está en el `CHECK` de `memberships.role` desde la primera migración, los permisos se resuelven en un solo módulo por el par (rol, acción), y el token **no lleva permisos** | Se le escribe su fila en la matriz de permisos. Aquí lo caro no es la migración: es el **contrato de la API**, porque añadir un valor a un enumerado que una app ya instalada interpreta rompe compatibilidad (ADR-0012) |

### 5.2 Lo demás que es v2, con y sin hueco

| Qué es v2 | Requisito | Estado del hueco |
|---|---|---|
| Sello «Verificado» con documento o RUC | ONB-5 | **Cubierto** · `businesses.verified_at`, hoy siempre `NULL` |
| Opciones combinables de servicio | SRV-2 | **Cubierto** · `service_variants` admite crecer sin migrar la reserva |
| Override de precio y duración por profesional | SRV-3 | **Cubierto** · `staff_services` es tabla de unión con sitio para columnas propias |
| Datos de salud del cliente, con consentimiento | RSV-6 | **Deliberadamente sin hueco** · `client_profiles` es flaco a propósito: son datos sensibles bajo la Ley 81 y no se recogen «ya que estamos» |
| Inglés | NTF-3 y §6 | **Cubierto** · `notification_templates.locale`, `users.locale`, `service_categories.seo_*`, y todos los textos externalizados desde el primer componente (Sprint 3) |
| Factura DGI | PAY-4 / D16 | **Cubierto** · `invoices` y `businesses.tax_id` / `tax_id_dv` |
| Subasta, CPC, destacados en home y push a cercanos | ADS-6 | **Cubierto** · `ad_products.placement`, que en v1 solo admite `categoria_zona` |
| **Paquetes, combos y promociones** | SRV-6 | **Sin hueco declarado.** `booking_items` (varias líneas por cita) y `coupons` cubren parte; falta la entidad «paquete» · §8 |
| **Lista de espera** | RSV-8 | **Sin hueco declarado** · §8 |
| **Reservas recurrentes** | RSV-9 | **Sin hueco declarado** · §8 |
| **Google Calendar** | AGD-7 | **Sin hueco declarado.** `booking_events` y el `.ics` de RSV-7 son la base natural · §8 |

Y lo del §11 del brief que ni siquiera llega a requisito codificado —POS y caja, inventario, nómina y
comisiones, email marketing, fidelidad y gift cards, venta de productos— **no tiene ni hueco ni
mención**, y así debe seguir. La constitution lo dice en su §1: no se construye «ya que estamos».

### 5.3 La regla operativa

**Nada de esta sección puede aparecer en ningún `TAREAS.md`.** Ni como tarea bloqueada, ni como
«pendiente para más adelante», ni como comentario en una tarea de otra cosa. Un `TAREAS.md` es la
lista de lo que se va a construir; meter ahí lo que no se va a construir convierte el tablero en una
lista de deseos y deja de servir para saber qué falta.

Lo único legítimo es **la tarea que deja el hueco**, que es otra cosa: `ARQ-T003` («los huecos de v2
nombrados uno a uno») y `BE-T004` («hueco para `recepcion`») son correctas porque construyen la
columna, no la función. Comprobado hoy: **no existe en ningún `TAREAS.md` del repositorio ninguna
tarea que construya una función v2.** Esa comprobación se repite en cada puerta de fase, y es
criterio de rechazo de QA, no una recomendación.

---

## 6. Los no funcionales del §6, convertidos en comprobaciones

**Un no funcional que no se puede comprobar es una intención, no un requisito.** «Rendimiento
adecuado» no es verificable; «la búsqueda responde por debajo de 500 ms en el percentil 95 con 5.000
negocios sembrados, medido con este comando y anotado con este número» sí lo es. Lo que sigue
convierte cada línea del §6 en algo que alguien concreto puede comprobar en un momento concreto, y
dice sin rodeos cuáles **hoy no se pueden comprobar** y qué se propone en su lugar.

### 6.1 Los que ya son verificables y están en el plan

| No funcional | Criterio verificable | Cómo se comprueba | Quién · cuándo |
|---|---|---|---|
| **Multi-tenant lógico**, autorización a nivel de fila en todos los endpoints | Fijado el negocio A, ninguna consulta a ninguna tabla devuelve una fila de B. Y **ninguna tabla con datos de negocio existe sin su política** | Dos pruebas automáticas: la de aislamiento cruzado, y la que recorre el catálogo de PostgreSQL y falla si aparece una tabla con `business_id` sin política. La primera debe **fallar si se le quita la política a mano** a una tabla: si no falla, no está probando nada | `agenda-testing` escribe · `agenda-qa-validador` valida · Sprint 2 y en cada sprint posterior |
| **Disponibilidad p95 < 300 ms** | El cálculo de un día completo sobre el conjunto de ejemplo, medido en el percentil 95 y **con el número anotado** | Medición repetida contra PostgreSQL real con el seed cargado; el número va al tablero, no a la conversación | `agenda-backend` mide · Sprint 5, criterio de la puerta del motor |
| **Búsqueda p95 < 500 ms** | «Barbería cerca» con posición del móvil, ordenada por cercanía, **con 5.000 negocios sembrados** | Medición sobre el seed ampliado; sin ese volumen la medición no significa nada y medir sobre veinte negocios es el riesgo declarado del plan | `agenda-backend` mide, `agenda-devops` siembra el volumen · Sprint 11 |
| **No hay doble reserva** | Dos transacciones simultáneas contra PostgreSQL real sobre el mismo hueco: una gana, la otra recibe `409 SLOT_NO_DISPONIBLE` | Prueba de concurrencia real, no simulada. Y la contraprueba: **quitando la restricción de la base, la prueba falla**. Eso es lo que demuestra que la garantía la da Postgres y no un `if` | `agenda-testing` · Sprints 4 y 5 |
| **Lighthouse móvil ≥ 90** | La medición en móvil de la página de perfil da 90 o más | Lighthouse en modo móvil, **en cada entrega de la Fase 2 y no al cerrarla**; el número se anota | `agenda-frontend-web` mide · `agenda-qa-validador` valida · Sprint 10 en adelante |
| **SSR indexable** | Al pedir el perfil y mirar el código fuente **sin ejecutar JavaScript**, están el nombre, los servicios, los precios y el horario. Los datos estructurados pasan el validador de Google | `curl` del HTML crudo más el validador de schema.org. El sitemap contiene los perfiles publicados y las combinaciones con negocios, **y ninguna más** | `agenda-frontend-web` · `agenda-testing` para el sitemap · Sprint 10 |
| **Ningún teléfono expuesto** | En el código fuente de cualquier página pública y en cualquier respuesta de API sin autorizar **no aparece ningún número** | Prueba que recorre los serializadores públicos y falla si alguno declara un campo de contacto, más inspección del HTML servido. El click-to-chat se resuelve en servidor y deja su clic en `listing_clicks_daily` | `agenda-seguridad-compliance` · Sprints 9 y 10 |
| **Jobs idempotentes** | Ejecutar el planificador dos veces seguidas produce **un** mensaje, y se puede enseñar la fila de la cola que lo demuestra | El índice único sobre `notifications.idempotency_key` convierte el segundo encolado en un conflicto que no inserta. La prueba lo ejecuta dos veces y cuenta filas | `agenda-testing` · Sprint 9 |
| **Ley 81 y borrado de cuenta** | Borrar la cuenta desde dentro del producto **borra lo que hay que borrar y anonimiza lo que tiene que quedarse**, tabla por tabla según el §15 del modelo; y el consentimiento queda registrado con su finalidad y su versión | Prueba que ejecuta el borrado sobre un usuario con reservas, opiniones y notificaciones, y verifica la tabla de verbos entera (borrar / anonimizar / conservar). El trabajo es idempotente: ejecutarlo dos veces da el mismo resultado | `agenda-seguridad-compliance` define · `agenda-testing` prueba · Sprints 2 y 6 |
| **Español con strings externalizados** | **Ni una cadena de texto escrita directamente en un componente** | Regla de lint que falla ante un literal de texto en JSX, más revisión en la puerta del Sprint 3 | `agenda-frontend-web` · `agenda-qa-validador` · Sprint 3 |
| **Localización `America/Panama` + USD** | La misma prueba, ejecutada **con el reloj del proceso en otra zona**, da el mismo resultado | El corredor de pruebas fija el reloj en UTC a propósito, para que un despiste de huso no pase desapercibido. El símbolo de moneda sale de `platform_settings`, no del código | `agenda-testing` · Sprint 4 |
| **Mobile-first** | Todo criterio de «hecho» de interfaz se comprueba **a 390 px, en el navegador, con capturas** | Verificación en vivo. «Build verde» no es evidencia: la CSP, el runtime y el diseño no salen ahí, y ese fallo ya se ha colado antes en la casa | `agenda-qa-validador` · en cada sprint con interfaz |
| **Calidad: E2E de los seis recorridos** | Registrar negocio, publicar, reservar, cancelar, opinar y comprar ads, de punta a punta | Los cinco primeros se automatizan en las fases 1 y 2; **el sexto no se puede escribir hasta la Fase 4** y queda anotado como pendiente con su fase, no como olvido | `agenda-testing` · Sprints 6 a 14 |

### 6.2 Los que hoy son una intención y hay que convertir en requisito

Estos cinco están enunciados en el §6 del brief pero **no tienen hoy ninguna comprobación en ningún
criterio de «hecho» del plan**. Se dicen aquí tal cual, con la comprobación concreta que se propone.

| No funcional | Por qué hoy no es verificable | Comprobación que se propone | Quién |
|---|---|---|---|
| **Escala v1: 5.000 negocios, 100.000 clientes, 50.000 reservas/mes sin rediseño** | El plan solo siembra **5.000 negocios** (Sprint 11). Los 100.000 clientes y las 50.000 reservas mensuales no se siembran en ningún sitio, así que la parte de la escala que afecta a la **agenda** —que es la tabla que más crece— no se mide nunca | Ampliar el seed a un mes de reservas realista (≈ 50.000 filas en `staff_occupancy` y `bookings`) y volver a medir **la disponibilidad** con ese volumen, no solo la búsqueda. Es la medición que de verdad puede sorprender: la exclusión GiST se evalúa en cada inserción | `agenda-devops` siembra · `agenda-backend` mide · añadir al Sprint 11 |
| **«Panel usable en gama media con 3G / 4G»** | No hay ningún número. «Usable» no es comprobable, y una agenda que va bien en un portátil puede tardar ocho segundos en un móvil de 120 dólares | Fijar un **presupuesto de peso** para la pantalla de agenda —JavaScript transferido y tiempo hasta interactivo— y medirlo con Lighthouse en móvil **con estrangulamiento de red y de CPU**, no solo con el 90 global. Un número, anotado, que se pueda comparar entre entregas | `agenda-frontend-web` · Sprints 8 y 10 |
| **Fiabilidad 99,5 % y backups con restauración probada** | **Este equipo no despliega**, así que ni la disponibilidad ni los backups de producción se pueden comprobar aquí. Y el precedente de la casa es feo: los backups de otro proyecto llevaban meses rotos sin que nadie lo notara | Partir el requisito en dos. Lo verificable aquí: los jobs idempotentes (ya está) y un **procedimiento de restauración escrito y probado contra el Compose local** —volcar, borrar la base, restaurar, y comprobar que el seed y las migraciones cuadran—. Lo que no: el 99,5 % medido y el backup de producción, que son de Luis y su infraestructura, y quedan anotados como tales | Equipo: la restauración local, Sprint 1 · Luis: la disponibilidad y el backup real |
| **OWASP Top 10 y dependencias auditadas** | «Cumplir OWASP» no es comprobable: es una lista de categorías, no una prueba | Convertirlo en una lista corta y ejecutable: autorización por fila probada (ya está), ausencia de referencia directa a objetos ajenos —pedir el recurso de otro negocio devuelve error de permiso, no datos—, límite de peticiones en los endpoints públicos y en el OTP, cabeceras de seguridad y CSP **comprobadas en el navegador y no con `curl`**, y `pnpm audit` / auditoría de dependencias de Python **en el corredor local, fallando la ejecución** ante vulnerabilidad alta | `agenda-seguridad-compliance` define la lista · `agenda-testing` la automatiza |
| **Observabilidad: logs, métricas, alertas, Sentry, health checks** | Sentry necesita una credencial que hoy no existe, y las alertas viven en la infraestructura, que no es de este equipo | Lo verificable en local: **logs estructurados** con identificador de petición y de negocio, `/health` respondiendo en el Compose, y las métricas de las dos operaciones que importan —disponibilidad y búsqueda— expuestas. Sentry queda **detrás de una variable documentada** en `.env.example` y anotado como no verificado, con su dueño | `agenda-devops` y `agenda-backend` · Sprint 1 y Sprint 9 |
| **Accesibilidad WCAG AA en los flujos de reserva** | El contraste ya se comprueba en el Sprint 3, pero AA es bastante más que contraste, y hoy no hay nada que compruebe lo demás | Añadir tres comprobaciones al recorrido de reserva y al de agenda: analizador automático de accesibilidad sin infracciones serias, **recorrido completo solo con teclado** (incluido el selector de hora, que es el componente que más se rompe) y etiquetas accesibles en los campos del formulario de reserva. El objetivo táctil de 44 px y el cuerpo de 16 px ya son tokens y se verifican ahí | `agenda-frontend-web` · `agenda-qa-validador` · Sprints 8 y 13 |

---

## 7. Contradicciones detectadas entre brief, plan y contratos

No son errores graves, pero **están sin resolver y conviene decidirlos antes de construir**, porque
cada uno se resuelve en un sitio distinto y ninguno se resuelve solo.

1. **Las reservas del cliente están etiquetadas en dos fases distintas.** El §5 de
   [`fase-3-contratos-api.md`](fase-3-contratos-api.md) titula «Disponibilidad y reservas — **Fase
   1**» e incluye `POST /mi/reservas`, `GET /mi/reservas`, `/cancelar` y `/reprogramar`; el
   [plan de sprints](fase-5-plan-de-sprints.md) construye la reserva del cliente en el **Sprint 13,
   Fase 2**. Este documento sigue al plan —RSV-1, RSV-4 (lado cliente) y RSV-7 quedan en Fase 2— y
   propone la lectura que reconcilia las dos: los endpoints `/mi/reservas*` pueden existir desde la
   Fase 1 porque el motor y el ciclo de estados ya están, pero **la superficie que los usa es de la
   Fase 2**. Si se prefiere lo contrario, hay que cambiar el plan, no la tabla.
2. **Hay un endpoint público en la Fase 1 y el límite de peticiones llega en la Fase 2.**
   `GET /publico/negocios/{slug}/disponibilidad` no lleva autorización y aparece en la sección de
   Fase 1, mientras que los límites que protegen la base de negocios frente al raspado se construyen
   en el Sprint 11. Es una ventana real: hay que **adelantar el límite de peticiones a ese endpoint**
   en cuanto exista, no cuando llegue la búsqueda.
3. **ONB-6 define el estado «suspendido» en la Fase 1 y nadie puede suspender hasta la Fase 3.** La
   acción vive en ADM-2. Mientras tanto, suspender es una sentencia SQL. No es un problema si está
   escrito; es un problema si el día que haga falta nadie sabe cómo se hace.
4. **REV-6 aparece en el Sprint 9 (Fase 1) y en el Sprint 14 (Fase 2).** En la Fase 1 el mensaje de
   «¿cómo te fue?» llevaría a una pantalla que todavía no existe. La resolución que este documento
   asume: el **evento se encola** en la Fase 1 —está en la lista de eventos del sprint— y el envío se
   **activa** en la Fase 2, cuando ya hay dónde escribir la opinión. Si no, es un mensaje que lleva a
   ninguna parte, que es peor que no mandarlo.
5. **MKT-3 dice «ajustable desde back-office» y el back-office es la Fase 3.** Ya está explicado en
   el §4: en la Fase 2 el ajuste es una fila en `ranking_weights`. El fondo del requisito —ningún
   número de ranking en el código— se cumple; la forma llega después. Lo mismo con SRV-4, MKT-6 y
   NEG-2, cuyas taxonomías se administran en la Fase 3 pero se usan desde la 1 y la 2.

---

## 8. Requisitos sin cubrir todavía

Lo que **ningún ADR, ningún endpoint y ninguna tabla cubre a día de hoy**. Se dice aquí en vez de
disimularlo, porque un requisito que solo existe en el brief y en esta tabla es un requisito que
alguien va a descubrir tarde. Cada uno lleva su fase y su tamaño real: casi todos son pequeños, y
por eso mismo no hay excusa para dejarlos sin nombre.

| Requisito | Qué falta exactamente | Fase en que hace falta | Tamaño |
|---|---|---|---|
| **NEG-4 · QR descargable** | El slug está resuelto y el Sprint 10 menciona el QR, pero **no hay endpoint en el contrato ni decisión** de si se genera en el servidor (`GET /negocio/qr`, con logotipo y tamaño para impresión) o en el cliente. No es lo mismo: un QR para pegar en la puerta del salón se imprime, y un PNG de 200 px pixelado en un cartel es una queja | 2 | Pequeño. Una decisión y un endpoint |
| **NTF-1 · canal push** | `notifications.channel` admite `push` y `destination` puede guardar un token, pero **no existe ninguna tabla ni endpoint que registre el token de dispositivo** de un usuario, ni ADR que decida el proveedor (FCM / APNs, o Expo por encima). Sin registro de dispositivos, el canal push no puede existir | 5, pero la tabla es barata ahora | Pequeño hoy, incómodo después: es una tabla nueva con datos de sesión vivos |
| **APP-1 a APP-6 · sin ADR** | D7 fija Expo / React Native como valor por defecto, y hay agente `agenda-movil` con sus tareas, pero **no hay ningún ADR de la app**: ni de estrategia de actualización por aire, ni de almacenamiento seguro de la sesión en el dispositivo, ni de qué comparte con la web más allá de los tokens de diseño | 5 | Mediano. Es un ADR, y toca escribirlo antes de la Fase 5, no durante |
| **APP-5 · caché y estados optimistas** | ADR-0012 fija idempotencia en las escrituras, que es la mitad difícil, pero **no fija validadores de caché HTTP** (`ETag`, `If-None-Match`, `Cache-Control`) para las lecturas. Sin ellos, «caché de la agenda del día» se implementa a mano en la app y cada pantalla lo resuelve a su manera | 5 | Pequeño si se decide ahora, en el mismo ADR-0012 o en uno que lo supere |
| **PAY-2 · sin ADR de pasarela** | El esquema de `payments` es agnóstico a propósito y eso está bien resuelto, pero **no hay ADR** que fije el contrato interno de cobro: qué interfaz implementa un proveedor, cómo se verifican y se deduplican los webhooks, y cómo se concilia. La elección concreta es de Luis (D5, P2); la **forma** no depende de él y se puede escribir ya | 4 | Mediano. No bloquea nada hoy, pero escribirlo tarde significa escribirlo con prisa y con dinero real de por medio |
| **ADM-6 · exportaciones CSV** | La auditoría está resuelta con `audit_logs`, pero **la exportación CSV no está modelada ni contratada**. Y no es un botón: una exportación de negocios o de reservas es una operación pesada, con datos personales dentro, que necesita generarse en segundo plano, entregarse con enlace caducable y quedar registrada en la auditoría — exactamente el patrón que ya existe para `privacy_requests.artifact_key` | 3 | Pequeño si se reutiliza ese patrón; feo si se resuelve con un `SELECT` síncrono |
| **SRV-6, RSV-8, RSV-9, AGD-7 · v2 sin hueco** | Paquetes y combos, lista de espera, reservas recurrentes y Google Calendar son v2 y **no tienen hueco declarado** en el §14 del modelo. Es coherente con el encargo, que solo pidió cinco huecos concretos, pero conviene decir cuál de los cuatro dolería. **Lista de espera y reservas recurrentes son inofensivas**: son tablas nuevas que cuelgan de `bookings` sin tocarla. **Paquetes sí importa**: si un paquete acaba siendo «un servicio raro» en lugar de una entidad propia sobre `booking_items`, se paga en la Fase 6 | v2 / Fase 6 | Ninguno hoy. Solo dejarlo dicho |

**Ninguno de estos siete bloquea la Fase 0, la 1 ni la 2.** Los tres primeros que conviene mover ya,
por orden: la tabla de tokens de dispositivo (es barata hoy y cara con usuarios), el ADR de la app
(porque la Fase 5 depende de credenciales que tardan semanas) y la decisión del QR (porque es de una
tarde y está en el alcance del Sprint 10).

Todo lo de esta sección va al tablero con su estado y su dueño **en la misma sesión** en que este
documento se cierra. Nada pendiente solo en prosa, tampoco la de este documento.
