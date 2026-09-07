# Las pantallas que faltan · Estado: sin iniciar

> **La API de todo esto ya existe y está probada.** Lo que falta es la pantalla. Se construye
> cuando Luis elija dirección visual, y por eso está aquí escrito: para que ese día sea montar
> pantallas y no volver a decidir qué hacen.
>
> Ninguna de estas pantallas existe hoy en `apps/web`.

## Del cliente

| Pantalla | Qué tiene que hacer | Con qué |
|---|---|---|
| **Perfil de un profesional** | Foto, titular, descripción, años, cuánta gente ha atendido, nota y reseñas, sus servicios, sus fotos de trabajo, sus redes y su calendario | `GET /publico/negocios/{slug}/profesionales/{slug}` |
| **Buscar personas, no locales** | La misma búsqueda pero devolviendo profesionales, con su salón y su próxima hora | `GET /publico/profesionales` |
| **Reservar empezando por la persona** | Elegir profesional → uno de **sus** servicios → hora. El camino de siempre se queda | `GET /publico/profesionales/{id}/disponibilidad` |
| **Mapa** | Los salones del rectángulo visible, con nota y número de reseñas, y la ficha al tocar | `GET /publico/mapa` |
| **Aceptar una invitación** | Quien recibe el correo entra, ve a qué salón y con qué papel, y acepta | `POST /invitaciones/ver` y `/aceptar` |

**El mapa necesita una decisión de Luis:** la consulta es nuestra y no cuesta nada, pero
**dibujar las baldosas** necesita un proveedor (Mapbox o Google) y su clave. Es la decisión D8,
abierta desde el 1 de septiembre por coste.

## Del profesional

| Pantalla | Qué tiene que hacer | Con qué |
|---|---|---|
| **Mi perfil** | Editar su titular, su descripción, sus años y sus redes | `GET`/`PATCH /mi/perfil-profesional` |
| **Mis fotos** | Subirlas y **atarlas a un servicio del salón**, que es lo que hace que se vea quién hizo qué | `/mi/perfil-profesional/fotos` |
| **Fichar** | «Ya llegué» y «ya salgo», y solo si el dueño se lo ha activado | `POST /negocio/fichajes` |

## Del dueño

| Pantalla | Qué tiene que hacer | Con qué |
|---|---|---|
| **Todos los calendarios** | El día del salón con una columna por persona | `GET /negocio/agenda/columnas` |
| **Finanzas** | Lo facturado por día, semana y mes, con el ticket medio y cuántas citas no tenían precio | `GET /negocio/finanzas` |
| **Mejor del mes** | Por importe o por número de servicios, filtrable por categoría | `GET /negocio/mejor-del-mes` |
| **Publicidad flash** | Escribir el banner del salón, ponerle fecha de fin y apagarlo | `/negocio/anuncios` |
| **Fichaje, persona a persona** | El interruptor por profesional, y el parte de horas | `PUT /negocio/profesionales/{id}/fichaje`, `GET /negocio/fichajes` |
| **Personas del local** | Invitar por correo con su papel, y quitar a alguien | `/negocio/miembros` |
| **Alta del local en tres pasos** | Crear el local → asignar personas → dar de alta servicios. El precio es opcional y ya se puede decir «a consultar» | `POST /negocios`, `/negocio/miembros/invitaciones`, `POST /negocio/servicios` |

## Lo que hay que rehacer, no añadir

Todas las pantallas que ya existen. Luis las rechazó enteras —«está todo oscuro, los botones
están incompletos, se ve todo fatal»— y se rehacen con la dirección que elija. Lo que **sí**
sobrevive y no hay que volver a descubrir:

- La barra de pestañas del teléfono va **fija abajo**, donde llega el pulgar.
- Los hijos de una rejilla necesitan `min-width: 0` o una fila larga estira el panel entero.
- El envoltorio de un campo no es el campo: dos recuadros, uno dentro de otro.
- Reservar tiene que **decir** que la cita quedó hecha, y solo prometer cancelar si se puede.
- Un profesional que escriba una URL del dueño va a su agenda, sin sermón de permisos.
- `make barrer` comprueba las veinte pantallas a 390 y a 1440. Se usa antes de decir «hecho».
