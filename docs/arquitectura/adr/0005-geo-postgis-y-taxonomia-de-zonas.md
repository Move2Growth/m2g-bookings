# ADR-0005 · Geografía: PostGIS para distancia, taxonomía de zonas para SEO

- **Estado:** aceptada
- **Fecha:** 2026-09-01

## Contexto

El marketplace necesita dos cosas que parecen la misma y no lo son:

1. **«Barberías cerca de mí»** — ordenar por distancia real desde un punto, con p95 < 500 ms sobre 5.000 negocios (MKT-1, MKT-2).
2. **«Barbería en San Francisco»** — páginas **categoría × zona** que Google indexa y que traen la mitad del negocio (MKT-6, MKT-7). Eso no es un radio: es una entidad con nombre, URL estable y contenido.

## Decisión

**[decisión]** Las dos cosas conviven, cada una con su mecanismo.

**Distancia:** `locations.geo` de tipo `geography(Point, 4326)` con índice GiST. Las consultas usan `ST_DWithin` para filtrar por radio y `ST_Distance` para ordenar. `geography` y no `geometry`: devuelve metros directamente y evita el error clásico de ordenar por grados.

**Zonas:** tabla `zones` **jerárquica y administrable** (provincia → distrito → corregimiento → barrio) con `parent_id`, `slug` y `path` materializado para consultar una rama entera sin recursión. La zona de un negocio se resuelve al guardar la ubicación y se **persiste** en `locations.zone_id`; no se recalcula en cada búsqueda.

- **[decisión]** La zona del negocio es **editable por el dueño**. La asignación automática por punto es una sugerencia: en Panamá los límites de corregimiento no coinciden con lo que la gente llama su barrio, y el dueño sabe mejor dónde está.
- **[decisión]** Las páginas categoría × zona se generan **solo para combinaciones con negocios publicados**. Miles de páginas vacías son contenido de baja calidad y Google penaliza.
- **[decisión]** El geocoding (dirección → punto) se **cachea por texto normalizado**: es de pago y se repite mucho. El coste de mapas es un riesgo declarado del brief.
- **[pregunta abierta]** El proveedor de mapas y geocoding es **D8: Mapbox por defecto, pendiente de confirmar con Luis por coste.** Hasta entonces, la integración vive detrás de una interfaz `GeocodingProvider` con una implementación local para desarrollo y pruebas: no bloquea la Fase 2.

## Alternativas consideradas

- **Solo distancia, sin zonas.** Descartado: sin páginas categoría × zona no hay SEO, y sin SEO no llega la mitad del tráfico.
- **Solo zonas, sin PostGIS.** Descartado: «cerca de mí» con GPS es el gesto principal en el móvil.
- **Cuadrículas o geohash en vez de PostGIS.** Descartado: se reimplementa peor lo que Postgres ya hace bien, y PostGIS ya es requisito del brief.
- **Zonas fijas en código.** Descartado: MKT-6 pide taxonomía administrable, y Panamá cambia de corregimientos.

## Consecuencias

- La migración inicial activa **`postgis`**; el `docker-compose.yml` usa una imagen que ya la trae (`postgis/postgis:16-3.4`), porque el `postgres:16` pelado no la tiene y ese es un traspié de arranque garantizado.
- El seed carga un **árbol real de zonas de Ciudad de Panamá** (Bella Vista, San Francisco, El Cangrejo, Costa del Este, Obarrio…), no «Zona 1 / Zona 2».
- Ordenar por distancia y por ranking a la vez obliga a que la distancia sea **una entrada de la fórmula de ranking** (ADR-0009), no un orden aparte.
