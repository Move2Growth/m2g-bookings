# @agenda/api-types

Los tipos TypeScript de la API, **generados desde el OpenAPI que publica FastAPI**. Los
consumen la web pública, el back-office y la app.

**Aquí no se escribe nada a mano.** Un tipo escrito a mano se desincroniza del servidor el
primer día que alguien renombra un campo, y el fallo aparece en el navegador de un cliente, no
en el ordenador de quien lo rompió. Generándolos, un cambio de contrato rompe **en
compilación**, que es exactamente donde se quiere que rompa.

## Cómo se regeneran

Desde la raíz del repositorio, con la API levantada:

```bash
make contrato
```

Ese comando vuelca `/api/v1/openapi.json` a `openapi.json` y regenera `tipos.ts`.

## Qué se commitea

Se commitean **`openapi.json` y `tipos.ts`**. Podrían generarse en cada instalación, pero
tenerlos en el repositorio significa que el diff de un cambio de contrato **se ve en la
revisión**: si un campo desaparece o cambia de tipo, aparece en el commit y alguien lo mira. Es
la diferencia entre enterarse al revisar y enterarse en producción.

## La regla de compatibilidad

Dentro de `v1` se pueden **añadir** campos y valores opcionales. No se puede quitar un campo,
renombrarlo, estrechar un tipo ni añadir un valor a un enumerado que el cliente ya interpreta:
hay una app en las tiendas que no se actualiza cuando nosotros queremos. Lo que rompa eso va a
`v2` (ADR-0012).
