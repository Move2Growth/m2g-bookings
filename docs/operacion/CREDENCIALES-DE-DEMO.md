# Credenciales de la demo local · Estado: completado

> **Todas las cuentas de ejemplo tienen la misma contraseña.** Ya no hay que pedir códigos:
> el acceso es correo y contraseña desde la migración 0008.

```
Contraseña de todas:   demo-panama-2026
```

Se cambia con `SEMILLA_CONTRASENA` en el `.env`. No es un secreto y no debe tratarse como tal:
`python -m agenda.semilla` **se niega a correr fuera de local**, y estas cuentas se borran y se
rehacen enteras en cada carga.

## Dónde se entra

| | |
|---|---|
| Web pública, clientas y salones | http://localhost:3100 |
| Pantalla de acceso | http://localhost:3100/entrar |
| API y su documentación | http://localhost:8000/docs |

## Clientas

| Nombre | Correo |
|---|---|
| Abdiel Him | `abdiel@demo.pa` |
| Zuleika Rodríguez | `zuleika@demo.pa` |
| Carlos Alberto Vega | `carlos@demo.pa` |
| Milagros Espino | `milagros@demo.pa` |
| Ricardo Sanjur | `ricardo@demo.pa` |
| Nadia Quintero | `nadia@demo.pa` |

Entran y acaban en **sus citas**.

## Salones

El correo se deriva del slug, así que no hay que consultar esta tabla para adivinarlo:
`dueno.<slug>@demo.pa` manda en el salón, y `pro.<slug>@demo.pa` es un profesional que **solo ve
su propia agenda**. Entrando con cualquiera de los dos se cae directo en el panel del negocio.

| Salón | Slug | Estado |
|---|---|---|
| Barbería El Cangrejo | `barberia-el-cangrejo` | publicado |
| Barbería San Francisco | `barberia-san-francisco` | publicado |
| Estudio de Cejas Bella Vista | `estudio-de-cejas-bella-vista` | publicado |
| Estética Integral Obarrio | `estetica-integral-obarrio` | publicado |
| Maquillaje por Karla | `maquillaje-por-karla` | publicado |
| Nails & Lashes Obarrio | `nails-and-lashes-obarrio` | publicado |
| Peluquería Doña Elvia | `peluqueria-dona-elvia` | publicado |
| Salón Obarrio | `salon-obarrio` | publicado |
| Spa Costa del Este | `spa-costa-del-este` | publicado |
| Spa Urbano El Cangrejo | `spa-urbano-el-cangrejo` | publicado |
| **Uñas por Vanessa** | `unas-por-vanessa` | **borrador** — está a propósito: sirve para ver qué pasa con un salón sin publicar |

## Consola interna de M2G

**No comparte nada con lo de arriba**, y es deliberado: otras tablas, otro rol de base de datos,
caducidad más corta y **segundo factor obligatorio**. Si un superadministrador fuera un usuario
con una casilla marcada, cualquier fallo de escalada en la aplicación de la clienta sería una
escalada al back-office de toda la plataforma.

Se crea con `python -m agenda.consola_alta`, que imprime **una sola vez** la contraseña y el
secreto del segundo factor. No están aquí ni pueden estarlo.

## Si algo no entra

- **429 «Demasiados intentos fallidos»**: ocho contraseñas malas seguidas cierran esa cuenta
  quince minutos. Es el freno contra la fuerza bruta, no un fallo. Se puede levantar a mano:
  `UPDATE users SET locked_until = NULL, failed_logins = 0 WHERE email = '...';`
- **Nada carga**: `make arriba` y esperar a que la web responda en el 3100.
- **La contraseña no funciona en ninguna cuenta**: la semilla se cargó con otra. Volver a
  cargarla con `make semilla`.
