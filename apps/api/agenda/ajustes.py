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
    origenes_permitidos: str = "http://localhost:3000,http://localhost:3100"

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
    redis_url: str = "redis://localhost:6380/0"

    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    sms_api_key: str = ""
    email_api_key: str = ""
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
