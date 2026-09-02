"""Errores de dominio y su forma en la API.

Todos los errores salen con la misma forma (ADR-0012):

    {"error": {"codigo": "SLOT_NO_DISPONIBLE", "mensaje": "…", "detalles": {…}}}

El **código es estable y lo consume el cliente**; el **mensaje es para leer** y puede cambiar
sin previo aviso. Esa distinción importa más de lo que parece: hay una app en tiendas que no se
actualiza cuando nosotros queremos, y si el cliente ramificara por el texto del mensaje,
cualquier corrección de una tilde rompería una versión antigua.

Los mensajes están escritos para enseñarlos tal cual a una persona, en español de Panamá y sin
jerga. «Ese horario se acaba de ocupar» es una frase que el dueño del salón entiende;
«conflicto de exclusión en staff_occupancy» no.
"""

from __future__ import annotations

from typing import Any


class ErrorDeDominio(Exception):
    """Algo que el usuario puede entender y, casi siempre, corregir."""

    codigo: str = "ERROR"
    estado_http: int = 400
    mensaje: str = "No se pudo completar la operación."

    def __init__(self, mensaje: str | None = None, **detalles: Any) -> None:
        self.mensaje = mensaje or self.mensaje
        self.detalles = detalles
        super().__init__(self.mensaje)

    def como_respuesta(self) -> dict[str, Any]:
        cuerpo: dict[str, Any] = {"codigo": self.codigo, "mensaje": self.mensaje}
        if self.detalles:
            cuerpo["detalles"] = self.detalles
        return {"error": cuerpo}


# ── Disponibilidad y reservas ─────────────────────────────────────────────────────────────


class SlotNoDisponible(ErrorDeDominio):
    """Otra persona confirmó ese hueco primero.

    Es el error que traduce la violación de la restricción de exclusión (`SQLSTATE 23P01`).
    Llega **al confirmar**, no al mirar, porque mirar no aparta nada: quien confirma compite.
    No se reintenta en silencio con el hueco siguiente — meterle a alguien una cita a otra hora
    sin que la haya elegido es peor que el error.
    """

    codigo = "SLOT_NO_DISPONIBLE"
    estado_http = 409
    mensaje = "Ese horario se acaba de ocupar. Elige otro y lo confirmamos enseguida."


class FueraDeAntelacion(ErrorDeDominio):
    codigo = "FUERA_DE_ANTELACION"
    estado_http = 422
    mensaje = "Esa hora ya no se puede reservar con tan poca antelación."


class FueraDeVentanaDeCancelacion(ErrorDeDominio):
    codigo = "FUERA_DE_VENTANA_DE_CANCELACION"
    estado_http = 422
    mensaje = "Ya pasó el plazo para cancelar por tu cuenta. Escríbele al negocio y lo arreglan."


class ReservaNoModificable(ErrorDeDominio):
    codigo = "RESERVA_NO_MODIFICABLE"
    estado_http = 409
    mensaje = "Esa reserva ya está cerrada y no se puede cambiar."


class ServicioNoDisponible(ErrorDeDominio):
    codigo = "SERVICIO_NO_DISPONIBLE"
    estado_http = 422
    mensaje = "Ese servicio ya no está disponible con ese profesional."


# ── Negocio ───────────────────────────────────────────────────────────────────────────────


class NegocioNoPublicado(ErrorDeDominio):
    codigo = "NEGOCIO_NO_PUBLICADO"
    estado_http = 404
    mensaje = "Este negocio todavía no está publicado."


class FaltaMinimoParaPublicar(ErrorDeDominio):
    """Mínimo de D11: un servicio activo, horario, ubicación y una foto."""

    codigo = "FALTA_MINIMO_PARA_PUBLICAR"
    estado_http = 422
    mensaje = "Faltan cosas por completar antes de publicar el negocio."


# ── Identidad ─────────────────────────────────────────────────────────────────────────────


class OtpInvalido(ErrorDeDominio):
    codigo = "OTP_INVALIDO"
    estado_http = 401
    # El mismo mensaje para código erróneo y para código caducado: distinguirlos le diría a
    # quien prueba códigos al azar cuándo va por buen camino.
    mensaje = "Ese código no es válido. Pide uno nuevo y vuelve a intentarlo."


class DemasiadosIntentos(ErrorDeDominio):
    codigo = "DEMASIADOS_INTENTOS"
    estado_http = 429
    mensaje = "Demasiados intentos seguidos. Espera un momento y vuelve a probar."


class NoAutorizado(ErrorDeDominio):
    codigo = "NO_AUTORIZADO"
    estado_http = 403
    mensaje = "No tienes permiso para hacer eso en este negocio."


class TelefonoNoVerificado(ErrorDeDominio):
    """D9: no hay reserva como invitado. El teléfono verificado es lo que sostiene el
    control de no-shows sin pedir un depósito."""

    codigo = "TELEFONO_NO_VERIFICADO"
    estado_http = 403
    mensaje = "Verifica tu teléfono para poder reservar."


class NoExiste(ErrorDeDominio):
    """Lo que se pidió no está, o está en otro negocio y por tanto **no está**.

    Es el mismo error en los dos casos a propósito: distinguir «no existe» de «existe pero no
    es tuyo» convierte cualquier listado en un detector de identificadores ajenos.
    """

    codigo = "NO_EXISTE"
    estado_http = 404
    mensaje = "Eso no existe o ya no está disponible."


class DatoInvalido(ErrorDeDominio):
    """El cuerpo cumple el esquema pero la regla de negocio no se cumple."""

    codigo = "DATO_INVALIDO"
    estado_http = 422
    mensaje = "Alguno de los datos enviados no es válido."


# ── Reseñas ───────────────────────────────────────────────────────────────────────────────


class ResenaNoPermitida(ErrorDeDominio):
    """REV-1 en una sola clase: sin cita completada, fuera de plazo o repetida.

    El mensaje concreto lo pone quien la lanza; el código es uno solo porque para el cliente
    todos significan lo mismo — esta reseña no se puede dejar — y ramificar por subcódigos le
    obligaría a mantener una lista que no le sirve para nada.
    """

    codigo = "RESENA_NO_PERMITIDA"
    estado_http = 422
    mensaje = "Esa reseña no se puede dejar."


class YaExiste(ErrorDeDominio):
    """Se intentó crear algo que ya estaba: una segunda reseña, una segunda respuesta."""

    codigo = "YA_EXISTE"
    estado_http = 409
    mensaje = "Eso ya existe y no se puede duplicar."


# ── Back-office ───────────────────────────────────────────────────────────────────────────


class CredencialesInvalidas(ErrorDeDominio):
    """Correo, contraseña o segundo factor incorrectos. **Los tres dan el mismo error.**

    Decir cuál de los tres falló le diría a quien prueba combinaciones por dónde va bien.
    """

    codigo = "CREDENCIALES_INVALIDAS"
    estado_http = 401
    mensaje = "No pudimos verificar esas credenciales."
