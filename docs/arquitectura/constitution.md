# Constitution — principios de Bukeo

> Los **principios no negociables** que todo agente respeta. No es *qué* se construye (eso es el [brief](../BRIEF-PRODUCTO.md)) ni *cómo* se decide cada cosa (eso son los [ADR](adr/)), sino los valores y restricciones permanentes que enmarcan cualquier decisión.
>
> **Cualquier agente que vea un choque entre una tarea y un principio de aquí para y escala** en `../ai-development/ESTADO-GLOBAL.md`. No lo resuelve por su cuenta.

## 1. Propósito y alcance

- **Para quién:** el salón, la barbería, el spa pequeño y el profesional independiente de Panamá — y, del otro lado, el cliente que busca dónde cortarse el pelo cerca.
- **Qué resuelve:** que un negocio pequeño tenga agenda y presencia sin pagar una suscripción mensual, y que el cliente encuentre y reserve sin llamar por teléfono.
- **Qué NO es:** no es un POS, ni inventario, ni nómina, ni email marketing, ni fidelidad, ni venta de productos. Todo eso está fuera de alcance v1 (§11 del brief) y no se construye «ya que estamos».

## 2. Principios de producto

- **El teléfono es el caso principal, no una adaptación.** El dueño del salón no tiene escritorio: tiene un móvil de gama media, 3G y las manos ocupadas. Todo se diseña y se prueba **a 390 px** primero.
- **Gratis de verdad para el negocio.** Sin tarjeta para registrarse, sin límites escondidos, sin funciones cortadas que empujen a pagar.
- **El posicionamiento pagado es transparente y acotado.** Etiquetado «Patrocinado», intercalado, máximo 2 de cada 10, y **nunca oculta a los orgánicos**.
- **El dinero no compra reputación.** El patrocinio no toca el rating ni las reviews. Jamás.
- **Un negocio nuevo tiene que poder arrancar.** El ranking lleva boost temporal para los recién llegados, o el marketplace nace bloqueado.
- **Menos pantallas.** Máximo 3 pantallas tras elegir servicio para completar una reserva; menos de 10 minutos para dejar un negocio operativo desde el móvil.
- **Español llano en pantalla.** Ninguna jerga interna, ningún código de requisito visible al usuario.

## 3. Principios de ingeniería

- **Memoria en archivos:** ningún estado importante vive solo en el chat.
- **Los ADR mandan:** la arquitectura es la fuente de verdad; una decisión se supera con un ADR nuevo, no se edita.
- **La arquitectura antes que el código:** lo que no está decidido por escrito, no se construye a ojo.
- **Verificar en vivo, no «build verde»:** la UI y el runtime se dan por buenos observándolos funcionar en el navegador. La CSP y el diseño no salen en un build.
- **Las pruebas del motor de disponibilidad se escriben antes que el motor.**
- **Un foco cada vez / paralelismo seguro:** solo se paraleliza lo que no colisiona en los mismos archivos.
- **Nada pendiente solo en prosa:** toda deuda va al tablero con su estado.

## 4. Restricciones permanentes

- **Infra y despliegue no son de este equipo.** Se desarrolla y valida en local; se entrega `docker-compose.yml` de un comando, migraciones desde cero, `.env.example` documentado y README de arranque.
- **Cumplimiento legal:** Ley 81 de 2019 de Panamá — consentimiento, derechos del titular, política de privacidad, retención y **borrado de cuenta desde dentro de la app**.
- **Sin credenciales inventadas:** si falta un servicio externo (WhatsApp, pasarela, mapas), se para y se pide.
- **Nada que cobre dinero de verdad** a un negocio o a un cliente se enciende sin OK explícito de Luis.
- **Zona horaria:** `America/Panama` (sin DST) en v1, pero el modelo guarda UTC + zona del negocio porque España viene después.
- **Idioma:** español (Panamá) en v1 con **todos los strings externalizados desde el día uno**.

## 5. Garantías que no se rompen

> Las invariantes que, si se rompieran, invalidarían el producto. QA las trata como criterio de rechazo, no como recomendación.

1. **Aislamiento entre negocios.** Ninguna consulta devuelve datos de otro negocio. La autorización a nivel de fila está en **todos** los endpoints, desde la primera migración.
2. **No hay doble reserva.** Dos clientes confirmando el mismo slot a la vez, bajo carga real: uno gana y el otro recibe un error claro. Es una garantía transaccional de la base de datos, no un `if` en Python.
3. **Ningún teléfono en claro** en listados, perfiles públicos ni respuestas de API sin autorizar. El click-to-chat se resuelve en servidor.
4. **Ningún dato de tarjeta tocado ni almacenado.** Solo el token de la pasarela.
5. **Ningún secreto en git**, ni en logs, ni en bitácoras.
6. **Ningún job duplica un efecto visible.** Los recordatorios y los cobros son idempotentes.
7. **El precio del plan es un dato, no código.** Pasar de 0 a 1 $ es cambiar un número en el back-office.
8. **Los perfiles públicos se renderizan en servidor.** Sin SSR indexable no hay marketplace, y sin marketplace no hay negocio.
