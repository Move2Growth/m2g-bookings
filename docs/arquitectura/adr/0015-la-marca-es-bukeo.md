# ADR-0015 · La marca es Bukeo

- **Estado:** aceptada
- **Fecha:** 2026-09-01
- **Supera:** el «por definir» de la decisión D1 del brief

## Contexto

D1 dejaba el nombre comercial sin decidir y el equipo trabajaba con un codename. Eso era
correcto mientras no hubiera identidad, pero se ha vuelto un problema real: **sin marca no hay
producto, solo funcionalidad**. Una plataforma de belleza que llega al teléfono de una clienta
sin nombre, sin voz y sin cara no compite con nadie, y el salón que la enseña a sus clientas no
tiene qué enseñar.

Luis ha decidido el nombre: **Bukeo**.

## Decisión

**[decisión]** La marca del producto es **Bukeo**, en las tres superficies y en todo material.

- **[decisión]** El nombre **sigue sin escribirse a fuego en ninguna pantalla**. Vive en
  configuración (`NEXT_PUBLIC_NOMBRE_COMERCIAL`) y en `packages/tokens`. La regla no era «no
  sabemos cómo se llama»: era que **la identidad se cambia en un sitio**, y eso vale igual
  ahora que hay nombre.
- **[decisión]** La identidad completa (estrategia, logo, color con proporciones, tipografía y
  aplicaciones) vive en [`docs/marca/BRANDBOOK-BUKEO.md`](../../marca/BRANDBOOK-BUKEO.md), con
  el mismo formato de ocho apartados que el brandbook de RŪTA, que es el estándar de la casa.
- **[decisión]** Los tokens de `packages/tokens` son **la implementación** del brandbook. Si el
  brandbook y los tokens divergen, manda el brandbook y se corrigen los tokens; ningún
  componente define color, tipografía ni radio por su cuenta.
- **[pregunta abierta]** El **dominio** sigue sin cerrarse. No bloquea nada hasta que haya que
  indexar en Google y mandar plantillas a Meta.

## Alternativas consideradas

- **Seguir con el codename hasta la Fase 2.** Es lo que se venía haciendo y es lo que ha
  producido un producto sin piel: pantallas correctas que no se parecen a nada.
- **Marca genérica de plantilla** (tipografía neutra, azul de sistema, esquinas redondeadas).
  Descartado: es exactamente el aspecto que hace que un marketplace nuevo parezca un ejercicio.

## Consecuencias

- Todo el material y las pantallas pasan a decir Bukeo. El cambio fue mecánico porque el nombre
  ya salía de configuración, que era justo el motivo de la regla.
- Aparece un artefacto nuevo y vivo: el brandbook. Cambiar la identidad ahora tiene un sitio
  donde discutirse antes de tocar código.
- La identidad se eligió **de forma adversarial**: tres direcciones independientes compitiendo
  con prototipos comparables y tres críticos intentando tumbarlas. El resultado y el porqué
  están en [`docs/marca/DECISION-DE-MARCA.md`](../../marca/DECISION-DE-MARCA.md).
