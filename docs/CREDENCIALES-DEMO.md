# Credenciales de la demo — Estado: al día (1 sep 2026)

> **Todas estas cuentas son de mentira y viven solo en tu máquina.** Las crea `make semilla` y
> se rehacen enteras cada vez que lo ejecutas. Aquí no hay ni un dato de una persona real.
>
> **No hay contraseñas.** Se entra con el teléfono y un código de seis dígitos que **la propia
> pantalla te enseña**, porque en local todavía no hay canal de WhatsApp. En cualquier otro
> entorno el código viaja por WhatsApp y no aparece en ningún sitio.

---

## Dónde está cada cosa

| Qué | URL |
|---|---|
| Marketplace (lo que ve un cliente) | <http://localhost:3100> |
| Entrar (clientes y salones, la misma puerta) | <http://localhost:3100/entrar> |
| Mis citas (cliente) | <http://localhost:3100/mis-reservas> |
| Panel del salón | <http://localhost:3100/panel> |
| Documentación de la API | <http://localhost:8000/docs> |

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

### Los clientes del seed

Cada salón tiene fichas de cliente con historial —completadas, un no-show y una cancelada— para
que las métricas y el ranking tengan de qué comer. Son estos, y **también pueden entrar**:

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
