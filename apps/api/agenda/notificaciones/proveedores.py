"""Cómo sale un mensaje al mundo. Un canal, un proveedor, una interfaz (ADR-0007).

Todo lo que hay aquí existe para que el resto del sistema **no sepa** si detrás hay una llamada
a Meta o un archivo de texto. La cola decide qué mandar; esto solo lo manda.

Hay una decisión que parece de comodidad y no lo es: **sin credenciales se usa el proveedor de
desarrollo**. No es un modo degradado ni un apaño para las pruebas — es lo que permite que
alguien clone el repositorio, levante el stack y vea el recordatorio de las 24 h escrito en un
archivo, sin pedirle una clave de Meta a nadie. Las plantillas de WhatsApp las aprueba Meta y
esa aprobación no está en nuestras manos; si el núcleo dependiera de ella, el núcleo estaría
parado.

La otra decisión es lo que este archivo **no** hace. `ProveedorWhatsApp` y `ProveedorCorreo`
son esqueletos honestos: comprueban sus credenciales y, cuando las tienen, fallan diciendo
exactamente qué falta por verificar contra el proveedor real. No se inventa aquí ni una URL ni
un formato de cuerpo: un cliente HTTP escrito de memoria contra una API que nadie ha llamado
tiene el mismo valor que no tener nada, con la diferencia de que parece que funciona.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import smtplib
import ssl
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from agenda.ajustes import Ajustes, obtener_ajustes

registro = logging.getLogger("agenda.notificaciones")

#: Los cuatro canales del esquema. El orden no significa nada; la preferencia la decide la cola.
CANALES: tuple[str, ...] = ("whatsapp", "email", "push", "sms")

#: Dónde escribe el proveedor de desarrollo cuando nadie le dice otra cosa. Se puede apuntar a
#: otro sitio con `AGENDA_BUZON_NOTIFICACIONES`, que es lo que hacen las pruebas para no
#: mezclar ejecuciones.
VARIABLE_DEL_BUZON = "AGENDA_BUZON_NOTIFICACIONES"


class ProveedorNoConfigurado(RuntimeError):
    """Se ha pedido mandar por un canal cuyo proveedor no tiene credenciales.

    **No es un error de dominio**: no lo provoca el usuario y no hay mensaje amable que
    enseñarle. Es un fallo de configuración del despliegue, y sale como tal para que se vea en
    los registros del trabajador en vez de convertirse en una notificación «fallida» silenciosa
    que nadie relaciona con una variable de entorno vacía.
    """


@dataclass(frozen=True)
class MensajeSaliente:
    """Lo que el proveedor necesita saber. **Nada de la cola viaja aquí dentro.**

    En concreto no viaja la fila de `notifications`: el proveedor no tiene por qué poder
    tocarla, y si la tuviera acabaría marcándola él, que es justo la responsabilidad que la
    separación entre decidir y entregar quiere evitar.
    """

    canal: str
    destino: str
    plantilla: str
    locale: str = "es-PA"
    variables: dict[str, Any] = field(default_factory=dict)
    #: Solo para correo y para el buzón de desarrollo. En WhatsApp el texto lo pone la
    #: plantilla aprobada, no nosotros.
    asunto: str | None = None
    cuerpo: str | None = None
    notificacion_id: uuid.UUID | None = None


@dataclass(frozen=True)
class ResultadoDeEnvio:
    """Lo que dijo el proveedor. Se guarda tal cual en `notification_deliveries`.

    `coste_minor` se rellena cuando el proveedor lo informa, porque es el dato que permite
    responder con números a «¿el recordatorio de 24 h vale lo que cuesta?». Vacío es vacío: no
    se estima por nuestra cuenta.
    """

    proveedor: str
    estado: str  # aceptado | rechazado
    id_en_el_proveedor: str | None = None
    coste_minor: int | None = None
    moneda: str | None = None
    crudo: dict[str, Any] = field(default_factory=dict)


class ProveedorDeMensajes(ABC):
    """La interfaz. Un proveedor acepta unos canales y sabe mandar por ellos.

    `enviar` tiene un contrato corto y estricto: **devuelve** si el proveedor aceptó el
    mensaje y **lanza** si no pudo mandarlo. Quien decide si eso se reintenta es la cola, que
    es la única que sabe cuántas veces se ha intentado ya.
    """

    nombre: str = "abstracto"
    canales: tuple[str, ...] = ()

    def acepta(self, canal: str) -> bool:
        return canal in self.canales

    @abstractmethod
    async def enviar(self, mensaje: MensajeSaliente) -> ResultadoDeEnvio: ...


class ProveedorDeDesarrollo(ProveedorDeMensajes):
    """Escribe el mensaje en el registro y en un archivo. **El que se usa sin credenciales.**

    El archivo es un JSON por línea y no un texto bonito a propósito: así una prueba puede
    leerlo y afirmar sobre él sin analizar prosa, y una persona puede seguirlo con `tail -f`
    mientras usa la web.
    """

    nombre = "desarrollo"
    canales = CANALES

    def __init__(self, buzon: Path | str | None = None) -> None:
        self.buzon = Path(buzon) if buzon is not None else _buzon_por_defecto()

    async def enviar(self, mensaje: MensajeSaliente) -> ResultadoDeEnvio:
        anotacion = {
            "instante": datetime.now(UTC).isoformat(),
            "canal": mensaje.canal,
            "destino": mensaje.destino,
            "plantilla": mensaje.plantilla,
            "locale": mensaje.locale,
            "variables": mensaje.variables,
            "asunto": mensaje.asunto,
            "cuerpo": mensaje.cuerpo,
            "notificacion_id": str(mensaje.notificacion_id) if mensaje.notificacion_id else None,
        }
        self.buzon.parent.mkdir(parents=True, exist_ok=True)
        with self.buzon.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(anotacion, ensure_ascii=False) + "\n")

        registro.info(
            "notificación %s por %s a %s (plantilla %s)",
            mensaje.notificacion_id,
            mensaje.canal,
            mensaje.destino,
            mensaje.plantilla,
        )
        return ResultadoDeEnvio(
            proveedor=self.nombre,
            estado="aceptado",
            # El identificador es nuestro y se nota que lo es. Que no se pueda confundir con
            # uno de Meta ahorra una investigación el día que alguien lo busque en su panel.
            id_en_el_proveedor=f"desarrollo-{uuid.uuid4().hex[:12]}",
            crudo=anotacion,
        )

    def mensajes(self) -> list[dict[str, Any]]:
        """Lo escrito hasta ahora, para que las pruebas afirmen sobre el efecto real."""
        if not self.buzon.exists():
            return []
        with self.buzon.open(encoding="utf-8") as archivo:
            return [json.loads(linea) for linea in archivo if linea.strip()]


class ProveedorWhatsApp(ProveedorDeMensajes):
    """WhatsApp Cloud API de Meta. **Esqueleto: falta la credencial y falta la aprobación.**

    Dos cosas bloquean este canal y ninguna la resuelve escribiendo código: el token de la
    cuenta y que Meta apruebe las plantillas. Mientras tanto esto comprueba lo que puede
    comprobar —que hay credenciales y que la plantilla lleva nombre en el proveedor— y falla
    con un mensaje que dice qué falta, en vez de simular un envío que no ocurrió.
    """

    nombre = "whatsapp_cloud"
    canales = ("whatsapp",)

    def __init__(self, token: str = "", phone_id: str = "") -> None:
        self.token = token
        self.phone_id = phone_id

    @property
    def configurado(self) -> bool:
        return bool(self.token and self.phone_id)

    async def enviar(self, mensaje: MensajeSaliente) -> ResultadoDeEnvio:
        if not self.configurado:
            raise ProveedorNoConfigurado(
                "WhatsApp no tiene credenciales: faltan WHATSAPP_TOKEN y WHATSAPP_PHONE_ID. "
                "Sin ellas el canal no se usa; con el entorno local se manda por el proveedor "
                "de desarrollo."
            )
        raise NotImplementedError(
            "El canal de WhatsApp está sin verificar contra Meta. Faltan la cuenta de negocio, "
            "el token permanente y las plantillas aprobadas; el cliente HTTP se escribe cuando "
            "haya con qué probarlo, no antes."
        )


class ProveedorCorreo(ProveedorDeMensajes):
    """Correo transaccional **por SMTP** (ADR-0024).

    El correo es el respaldo de WhatsApp y el canal de todo lo que no es urgente: la invitación
    al equipo y la recuperación de contraseña dependen de él.

    ## Por qué SMTP y no la API de un proveedor

    Por lo mismo que el almacén de fotos habla S3: **lo hablan todos**. Resend, SendGrid,
    Postmark, Amazon SES y Mailgun aceptan SMTP, así que elegir proveedor deja de ser una
    decisión de arquitectura y pasa a ser cinco variables de entorno. Escribir contra la API
    de uno concreto sería atar el código a una elección que todavía no está hecha — y que se
    puede cambiar el día que sus precios suban.

    El precio de SMTP es que **no devuelve identificador de mensaje ni coste**, y por eso
    `id_en_el_proveedor` y `coste_minor` se quedan vacíos: vacío es vacío y no se estima por
    nuestra cuenta. Quien quiera esos datos los tiene en el panel del proveedor.

    ## El envío va en un hilo aparte

    `smtplib` es de la biblioteca estándar y es **bloqueante**. Llamarlo directamente desde el
    trabajador pararía el bucle de eventos mientras un servidor de correo lento contesta, y con
    él pararía todo lo demás que ese proceso esté entregando.
    """

    nombre = "smtp"
    canales = ("email",)

    def __init__(
        self,
        *,
        host: str,
        puerto: int,
        usuario: str = "",
        contrasena: str = "",
        desde: str = "",
        tls: bool = True,
    ) -> None:
        self.host = host
        self.puerto = puerto
        self.usuario = usuario
        self.contrasena = contrasena
        self.desde = desde
        self.tls = tls

    @property
    def configurado(self) -> bool:
        # Un servidor y un remitente bastan: **el usuario y la contraseña no**, porque un
        # relé de la propia red no pide ninguno, y exigirlos dejaría ese caso fuera sin motivo.
        return bool(self.host and self.desde)

    def _mandar(self, mensaje: MensajeSaliente) -> None:
        """Lo bloqueante, para llamarlo desde un hilo."""
        correo = EmailMessage()
        correo["From"] = self.desde
        correo["To"] = mensaje.destino
        correo["Subject"] = mensaje.asunto or ""
        # Un identificador estable por notificación: es lo que deja rastrear un correo desde el
        # panel del proveedor hasta la fila que lo pidió, sin adivinar por la hora.
        if mensaje.notificacion_id is not None:
            correo["X-Agenda-Notificacion"] = str(mensaje.notificacion_id)
        correo.set_content(mensaje.cuerpo or "")

        with smtplib.SMTP(self.host, self.puerto, timeout=20) as servidor:
            if self.tls:
                servidor.starttls(context=ssl.create_default_context())
            if self.usuario:
                servidor.login(self.usuario, self.contrasena)
            servidor.send_message(correo)

    async def enviar(self, mensaje: MensajeSaliente) -> ResultadoDeEnvio:
        if not self.configurado:
            raise ProveedorNoConfigurado(
                "El correo no tiene servidor: faltan SMTP_HOST y SMTP_DESDE. Sin ellos el canal "
                "no se usa; en local se manda al buzón del docker-compose."
            )
        try:
            await asyncio.to_thread(self._mandar, mensaje)
        except smtplib.SMTPResponseException as fallo:
            # El servidor contestó y dijo que no. Se guarda su código y su frase tal cual: es
            # lo que distingue «esa dirección no existe» de «hoy no, vuelve luego».
            return ResultadoDeEnvio(
                proveedor=self.nombre,
                estado="rechazado",
                crudo={
                    "codigo": fallo.smtp_code,
                    "motivo": fallo.smtp_error.decode(errors="replace")
                    if isinstance(fallo.smtp_error, bytes)
                    else str(fallo.smtp_error),
                },
            )
        # Sin excepción, el servidor lo aceptó. **Aceptado no es entregado** y no se finge que
        # lo sea: lo que pase después —rebote, buzón lleno— lo cuenta el proveedor en su panel.
        return ResultadoDeEnvio(proveedor=self.nombre, estado="aceptado")


def registro_de_proveedores(
    *, ajustes: Ajustes | None = None, buzon: Path | str | None = None
) -> dict[str, ProveedorDeMensajes]:
    """El proveedor de cada canal, según haya credenciales o no.

    Un solo sitio decide esto. Si la elección estuviera repartida por los trabajos, apagar un
    canal dejaría de ser configuración y volvería a ser un despliegue, que es exactamente lo
    que ADR-0007 quiere evitar.
    """
    ajustes = ajustes or obtener_ajustes()
    desarrollo = ProveedorDeDesarrollo(buzon)

    # **El correo se manda de verdad siempre que haya a dónde**, también en local, porque en
    # local hay un servidor de correo en el propio `docker-compose`. No es un capricho: un
    # correo escrito en un fichero de registro no enseña que el enlace de la invitación estaba
    # roto, ni que el asunto salía vacío, ni que el acento del nombre del salón se rompía por el
    # camino. Un buzón que se abre en el navegador, sí. Y no le llega a nadie.
    correo: ProveedorDeMensajes = ProveedorCorreo(
        host=ajustes.smtp_host,
        puerto=ajustes.smtp_puerto,
        usuario=ajustes.smtp_usuario,
        contrasena=ajustes.smtp_contrasena,
        desde=ajustes.smtp_desde,
        tls=ajustes.smtp_tls,
    )
    if not correo.configurado:
        correo = desarrollo

    if ajustes.usa_proveedores_de_desarrollo:
        # Lo demás sí va al buzón de fichero: WhatsApp no se puede simular sin Meta, el push es
        # de la app y el SMS es el respaldo del OTP. Ahí el fichero lleva la conversación
        # completa en orden, que es como se lee cuando algo no cuadra.
        return {**dict.fromkeys(CANALES, desarrollo), "email": correo}

    return {
        "whatsapp": ProveedorWhatsApp(ajustes.whatsapp_token, ajustes.whatsapp_phone_id),
        "email": correo,
        # Push y SMS siguen sin proveedor real: push es de la app (Fase 3) y el SMS solo es el
        # respaldo del OTP. Mandarlos al buzón es más honesto que un esqueleto que no aporta.
        "push": desarrollo,
        "sms": desarrollo,
    }


def _buzon_por_defecto() -> Path:
    """Fuera del repositorio a propósito: un buzón versionado se acaba commiteando."""
    del_entorno = os.environ.get(VARIABLE_DEL_BUZON)
    if del_entorno:
        return Path(del_entorno)
    return Path(tempfile.gettempdir()) / "agenda-notificaciones" / "buzon.jsonl"
