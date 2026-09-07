"""Un salón con dos profesionales que ya tienen perfil público, fotos e historial.

Monta lo que hace falta para probar el encargo del 7 de septiembre §3: slug, titular, redes,
fotos de galería y de trabajo, citas **completadas** —que son las que cuentan para «cuánta
gente ha atendido»— y una reseña.

Se monta con el rol **dueño**, que se salta la seguridad por fila. Es el único sitio donde eso
es correcto: preparar el escenario exige escribir filas que después, desde el rol de la
aplicación o el del marketplace, precisamente **no** se van a poder ver.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from pruebas.bd.escenario_panel import SalonConEquipo, conexion_de_dueno, montar_salon


@dataclass(frozen=True)
class SalonConPerfiles:
    """El salón de `montar_salon`, ya con la identidad pública del equipo puesta."""

    salon: SalonConEquipo
    #: `slug` de cada quien dentro de este salón.
    slug_de_kevin: str
    slug_de_marielys: str
    #: Fotos de Kevin: una atada al servicio («esto lo hizo él») y una suelta (su galería).
    foto_de_trabajo: uuid.UUID
    foto_de_galeria: uuid.UUID
    #: Cuántas citas completadas tiene cada uno y a cuánta gente distinta atendió.
    citas_completadas_de_kevin: int
    clientes_distintos_de_kevin: int


async def montar_salon_con_perfiles(*, sufijo: str | None = None) -> SalonConPerfiles:
    salon = await montar_salon(sufijo)
    marca = salon.slug.replace("barberia-", "")

    slug_kevin = f"kevin-{marca}"
    slug_marielys = f"marielys-{marca}"

    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                """
                UPDATE staff_profiles
                   SET slug = :slug,
                       headline = 'Barbero. Fades y perfilado de barba',
                       bio = 'Nueve años detrás de la silla, en El Cangrejo.',
                       years_experience = 9,
                       instagram = 'kevincortes507',
                       x = 'kevincortes'
                 WHERE id = :id
                """
            ),
            {"slug": slug_kevin, "id": salon.kevin.id},
        )
        await sesion.execute(
            text("UPDATE staff_profiles SET slug = :slug, headline = 'Colorista' WHERE id = :id"),
            {"slug": slug_marielys, "id": salon.marielys.id},
        )

        foto_trabajo = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO staff_media (id, business_id, staff_id, service_id, storage_key,
                                             alt_text, position, moderation_status)
                    VALUES (gen_random_uuid(), :negocio, :staff, :servicio, '/fotos/spa.webp',
                            'Corte + barba por Kevin', 0, 'aprobada')
                    RETURNING id
                    """
                ),
                {
                    "negocio": salon.negocio_id,
                    "staff": salon.kevin.id,
                    "servicio": salon.servicio_id,
                },
            )
        ).scalar_one()

        foto_galeria = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO staff_media (id, business_id, staff_id, service_id, storage_key,
                                             position, moderation_status)
                    VALUES (gen_random_uuid(), :negocio, :staff, NULL, '/fotos/unas.webp',
                            1, 'aprobada')
                    RETURNING id
                    """
                ),
                {"negocio": salon.negocio_id, "staff": salon.kevin.id},
            )
        ).scalar_one()

        # Tres citas de Kevin ya cerradas con **dos** clientas distintas: es lo que distingue
        # «tres citas atendidas» de «dos personas atendidas», y las dos cifras se enseñan.
        await _cita_pasada(sesion, salon, salon.kevin.id, salon.cliente_de_kevin, dias=2)
        await _cita_pasada(sesion, salon, salon.kevin.id, salon.cliente_de_kevin, dias=3)
        await _cita_pasada(sesion, salon, salon.kevin.id, salon.cliente_de_marielys, dias=4)
        # Y una cancelada, que **no** cuenta: si contara, el número diría lo que no es.
        await _cita_pasada(
            sesion,
            salon,
            salon.kevin.id,
            salon.cliente_de_kevin,
            dias=5,
            estado="cancelada_cliente",
        )

    return SalonConPerfiles(
        salon=salon,
        slug_de_kevin=slug_kevin,
        slug_de_marielys=slug_marielys,
        foto_de_trabajo=foto_trabajo,
        foto_de_galeria=foto_galeria,
        citas_completadas_de_kevin=3,
        clientes_distintos_de_kevin=2,
    )


async def _cita_pasada(
    sesion,
    salon: SalonConEquipo,
    staff_id: uuid.UUID,
    cliente_id: uuid.UUID,
    *,
    dias: int,
    estado: str = "completada",
) -> uuid.UUID:
    """Una cita de hace unos días, con su ocupación, como la escribe la API."""
    inicio = (datetime.now(UTC) - timedelta(days=dias)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    fin = inicio + timedelta(minutes=45)

    reserva_id = (
        await sesion.execute(
            text(
                """
                INSERT INTO bookings (business_id, staff_id, business_client_id, status,
                                      starts_at, ends_at, total_duration_min,
                                      total_amount_minor, source)
                VALUES (:negocio, :staff, :cliente, :estado, :inicio, :fin, 45, 1800,
                        'negocio_manual')
                RETURNING id
                """
            ),
            {
                "negocio": salon.negocio_id,
                "staff": staff_id,
                "cliente": cliente_id,
                "estado": estado,
                "inicio": inicio,
                "fin": fin,
            },
        )
    ).scalar_one()

    await sesion.execute(
        text(
            """
            INSERT INTO staff_occupancy (business_id, staff_id, kind, status, booking_id,
                                         starts_at, ends_at, buffer_before_min, buffer_after_min)
            VALUES (:negocio, :staff, 'reserva', :estado, :reserva, :inicio, :fin, 0, 0)
            """
        ),
        {
            "negocio": salon.negocio_id,
            "staff": staff_id,
            "estado": estado,
            "reserva": reserva_id,
            "inicio": inicio,
            "fin": fin,
        },
    )
    return reserva_id
