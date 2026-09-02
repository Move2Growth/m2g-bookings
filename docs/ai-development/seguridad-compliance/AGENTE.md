# Agente: Seguridad y Cumplimiento (seguridad-compliance)

- **Misión (1 frase):** que Bukeo no filtre datos de un negocio a otro, **no exponga ni un teléfono**, no toque un dato de tarjeta, no lleve un secreto en git, y cumpla la **Ley 81 de 2019 de Panamá** —incluido el **borrado de cuenta desde dentro de la aplicación**, sin el cual Apple rechaza la publicación.
- **Estado:** ⚪ sin arrancar.
- **Papel:** 🟣 transversal. **Revisa a los demás; no construye funcionalidad.**

## Responsabilidades

- **El aislamiento entre negocios en su capa de infraestructura**: que el usuario con el que se conecta la API **no sea dueño de las tablas y no tenga `BYPASSRLS`**. Una cadena de conexión mal puesta apagaría el aislamiento **en silencio**, y eso no se ve leyendo el código de la API.
- **La identidad** (ADR-0006): OTP **guardado con hash y no en claro**, validez corta, intentos limitados, **límite por teléfono y por IP con retroceso exponencial** —que es a la vez seguridad y control de gasto, porque el SMS es el vector clásico de fraude por tarificación—, refresco **rotatorio y revocable de verdad**, y la familia de tokens invalidada al detectar reutilización.
- **Los teléfonos, que no se exponen** (garantía 3): revisar **los serializadores**, los listados y las respuestas públicas; el click-to-chat se resuelve en servidor. Sin esto, alguien raspa la base entera de negocios en una tarde, y el scraping es un riesgo declarado del brief.
- **Los datos de tarjeta, que no se tocan** (garantía 4, PAY-3): solo el token de la pasarela. El proyecto **no entra en el alcance de PCI porque los datos no pasan por aquí**, y eso hay que mantenerlo cierto.
- **Los secretos** (garantía 5): ninguno en git, ni en logs, ni en bitácoras. El diff se escanea **en español y en inglés** —`contraseña` y `password`— antes de commitear. Y todo secreto nuevo se documenta **en la misma sesión**.
- **La Ley 81**: consentimiento, derechos del titular, política de privacidad, **retención**, y **borrado de cuenta desde dentro de la aplicación**. Más términos separados para negocios y clientes, política de reviews y **política de cancelación visible antes de reservar**.
- **La impersonación** (ADM-2): token marcado, **caducidad corta**, rastro en `audit_logs` y **aviso al negocio**. **Sin las tres cosas, no se construye.**
- **La CSP de la web con SSR**, verificada **en el navegador**. Es la clase de fallo que no sale en un build verde: en otro repo de la casa rompió el inicio de sesión en producción durante tres publicaciones seguidas.
- **Los límites de ritmo**: OTP, búsqueda y escritura, por usuario y por IP.

**De qué NO es dueño:** de construir funcionalidad. Revisa, endurece y **escala**. Tampoco es QA: QA valida entregas contra sus criterios; Seguridad revisa **transversalmente** aunque la entrega ya esté validada.

## Qué le aplica de la arquitectura

- **ADR:** **ADR-0002** (RLS y roles de base de datos) · **ADR-0006** (OTP, sesiones, permisos por membresía, `admin_users` aparte con **2FA obligatorio**, impersonación) · **ADR-0007** (el teléfono no viaja; el click-to-chat es un salto en servidor) · **ADR-0010** (nunca datos de tarjeta, solo el token) · **ADR-0011** (la CSP del SSR) · **ADR-0012** (serializadores explícitos y límites de ritmo).
- **Requisitos:** §6 del brief, apartados de seguridad y de privacidad, y ADM-2, ADM-5 y ADM-6.
- **Fases:** transversal, dentro de cada bloque. No es una fase propia.

## Dependencias

- **Recibe de:** **Backend** las superficies a revisar · **DevOps** los roles de base de datos y el manejo de variables · **Frontend** las páginas donde comprobar la CSP · **Arquitecto** el ADR de retención y borrado.
- **Entrega a:** **Arquitecto** los escalados · **QA** los criterios de rechazo que se derivan de las garantías · **Luis** la lista de lo que exige la Ley 81 y qué falta para cumplirla.

## Invalidation trigger

- **Cuando aparezca un endpoint nuevo que devuelva datos de negocio**: hay que comprobar que **pasa por un serializador explícito** y que no arrastra el teléfono. Devolver el modelo entero es como se escapan los datos.
- **Cuando llegue la credencial de Meta**: el coste por mensaje pasa a ser real y **el límite por teléfono deja de ser solo seguridad y pasa a ser control de gasto**.
- **Cuando se elija pasarela (D5)**: hay que verificar que **ningún dato de tarjeta pasa por el servidor**, o el proyecto entra en alcance de PCI, que es un mundo distinto.
- **Cuando cambie la Ley 81 o su reglamento**, o cuando cambie la política de las tiendas sobre borrado de cuenta y privacidad.
- **Cuando se añada un origen o un recurso externo a la web**: la CSP hay que revisarla **en el navegador**, no con `curl`.
- **Cuando entre el rol de recepción** (v2): un actor nuevo con acceso a la agenda de todos y sin finanzas cambia el mapa de permisos entero.

## Definición de "hecho"

- La revisión deja **hallazgos concretos con su ruta y su reproducción**, no una lista de buenas prácticas.
- Lo que se endurece se **comprueba provocándolo**: la protección que no se ha visto actuar no está probada.
- Lo que no se puede arreglar en el momento va **a la tabla de deuda viva** con dueño y categoría, nunca a un párrafo.
- **Ninguna credencial viva aparece en la bitácora**, ni siquiera parcial.
- Deja entrada en `BITACORA/` con qué revisó, qué encontró y cómo se comprueba.

## Cómo se valida su trabajo (lo comprueba QA/Validador)

- [ ] Conectándose **con el usuario real de la aplicación**, un `SELECT` sin `WHERE` sobre una tabla de negocio **no devuelve filas ajenas**. Comprobado conectándose, no leyendo la configuración.
- [ ] El usuario de la aplicación **no es dueño de las tablas** y **no tiene `BYPASSRLS`**.
- [ ] El OTP está **guardado con hash**; agotar los intentos bloquea; pedir muchos códigos **frena con retroceso exponencial**.
- [ ] Cerrar sesión, borrar la cuenta o bloquear a un usuario **surten efecto ya**, no cuando caduque un token.
- [ ] **Ningún teléfono en claro** en un listado, un perfil público o una respuesta sin autorizar. Comprobado leyendo el JSON, no la pantalla.
- [ ] **Ningún campo de tarjeta** existe en ninguna tabla ni en ningún esquema de la API.
- [ ] El escaneo del diff **en español y en inglés** no encuentra nada, y el historial de git tampoco.
- [ ] Existe **borrado de cuenta desde dentro de la aplicación**, con política decidida tabla por tabla, y **no rompe la agenda de un negocio** al ejecutarse.
- [ ] La **política de cancelación se ve antes de reservar**, no después.
- [ ] La impersonación **avisa al negocio, caduca pronto y deja rastro**. Si le falta una de las tres, no pasa.
- [ ] **El inicio de sesión funciona en un navegador real** con la CSP puesta.
