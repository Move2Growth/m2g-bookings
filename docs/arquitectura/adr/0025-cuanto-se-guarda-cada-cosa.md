# ADR-0025 · Cuánto se guarda cada cosa, y qué no se borra nunca

- **Estado:** aceptada
- **Fecha:** 2026-09-10

## Contexto

La Ley 81 de Panamá no dice solo «guarda los datos con cuidado»: dice **no los guardes más de lo que
haga falta**. Tres preguntas quedaban abiertas —**P14, P15 y P16**— y las tres tenían que estar
contestadas **antes de que haya datos reales de personas**.

Las tres tenían ya una respuesta por defecto escrita. Lo que no tenían era código: un plazo que solo
vive en un documento no es un plazo, es una intención. Y sin plazo, `audit_logs` crece para siempre
— y el día que estorbe, alguien la vacía con prisa y sin criterio, que es la peor forma de borrar.

## Decisión

**[decisión · P14] El texto de una opinión sobrevive a su autor, anonimizado.** Un salón que reunió
cuarenta opiniones no puede perderlas porque un cliente se dé de baja, y quien las lee tampoco. Lo
resuelve la lápida del usuario —la fila sobrevive anonimizada porque de ella cuelgan reservas y
opiniones—, no un borrado por antigüedad. Ya estaba en el modelo; aquí queda fijado.

**[decisión · P15] El registro de auditoría se guarda doce meses.** Es el rastro de las acciones
internas: quién entró en qué negocio, quién forzó una cancelación, quién suplantó a quién. Doce
meses cubre de sobra una reclamación —que llega en semanas, no en años— sin convertir la tabla en un
archivo histórico de la vida privada de nadie. Es `RETENCION_AUDITORIA_MESES` y se cambia sin
desplegar.

**[decisión · P16] Nada fiscal se borra por antigüedad. Punto.** El plazo de las facturas no lo
decide el producto: lo dice la DGI. El valor por defecto son **cinco años** en
`RETENCION_FACTURAS_ANOS` y **lleva una marca visible: hay que confirmarlo con la asesoría**.
Mientras tanto, **ningún trabajo borra una factura** — hay una prueba que mete una de hace diez años
y comprueba que sigue ahí después del barrido. Se prefiere guardar de más a borrar de menos: lo
primero es una tabla grande, lo segundo es un problema con Hacienda.

**[decisión] El borrado va por lotes y con tope de vueltas.** Un `DELETE` de un millón de filas
mantiene una tabla bloqueada el rato que tarde, y el trabajo corre de madrugada aquí pero a esa hora
hay salones abiertos en otra zona. El tope de vueltas es explícito y no un `while True`: si algo va
mal —un reloj movido, un plazo puesto en cero— el trabajo se para y lo dice, en vez de vaciar la
tabla en silencio.

## Alternativas consideradas

- **Guardar la auditoría para siempre.** Es lo que había, y es lo que la Ley 81 pide no hacer.
- **Un plazo corto, de tres meses.** Descartado: una reclamación puede llegar meses después, y
  entonces la única prueba de qué hizo el equipo interno ya no existe.
- **Borrar también lo fiscal pasado el plazo.** Descartado hasta que la asesoría confirme el número.
  Un trabajo automático que borra facturas es exactamente el tipo de cosa que nadie revisa hasta que
  hace falta una.
- **Anonimizar la auditoría en vez de borrarla.** Interesante y descartado por ahora: un rastro
  anonimizado de quién suplantó a quién no sirve para lo que sirve un rastro de auditoría.

## Consecuencias

- El trabajo corre **una vez al día, de madrugada**, y no toca nada de un negocio: `audit_logs` es
  de la plataforma.
- **Falta la pantalla de «bórrame la cuenta»**, que es el otro lado de la Ley 81 y no lo cubre este
  ADR. El modelo ya la tiene prevista —la lápida está en `users`— pero el camino desde la pantalla
  no existe. Queda anotado como deuda viva.
- `RETENCION_FACTURAS_ANOS` es hoy **documentación ejecutable**: está para que el día que la asesoría
  confirme el número haya un solo sitio donde ponerlo.
