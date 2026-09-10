"""Configuración de la aplicación, leída del entorno.

Toda variable que se añada aquí se documenta **en la misma sesión** en `.env.example` y en
`docs/operacion/SECRETOS-Y-VARIABLES.md`: nombre y para qué sirve, nunca el valor.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Entorno(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCCION = "produccion"


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    entorno: Entorno = Entorno.LOCAL
    secret_key: str = "desarrollo-no-usar-en-produccion"
    nivel_log: str = "info"
    url_publica_web: str = "http://localhost:3000"
    # Orígenes que pueden llamar a esta API desde un navegador, separados por comas. Explícitos
    # y no `*`: con credenciales, un comodín regala las sesiones de todo el mundo.
    # `localhost` y `127.0.0.1` **no son el mismo origen** para el navegador, y entrar por uno
    # u otro es cuestión de qué escribió la persona en la barra. Faltando uno, la pantalla
    # carga pero ninguna petición sale, que es de los fallos más desconcertantes que hay.
    # Los puertos 3200, 3300 y 3400 son para levantar copias de la web mientras se
    # trabaja en paralelo. Sin ellos, esa copia carga la pantalla y **no sale ni una petición**,
    # que es el fallo más desconcertante que hay: parece un problema del código de la pantalla.
    origenes_permitidos: str = (
        "http://localhost:3000,http://localhost:3100,http://localhost:3200,http://localhost:3300,"
        "http://localhost:3400,"
        "http://127.0.0.1:3000,http://127.0.0.1:3100,http://127.0.0.1:3200,http://127.0.0.1:3300,"
        "http://127.0.0.1:3400"
    )

    # Panamá no tiene horario de verano, pero el instante se guarda en UTC igual: el modelo
    # tiene que aguantar España después (ADR-0003).
    zona_horaria_defecto: str = "America/Panama"
    # Los importes se guardan en centavos; esto es solo el código de moneda que los acompaña.
    moneda_defecto: str = "USD"

    database_url: str = "postgresql+asyncpg://agenda_api:agenda@localhost:5433/agenda"
    database_url_migraciones: str = "postgresql+psycopg://agenda_owner:agenda@localhost:5433/agenda"
    # Rol de solo lectura del marketplace. Es otra conexión, no un `SET ROLE`: un olvido con
    # una sola conexión dejaría una consulta pública corriendo con permisos de negocio.
    database_url_publico: str = "postgresql+asyncpg://agenda_publico:agenda@localhost:5433/agenda"
    # Rol del back-office. Tercera conexión y no un `SET ROLE`, por lo mismo que la pública:
    # si un endpoint de la consola compartiera conexión con la API del negocio, un fallo de
    # autorización allí tendría los permisos del equipo interno aquí.
    database_url_admin: str = "postgresql+asyncpg://agenda_admin:agenda@localhost:5433/agenda"
    redis_url: str = "redis://localhost:6380/0"

    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    sms_api_key: str = ""
    mapas_token: str = ""
    pasarela_api_key: str = ""
    sentry_dsn: str = ""

    # Valores por defecto de negocio que el brief deja configurables. Viven aquí como
    # semilla: cada negocio guarda los suyos, y el back-office podrá cambiarlos sin desplegar.
    granularidad_minutos: int = Field(default=15, ge=5, le=60)
    antelacion_minima_horas: int = Field(default=1, ge=0)
    antelacion_maxima_dias: int = Field(default=60, ge=1)
    ventana_cancelacion_horas: int = Field(default=2, ge=0)
    ventana_review_dias: int = Field(default=14, ge=1)

    # ── Cuánto se guarda cada cosa (Ley 81 · ADR-0025) ────────────────────────────────────
    #
    # La Ley 81 no dice solo «guarda los datos con cuidado»: dice **no los guardes más de lo que
    # haga falta**. Un plazo puesto aquí es una decisión revisable; sin plazo, la tabla crece
    # para siempre y el día que estorbe alguien la vacía con prisa y sin criterio.
    #: El rastro de las acciones internas: quién entró en qué negocio, quién forzó una
    #: cancelación, quién suplantó a quién. Doce meses cubre de sobra una reclamación —que llega
    #: en semanas, no en años— sin volverse un archivo histórico de la vida privada de nadie.
    retencion_auditoria_meses: int = Field(default=12, ge=1, le=120)
    #: **Este plazo no lo decide el producto: lo dice la DGI, y hay que confirmarlo con la
    #: asesoría.** Cinco años es el valor por defecto y equivocarse hacia abajo es un problema
    #: con Hacienda, así que **nada lo borra**: está aquí para que el día que se confirme haya
    #: un solo sitio donde ponerlo, no para que un trabajo empiece a borrar facturas.
    retencion_facturas_anos: int = Field(default=5, ge=1, le=20)

    # ── El correo transaccional, por SMTP (ADR-0024) ──────────────────────────────────────
    #
    # **SMTP y no la API de un proveedor concreto**, por el mismo motivo que el almacén habla
    # S3: lo hablan todos —Resend, SendGrid, Postmark, Amazon SES, Mailgun—, así que elegir
    # proveedor deja de ser una decisión de arquitectura y pasa a ser cinco variables.
    #
    # En local apunta al buzón del `docker-compose`, que enseña los correos en una web y no le
    # manda nada a nadie.
    smtp_host: str = "correo"
    smtp_puerto: int = 1025
    smtp_usuario: str = ""
    smtp_contrasena: str = ""
    #: El remitente. En un entorno publicado tiene que ser una dirección del dominio verificado,
    #: con SPF y DKIM puestos, o el correo acaba en la carpeta de basura de todo el mundo.
    smtp_desde: str = "Tanda <hola@localhost>"
    #: `STARTTLS`. Falso en local —el buzón de desarrollo no cifra— y **verdadero en cualquier
    #: otro sitio**: sin esto, el usuario y la contraseña del proveedor viajan en claro.
    smtp_tls: bool = False

    # ── El almacén de fotos, compatible con S3 (ADR-0023) ─────────────────────────────────
    #
    # Los valores por defecto apuntan al MinIO del `docker-compose`, para que una máquina
    # recién clonada pueda subir una foto sin credencial de nadie. **No son un secreto y no
    # pretenden serlo**: solo abren un almacén que vive en el portátil.
    #
    # `s3_endpoint` es la dirección que usa la API para firmar y para borrar —dentro de la red
    # de Docker—, y `s3_endpoint_publico` la que el **navegador** usa para subir. Son dos
    # porque `almacen:9000` no existe fuera de Docker y `localhost:9000` no existe dentro; con
    # una sola, o no firma la API o no sube el navegador, y el fallo no se parece a su causa.
    s3_endpoint: str = "http://almacen:9000"
    s3_endpoint_publico: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "m2g-agenda-media-dev"
    s3_access_key_id: str = "agenda-local"
    s3_secret_access_key: str = "agenda-local-secreta"

    #: Cuánto vale un permiso de subida. Cinco minutos: lo que tarda alguien en elegir una foto
    #: y que se suba con una conexión mala, y poco para que un permiso filtrado sirva de algo.
    s3_permiso_minutos: int = Field(default=5, ge=1, le=60)
    #: El tope de una foto. Cinco megas es una foto de móvil sin recortar; más que eso es
    #: alguien subiendo un archivo que no es una foto.
    s3_tamano_maximo_bytes: int = Field(default=5 * 1024 * 1024, ge=100_000)

    # Base de las URL de las fotos. Vacía significa «la clave ya es una ruta servible»
    # (`/fotos/spa.webp`) o una URL absoluta. Con el almacén en marcha se rellena con la
    # dirección pública del cubo y **no se toca ni una fila ni una pantalla**.
    url_base_media: str = "http://localhost:9000/m2g-agenda-media-dev"

    # La sesión del back-office caduca antes que la de un cliente y no se negocia: quien tiene
    # acceso a todos los negocios no puede dejarse la sesión abierta en un portátil.
    acceso_admin_minutos: int = Field(default=30, ge=5, le=240)
    refresco_admin_horas: int = Field(default=8, ge=1, le=72)

    # Cuenta de la consola que se crea con `python -m agenda.consola_alta`. Sin valor en el
    # repositorio: se pone en el `.env` de cada máquina y nunca se commitea.
    consola_email_inicial: str = ""
    consola_password_inicial: str = ""

    # La contraseña que comparten todas las cuentas de ejemplo de `python -m agenda.semilla`.
    # **No es un secreto y no pretende serlo**: la semilla se niega a correr fuera de local, y
    # todas esas cuentas se borran y se rehacen en cada carga. Está aquí, y no escrita dentro
    # del código, para poder cambiarla en una máquina sin tocar el repositorio.
    semilla_contrasena: str = "demo-panama-2026"

    @property
    def es_local(self) -> bool:
        return self.entorno is Entorno.LOCAL

    @property
    def usa_proveedores_de_desarrollo(self) -> bool:
        """Sin credenciales no se llama a nadie de fuera: se usa la implementación local.

        Es lo que permite que `make arriba` funcione en una máquina nueva sin ninguna
        credencial, y que las pruebas no dependan de Meta ni de la pasarela.
        """
        return self.es_local or not self.whatsapp_token


@lru_cache
def obtener_ajustes() -> Ajustes:
    return Ajustes()
