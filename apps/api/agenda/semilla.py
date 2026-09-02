"""Datos de ejemplo para desarrollo: un pedazo de Ciudad de Panamá.

    python -m agenda.semilla

**Esto no es decoración: es material de prueba.** Con «Servicio 1 · 100,00» no se ve que un
balayage de tres horas no cabe en el hueco de las cinco de la tarde, ni que el buffer de
limpieza deja fuera la última cita del día. Por eso hay cuatro negocios con horarios distintos
entre sí, profesionales que no trabajan todo el día, y la agenda **medio llena** de la semana
que viene.

Dos propiedades que hay que conservar si alguien lo amplía:

* **Idempotente**: se puede volver a cargar. Se borra y se vuelve a crear lo que gestiona, y no
  se toca nada más.
* **Relativo a hoy**: las citas se generan a partir de la fecha de ejecución. Un seed con fechas
  fijas envejece y a las dos semanas enseña una agenda vacía, que es justo lo contrario de lo
  que hace falta ver.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.ajustes import obtener_ajustes
from agenda.modelos.catalogo import Service, ServiceCategory
from agenda.modelos.clientes import BusinessClient
from agenda.modelos.equipo import StaffHours, StaffProfile, StaffService
from agenda.modelos.identidad import User
from agenda.modelos.marketplace import Zone
from agenda.modelos.negocio import Business, BusinessHours, BusinessSettings, Location
from agenda.modelos.reservas import Booking, BookingItem, StaffOccupancy

PANAMA = ZoneInfo("America/Panama")
ajustes = obtener_ajustes()

# El seed se carga con el rol dueño: crea filas de varios negocios a la vez, y la seguridad
# por fila —que es lo que se quiere en producción— impediría precisamente eso.
URL = ajustes.database_url_migraciones.replace("postgresql+psycopg", "postgresql+asyncpg")


# ── Geografía real ────────────────────────────────────────────────────────────────────────
# Corregimientos y barrios de verdad de Ciudad de Panamá. Las páginas categoría × zona son URL
# públicas indexadas: «Zona 1 / Zona 2» no lo busca nadie en Google.
ZONAS = [
    ("provincia", "Panamá", "panama", None),
    ("distrito", "Ciudad de Panamá", "ciudad-de-panama", "panama"),
    ("corregimiento", "Bella Vista", "bella-vista", "ciudad-de-panama"),
    ("corregimiento", "San Francisco", "san-francisco", "ciudad-de-panama"),
    ("corregimiento", "Juan Díaz", "juan-diaz", "ciudad-de-panama"),
    ("barrio", "El Cangrejo", "el-cangrejo", "bella-vista"),
    ("barrio", "Obarrio", "obarrio", "bella-vista"),
    ("barrio", "Costa del Este", "costa-del-este", "juan-diaz"),
]

CATEGORIAS = [
    ("barberia", "Barbería"),
    ("peluqueria", "Peluquería y salón"),
    ("unas", "Uñas"),
    ("pestanas-cejas", "Pestañas y cejas"),
    ("maquillaje", "Maquillaje"),
    ("depilacion", "Depilación"),
    ("spa-masajes", "Spa y masajes"),
    ("estetica", "Estética facial y corporal"),
]

L, M, X, J, V, S, D = range(7)  # días de la semana, como los devuelve `date.weekday()`


def _hora(h: int, m: int = 0) -> time:
    return time(h, m)


# ── Los cuatro negocios ───────────────────────────────────────────────────────────────────
# Cada uno existe para que se vea un caso distinto del motor: horarios que no coinciden con el
# del negocio, jornada partida, cierre a mediodía y un profesional que trabaja solo de tarde.
NEGOCIOS = [
    {
        "slug": "barberia-el-cangrejo",
        "nombre": "Barbería El Cangrejo",
        "categoria": "barberia",
        "zona": "el-cangrejo",
        "direccion": "Calle 47 con Vía Argentina, El Cangrejo",
        "punto": (-79.5306, 8.9871),
        "estado": "publicado",
        "horario": [(d, _hora(9), _hora(19)) for d in (L, M, X, J, V)] + [(S, _hora(9), _hora(17))],
        "servicios": [
            ("Corte clásico", 30, 1200, 0, 5),
            ("Corte + barba", 45, 1800, 0, 10),
            ("Arreglo de barba", 20, 800, 0, 5),
            ("Corte niño", 30, 1000, 0, 5),
        ],
        "equipo": [
            {
                "nombre": "Kevin Ortega",
                "horario": [(d, _hora(9), _hora(19)) for d in (L, M, X, J, V)]
                + [(S, _hora(9), _hora(17))],
                "almuerzo": (_hora(13), _hora(14)),
            },
            {
                # Solo de tarde: es el caso que rompe los motores que asumen que el
                # profesional trabaja el horario del negocio.
                "nombre": "Yaritza Beitía",
                "horario": [(d, _hora(14), _hora(19)) for d in (M, X, J, V)]
                + [(S, _hora(10), _hora(17))],
                "almuerzo": None,
            },
        ],
    },
    {
        "slug": "salon-obarrio",
        "nombre": "Salón Obarrio",
        "categoria": "peluqueria",
        "zona": "obarrio",
        "direccion": "Calle 53 Este, Obarrio",
        "punto": (-79.5218, 8.9836),
        "estado": "publicado",
        "horario": [(d, _hora(9), _hora(19)) for d in (M, X, J, V, S)],
        "servicios": [
            ("Corte y peinado", 60, 2500, 0, 10),
            ("Balayage", 180, 12000, 0, 15),
            ("Tinte raíz", 90, 5500, 0, 15),
            ("Keratina", 150, 9000, 0, 15),
            ("Peinado de fiesta", 45, 3500, 0, 10),
        ],
        "equipo": [
            {
                "nombre": "Marielys Ruiz",
                "horario": [(d, _hora(9), _hora(19)) for d in (M, X, J, V, S)],
                "almuerzo": (_hora(13), _hora(14)),
            },
            {
                "nombre": "Ana Lucía Ábrego",
                "horario": [(d, _hora(11), _hora(19)) for d in (M, X, J, V)]
                + [(S, _hora(9), _hora(15))],
                "almuerzo": (_hora(14), _hora(15)),
            },
            {
                "nombre": "Dayana Pinzón",
                "horario": [(d, _hora(9), _hora(15)) for d in (M, X, J, V, S)],
                "almuerzo": None,
            },
            {
                "nombre": "Josué Camaño",
                "horario": [(d, _hora(12), _hora(19)) for d in (J, V, S)],
                "almuerzo": None,
            },
        ],
    },
    {
        "slug": "spa-costa-del-este",
        "nombre": "Spa Costa del Este",
        "categoria": "spa-masajes",
        "zona": "costa-del-este",
        "direccion": "Ave. Centenario, Costa del Este",
        "punto": (-79.4666, 9.0141),
        "estado": "publicado",
        # Jornada partida: cierra a mediodía. Es el caso que parte la agenda en dos tramos y
        # deja fuera los servicios largos de la franja corta.
        "horario": [(d, _hora(10), _hora(13)) for d in (M, X, J, V, S)]
        + [(d, _hora(15), _hora(20)) for d in (M, X, J, V, S)],
        "servicios": [
            ("Masaje relajante", 60, 5000, 10, 15),
            ("Masaje descontracturante", 90, 7000, 10, 15),
            ("Limpieza facial profunda", 75, 6000, 5, 15),
            ("Depilación con cera piernas completas", 45, 3000, 5, 10),
        ],
        "equipo": [
            {
                "nombre": "Ivonne Saavedra",
                "horario": [(d, _hora(10), _hora(13)) for d in (M, X, J, V, S)]
                + [(d, _hora(15), _hora(20)) for d in (M, X, J, V, S)],
                "almuerzo": None,
            },
            {
                "nombre": "Rita Achurra",
                "horario": [(d, _hora(15), _hora(20)) for d in (M, X, J, V)],
                "almuerzo": None,
            },
        ],
    },
    {
        "slug": "unas-por-vanessa",
        "nombre": "Uñas por Vanessa",
        "categoria": "unas",
        "zona": "san-francisco",
        "direccion": "Calle 74 Este, San Francisco",
        "punto": (-79.5063, 9.0006),
        # A propósito **en borrador**: sin él no se puede probar la puerta de publicación
        # (ONB-6, D11), que es lo que separa un perfil a medias del marketplace.
        "estado": "borrador",
        "horario": [(d, _hora(10), _hora(18)) for d in (L, M, X, J, V, S)],
        "servicios": [
            ("Manicura semipermanente", 75, 2500, 0, 10),
            ("Uñas acrílicas", 120, 4500, 0, 15),
            ("Pedicura spa", 60, 3000, 0, 10),
        ],
        "equipo": [
            {
                "nombre": "Vanessa Him",
                "horario": [(d, _hora(10), _hora(18)) for d in (L, M, X, J, V, S)],
                "almuerzo": (_hora(13), _hora(14)),
            }
        ],
    },
]

CLIENTES = [
    ("Abdiel Him", "+50761230001"),
    ("Zuleika Rodríguez", "+50761230002"),
    ("Carlos Alberto Vega", "+50761230003"),
    ("Milagros Espino", "+50761230004"),
    ("Ricardo Sanjur", "+50761230005"),
    ("Nadia Quintero", "+50761230006"),
]


async def sembrar(sesion: AsyncSession) -> None:
    await _limpiar(sesion)
    zonas = await _zonas(sesion)
    categorias = await _categorias(sesion)
    clientes_plataforma = await _clientes_plataforma(sesion)

    for definicion in NEGOCIOS:
        await _negocio(sesion, definicion, zonas, categorias, clientes_plataforma)


async def _limpiar(sesion: AsyncSession) -> None:
    """Borra lo que gestiona el seed y nada más.

    En orden de dependencia y con `TRUNCATE … CASCADE` sobre las tablas del ejemplo: es más
    rápido y, sobre todo, no deja a medias una carga anterior que se hubiera quedado colgada.
    """
    await sesion.execute(
        text(
            "TRUNCATE bookings, booking_items, booking_events, staff_occupancy, "
            "business_clients, staff_services, staff_hours, staff_profiles, services, "
            "business_hours, business_settings, locations, businesses, users, zones, "
            "service_categories RESTART IDENTITY CASCADE"
        )
    )


async def _zonas(sesion: AsyncSession) -> dict[str, Zone]:
    creadas: dict[str, Zone] = {}
    for nivel, nombre, slug, padre in ZONAS:
        zona = Zone(
            level=nivel,
            name=nombre,
            slug=slug,
            parent_id=creadas[padre].id if padre else None,
            path=f"{creadas[padre].path}/{slug}" if padre else slug,
        )
        sesion.add(zona)
        await sesion.flush()
        creadas[slug] = zona
    return creadas


async def _categorias(sesion: AsyncSession) -> dict[str, ServiceCategory]:
    creadas: dict[str, ServiceCategory] = {}
    for posicion, (slug, nombre) in enumerate(CATEGORIAS):
        categoria = ServiceCategory(slug=slug, name=nombre, position=posicion)
        sesion.add(categoria)
        await sesion.flush()
        creadas[slug] = categoria
    return creadas


async def _clientes_plataforma(sesion: AsyncSession) -> list[User]:
    usuarios = []
    for nombre, telefono in CLIENTES:
        usuario = User(
            full_name=nombre,
            phone_e164=telefono,
            phone_verified_at=datetime.now(UTC),
        )
        sesion.add(usuario)
        usuarios.append(usuario)
    await sesion.flush()
    return usuarios


async def _negocio(
    sesion: AsyncSession,
    definicion: dict,
    zonas: dict[str, Zone],
    categorias: dict[str, ServiceCategory],
    clientes_plataforma: list[User],
) -> None:
    dueno = User(
        full_name=f"Dueño de {definicion['nombre']}",
        phone_e164=f"+5076999{abs(hash(definicion['slug'])) % 10000:04d}",
        phone_verified_at=datetime.now(UTC),
    )
    sesion.add(dueno)
    await sesion.flush()

    negocio = Business(
        slug=definicion["slug"],
        display_name=definicion["nombre"],
        owner_user_id=dueno.id,
        timezone="America/Panama",
        status=definicion["estado"],
    )
    sesion.add(negocio)
    await sesion.flush()

    lon, lat = definicion["punto"]
    sesion.add(
        Location(
            business_id=negocio.id,
            address_line=definicion["direccion"],
            zone_id=zonas[definicion["zona"]].id,
            geo=f"SRID=4326;POINT({lon} {lat})",
        )
    )
    sesion.add(BusinessSettings(business_id=negocio.id))
    for weekday, abre, cierra in definicion["horario"]:
        sesion.add(
            BusinessHours(business_id=negocio.id, weekday=weekday, opens_at=abre, closes_at=cierra)
        )

    servicios = []
    for posicion, (nombre, minutos, precio, antes, despues) in enumerate(definicion["servicios"]):
        servicio = Service(
            business_id=negocio.id,
            service_category_id=categorias[definicion["categoria"]].id,
            name=nombre,
            duration_min=minutos,
            price_kind="fijo",
            price_minor=precio,
            buffer_before_min=antes,
            buffer_after_min=despues,
            position=posicion,
        )
        sesion.add(servicio)
        servicios.append(servicio)
    await sesion.flush()

    equipo = []
    for posicion, persona in enumerate(definicion["equipo"]):
        profesional = StaffProfile(
            business_id=negocio.id, display_name=persona["nombre"], position=posicion
        )
        sesion.add(profesional)
        await sesion.flush()
        equipo.append(profesional)

        for weekday, empieza, termina in persona["horario"]:
            sesion.add(
                StaffHours(
                    business_id=negocio.id,
                    staff_id=profesional.id,
                    weekday=weekday,
                    starts_at=empieza,
                    ends_at=termina,
                    kind="trabajo",
                )
            )
        if persona["almuerzo"]:
            empieza, termina = persona["almuerzo"]
            for weekday, _, _ in persona["horario"]:
                sesion.add(
                    StaffHours(
                        business_id=negocio.id,
                        staff_id=profesional.id,
                        weekday=weekday,
                        starts_at=empieza,
                        ends_at=termina,
                        kind="descanso",
                    )
                )

        # Todos prestan todos los servicios del negocio: el override por profesional es v2.
        for servicio in servicios:
            sesion.add(
                StaffService(
                    business_id=negocio.id, staff_id=profesional.id, service_id=servicio.id
                )
            )

    fichas = []
    for usuario in clientes_plataforma[:4]:
        ficha = BusinessClient(
            business_id=negocio.id,
            user_id=usuario.id,
            display_name=usuario.full_name,
            phone_e164=usuario.phone_e164,
            source="marketplace",
        )
        sesion.add(ficha)
        fichas.append(ficha)
    await sesion.flush()

    if definicion["estado"] == "publicado":
        await _agenda_de_ejemplo(sesion, negocio, equipo, servicios, fichas)


async def _agenda_de_ejemplo(
    sesion: AsyncSession,
    negocio: Business,
    equipo: list[StaffProfile],
    servicios: list[Service],
    fichas: list[BusinessClient],
) -> None:
    """Llena la agenda **a medias**, que es lo interesante.

    Una agenda vacía no enseña nada y una llena tampoco: lo que hay que poder ver es que el
    balayage de tres horas ya no cabe esta tarde pero sí el martes, y que entre dos citas
    pegadas no entra otra por culpa del buffer. Se reparte de forma determinista —sin azar—
    para que dos cargas den lo mismo y una captura de pantalla se pueda comparar con la
    siguiente.
    """
    hoy = datetime.now(PANAMA).date()
    horas_base = [10, 11, 15, 16]

    for dia_offset in range(0, 7):
        dia = hoy + timedelta(days=dia_offset)
        if dia.weekday() == D:  # domingo: casi nadie abre
            continue

        for indice, profesional in enumerate(equipo):
            # Cada profesional coge dos huecos del día, desplazados entre sí para que la
            # agenda no salga en bloque y se vean los huecos intercalados.
            for salto in (0, 2):
                posicion = (indice + salto + dia_offset) % len(horas_base)
                hora_local = horas_base[posicion]
                servicio = servicios[(indice + salto + dia_offset) % len(servicios)]
                cliente = fichas[(indice + salto + dia_offset) % len(fichas)]

                inicio = datetime.combine(dia, time(hora_local, 0), tzinfo=PANAMA).astimezone(UTC)
                fin = inicio + timedelta(minutes=servicio.duration_min)

                estado = _estado_segun_fecha(dia, hoy, indice + salto)
                await _cita(sesion, negocio, profesional, servicio, cliente, inicio, fin, estado)


def _estado_segun_fecha(dia: date, hoy: date, semilla: int) -> str:
    """Lo pasado ya tiene desenlace; lo futuro está confirmado.

    Se incluyen un no-show y una cancelación **a propósito**: sin ellos, la tasa de completado
    del ranking sale perfecta para todo el mundo y no se ve funcionar.
    """
    if dia < hoy:
        return ("completada", "completada", "no_show", "cancelada_cliente")[semilla % 4]
    return "confirmada"


async def _cita(
    sesion: AsyncSession,
    negocio: Business,
    profesional: StaffProfile,
    servicio: Service,
    cliente: BusinessClient,
    inicio: datetime,
    fin: datetime,
    estado: str,
) -> None:
    reserva = Booking(
        business_id=negocio.id,
        staff_id=profesional.id,
        business_client_id=cliente.id,
        client_user_id=cliente.user_id,
        status=estado,
        starts_at=inicio,
        ends_at=fin,
        total_duration_min=servicio.duration_min,
        total_amount_minor=servicio.price_minor or 0,
        currency=servicio.currency,
        source="negocio_manual",
        confirmed_at=inicio - timedelta(days=1),
    )
    sesion.add(reserva)
    await sesion.flush()

    sesion.add(
        BookingItem(
            business_id=negocio.id,
            booking_id=reserva.id,
            position=1,
            service_id=servicio.id,
            name_snapshot=servicio.name,
            duration_min_snapshot=servicio.duration_min,
            price_kind_snapshot=servicio.price_kind,
            price_minor_snapshot=servicio.price_minor,
            currency=servicio.currency,
            buffer_before_min_snapshot=servicio.buffer_before_min,
            buffer_after_min_snapshot=servicio.buffer_after_min,
        )
    )
    sesion.add(
        StaffOccupancy(
            business_id=negocio.id,
            staff_id=profesional.id,
            kind="reserva",
            status=estado,
            booking_id=reserva.id,
            starts_at=inicio,
            ends_at=fin,
            buffer_before_min=servicio.buffer_before_min,
            buffer_after_min=servicio.buffer_after_min,
        )
    )
    await sesion.flush()


async def principal() -> None:
    motor = create_async_engine(URL, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            await sembrar(sesion)

        async with crear() as sesion:
            negocios = (await sesion.execute(select(Business))).scalars().all()
            citas = (await sesion.execute(select(Booking))).scalars().all()

        print(f"Cargados {len(negocios)} negocios y {len(citas)} citas.")
        for negocio in negocios:
            print(f"  · {negocio.display_name} ({negocio.status}) — /{negocio.slug}")
    finally:
        await motor.dispose()


if __name__ == "__main__":
    asyncio.run(principal())
