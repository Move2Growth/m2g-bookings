"""El panel: el profesional editando lo suyo y el dueño gestionando el equipo.

Las sesiones se montan **igual que las monta `dependencias.py`** —negocio fijado y, cuando
quien pregunta no es el dueño, también el profesional— porque si no, esto probaría un mundo
que no existe: la mitad de las reglas de este módulo las aplica PostgreSQL y solo aparecen con
`app.current_staff_id` declarado.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.api import negocio_equipo as api_equipo
from agenda.api import perfil_profesional as api_perfil
from agenda.api.dependencias import Identidad
from agenda.errores import DatoInvalido, NoAutorizado, NoExiste
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_panel import montar_salon
from pruebas.bd.escenario_profesional import montar_salon_con_perfiles

pytestmark = pytest.mark.bd


@asynccontextmanager
async def como(
    negocio_id: uuid.UUID,
    usuario_id: uuid.UUID,
    *,
    rol: str,
    staff_id: uuid.UUID | None = None,
) -> AsyncIterator[tuple[AsyncSession, Identidad]]:
    """Una sesión de `/negocio/…` o de `/mi/…`, con lo mismo declarado que en producción."""
    motor = create_async_engine(URL_APP, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    identidad = Identidad(usuario_id=usuario_id, negocio_id=negocio_id, rol=rol)
    identidad.staff_id = staff_id
    try:
        async with crear() as sesion, sesion.begin():
            await sesion.execute(
                text("SELECT set_config('app.current_business_id', :negocio, true)"),
                {"negocio": str(negocio_id)},
            )
            if staff_id is not None:
                await sesion.execute(
                    text("SELECT set_config('app.current_staff_id', :staff, true)"),
                    {"staff": str(staff_id)},
                )
            yield sesion, identidad
    finally:
        await motor.dispose()


# ── El profesional, sobre su ficha ────────────────────────────────────────────────────────


async def test_el_profesional_edita_su_perfil_y_le_normalizan_las_redes():
    """Pega la URL de Instagram y se guarda **el usuario**. Es el caso normal, no el raro."""
    montado = await montar_salon_con_perfiles()
    async with como(
        montado.salon.negocio_id,
        montado.salon.kevin.user_id,
        rol="profesional",
        staff_id=montado.salon.kevin.id,
    ) as sesion_negocio:
        perfil = await api_perfil.editar_mi_perfil(
            api_perfil.CambioDeMiPerfil(
                titular="Barbero. Fades, barba y cejas",
                descripcion="Diez años en El Cangrejo.",
                anos_de_experiencia=10,
                instagram="https://www.instagram.com/kevin.cortes/",
                facebook="@kevin.cortes.barber",
            ),
            sesion_negocio,
        )

    assert perfil.titular == "Barbero. Fades, barba y cejas"
    assert perfil.anos_de_experiencia == 10
    assert perfil.instagram == "kevin.cortes"
    assert perfil.instagram_url == "https://instagram.com/kevin.cortes"
    assert perfil.facebook == "kevin.cortes.barber"
    # Y lo que no puede tocar sigue como estaba: lo devuelve para poder explicarlo en pantalla.
    assert perfil.activo is True
    assert perfil.visible_en_marketplace is True
    # Los números salen calculados, no de un campo que se pueda mandar.
    assert perfil.citas_atendidas == 3


async def test_un_enlace_a_otro_sitio_no_entra_en_el_campo_de_una_red():
    """El perfil público no es un tablón de anuncios. Y el error dice qué campo falla."""
    montado = await montar_salon_con_perfiles()
    async with como(
        montado.salon.negocio_id,
        montado.salon.kevin.user_id,
        rol="profesional",
        staff_id=montado.salon.kevin.id,
    ) as sesion_negocio:
        with pytest.raises(DatoInvalido) as fallo:
            await api_perfil.editar_mi_perfil(
                api_perfil.CambioDeMiPerfil(instagram="https://sitio-cualquiera.com/promo"),
                sesion_negocio,
            )
    assert fallo.value.detalles["campo"] == "instagram"


async def test_una_ficha_sin_slug_se_queda_con_uno_al_guardar_el_perfil():
    """La red de seguridad de que nadie acabe sin URL pública.

    Una ficha creada desde el mostrador antes de que existiera el slug —o por una vía que se
    olvide de ponerlo— gana el suyo la primera vez que su titular toca el perfil.
    """
    salon = await montar_salon()
    async with como(
        salon.negocio_id, salon.kevin.user_id, rol="profesional", staff_id=salon.kevin.id
    ) as sesion_negocio:
        perfil = await api_perfil.editar_mi_perfil(
            api_perfil.CambioDeMiPerfil(titular="Barbero"), sesion_negocio
        )
    assert perfil.slug == "kevin-ortega"


async def test_el_profesional_no_puede_editar_la_ficha_de_su_companera_por_esta_puerta():
    """El endpoint del dueño le contesta `403` **antes** de tocar nada.

    Sin este `exigir_dueno`, la política de la base dejaría leer y bloquearía el `UPDATE`, el
    `UPDATE` no tocaría ninguna fila y el ORM devolvería un 500 en vez de un «no tienes
    permiso». Es el mismo tropiezo que ya documentó la bitácora 0001.
    """
    montado = await montar_salon_con_perfiles()
    async with como(
        montado.salon.negocio_id,
        montado.salon.kevin.user_id,
        rol="profesional",
        staff_id=montado.salon.kevin.id,
    ) as sesion_negocio:
        with pytest.raises(NoAutorizado):
            await api_equipo.editar_profesional(
                montado.salon.marielys.id,
                api_equipo.CambioDeProfesional(titular="Yo mando aquí"),
                sesion_negocio,
            )


async def test_quien_no_tiene_ficha_de_profesional_lo_sabe_por_el_mensaje():
    """Un dueño que no atiende no tiene perfil público, y eso se dice, no se inventa."""
    salon = await montar_salon()
    async with como(salon.negocio_id, salon.dueno_user_id, rol="dueno") as sesion_negocio:
        with pytest.raises(NoAutorizado):
            await api_perfil.leer_mi_perfil(sesion_negocio)


# ── Las fotos ─────────────────────────────────────────────────────────────────────────────


async def test_el_profesional_sube_una_foto_y_la_ata_a_un_servicio_del_salon():
    """«Que se vea quién hizo qué», que es como lo pidió Luis."""
    montado = await montar_salon_con_perfiles()
    async with como(
        montado.salon.negocio_id,
        montado.salon.kevin.user_id,
        rol="profesional",
        staff_id=montado.salon.kevin.id,
    ) as sesion_negocio:
        suelta = await api_perfil.anadir_mi_foto(
            api_perfil.NuevaFoto(clave="/fotos/spa.webp", descripcion="Mi silla"),
            sesion_negocio,
        )
        assert suelta.servicio_id is None

        atada = await api_perfil.editar_mi_foto(
            suelta.id,
            api_perfil.CambioDeFoto(servicio_id=montado.salon.servicio_id),
            sesion_negocio,
        )
        assert atada.servicio_id == montado.salon.servicio_id

        # Y se puede devolver a la galería. `servicio_id: null` significa «no lo cambies», así
        # que quitarlo es una petición explícita y no un descuido de serialización.
        devuelta = await api_perfil.editar_mi_foto(
            suelta.id, api_perfil.CambioDeFoto(quitar_servicio=True), sesion_negocio
        )
        assert devuelta.servicio_id is None


async def test_no_se_puede_atar_una_foto_a_un_servicio_de_otro_salon():
    """Si se pudiera, «quién hizo qué» apuntaría a un servicio que esa persona no presta."""
    montado = await montar_salon_con_perfiles()
    otro = await montar_salon()

    async with como(
        montado.salon.negocio_id,
        montado.salon.kevin.user_id,
        rol="profesional",
        staff_id=montado.salon.kevin.id,
    ) as sesion_negocio:
        with pytest.raises(DatoInvalido):
            await api_perfil.anadir_mi_foto(
                api_perfil.NuevaFoto(clave="/fotos/spa.webp", servicio_id=otro.servicio_id),
                sesion_negocio,
            )


async def test_el_dueno_sube_el_trabajo_de_su_equipo():
    """Lo normal cuando el barbero no usa la aplicación: la sube quien lleva el salón."""
    montado = await montar_salon_con_perfiles()
    async with como(
        montado.salon.negocio_id, montado.salon.dueno_user_id, rol="dueno"
    ) as sesion_negocio:
        foto = await api_perfil.anadir_foto_del_equipo(
            montado.salon.marielys.id,
            api_perfil.NuevaFoto(clave="/fotos/unas.webp", servicio_id=montado.salon.servicio_id),
            sesion_negocio,
        )
        del_equipo = await api_perfil.listar_fotos_del_equipo(
            montado.salon.marielys.id, sesion_negocio, solo_servicio=montado.salon.servicio_id
        )
    assert [f.id for f in del_equipo] == [foto.id]


async def test_un_profesional_no_sube_fotos_a_nombre_de_otro_ni_por_la_puerta_del_dueno():
    montado = await montar_salon_con_perfiles()
    async with como(
        montado.salon.negocio_id,
        montado.salon.kevin.user_id,
        rol="profesional",
        staff_id=montado.salon.kevin.id,
    ) as sesion_negocio:
        with pytest.raises(NoAutorizado):
            await api_perfil.anadir_foto_del_equipo(
                montado.salon.marielys.id,
                api_perfil.NuevaFoto(clave="/fotos/spa.webp"),
                sesion_negocio,
            )


async def test_borrar_una_foto_que_no_es_tuya_da_el_mismo_404_que_una_que_no_existe():
    """Distinguirlos convertiría el endpoint en un detector de identificadores ajenos."""
    montado = await montar_salon_con_perfiles()
    async with como(
        montado.salon.negocio_id,
        montado.salon.marielys.user_id,
        rol="profesional",
        staff_id=montado.salon.marielys.id,
    ) as sesion_negocio:
        with pytest.raises(NoExiste):
            await api_perfil.quitar_mi_foto(montado.foto_de_trabajo, sesion_negocio)
        with pytest.raises(NoExiste):
            await api_perfil.quitar_mi_foto(uuid.uuid4(), sesion_negocio)


# ── El dueño, sobre el equipo ─────────────────────────────────────────────────────────────


async def test_el_dueno_pone_el_perfil_publico_de_alguien_del_equipo():
    """El equipo lo gestiona el dueño (STF-3), y eso incluye el slug y las redes."""
    montado = await montar_salon_con_perfiles()
    async with como(
        montado.salon.negocio_id, montado.salon.dueno_user_id, rol="dueno"
    ) as sesion_negocio:
        ficha = await api_equipo.editar_profesional(
            montado.salon.marielys.id,
            api_equipo.CambioDeProfesional(
                titular="Colorista. Balayage y corrección",
                anos_de_experiencia=12,
                instagram="@marielys.color",
                slug="Marielys Ruiz",
            ),
            sesion_negocio,
        )

    assert ficha.titular == "Colorista. Balayage y corrección"
    assert ficha.anos_de_experiencia == 12
    assert ficha.instagram == "marielys.color"
    # El slug entra como texto libre y sale como URL: es lo que evita un `/{negocio}/Marielys
    # Ruiz` con un espacio dentro.
    assert ficha.slug == "marielys-ruiz"
