# Credenciales de la demo — Estado: al día (2 sep 2026)

> **Todas estas cuentas son de mentira y viven solo en tu máquina.** Las crea `make semilla` y
> se rehacen enteras cada vez que lo ejecutas. Aquí no hay ni un dato de una persona real.
>
> **Para clientes y salones no hay contraseñas.** Se entra con el teléfono y un código de seis
> dígitos que **la propia pantalla te enseña**, porque en local todavía no hay canal de
> WhatsApp. En cualquier otro entorno el código viaja por WhatsApp y no aparece en ningún sitio.
>
> **La consola interna sí tiene contraseña y segundo factor**, y por eso está más abajo con una
> advertencia: esa cuenta **solo la crea el seed cuando `ENTORNO=local`**. No es una convención
> ni un aviso; es un `return` en `agenda/semilla.py` que impide que llegue a existir en
> cualquier otro entorno por copiar el seed.

---

## Dónde está cada cosa

| Qué | URL |
|---|---|
| Portada | <http://localhost:3100> |
| Cómo funciona (la página que explica el producto) | <http://localhost:3100/como-funciona> |
| Marketplace con filtros | <http://localhost:3100/buscar> |
| Una ficha con fotos y reseñas | <http://localhost:3100/spa-costa-del-este> |
| Entrar (clientes y salones, la misma puerta) | <http://localhost:3100/entrar> |
| Mis citas · Guardados · Perfil | `/mi/citas` · `/mi/favoritos` · `/mi/perfil` |
| Panel del salón (siete pestañas) | `/panel/agenda` · `servicios` · `equipo` · `horario` · `clientes` · `resenas` · `ficha` |
| Consola interna de M2G | <http://localhost:3100/consola> |
| Documentación de la API | <http://localhost:8000/docs> |

> **Por dónde empezar para verlo entero:** abre `/buscar`, entra en **Spa Costa del Este** —es el
> único con foto y con reseñas respondidas—, reserva una hora, y luego entra con el teléfono de
> ese salón para verla caer en su agenda. Con eso has recorrido las dos mitades del producto.

---

## La cuenta de cliente

| | |
|---|---|
| **Teléfono** | **`+50761234567`** |
| Qué ve | El marketplace, los perfiles, las horas libres, sus citas y el botón de cancelar |
| Citas que ya tiene | Dos: una en Peluquería Doña Elvia y otra en Nails & Lashes Obarrio |

**Cómo entrar:** abre <http://localhost:3100/entrar>, escribe el teléfono, pulsa «Mandarme el
código» y **la pantalla te enseña el código**. Al entrar te lleva a *Mis citas*, no al panel,
porque esta cuenta no tiene ningún salón.

**Para reservar** no hace falta entrar antes: eliges salón, servicio y hora, y el teléfono se
te pide **encima de la pantalla de confirmar**, sin sacarte del flujo ni perder lo elegido.

---

## Los once salones

Diez publicados y uno en borrador. El borrador está a propósito: es lo que permite ver que **un
negocio a medias no aparece en el marketplace**, y que no lo esconde el código sino la propia
base de datos.

| Salón | Teléfono del dueño | Forma | Qué caso enseña |
|---|---|---|---|
| **Barbería El Cangrejo** | `+50760000001` | 2 barberos | Una barbera que **solo trabaja de tarde**: el horario del profesional no es el del negocio |
| **Salón Obarrio** | `+50760000002` | 4 profesionales | Equipo con cuatro horarios distintos y un balayage de **3 h** que no cabe en cualquier hueco |
| **Spa Costa del Este** | `+50760000003` | 2 profesionales | **Jornada partida**: cierra a mediodía, y los servicios largos no caben en la franja corta |
| **Uñas por Vanessa** | `+50760000004` | 1 persona · **borrador** | La puerta de publicación: no sale en el marketplace y su perfil devuelve 404 |
| **Peluquería Doña Elvia** | `+50760000005` | 1 persona | El negocio más común del país: **unipersonal de barrio**, sin recepción |
| **Barbería San Francisco** | `+50760000006` | 1 persona | Unipersonal que **abre a mediodía y cierra a las 21:00** |
| **Estudio de Cejas Bella Vista** | `+50760000007` | 2 profesionales | Una de las dos solo trabaja tres días a la semana |
| **Nails & Lashes Obarrio** | `+50760000008` | 3 profesionales | Horarios escalonados: mañana, tarde y jornada completa |
| **Spa Urbano El Cangrejo** | `+50760000009` | 3 profesionales | Servicios de **2 h** con buffers largos de limpieza |
| **Maquillaje por Karla** | `+50760000010` | 1 persona | Solo jueves, viernes y sábado, con un servicio de **3 h**: la agenda se llena con dos citas |
| **Estética Integral Obarrio** | `+50760000011` | 4 profesionales | Jornada partida **y** equipo grande: el caso que más estresa la agenda |

**Cómo entrar a un salón:** <http://localhost:3100/entrar> con el teléfono del dueño. Como esa
cuenta sí tiene negocio, te lleva directo a la agenda.

### Los profesionales con cuenta

**El primero de cada salón tiene cuenta; los demás no**, que es el reparto de un salón real
(ONB-4): el dueño apunta a su equipo en dos minutos y las invitaciones llegan después.

| Teléfono | Quién | Salón |
|---|---|---|
| `+50762000001` | Kevin Ortega | Barbería El Cangrejo |
| `+50762000002` … `+50762000011` | El primero del equipo | Los otros diez salones, en el orden de la tabla de arriba |

**Qué ve un profesional y qué no.** Entra igual que un dueño y aterriza en el panel, pero:

- su agenda trae **solo sus citas**; las de su compañera no existen para él,
- puede editar **su** horario y sus descansos, no los de nadie más,
- ve los servicios y los precios —le hacen falta para entender su día— pero **no puede
  cambiarlos**: recibe `403 NO_AUTORIZADO`,
- de finanzas no ve **nada**, ni facturas ni suscripción.

Y lo que importa: eso **no lo decide un `if`**. Lo decide PostgreSQL con políticas restrictivas
(migración 0006). Si te conectas a la base con el rol de la aplicación declarando el negocio y
el profesional, un `SELECT * FROM bookings` sin `WHERE` sigue devolviendo solo lo suyo.

---

## La consola interna de M2G

> ⚠️ **Cuenta de mentira y solo local.** Ni esta contraseña ni este segundo factor existen fuera
> de tu máquina. La cuenta de verdad se crea con `python -m agenda.consola_alta`, que genera
> credenciales al azar y **las enseña una sola vez**.

| | |
|---|---|
| **Correo** | `consola@bukeo.local` |
| **Contraseña** | `consola-de-demo-solo-en-local` |
| **Segundo factor (base32)** | `JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP` |
| Rol | `superadmin` |

**El segundo factor es obligatorio y no se puede apagar**: quien entra aquí ve los datos de
todos los negocios de la plataforma. Tienes dos formas de conseguir el código:

```bash
# La cómoda: te lo imprime por pantalla (solo funciona con ENTORNO=local)
cd apps/api && ./.venv/bin/python -m agenda.consola_codigo

# La de verdad: mete el secreto base32 de arriba en tu autenticador
```

**Qué se puede hacer desde la consola:** buscar negocios y ver cuántas reservas, clientes y
reseñas tiene cada uno; **suspender** uno y comprobar que desaparece del marketplace *sin
perder ni una cita*; reactivarlo; resolver reportes de reseñas —ocultar una recalcula el rating
del salón en el acto—; **cambiar los pesos del ranking**, que crea una versión nueva en vez de
un `UPDATE`, porque hay que poder responder a «¿con qué pesos salía este negocio el noveno la
semana pasada?»; publicar versiones de plan; ver las métricas; y exportar CSV.

**Su sesión dura menos** que la de un cliente (30 minutos de acceso, 8 horas de refresco) y
**su token no vale en `/mi` ni en `/negocio`**, aunque esté firmado con la misma clave.

---

### Los clientes del seed

Cada salón tiene fichas de cliente con **dos semanas de historial hacia atrás** —completadas,
no-shows y canceladas— para que las métricas, el ranking y las reseñas tengan de qué comer. Sin
pasado no habría ni una reseña posible, porque REV-1 las ata a una cita atendida. Son estos, y
**también pueden entrar**:

`+50761230001` Abdiel Him · `+50761230002` Zuleika Rodríguez · `+50761230003` Carlos Alberto
Vega · `+50761230004` Milagros Espino · `+50761230005` Ricardo Sanjur · `+50761230006` Nadia
Quintero

---

## Qué mirar para ver si está bien montado

**Que el aislamiento es de verdad.** Entra con el dueño de un salón y mira su agenda; entra con
el de otro y mira la suya. Ninguno ve nada del otro, y no porque el código filtre: si te
conectas a la base con el rol de la aplicación sin declarar negocio, no ves ni una fila.

**Que los huecos son huecos de verdad.** En el perfil de la barbería, elige un día y fíjate en
que la lista salta —09:00, 09:15 y luego 10:45—. Ese agujero es una cita ya puesta; el de la
una es el almuerzo del barbero.

**Que un servicio largo no cabe en cualquier sitio.** En Salón Obarrio elige el balayage de tres
horas: hay días sin una sola hora libre y otros con veinte. En Maquillaje por Karla, el
maquillaje de novia de tres horas deja el día prácticamente cerrado.

**Que no se puede reservar dos veces el mismo hueco.** Abre el mismo salón en dos pestañas,
elige la misma hora en las dos y confirma. Una entra; la otra recibe *«ese horario se acaba de
ocupar»*. No lo decide el código: lo decide PostgreSQL.

**Que el rating no es la media.** En el perfil de cualquier salón, compara los dos números del
resumen: la media aritmética y la puntuación. Un salón con cuatro reseñas de cinco estrellas
**no** aparece con 5,00, sino cerca de 4,4: es la ponderación bayesiana de REV-5, y es lo que
impide que una sola opinión adelante a un negocio con ochenta.

**Que una reseña necesita una cita atendida.** Entra como cliente, abre una cita futura e
intenta reseñarla: no se puede. Pídele al salón que la marque como completada y entonces sí.
La segunda reseña de la misma cita devuelve `409`, y no porque lo mire el código: hay un único
en la base que lo impide igual.

**Que el teléfono del salón no viaja.** Mira el JSON de <http://localhost:8000/api/v1/publico/negocios/spa-costa-del-este>:
trae `tiene_whatsapp: true` y **ningún número**. El botón de WhatsApp llama a `/chat`, que
apunta el clic en el servidor y responde con la redirección.

**Que el borrador no existe para el público.** <http://localhost:3100/unas-por-vanessa> devuelve
404 aunque el negocio esté en la base con sus servicios y su equipo.

---

## Rehacer la demo

```bash
make semilla       # vuelve a dejar los once salones como están aquí descritos
make reiniciar     # borra la base entera y la monta de cero
node scripts/recorrido-cliente.mjs   # hace el recorrido de una clienta y deja capturas
```

El seed es **determinista**: los teléfonos de esta página no cambian entre cargas, y las citas
se generan siempre relativas a hoy, así que la agenda de ejemplo nunca aparece vacía por haber
envejecido.
