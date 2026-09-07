# ADR-0020 · El profesional es una entidad de primera

- **Estado:** aceptada
- **Fecha:** 2026-09-07
- **Complementa a:** ADR-0004 (el motor de disponibilidad, que no cambia) y al brief de producto,
  cuyo flujo de reserva RSV-1 va de negocio a servicio a profesional

## Contexto

El producto se construyó alrededor del **local**: se busca un salón, se elige un servicio del
salón y, al final, se elige con quién. El profesional era una fila de `staff_profiles` que servía
para calcular huecos y para no dejar que dos citas cayeran encima.

Luis señaló el fallo de fondo el 7 de septiembre: *«hace falta que el profesional tenga un
perfil… deberían poder elegir lo primero el profesional con el que te quieres atender»*. Y tiene
razón en el negocio: nadie compra «una peluquería». Se vuelve donde Yaris porque Yaris hace las
trenzas como nadie, y si Yaris se cambia de salón, la clienta se cambia con ella.

## Decisión

**[decisión] El profesional tiene perfil público propio y se puede elegir antes que el local.**

- `staff_profiles` gana `slug` —**único por negocio, no global**, porque la misma persona puede
  trabajar en dos salones y su ficha es distinta en cada uno—, `headline`, `years_experience` y
  las tres redes sociales.
- **De las redes se guarda el usuario, nunca la URL.** Una URL entera en un perfil público es un
  enlace a cualquier sitio, y «que sea de Instagram» no se puede validar mirando una cadena
  arbitraria. La URL se compone al pintar.
- Tabla nueva `staff_media`, con `service_id` **nulable**: atada a un servicio significa «esto lo
  hizo esta persona»; suelta es su galería. Es lo que pidió Luis con «que se pueda ver quién hizo
  qué».
- **Cuánta gente ha atendido y su nota se calculan al leer.** Un contador guardado se
  desincroniza el primer día que alguien cierra una cita a mano en la base.
- El camino de reserva inverso —profesional → uno de **sus** servicios → hora— convive con el de
  siempre. **El motor de disponibilidad no cambia ni una línea**: ya sabía calcular los huecos de
  una persona concreta.

## Consecuencias

- El marketplace deja de tener una sola unidad de venta. Un salón y una persona compiten en la
  misma lista, y el ranking tendrá que decidir cómo se mezclan; hoy son dos búsquedas separadas.
- Un perfil público de persona es dato personal: la política del rol público lo ata a que el
  negocio esté publicado **y** a `visible_in_marketplace`, y no expone ni teléfono ni correo.
- La búsqueda de profesionales **no ordena por distancia** todavía, y las citas atendidas no
  viajan en ella —contarlas ahí sería una consulta por resultado—. Está anotado como deuda.
- Las fotos de trabajo entran **aprobadas**: con `pendiente` por defecto ninguna galería se vería
  nunca, y no hay cola de moderación para ellas. Es deuda consciente, no un olvido.
