# Contratos de API — fases 1 y 2

> **Estado:** en proceso (Fase 0 · diseño; el contrato definitivo lo genera FastAPI y vive en `/api/v1/openapi.json`)
>
> Este documento es el **mapa acordado antes de construir**: qué endpoints existen, quién puede llamarlos y qué requisito del brief cubre cada uno. Las convenciones (versionado, errores, paginación, idempotencia, enumerados) están en [ADR-0012](adr/0012-api-rest-versionada-y-contrato-openapi.md) y no se repiten aquí.

---

## 1. Las tres audiencias de la misma API

Un endpoint pertenece siempre a una de estas tres, y eso determina qué autorización lleva:

| Audiencia | Prefijo | Quién | Autorización |
|---|---|---|---|
| **Pública** | `/api/v1/publico/…` | Cualquiera, incluido el rastreador de Google | Ninguna. Solo datos publicables: **nunca teléfonos, correos ni datos de clientes** |
| **Cliente** | `/api/v1/mi/…` | Persona autenticada actuando como cliente | Sesión de usuario |
| **Negocio** | `/api/v1/negocio/…` | Dueño o profesional del negocio activo | Sesión de negocio; fija `app.current_business_id` (ADR-0002) y comprueba el rol |

El back-office de M2G (`/api/v1/admin/…`) es Fase 3 y usa su propio rol de base de datos.

**La regla que evita el accidente:** un endpoint público **no puede** compartir serializador con uno de negocio. Los serializadores públicos se declaran aparte, y una prueba comprueba que ninguna respuesta pública contiene campos de contacto.

---

## 2. Identidad y sesión — Fase 1

| Método y ruta | Qué hace | Requisito |
|---|---|---|
| `POST /auth/otp/solicitar` | Envía un código al teléfono por WhatsApp. Limitado por teléfono y por IP | ONB-1 |
| `POST /auth/otp/verificar` | Canjea el código por sesión. Crea el usuario si no existía | ONB-1 |
| `POST /auth/social/{google\|apple}` | Inicio de sesión social. Enlaza a la cuenta existente **solo** si el correo viene verificado | ONB-1 |
| `POST /auth/refrescar` | Rota el refresco. Reutilizar uno ya rotado invalida la familia entera | ADR-0006 |
| `POST /auth/cerrar-sesion` | Revoca el refresco de este dispositivo | — |
| `GET /mi/perfil` · `PATCH /mi/perfil` | Datos del usuario | — |
| `POST /mi/contexto/negocio` | Cambia a «modo negocio»: devuelve una sesión con el negocio activo | ONB-3 |
| `DELETE /mi/cuenta` | **Borrado de cuenta desde la app.** Borra y anonimiza según la política del modelo de datos | Ley 81 |

---

## 3. Alta y perfil del negocio — Fase 1

| Método y ruta | Qué hace | Requisito |
|---|---|---|
| `POST /negocios` | Alta self-service, sin tarjeta. Crea negocio en `borrador`, membresía de dueño y suscripción al plan Gratis | ONB-2, PAY-1 |
| `GET` · `PATCH /negocio/perfil` | Nombre, descripción, categorías, redes, WhatsApp | NEG-1 |
| `PUT /negocio/ubicacion` | Dirección, pin en el mapa y zona (sugerida, editable) | NEG-1, MKT-6 |
| `PUT /negocio/horario` | Horario semanal. **Avisa de las reservas que quedarían fuera; no las borra** | AGD-2, caso 4 del motor |
| `GET` · `PUT /negocio/ajustes` | Granularidad, antelación mínima y máxima, auto-confirmación, ventana de cancelación | AGD-1, RSV-4, D10 |
| `POST /negocio/media` · `DELETE …/{id}` | Portada y galería | NEG-1, D11 |
| `GET /negocio/checklist` | Progreso del perfil y qué falta para publicar | ONB-7 |
| `POST /negocio/publicar` | Publica. **Rechaza si falta el mínimo**: un servicio activo, horario, ubicación y una foto | ONB-6, D11 |

---

## 4. Servicios y equipo — Fase 1

| Método y ruta | Qué hace | Requisito |
|---|---|---|
| `GET` · `POST` · `PATCH` · `DELETE /negocio/servicios[/{id}]` | Nombre, categoría global, duración, precio (fijo, «desde» o a consultar), **buffers antes y después**, foto, orden, activo | SRV-1 |
| `GET` · `POST` · `PATCH /negocio/servicios/{id}/variantes` | Variantes con precio y duración propios | SRV-2 |
| `GET /catalogo/categorias` | Categorías globales de M2G (público, cacheable) | SRV-4 |
| `GET` · `POST` · `PATCH /negocio/profesionales[/{id}]` | Ficha, activo, visible en el marketplace | STF-1, STF-2 |
| `PUT /negocio/profesionales/{id}/servicios` | Qué presta cada quien | SRV-3 |
| `PUT /negocio/profesionales/{id}/horario` | Horario propio, **distinto del negocio: es el caso normal** | STF-1 |
| `POST /negocio/profesionales/{id}/invitacion` | Invita por WhatsApp o correo. También existe el profesional «sin cuenta» | ONB-4 |
| `GET` · `POST` · `DELETE /negocio/bloqueos[/{id}]` | Bloqueos puntuales y recurrentes: almuerzo, día libre, vacaciones | AGD-3 |

---

## 5. Disponibilidad y reservas — Fase 1

Es el corazón. El diseño está en [`fase-3-motor-disponibilidad.md`](fase-3-motor-disponibilidad.md).

| Método y ruta | Qué hace | Requisito |
|---|---|---|
| `GET /publico/negocios/{slug}/disponibilidad` | Huecos para uno o varios servicios en un **rango de fechas**, con profesional concreto o «cualquiera». Devuelve slots con el profesional asociado y la zona horaria del negocio. **Nunca promete: informa** | AGD-1, STF-5 |
| `POST /mi/reservas` | Crea la reserva. **Transaccional**; acepta `Idempotency-Key`; devuelve `409 SLOT_NO_DISPONIBLE` si el hueco se acaba de ocupar | RSV-1, AGD-4 |
| `GET /mi/reservas` · `GET /mi/reservas/{id}` | Historial y detalle. Incluye `.ics` para añadir al calendario | RSV-7 |
| `POST /mi/reservas/{id}/cancelar` | Cancela hasta la ventana configurada (default 2 h); después, solo el negocio | RSV-4 |
| `POST /mi/reservas/{id}/reprogramar` | Libera el hueco viejo y ocupa el nuevo **en la misma transacción**; si el nuevo falla, no se libera el viejo | RSV-3 |
| `GET /negocio/agenda` | Vista de día o semana por profesional. Una petición por rango, no una por día | AGD-2 |
| `POST /negocio/reservas` | **Reserva manual** (walk-in o teléfono), con cliente registrado o «cliente rápido» de nombre y teléfono | AGD-2 |
| `PATCH /negocio/reservas/{id}` | Mover, reprogramar, cambiar servicio | AGD-2 |
| `POST /negocio/reservas/{id}/estado` | `confirmada`, `completada`, `no_show`, `cancelada_negocio`. Cada cambio deja evento | RSV-3, RSV-5 |
| `GET` · `PATCH /negocio/clientes[/{id}]` | Ficha del cliente **en este negocio**: historial, notas, contador de no-shows | RSV-6, RSV-5 |

**Forma de un slot devuelto:** instante de comienzo con desplazamiento explícito, duración total, profesional y precio calculado. **No lleva identificador reservable ni «bloqueo temporal»**: el slot no se aparta, se compite por él al confirmar (ADR-0004).

---

## 6. Marketplace — Fase 2

| Método y ruta | Qué hace | Requisito |
|---|---|---|
| `GET /publico/buscar` | Texto, categoría, ubicación (punto o zona), y filtros: distancia, precio, rating, atributos, **disponibilidad real** («ahora», «hoy», una fecha), abierto ahora, métodos de pago. Paginación por cursor. Devuelve orgánicos con **patrocinados intercalados y etiquetados** | MKT-1, MKT-2, MKT-4 |
| `GET /publico/negocios/{slug}` | Perfil completo publicable: servicios, equipo visible, horario, galería, reviews, punto en el mapa. **Sin teléfono en claro** | NEG-1, NEG-3 |
| `GET /publico/zonas` · `GET /publico/categorias` | Taxonomías para las páginas categoría × zona y el sitemap | MKT-6, MKT-7 |
| `GET /publico/z/{zona}/{categoria}` | Datos de la página indexable categoría × zona. **Solo combinaciones con negocios publicados** | MKT-7 |
| `GET /publico/negocios/{slug}/chat` | Salto a WhatsApp resuelto **en servidor**: registra el clic y redirige. El número nunca viaja al cliente | NEG-1, MKT-8 |
| `POST /publico/negocios/{slug}/impresion` | Registro agregado de impresiones | MKT-8 |
| `GET` · `POST` · `DELETE /mi/favoritos[/{id}]` | Favoritos | MKT-5 |
| `POST /mi/reservas/{id}/review` | Review **solo con reserva completada**, una por reserva, dentro de la ventana (default 14 días) | REV-1, REV-2 |
| `GET /publico/negocios/{slug}/reviews` | Reviews con su respuesta. Rating agregado **bayesiano** | REV-5 |
| `POST /negocio/reviews/{id}/respuesta` | Una respuesta pública por review | REV-3 |
| `POST /publico/reviews/{id}/reporte` | Reporte a moderación | REV-4 |

---

## 7. Lo que la API **no** hace en la Fase 1

Para que quede claro qué se echará en falta a propósito: no hay endpoints de ads (Fase 4), ni de back-office (Fase 3), ni de cobro real (ADR-0010: la interfaz existe, la pasarela la decide Luis en D5), ni de lista de espera, depósitos, multi-sede o recursos físicos, que son v2.
