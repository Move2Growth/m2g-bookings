"""Lo que solo existe en el portal del dueño: el anuncio del salón y el fichaje.

Las otras cuatro piezas del portal —todos los calendarios, las finanzas, la lista de
profesionales y el mejor del mes— **no traen tabla nueva**, y eso no es un olvido: son
consultas sobre las citas que ya existen. Un agregado guardado se desincroniza el primer día
que alguien cancela una cita a mano, y entonces el panel de finanzas miente sin fallar.

Aquí viven las dos que sí necesitan filas propias:

* **`business_banners`** — la «publicidad flash» del encargo: un texto del salón, con vigencia,
  que sale en su propia ficha pública. **No es `ad_campaigns`**, que es el posicionamiento
  pagado del marketplace y se cobra (ADR-0010). Mezclarlas sería regalar la portada del
  marketplace a cualquiera que escriba un banner.
* **`staff_clock_events`** — la entrada y la salida de cada persona. Es **dato laboral**: no
  tiene, ni tendrá, política pública. Y solo existe para quien el dueño ha encendido uno a uno
  (`staff_profiles.clock_in_enabled`, apagado por defecto): un fichaje que aparece sin que
  nadie lo pida se lee como vigilancia.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin, TenantMixin
from agenda.modelos.comunes import CreadoEnMixin, MarcasDeTiempoMixin

#: Lo que cabe en un anuncio. Da para «2x1 en color hasta el domingo» y no para un folleto:
#: el banner se lee de un vistazo en la ficha, encima del horario.
LARGO_MAXIMO_ANUNCIO = 280


class BusinessBanner(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """El anuncio que el salón escribe para su propia ficha (punto 6 del encargo).

    Dos decisiones que se ven en la migración y no aquí:

    * **No lleva enlace.** Un campo de URL libre en una superficie pública es un redirector
      abierto y un vector de spam, y no hace falta para lo que se pidió: el anuncio es del
      salón y el botón para hablar con él ya existe.
    * **No puede haber dos anuncios activos que se pisen.** Lo impide una restricción de
      exclusión sobre el rango de vigencia, igual que las citas: así la ficha pública no tiene
      que elegir entre dos y el dueño se entera al guardar, no al mirar.
    """

    __tablename__ = "business_banners"

    message: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    #: `NULL` = sin fecha de fin. Es el caso del salón que anuncia algo permanente («abrimos
    #: los domingos») y no una promoción.
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            f"char_length(btrim(message)) BETWEEN 1 AND {LARGO_MAXIMO_ANUNCIO}",
            name="ck_business_banners_mensaje_con_texto",
        ),
        CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at", name="ck_business_banners_vigencia_coherente"
        ),
        # Parcial: la ficha pública solo mira los activos, y el índice completo acabaría
        # cargando con el histórico de promociones de todos los diciembres.
        Index(
            "ix_business_banners_vigentes",
            "business_id",
            "starts_at",
            postgresql_where=text("active"),
        ),
    )


class StaffClockEvent(IdMixin, TenantMixin, CreadoEnMixin, Base):
    """Una entrada o una salida. **Append-only y nunca pública.**

    Append-only de verdad: el rol de la aplicación tiene `SELECT` e `INSERT` y **no** tiene
    `UPDATE` ni `DELETE`, como `booking_events`. Un registro horario que se puede reescribir no
    prueba nada, ni a favor del salón ni a favor de quien trabaja allí; una equivocación se
    corrige con otro evento, no borrando el anterior.

    Y nunca pública: no hay política para `agenda_publico` ni permiso concedido, así que el
    marketplace no puede llegar aquí aunque un endpoint futuro lo intentara.
    """

    __tablename__ = "staff_clock_events"

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # `RESTRICT` y no `CASCADE`: dar de baja a alguien no puede borrar su registro horario.
        # La baja del equipo ya es lógica (`staff_profiles.deleted_at`), así que esto no
        # estorba a nadie.
        ForeignKey("staff_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # entrada | salida
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    #: Quién lo apuntó: la propia persona desde su móvil, o el dueño desde el mostrador.
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'profesional'"))
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("kind IN ('entrada','salida')", name="ck_staff_clock_events_kind_valido"),
        CheckConstraint(
            "source IN ('profesional','dueno')", name="ck_staff_clock_events_source_valido"
        ),
        Index(
            "ix_staff_clock_events_business_id_staff_id_occurred_at",
            "business_id",
            "staff_id",
            text("occurred_at DESC"),
        ),
    )
