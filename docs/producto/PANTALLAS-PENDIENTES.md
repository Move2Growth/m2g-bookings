# Las pantallas que faltan · Estado: en proceso

> **La API de todo esto ya existe y está probada.** Lo que falta es la pantalla. Se construye
> cuando Luis elija dirección visual, y por eso está aquí escrito: para que ese día sea montar
> pantallas y no volver a decidir qué hacen.
>
> **Las siete «Del dueño» ya están construidas** (7 de septiembre). Las del cliente y las del
> profesional siguen sin existir en `apps/web`.

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

## Del dueño — ✅ **hechas** el 7 de septiembre

> Están construidas y probadas en el navegador a 390 y a 1440 px. Viven todas en **`/panel/local`**,
> que es una zona con nombre propio y navegación propia: así es como se diferencia el portal del
> dueño del panel de un profesional sin depender del color, que se va a cambiar entero.
> Detalle en [`../ai-development/frontend-web/BITACORA/0001-portal-del-dueno.md`](../ai-development/frontend-web/BITACORA/0001-portal-del-dueno.md).

| Pantalla | Dónde está | Con qué |
|---|---|---|
| **Todos los calendarios** | `/panel/local/calendarios` | `GET /negocio/agenda/columnas` |
| **Finanzas** | `/panel/local/finanzas` | `GET /negocio/finanzas` |
| **Mejor del mes** | `/panel/local/mejor-del-mes` | `GET /negocio/mejor-del-mes` |
| **Publicidad flash** | `/panel/local/publicidad` | `/negocio/anuncios` |
| **Fichaje, persona a persona** | `/panel/local/fichaje` | `PUT /negocio/profesionales/{id}/fichaje`, `GET /negocio/fichajes` |
| **Personas del local** | `/panel/local/personas` | `/negocio/miembros` |
| **Alta del local en tres pasos** | `/panel/alta` | `POST /negocios`, `/negocio/miembros/invitaciones`, `POST /negocio/servicios` |

**Dos cosas que salieron de construirlas:**

- La **ficha pública no pintaba el anuncio** aunque la API ya lo devolvía. Se añadió, porque si no
  la previsualización del dueño sería una mentira.
- **`GET /mi/negocios` no ve los locales en borrador**, así que quien acaba de dar de alta el suyo
  y cierra sesión **no puede volver a entrar en él**. Es de la API y está en la deuda viva del
  tablero.

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
