"""El profesional como entidad de primera: su perfil, sus números y el camino inverso.

Estas pruebas llaman a las funciones de los endpoints con la **sesión que usarían de verdad**
—el rol del marketplace para lo público, el de la aplicación para el panel—, porque la mitad
de lo que se comprueba aquí solo existe con ese rol puesto: qué se ve, qué se cuenta y qué no
se devuelve nunca.

Lo que se prueba, en orden de importancia:

1. **Cuánta gente ha atendido se calcula al leer** y solo cuenta citas completadas. Un
   contador guardado se desincroniza el primer día que alguien toca una cita a mano.
2. **La nota es bayesiana**, como la del negocio: una sola reseña de cinco no la pone en 5,00.
3. **El camino inverso funciona**: se llega a los huecos de una persona sin saber en qué salón
   trabaja.
4. **Ningún teléfono sale por una ruta pública**, ni siquiera enterrado en una reseña.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import agenda.bd
from agenda.api import publico as api_publico
from agenda.api import publico_profesionales as api_profesionales
from agenda.dominio.ranking import PesosRanking
from agenda.errores import NoExiste
from agenda.servicios import profesionales as servicio_profesionales
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_panel import (
    conexion_de_dueno,
    crear_cita_completada,
    manana_a_las,
    montar_salon,
)
from pruebas.bd.escenario_profesional import montar_salon_con_perfiles

pytestmark = pytest.mark.bd

URL_PUBLICA = URL_APP.replace("agenda_api:", "agenda_publico:")


@pytest.fixture(autouse=True)
def api_apuntando_a_la_base_de_pruebas(monkeypatch):
    """Redirige el motor **global** a la base de pruebas.

    Hace falta porque el perfil público cuenta las citas atendidas abriendo su propia sesión
    con el negocio fijado (`agenda.bd.sesion_de_negocio`), igual que hace la disponibilidad.
    Ese motor se construye al importar el módulo a partir de `DATABASE_URL` y por defecto
    apunta a la base de **desarrollo**: sin esto, la prueba monta el salón en un sitio y la
    función lo busca en otro.
    """
    motor = create_async_engine(URL_APP, poolclass=None)
    monkeypatch.setattr(
        agenda.bd,
        "crear_sesion",
        async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False),
    )
    yield


@asynccontextmanager
async def sesion_publica() -> AsyncIterator[AsyncSession]:
    motor = create_async_engine(URL_PUBLICA, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            yield sesion
    finally:
        await motor.dispose()


@asynccontextmanager
async def sesion_del_negocio(negocio_id: uuid.UUID) -> AsyncIterator[AsyncSession]:
    motor = create_async_engine(URL_APP, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            await sesion.execute(
                text("SELECT set_config('app.current_business_id', :negocio, true)"),
                {"negocio": str(negocio_id)},
            )
            yield sesion
    finally:
        await motor.dispose()


# ── Cuánta gente ha atendido ──────────────────────────────────────────────────────────────


async def test_solo_cuentan_las_citas_completadas_y_las_personas_no_se_repiten():
    """Los dos números del encargo, y la diferencia entre ellos.

    Kevin tiene tres citas cerradas con **dos** clientas y una cancelada. «Tres atendidas» y
    «dos personas» son las dos respuestas correctas a dos preguntas distintas; contar la
    cancelada sería decir que atendió a alguien que no fue.
    """
    montado = await montar_salon_con_perfiles()
    async with sesion_del_negocio(montado.salon.negocio_id) as sesion:
        contados = await servicio_profesionales.atendidos(
            sesion, montado.salon.negocio_id, [montado.salon.kevin.id, montado.salon.marielys.id]
        )

    kevin = contados[montado.salon.kevin.id]
    assert kevin.citas == montado.citas_completadas_de_kevin == 3
    assert kevin.clientes == montado.clientes_distintos_de_kevin == 2
    # Marielys solo tiene la cita futura del escenario base: nada completado todavía.
    assert montado.salon.marielys.id not in contados


async def test_cancelar_una_cita_a_mano_en_la_base_baja_el_numero_en_el_acto():
    """Es el motivo por el que no hay contador guardado, escrito como prueba.

    Con una columna, este `UPDATE` dejaría el perfil diciendo «3 atendidas» para siempre y
    nadie se enteraría hasta que alguien contara a mano.
    """
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                """
                UPDATE bookings SET status = 'cancelada_negocio'
                 WHERE staff_id = :staff AND status = 'completada'
                   AND starts_at = (SELECT min(starts_at) FROM bookings
                                     WHERE staff_id = :staff AND status = 'completada')
                """
            ),
            {"staff": montado.salon.kevin.id},
        )

    async with sesion_del_negocio(montado.salon.negocio_id) as sesion:
        contados = await servicio_profesionales.atendidos(
            sesion, montado.salon.negocio_id, [montado.salon.kevin.id]
        )
    assert contados[montado.salon.kevin.id].citas == 2


# ── La nota ───────────────────────────────────────────────────────────────────────────────


async def test_la_nota_del_profesional_es_bayesiana_y_no_la_media():
    """Una sola reseña de cinco estrellas **no** deja a nadie en 5,00 (REV-5, ADR-0009).

    Es la misma regla que gobierna el rating del negocio y por el mismo motivo: si no, quien
    tiene una reseña adelanta a quien lleva ochenta de 4,7, y el orden deja de significar nada.
    """
    salon = await montar_salon()
    cita = await crear_cita_completada(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        salon.dueno_user_id,
    )
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                """
                INSERT INTO reviews (business_id, booking_id, author_user_id, staff_id,
                                     rating, staff_rating, status)
                VALUES (:negocio, :cita, :autor, :staff, 5, 5, 'publicada')
                """
            ),
            {
                "negocio": salon.negocio_id,
                "cita": cita,
                "autor": salon.dueno_user_id,
                "staff": salon.kevin.id,
            },
        )

    pesos = PesosRanking()
    async with sesion_publica() as sesion:
        notas = await servicio_profesionales.notas(sesion, [salon.kevin.id], pesos)

    nota = notas[salon.kevin.id]
    assert nota.numero == 1
    assert nota.media == 5.0
    assert nota.puntuacion < 5.0
    # El valor exacto sale de los pesos configurables, no de una constante del código.
    esperado = (pesos.reviews_de_confianza * pesos.rating_medio_global + 5) / (
        pesos.reviews_de_confianza + 1
    )
    assert nota.puntuacion == round(esperado, 2)


async def test_quien_no_tiene_resenas_no_tiene_nota_inventada():
    """`null`, no la media global: enseñar la media de la plataforma como suya es inventarle
    una reputación que nadie le dio."""
    montado = await montar_salon_con_perfiles()
    async with sesion_publica() as sesion:
        equipo = await api_profesionales.equipo_del_negocio(montado.salon.slug, sesion)

    assert equipo, "el equipo visible no puede salir vacío"
    assert all(p.nota is None for p in equipo)


# ── El perfil público ─────────────────────────────────────────────────────────────────────


async def test_el_perfil_trae_lo_que_pidio_luis():
    """Fotos, servicios, reseñas, redes, cuánta gente ha atendido y su nota, en una petición."""
    montado = await montar_salon_con_perfiles()
    async with sesion_publica() as sesion:
        perfil = await api_profesionales.perfil_del_profesional(
            montado.salon.slug, montado.slug_de_kevin, sesion
        )

    assert perfil.nombre == "Kevin Ortega"
    assert perfil.titular == "Barbero. Fades y perfilado de barba"
    assert perfil.descripcion is not None
    assert perfil.anos_de_experiencia == 9
    assert perfil.citas_atendidas == 3
    assert perfil.clientes_atendidos == 2
    assert [s.id for s in perfil.catalogo] == [montado.salon.servicio_id]
    # Una foto atada al servicio y otra suelta: las dos mitades de `service_id` nulable.
    assert [f.id for f in perfil.trabajos] == [montado.foto_de_trabajo]
    assert perfil.trabajos[0].servicio == "Corte + barba"
    assert [f.id for f in perfil.galeria] == [montado.foto_de_galeria]
    # Se guarda el usuario; la dirección se compone al servir.
    assert perfil.redes.instagram == "kevincortes507"
    assert perfil.redes.instagram_url == "https://instagram.com/kevincortes507"
    assert perfil.redes.facebook is None


async def test_el_perfil_se_alcanza_por_slug_o_por_identificador():
    """El slug es lo que se comparte; el identificador es la salida para quien no tiene slug."""
    montado = await montar_salon_con_perfiles()
    async with sesion_publica() as sesion:
        por_slug = await api_profesionales.perfil_del_profesional(
            montado.salon.slug, montado.slug_de_kevin, sesion
        )
        por_id = await api_profesionales.perfil_del_profesional(
            montado.salon.slug, str(montado.salon.kevin.id), sesion
        )
    assert por_slug.id == por_id.id == montado.salon.kevin.id


async def test_un_profesional_oculto_no_tiene_perfil_publico():
    """Y da el **mismo** 404 que uno que no existe: distinguirlos sería un detector de fichas
    ocultas, que es información del salón y no de quien pregunta."""
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE staff_profiles SET visible_in_marketplace = false WHERE id = :id"),
            {"id": montado.salon.kevin.id},
        )

    async with sesion_publica() as sesion:
        with pytest.raises(NoExiste):
            await api_profesionales.perfil_del_profesional(
                montado.salon.slug, montado.slug_de_kevin, sesion
            )
        with pytest.raises(NoExiste):
            await api_profesionales.perfil_del_profesional(
                montado.salon.slug, "nadie-con-este-nombre", sesion
            )


async def test_el_perfil_publico_no_devuelve_ningun_telefono():
    """Garantía nº 3. Se comprueba sobre el **JSON entero**, no campo a campo.

    Mirar campo a campo comprueba los que uno recordó mirar; serializar y buscar la cadena
    encuentra también el que se coló dentro de una reseña o de un objeto anidado.
    """
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        telefono = (
            await sesion.execute(
                text("SELECT phone_e164 FROM business_clients WHERE id = :id"),
                {"id": montado.salon.cliente_de_kevin},
            )
        ).scalar_one()

    # Sin esto la prueba pasaría en verde buscando la cadena vacía, que está en todas partes
    # y en ninguna. Es el fallo silencioso clásico de una prueba de fuga.
    assert telefono and telefono.startswith("+507")

    async with sesion_publica() as sesion:
        perfil = await api_profesionales.perfil_del_profesional(
            montado.salon.slug, montado.slug_de_kevin, sesion
        )
        equipo = await api_profesionales.equipo_del_negocio(montado.salon.slug, sesion)
        encontrados = await api_profesionales.buscar_profesionales(sesion, texto="Kevin")

    for cuerpo in (perfil, *equipo, *encontrados):
        crudo = cuerpo.model_dump_json()
        assert telefono not in crudo
        assert "phone" not in crudo


# ── Elegir profesional primero ────────────────────────────────────────────────────────────


async def test_buscar_profesionales_por_nombre_y_por_titular():
    """Quien busca «Yaris» entra por aquí; quien busca «una barbería cerca», por la otra ruta."""
    montado = await montar_salon_con_perfiles()
    async with sesion_publica() as sesion:
        por_nombre = await api_profesionales.buscar_profesionales(
            sesion, texto="Kevin", negocio=montado.salon.slug
        )
        por_titular = await api_profesionales.buscar_profesionales(
            sesion, texto="Colorista", negocio=montado.salon.slug
        )

    assert [p.id for p in por_nombre] == [montado.salon.kevin.id]
    assert por_nombre[0].negocio_slug == montado.salon.slug
    assert [p.id for p in por_titular] == [montado.salon.marielys.id]


async def test_buscar_profesionales_por_la_categoria_del_servicio_que_prestan():
    """Por lo que hace la persona, no por lo que pone en el rótulo del salón."""
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        categoria = (
            await sesion.execute(
                text(
                    "SELECT c.slug FROM service_categories c "
                    "JOIN services s ON s.service_category_id = c.id WHERE s.id = :servicio"
                ),
                {"servicio": montado.salon.servicio_id},
            )
        ).scalar_one()
        # A Marielys se le quita el servicio: deja de aparecer en esa categoría aunque siga
        # trabajando en el mismo salón.
        await sesion.execute(
            text("DELETE FROM staff_services WHERE staff_id = :staff"),
            {"staff": montado.salon.marielys.id},
        )

    async with sesion_publica() as sesion:
        encontrados = await api_profesionales.buscar_profesionales(
            sesion, servicio=categoria, negocio=montado.salon.slug
        )

    assert [p.id for p in encontrados] == [montado.salon.kevin.id]


async def test_los_huecos_de_una_persona_se_piden_sin_saber_en_que_salon_trabaja():
    """El tercer paso del camino nuevo, y sale del **mismo motor** que la reserva de siempre.

    Se comprueba comparando las dos rutas: la de siempre —negocio + `profesional=`— y la
    nueva. Si dieran resultados distintos, habría dos motores, que es exactamente lo que el
    encargo dice que no puede pasar.
    """
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        for weekday in range(7):
            await sesion.execute(
                text(
                    """
                    INSERT INTO business_hours (business_id, weekday, opens_at, closes_at)
                    VALUES (:negocio, :dia, '09:00', '19:00')
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"negocio": montado.salon.negocio_id, "dia": weekday},
            )
            # Horario para **los dos**, a propósito: si solo lo tuviera Kevin, pedir «los
            # huecos de Kevin» y pedir «los huecos de cualquiera» darían lo mismo y la
            # prueba pasaría aunque el endpoint ignorase al profesional.
            for staff_id in (montado.salon.kevin.id, montado.salon.marielys.id):
                await sesion.execute(
                    text(
                        """
                        INSERT INTO staff_hours (business_id, staff_id, weekday, starts_at,
                                                 ends_at, kind)
                        VALUES (:negocio, :staff, :dia, '09:00', '19:00', 'trabajo')
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "negocio": montado.salon.negocio_id,
                        "staff": staff_id,
                        "dia": weekday,
                    },
                )

        # Un bloqueo **solo de Kevin** dentro del horario de apertura. Es lo que hace que las
        # dos preguntas —«los huecos de Kevin» y «los huecos de cualquiera»— den respuestas
        # distintas: sin él, la prueba pasaría aunque el endpoint ignorase al profesional.
        #
        # Las 15:00 UTC son las 10:00 en Panamá (UTC−5, sin horario de verano). Escribirlo en
        # UTC y comentarlo aquí es lo correcto: la aritmética de husos vive en el motor y solo
        # en el motor (ADR-0003).
        await sesion.execute(
            text(
                """
                INSERT INTO staff_occupancy (business_id, staff_id, kind, status, starts_at,
                                             ends_at, buffer_before_min, buffer_after_min,
                                             reason)
                VALUES (:negocio, :staff, 'bloqueo', 'activo', :inicio, :fin, 0, 0, 'Dentista')
                """
            ),
            {
                "negocio": montado.salon.negocio_id,
                "staff": montado.salon.kevin.id,
                "inicio": manana_a_las(15),
                "fin": manana_a_las(17),
            },
        )

    desde = manana_a_las(0)
    hasta = desde + timedelta(days=1)

    async with sesion_publica() as sesion:
        por_la_persona = await api_profesionales.disponibilidad_del_profesional(
            montado.salon.kevin.id,
            sesion,
            servicios=[montado.salon.servicio_id],
            desde=desde,
            hasta=hasta,
        )
        por_el_salon = await api_publico.disponibilidad(
            montado.salon.slug,
            sesion,
            servicios=[montado.salon.servicio_id],
            desde=desde,
            hasta=hasta,
            profesional=montado.salon.kevin.id,
        )

    assert por_la_persona.slots, "el barbero tiene horario: tiene que haber huecos"
    assert [(s.inicio, s.fin) for s in por_la_persona.slots] == [
        (s.inicio, s.fin) for s in por_el_salon.slots
    ]
    assert all(s.profesional_id == montado.salon.kevin.id for s in por_la_persona.slots)
    assert por_la_persona.zona == "America/Panama"

    # Y lo que de verdad demuestra que se le preguntó **a él**: las dos horas que tiene
    # bloqueadas no se ofrecen, aunque su compañera esté libre a esa hora. Si el endpoint
    # calculara «cualquiera disponible», estas horas saldrían a nombre de Marielys.
    bloqueado_desde, bloqueado_hasta = manana_a_las(15), manana_a_las(17)
    assert all(
        s.fin <= bloqueado_desde or s.inicio >= bloqueado_hasta for s in por_la_persona.slots
    )


async def test_la_ficha_del_salon_enseña_quien_hizo_que():
    """La frase de Luis, en el perfil del negocio: la foto del servicio lleva nombre al lado."""
    montado = await montar_salon_con_perfiles()
    async with sesion_publica() as sesion:
        ficha = await api_publico.perfil(montado.salon.slug, sesion)

    servicio = next(s for s in ficha.servicios if s.id == montado.salon.servicio_id)
    assert [t.id for t in servicio.trabajos] == [montado.foto_de_trabajo]
    assert servicio.trabajos[0].profesional == "Kevin Ortega"
    assert servicio.trabajos[0].profesional_id == montado.salon.kevin.id
    # Y el equipo de la ficha ya trae el enlace a su perfil.
    kevin = next(p for p in ficha.equipo if p.id == montado.salon.kevin.id)
    assert kevin.slug == montado.slug_de_kevin
    assert kevin.titular == "Barbero. Fades y perfilado de barba"


async def test_una_foto_de_alguien_oculto_no_se_pinta_en_la_ficha_del_servicio():
    """Sin nombre al lado, la foto es decoración; con el nombre de alguien oculto, es una fuga
    pequeña. Ninguna de las dos: no se pinta."""
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE staff_profiles SET visible_in_marketplace = false WHERE id = :id"),
            {"id": montado.salon.kevin.id},
        )

    async with sesion_publica() as sesion:
        ficha = await api_publico.perfil(montado.salon.slug, sesion)

    servicio = next(s for s in ficha.servicios if s.id == montado.salon.servicio_id)
    assert servicio.trabajos == []


# ── El slug ───────────────────────────────────────────────────────────────────────────────


async def test_el_slug_se_desempata_dentro_del_salon():
    """Dos personas con el mismo nombre en el mismo salón: la segunda es `-2`, no un error."""
    salon = await montar_salon()
    async with sesion_del_negocio(salon.negocio_id) as sesion:
        primero = await servicio_profesionales.slug_libre(sesion, salon.negocio_id, "Yaris Beitía")
        await sesion.execute(
            text("UPDATE staff_profiles SET slug = :slug WHERE id = :id"),
            {"slug": primero, "id": salon.kevin.id},
        )
        segundo = await servicio_profesionales.slug_libre(sesion, salon.negocio_id, "Yaris Beitía")

    assert primero == "yaris-beitia"
    assert segundo == "yaris-beitia-2"


async def test_editar_el_propio_slug_no_choca_consigo_mismo():
    """Guardar el perfil sin cambiar el slug no puede convertirlo en `-2` cada vez."""
    salon = await montar_salon()
    async with sesion_del_negocio(salon.negocio_id) as sesion:
        await sesion.execute(
            text("UPDATE staff_profiles SET slug = 'yaris' WHERE id = :id"),
            {"id": salon.kevin.id},
        )
        de_nuevo = await servicio_profesionales.slug_libre(
            sesion, salon.negocio_id, "yaris", excluir_id=salon.kevin.id
        )
    assert de_nuevo == "yaris"


async def test_buscar_personas_por_distancia_las_ordena_de_cerca_a_lejos():
    """`distancia_metros` viajaba en la respuesta y venía **siempre nulo**: un campo que miente.

    Se comprueba con dos salones separados y un punto pegado a uno de ellos. Lo que importa no es
    el número exacto —eso lo calcula PostGIS— sino que la lista salga en el orden que promete: si
    ordenar por distancia devolviera el orden de siempre, la pantalla mandaría a la gente al otro
    lado de la ciudad diciéndole que es lo más cercano.
    """
    cerca = await montar_salon_con_perfiles()
    lejos = await montar_salon_con_perfiles()

    marca = uuid.uuid4().hex[:8]
    async with conexion_de_dueno() as duenno:
        # **Se les crea la ubicación aquí**: el escenario base no la pone, y sin ella el filtro
        # por radio los descarta. Esa fue la trampa de la primera versión de esta prueba, que
        # comparaba una lista **vacía** consigo misma y pasaba también con el orden desactivado.
        # Ciudad de Panamá, y el segundo a unos siete kilómetros.
        for negocio_id, longitud, etiqueta in (
            (cerca.salon.negocio_id, -79.5231, "Obarrio"),
            (lejos.salon.negocio_id, -79.4600, "Costa del Este"),
        ):
            await duenno.execute(
                text(
                    "INSERT INTO locations (business_id, address_line, geo)"
                    " VALUES (:id, :donde, ST_SetSRID(ST_MakePoint(:lon, 8.9819), 4326))"
                ),
                {"id": negocio_id, "donde": etiqueta, "lon": longitud},
            )
        # **Los nombres se ponen al revés a propósito.** Sin esto, el orden por defecto —por
        # nombre de salón— podía coincidir con el de distancia y la prueba pasaba igual con el
        # orden desactivado, que es lo mismo que no probar nada. Se comprobó quitándolo.
        for negocio_id, nombre in (
            (lejos.salon.negocio_id, f"AAA lejos {marca}"),
            (cerca.salon.negocio_id, f"ZZZ cerca {marca}"),
        ):
            await duenno.execute(
                text("UPDATE businesses SET display_name = :nombre WHERE id = :id"),
                {"nombre": nombre, "id": negocio_id},
            )
            # La marca va también en el titular de su gente: el buscador filtra por la persona,
            # no por el salón, y hace falta acotar la búsqueda a estos dos y no a los cien que
            # deja cada ejecución anterior en la base de pruebas.
            await duenno.execute(
                text("UPDATE staff_profiles SET headline = :marca WHERE business_id = :id"),
                {"marca": marca, "id": negocio_id},
            )

    async with sesion_publica() as sesion:
        resultados = await api_profesionales.buscar_profesionales(
            sesion,
            texto=marca,
            longitud=-79.5231,
            latitud=8.9819,
            orden="distancia",
            radio_metros=20_000,
        )

    assert resultados, "El texto de búsqueda tiene que acotar a los dos salones de esta prueba."
    assert resultados[0].negocio.startswith("ZZZ cerca"), (
        "El primero tiene que ser el de al lado. Si sale el que se llama «AAA», lo que ordena es "
        "el nombre y no la distancia."
    )
    distancias = [r.distancia_metros for r in resultados]
    assert all(d is not None for d in distancias), (
        "Con un punto de búsqueda, la distancia no puede venir nula: es el campo que decide el "
        "orden y la pantalla lo enseña."
    )
    assert distancias == sorted(distancias), "La lista tiene que salir de cerca a lejos."

    # Y sin decir desde dónde, no se inventa una distancia ni un orden.
    async with sesion_publica() as sesion:
        sin_punto = await api_profesionales.buscar_profesionales(
            sesion, texto=marca, orden="distancia"
        )
    assert all(r.distancia_metros is None for r in sin_punto)
