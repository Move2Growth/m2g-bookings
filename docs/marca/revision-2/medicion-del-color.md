# Dónde está el color, medido — Estado: completado

> Medido en el navegador a 1440 px, sumando el área de cada elemento con fondo propio y
> quedándose con los cinco colores de más superficie. El script está al final para poder
> repetirlo. No es una opinión sobre el diseño: son los píxeles que hay.

---

## El resultado

| Pantalla | Blanco + arena | Tinta | Azul | Naranja | Filetes de 1 px | Elementos en ancho de cifra |
|---|---|---|---|---|---|---|
| `/` (portada) | 51 % | 29 % | 19 % | 1 % | 35 | 3 |
| `/como-funciona` | 47 % | 17 % | 36 % | 1 % | 25 | 8 |
| `/buscar` | 78 % | 8 % | 8 % | 6 % | 26 | **0** |
| `/spa-costa-del-este` | **94 %** | 1 % | 1 % | **0 %** | **44** | 1 |

## Qué dice esto, y no es agradable

**El brandbook dice que el color es la estructura. En la pantalla desde la que se reserva, el
94 % de la superficie es blanco y gris.** La ficha de un salón, que es la página que trae la
mitad del negocio, la que se comparte por WhatsApp y la que indexa Google, no tiene ni un bloque
de color. Tiene 44 filetes de 1 px, que es exactamente el mecanismo que el crítico de
accesibilidad rechazó en la dirección A y por el que ganó la B.

**La marca solo existe en las dos páginas de marketing.** La portada y el explicativo llevan
bloques a sangre porque son las dos que se reconstruyeron a mano al elegir la dirección B. En
cuanto se entra en el producto, en buscar, en la ficha y en el panel, el lenguaje desaparece y
queda una plantilla con la tipografía cambiada. Eso es literalmente lo que dijo Luis.

**El ancho de cifra no se usa.** Está declarado al 125 % en los tokens y en el buscador aparece
en **cero** elementos. Esto es un producto de horas, duraciones y precios: era el gesto propio
que estaba pagado y sin gastar.

**El naranja no está racionado: está ausente o está en los botones.** En la ficha del salón sale
al 0 %; en el buscador, al 6 % y todo dentro de un botón. La regla del brandbook, «el naranja
abre», se cumple al pie de la letra y no significa nada al mirar, porque abrir es lo que hace un
botón de todas formas.

## El listón para la revisión 2

Cualquier propuesta que se acepte tiene que mover estos números, y se vuelve a medir con el mismo
script en vez de discutir si ha mejorado:

- **La ficha del salón baja de ese 94 % de neutro.** Es la pantalla que hay que rehacer primero.
- **Los filetes de 1 px bajan de 44 a menos de 10 por pantalla.** Lo que separa es color, filo o
  aire, que es lo que dice el apartado 07 del brandbook.
- **El ancho de cifra aparece en todas las horas, duraciones y precios**, no en tres sitios.

## El script

```js
// Reparto de superficie por color de fondo, a 1440 px.
const area = new Map(); let total = 0
for (const e of document.querySelectorAll('body *')) {
  const fondo = getComputedStyle(e).backgroundColor
  if (!fondo || fondo === 'rgba(0, 0, 0, 0)') continue
  const c = e.getBoundingClientRect()
  const a = Math.max(0, c.width) * Math.max(0, c.height)
  if (a < 100) continue
  area.set(fondo, (area.get(fondo) ?? 0) + a); total += a
}
[...area.entries()].sort((x, y) => y[1] - x[1]).slice(0, 5)
  .map(([c, a]) => [c, Math.round((a / total) * 100)])
```
