# Cómo se valida algo antes de decir que está hecho

**Estado: vigente.** Aplica a **todos los proyectos de M2G**. Decisión de Luis, 1 de septiembre
de 2026, después de tres meses en los que lo que rompía producción siempre pasaba el mismo filtro:
compilaba.

---

## La regla

> **Nada está hecho hasta que se ha visto funcionar en un navegador, con una captura que lo
> demuestre.**

Y su corolario, que es el que más cuesta aceptar:

> **`curl` contra la API no es validar.** Ni el build verde. Ni las pruebas unitarias en verde.
> Ninguna de las tres ve lo que ve el usuario.

## Por qué, con los casos reales

No es una preferencia estética. Estos cuatro fallos **pasaron todos los filtros automáticos** y
llegaron a producción o estuvieron a punto:

| Qué se rompió | Qué decían los filtros | Cómo se encontró |
|---|---|---|
| La ficha del cliente no se abría al pulsarla — condicionada a un modo de panel que no existe | `tsc` limpio, build verde | **Pulsando el nombre del cliente** en un navegador |
| El panel sumaba un 5 % de recargo en un país donde ese recargo no existe | Todo verde; el cálculo real era correcto | **Mirando la pantalla**: los campos sumaban 7,5 y ponía 12,50 |
| Los clientes mexicanos vieron «Próximamente» en SPEI y OXXO y no pudieron pagar | Build verde, API respondiendo 200 | **Un cliente real**, en producción, un lunes por la mañana |
| El login roto tres releases seguidos por la CSP | `curl` daba 200 | **Abriendo el login en un navegador** |

El patrón se repite: **la API respondía bien y el usuario no podía usar el producto.** La CSP, el
runtime, un `if` mal puesto, un texto que no cabe, un botón bajo el pliegue — nada de eso sale en
una respuesta HTTP.

---

## Dónde se valida

Por orden. **No se salta un escalón.**

| Escalón | Cuándo | Qué demuestra |
|---|---|---|
| **1 · Local** | Mientras construyes | Que el flujo funciona de punta a punta |
| **2 · Desarrollo** | Antes de pedir revisión | Que funciona desplegado, no solo en tu máquina |
| **3 · Staging** | Antes de producción | Que funciona con datos parecidos a los de verdad |
| **4 · Producción** | Después de publicar | Que sigue funcionando donde importa |

**Producción se valida igual que el resto**, y no es opcional: es donde han aparecido la mitad de
los fallos de esta lista.

---

## Cómo se hace, en concreto

### Lo mínimo de cada validación

De cada cosa que termines:

1. **Captura del flujo entero**, no de una pantalla suelta. Si la feature es «reservar», la
   captura es: buscar → elegir → confirmar → verla en la agenda. Una pantalla aislada demuestra
   que el HTML existe, no que el flujo funciona.
2. **En escritorio y a 390 px.** Casi todos nuestros usuarios trabajan desde el teléfono.
3. **Cero errores de consola.** Se capturan y se miran; no se ignoran.
4. **Sin desbordamiento horizontal.** Se mide, no se estima a ojo.
5. **Con datos realistas.** Nunca «Producto 1 · 100,00».

### El guion base

Playwright sirve para todo esto y no hace falta más. Este es el esqueleto que usamos:

```python
from playwright.sync_api import sync_playwright

errores = []
with sync_playwright() as p:
    navegador = p.chromium.launch()
    for etiqueta, ancho, alto, movil in [("escritorio", 1440, 950, False),
                                          ("movil", 390, 844, True)]:
        pg = navegador.new_context(
            viewport={"width": ancho, "height": alto},
            is_mobile=movil, has_touch=movil,
        ).new_page()

        # 1) Los errores de consola se RECOGEN, no se ignoran: aquí salen la CSP y el runtime.
        pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        # 2) Y los códigos de estado de cada petición, para ver los 404 y 500 que la pantalla calla.
        pg.on("response", lambda r: errores.append(f"{r.status} {r.url}") if r.status >= 400 else None)

        pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(5000)          # que termine de pintar; ver la nota sobre networkidle

        pg.screenshot(path=f"{OUT}/{etiqueta}.png", full_page=True)

        # 3) El desbordamiento se MIDE.
        a = pg.evaluate("() => ({doc: document.documentElement.scrollWidth, win: window.innerWidth})")
        print(etiqueta, "DESBORDA" if a["doc"] > a["win"] + 1 else "ancho ok")

    print("ERRORES:", errores[:5])
    navegador.close()
```

### Comprobar lo que la pantalla afirma

Una captura enseña un número; no dice si es correcto. **El número se contrasta con una consulta
independiente**, escrita a mano, que no pase por el mismo código que lo produjo:

```bash
# La pantalla dice «73 transacciones en julio». ¿Lo son?
psql -c "SELECT count(*) FROM envios
          WHERE created_at >= timestamptz '2026-07-01 00:00 America/Panama'
            AND created_at <  timestamptz '2026-08-01 00:00 America/Panama'"
```

Ese contraste ha pillado cosas que ninguna prueba: una gráfica que contaba una métrica con el
nombre de otra, y un corte de mes en UTC que se comía cuatro transacciones.

### Cuando hay login y segundo factor

No es excusa para no validar. Se automatiza:

```python
import pyotp
pg.fill("input[type=email]", USUARIO)
pg.fill("input[type=password]", CONTRASENA)
pg.click("button[type=submit]"); pg.wait_for_timeout(4000)
campo = pg.query_selector("input[inputmode=numeric]")   # el 2FA aparece DESPUÉS del primer envío
if campo:
    campo.fill(pyotp.TOTP(SECRETO).now())
    pg.click("button[type=submit]"); pg.wait_for_timeout(8000)
```

**Las cuentas de prueba se crean en desarrollo o staging, nunca en producción**, y jamás se le
cambia la contraseña a la cuenta real de una persona para entrar tú.

---

## Trampas que nos han costado tiempo

Están aquí porque **cada una nos ha hecho perder al menos media hora**:

- **`wait_until="networkidle"` no llega nunca** en páginas con analítica: GTM sigue emitiendo
  balizas para siempre. Usa `domcontentloaded` + una espera fija.
- **El texto en MAYÚSCULAS por CSS no se encuentra** buscando el texto original. La tarjeta ponía
  «Tiempo de despacho» en el código y `TIEMPO DE DESPACHO` en pantalla: compara en mayúsculas.
- **El valor de un `<input>` no está en `inner_text()`.** Un formulario relleno parece vacío si lo
  buscas así. Léelo con `input_value()`.
- **Valida con una cuenta que tenga datos.** Un usuario de un comercio con 8 registros hace que
  todo parezca roto; el mismo código con el comercio de 1.187 funciona.
- **Comprueba el puerto antes de dar por bueno un `preview`.** Un servidor de otro proyecto en el
  mismo puerto te devuelve otra web y no te enteras.
- **En móvil las listas suelen ser tarjetas, no tablas.** Un selector `table tbody tr` no encuentra
  nada y parece un fallo del producto.
- **Un 404 en la consola puede no ser tuyo.** Míralo antes de perseguirlo: casi siempre es la
  analítica.

---

## Lo que NO cuenta como validación

- `curl` a la API. Ve el JSON, no la pantalla. **No aplica la CSP.**
- El build verde. Compila ≠ funciona.
- Las pruebas unitarias. Necesarias, y **cero de los cuatro fallos de arriba las habría pillado**.
- «Lo he mirado y se ve bien» sin captura.
- Una captura de una pantalla suelta cuando lo que se pedía era un flujo.

## Lo que sí hace falta además de la captura

La captura demuestra que **funciona**; no que sea **correcto**. Las dos cosas van juntas:

- **Pruebas automáticas** de la lógica que decide dinero, permisos o fechas. Y que **fallen si
  reintroduces el fallo** — si no, no prueban nada.
- **Migraciones probadas contra una base real**, no solo `alembic upgrade head` en el aire.
- **El contraste con la consulta independiente** cuando la pantalla afirma un número.

---

## Al entregar

Se entrega con esto, y sin esto no está entregado:

- [ ] Capturas del **flujo completo**, en escritorio y a 390 px
- [ ] **Cero errores** de consola, o los que haya explicados
- [ ] **Sin desbordamiento** horizontal, medido
- [ ] Los números de la pantalla **contrastados** con una consulta independiente
- [ ] Validado en **el entorno donde va a vivir**, no solo en local
- [ ] Lo que quedó fuera, **dicho** — con lo que salió por pantalla si algo falló
