# Entrega · Estado: la API completa; las pantallas, a la espera de la dirección visual

> **Qué es esto.** Lo que hay hecho, cómo verlo funcionando en tu máquina, qué falta y qué
> necesito de ti. **Reescrito el 7 de septiembre de 2026**; la versión anterior era del día 1 y
> describía un producto que ya no es este —decía que no había contraseñas y que la web estaba en
> el puerto 3000—.

---

## 1. Cómo levantarlo

Hace falta **Docker** y nada más. **Ninguna credencial**: WhatsApp, el correo, la pasarela y los
mapas tienen implementación de desarrollo, así que el stack arranca y las pruebas pasan sin una
sola clave.

```bash
cd ~/Desktop/kraken/m2g-bookings
cp .env.example .env      # no hay que rellenar nada para trabajar en local
make arriba               # levanta todo, migra desde cero y carga los datos de ejemplo
```

Levanta seis servicios: la base con PostGIS, Redis, la API, **los dos trabajadores** —el que
entrega y el que planifica— y la web.

| Qué | Dónde |
|---|---|
| Marketplace, perfiles y los tres portales | <http://localhost:3100> |
| Documentación de la API | <http://localhost:8000/docs> |
| Base de datos | `postgresql://agenda_api@localhost:5433/agenda` |

**Se entra con correo y contraseña.** Todas las cuentas de ejemplo comparten la misma y el correo
se deriva del slug del salón, así que se adivinan sin mirar ninguna tabla:

```
Clienta:      abdiel@demo.pa
Dueña:        dueno.salon-obarrio@demo.pa
Profesional:  pro.salon-obarrio@demo.pa
Contraseña:   demo-panama-2026
```

La lista entera, con los once salones y qué hacer si algo no entra, en
[`operacion/CREDENCIALES-DE-DEMO.md`](operacion/CREDENCIALES-DE-DEMO.md).

## 2. Qué hay

**73 tablas**, 11 migraciones que corren desde cero, **92 rutas y 117 operaciones** de API, **281
pruebas en verde** —la mayoría contra un PostgreSQL de verdad, porque lo que hay que probar son
restricciones de exclusión, seguridad por fila y PostGIS— y **26 pantallas**.

Del encargo del 7 de septiembre está **todo, API y pantallas**. Lo que espera a que elijas
dirección visual no es que existan, sino **cómo se ven**: el estilo se sustituye entero, y por eso
se construyeron con el vocabulario que ya había en vez de inventar aspecto dos veces.

| Lo que pediste | Dónde está |
|---|---|
| **Correo y contraseña** en vez de código | Hecho y en el producto vivo. El código se queda solo para verificar el teléfono antes de la primera reserva, que es donde hace falta |
| **El profesional con perfil propio** y elegible antes que el local | API entera: titular, descripción, años, fotos —incluidas las atadas a un servicio, que es lo que hace ver quién hizo qué—, redes, cuánta gente ha atendido, reseñas y su calendario |
| **Precio opcional** | Ya existía en el modelo y en la pantalla. Se arregló el 500 que daba crear un servicio con precio incoherente |
| **Alta del local en tres pasos** | API entera, con las invitaciones por correo y la regla de que un salón no se queda sin dueño |
| **Portal del dueño** | API entera: todos los calendarios en columnas, finanzas, publicidad flash, fichaje que se enciende persona a persona, y mejor del mes por importe o por número de servicios |
| **Mapa con reseñas** | Hecho, con pantalla. Las baldosas son de OpenStreetMap y no piden clave; **elegir con qué se publica sigue siendo tuyo**, pero es cambiar una URL |

El detalle de cada pantalla, y lo que sobrevive al rediseño para no volver a descubrirlo a
golpes, en [`producto/PANTALLAS-PENDIENTES.md`](producto/PANTALLAS-PENDIENTES.md).

## 3. Qué mirar para creerte que funciona

```bash
make barrer     # entra como clienta, como dueña y en la consola, y recorre las 20 pantallas
make pruebas    # 281 contra un PostgreSQL real
```

`make barrer` no comprueba que algo se vea bonito: comprueba que **carga, que no revienta, que no
enseña su propio error y que no desborda a lo ancho**, a 390 px y a 1440. Con él salió que el
panel del salón medía 562 px dentro de una pantalla de 390. Lo de «no enseña su propio error» se
añadió después, y no era teórico: ocho pantallas pasaban diciendo «Failed to fetch».

Y hay tres recorridos que se ejecutan solos, en un navegador de verdad:

```bash
node scripts/recorrido-cliente.mjs             # alta, buscar, elegir hora, verificar teléfono y reservar
node scripts/verificar-contraste-en-pantalla.mjs  # mide el contraste real, también detrás del acceso
```

## 4. Qué necesito de ti

**Elegir dirección visual.** Tres brandbooks en PDF, en tu escritorio y en
`docs/marca/revision-4/salida/`. Los tres pasan el listón que se escribió antes de verlos, los
tres los criticó alguien que no los hizo, y los tres corrigieron lo que se les encontró. **Hasta
que elijas, no se rehacen las pantallas**, y con ellas viene también el nombre: «Bukeo» está
descartado y cada dirección trae el suyo.

**El proveedor de mapas** (decisión D8). Ya no bloquea nada: el mapa está construido con teselas
de OpenStreetMap, que no piden clave. Lo que hay que decidir es **con qué se publica**, porque su
política de uso no admite tráfico serio. Cambiar de proveedor es una URL en `app/mapa/page.tsx`.

**El proveedor de correo.** Sin él la invitación al equipo llega al buzón de desarrollo y no a
una bandeja. Y hay algo más de fondo que hay que decidir con él: hoy los mensajes viajan con el
nombre de la plantilla y sus variables —así funciona WhatsApp, donde el texto lo guarda Meta—,
pero en correo alguien tiene que componer el asunto y el cuerpo, y eso no está construido.

**Las credenciales de Meta** para WhatsApp, que siguen bloqueando dar por buena la Fase 1 en el
canal real. Construida está; verificada en el canal, no.

## 5. Lo que sé que está mal y no he arreglado

- **Las fotos se suben por clave, no por archivo.** No hay almacenamiento de objetos decidido, así
  que la API recibe la ruta de una imagen que ya existe en algún sitio. Vale para la demo y no
  vale para producción.
- **Las fotos de trabajo de un profesional entran aprobadas.** La columna de moderación existe y
  la política pública la respeta, pero no hay cola: con «pendiente» por defecto ninguna galería
  se vería nunca.
- **La búsqueda de profesionales no ordena por distancia**, aunque el campo viaje.
- **El fichaje no se puede corregir.** Es solo-añadir a propósito: editarlo sin decidir quién
  puede y sin dejar rastro no probaría nada.
- **Los errores de validación de FastAPI no llevan la forma única del error** del resto de la API.
  Es anterior a este encargo y se ve en cualquier 422.

Todo eso está en el tablero con su tarea, no solo aquí:
[`ai-development/ESTADO-GLOBAL.md`](ai-development/ESTADO-GLOBAL.md).
