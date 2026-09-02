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
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.ajustes import obtener_ajustes
from agenda.dominio.ranking import PesosRanking
from agenda.dominio.totp import desde_base32
from agenda.modelos.catalogo import Service, ServiceCategory
from agenda.modelos.clientes import BusinessClient
from agenda.modelos.equipo import StaffHours, StaffProfile, StaffService
from agenda.modelos.identidad import AdminUser, Membership, User
from agenda.modelos.marketplace import RankingWeights, Zone
from agenda.modelos.monetizacion import Plan
from agenda.modelos.negocio import (
    Business,
    BusinessCategory,
    BusinessHours,
    BusinessMedia,
    BusinessSettings,
    Location,
)
from agenda.modelos.reservas import Booking, BookingItem, StaffOccupancy
from agenda.modelos.reviews import Review, ReviewReply
from agenda.servicios import resenas as servicio_resenas
from agenda.servicios.consola import hashear_password

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

# ── La cuenta de la consola interna, SOLO para la demo local ───────────────────────────────
# Están escritas aquí y documentadas en `docs/CREDENCIALES-DEMO.md` porque son de mentira y
# porque `_consola_de_demo` **se niega a crearlas fuera de `ENTORNO=local`**. La cuenta real se
# crea con `python -m agenda.consola_alta`, que genera credenciales al azar y las enseña una vez.
CONSOLA_DEMO_EMAIL = "consola@bukeo.local"
CONSOLA_DEMO_PASSWORD = "consola-de-demo-solo-en-local"
#: Base32, tal como se teclea en un autenticador. Fijo para que `make semilla` no obligue a
#: reconfigurarlo cada vez.
CONSOLA_DEMO_2FA = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"

#: Las dos únicas fotos de marca que existen (`docs/marca/BRANDBOOK-BUKEO.md` §02). Se sirven
#: desde `apps/web/public/fotos/`, así que la clave es la ruta tal cual.
PORTADAS = {
    "spa-costa-del-este": "/fotos/spa.webp",
    "unas-por-vanessa": "/fotos/unas.webp",
}


def _hora(h: int, m: int = 0) -> time:
    return time(h, m)


# ── Los cuatro negocios ───────────────────────────────────────────────────────────────────
# Cada uno existe para que se vea un caso distinto del motor: horarios que no coinciden con el
# del negocio, jornada partida, cierre a mediodía y un profesional que trabaja solo de tarde.
NEGOCIOS = [
    {
        "slug": "barberia-el-cangrejo",
        "telefono_dueno": "+50760000001",
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
                "telefono": "+50762000001",
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
        "telefono_dueno": "+50760000002",
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
                "telefono": "+50762000002",
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
        "telefono_dueno": "+50760000003",
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
                "telefono": "+50762000003",
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
        "telefono_dueno": "+50760000004",
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
                "telefono": "+50762000004",
                "horario": [(d, _hora(10), _hora(18)) for d in (L, M, X, J, V, S)],
                "almuerzo": (_hora(13), _hora(14)),
            }
        ],
    },
    {
        "slug": "peluqueria-dona-elvia",
        "telefono_dueno": "+50760000005",
        "nombre": "Peluquería Doña Elvia",
        "categoria": "peluqueria",
        "zona": "san-francisco",
        "direccion": "Calle 68, San Francisco",
        "punto": (-79.5091, 9.0021),
        "estado": "publicado",
        # **Unipersonal y de barrio.** Es el negocio más común del país y el que más manda en
        # el diseño: una sola persona, sin recepción, contestando el teléfono con las manos
        # llenas de tinte.
        "horario": [(d, _hora(8), _hora(17)) for d in (M, X, J, V, S)],
        "servicios": [
            ("Corte de dama", 45, 1500, 0, 10),
            ("Tinte completo", 120, 4500, 0, 15),
            ("Secado y planchado", 40, 1200, 0, 5),
            ("Tratamiento capilar", 60, 2000, 0, 10),
        ],
        "equipo": [
            {
                "nombre": "Elvia Cedeño",
                "telefono": "+50762000005",
                "horario": [(d, _hora(8), _hora(17)) for d in (M, X, J, V, S)],
                "almuerzo": (_hora(12), _hora(13)),
            }
        ],
    },
    {
        "slug": "barberia-san-francisco",
        "telefono_dueno": "+50760000006",
        "nombre": "Barbería San Francisco",
        "categoria": "barberia",
        "zona": "san-francisco",
        "direccion": "Vía Israel, San Francisco",
        "punto": (-79.5008, 9.0043),
        "estado": "publicado",
        # Unipersonal que abre tarde y cierra tarde: el caso que rompe cualquier motor que
        # asuma jornada de oficina.
        "horario": [(d, _hora(12), _hora(21)) for d in (M, X, J, V, S)],
        "servicios": [
            ("Corte fade", 40, 1500, 0, 10),
            ("Corte + barba", 55, 2000, 0, 10),
            ("Diseño de cejas", 15, 600, 0, 5),
        ],
        "equipo": [
            {
                "nombre": "Aníbal Rodríguez",
                "telefono": "+50762000006",
                "horario": [(d, _hora(12), _hora(21)) for d in (M, X, J, V, S)],
                "almuerzo": None,
            }
        ],
    },
    {
        "slug": "estudio-de-cejas-bella-vista",
        "telefono_dueno": "+50760000007",
        "nombre": "Estudio de Cejas Bella Vista",
        "categoria": "pestanas-cejas",
        "zona": "bella-vista",
        "direccion": "Calle 42, Bella Vista",
        "punto": (-79.5265, 8.9843),
        "estado": "publicado",
        "horario": [(d, _hora(10), _hora(19)) for d in (M, X, J, V, S)],
        "servicios": [
            ("Diseño y depilación de cejas", 30, 1800, 0, 5),
            ("Laminado de cejas", 60, 4000, 0, 10),
            ("Extensiones de pestañas clásicas", 120, 6500, 5, 15),
            ("Retoque de pestañas", 75, 4000, 5, 10),
        ],
        "equipo": [
            {
                "nombre": "Katherine Sánchez",
                "telefono": "+50762000007",
                "horario": [(d, _hora(10), _hora(19)) for d in (M, X, J, V, S)],
                "almuerzo": (_hora(14), _hora(15)),
            },
            {
                "nombre": "Génesis Batista",
                "horario": [(d, _hora(10), _hora(16)) for d in (X, J, V)],
                "almuerzo": None,
            },
        ],
    },
    {
        "slug": "nails-and-lashes-obarrio",
        "telefono_dueno": "+50760000008",
        "nombre": "Nails & Lashes Obarrio",
        "categoria": "unas",
        "zona": "obarrio",
        "direccion": "Calle 50, Obarrio",
        "punto": (-79.5192, 8.9861),
        "estado": "publicado",
        "horario": [(d, _hora(9), _hora(20)) for d in (L, M, X, J, V, S)],
        "servicios": [
            ("Manicura tradicional", 45, 1500, 0, 10),
            ("Manicura semipermanente", 75, 2800, 0, 10),
            ("Uñas acrílicas", 150, 5500, 0, 15),
            ("Pedicura spa", 60, 3200, 0, 10),
            ("Extensiones de pestañas", 120, 7000, 5, 15),
        ],
        "equipo": [
            {
                "nombre": "Yulissa Caballero",
                "telefono": "+50762000008",
                "horario": [(d, _hora(9), _hora(20)) for d in (L, M, X, J, V, S)],
                "almuerzo": (_hora(13), _hora(14)),
            },
            {
                "nombre": "Rosangela Díaz",
                "horario": [(d, _hora(13), _hora(20)) for d in (L, M, X, J, V, S)],
                "almuerzo": None,
            },
            {
                "nombre": "Keyla Montenegro",
                "horario": [(d, _hora(9), _hora(15)) for d in (M, X, J, V)],
                "almuerzo": None,
            },
        ],
    },
    {
        "slug": "spa-urbano-el-cangrejo",
        "telefono_dueno": "+50760000009",
        "nombre": "Spa Urbano El Cangrejo",
        "categoria": "spa-masajes",
        "zona": "el-cangrejo",
        "direccion": "Vía Argentina con Calle Arturo Motta",
        "punto": (-79.5324, 8.9887),
        "estado": "publicado",
        "horario": [(d, _hora(11), _hora(21)) for d in (M, X, J, V, S)],
        "servicios": [
            ("Masaje de espalda", 45, 3500, 10, 15),
            ("Masaje completo", 90, 6500, 10, 15),
            ("Ritual de piedras calientes", 120, 9000, 10, 20),
            ("Limpieza facial", 60, 4500, 5, 15),
        ],
        "equipo": [
            {
                "nombre": "Lorena Justavino",
                "telefono": "+50762000009",
                "horario": [(d, _hora(11), _hora(21)) for d in (M, X, J, V, S)],
                "almuerzo": (_hora(16), _hora(17)),
            },
            {
                "nombre": "Ariel Mendoza",
                "horario": [(d, _hora(11), _hora(17)) for d in (M, X, J, V)],
                "almuerzo": None,
            },
            {
                "nombre": "Sheila Prado",
                "horario": [(d, _hora(15), _hora(21)) for d in (J, V, S)],
                "almuerzo": None,
            },
        ],
    },
    {
        "slug": "maquillaje-por-karla",
        "dias_publicado": 6,
        "telefono_dueno": "+50760000010",
        "nombre": "Maquillaje por Karla",
        "categoria": "maquillaje",
        "zona": "costa-del-este",
        "direccion": "Ave. La Rotonda, Costa del Este",
        "punto": (-79.4702, 9.0106),
        "estado": "publicado",
        # Unipersonal con servicios largos y pocos huecos al día: el caso donde la agenda se
        # llena con dos citas y hay que ver que ya no cabe una tercera.
        "horario": [(d, _hora(7), _hora(19)) for d in (J, V, S)],
        "servicios": [
            ("Maquillaje social", 60, 5000, 15, 15),
            ("Maquillaje de novia con prueba", 180, 25000, 15, 30),
            ("Peinado y maquillaje", 120, 9000, 15, 20),
        ],
        "equipo": [
            {
                "nombre": "Karla Him",
                "telefono": "+50762000010",
                "horario": [(d, _hora(7), _hora(19)) for d in (J, V, S)],
                "almuerzo": None,
            }
        ],
    },
    {
        "slug": "estetica-integral-obarrio",
        "dias_publicado": 12,
        "telefono_dueno": "+50760000011",
        "nombre": "Estética Integral Obarrio",
        "categoria": "estetica",
        "zona": "obarrio",
        "direccion": "Calle 55 Este, Obarrio",
        "punto": (-79.5231, 8.9819),
        "estado": "publicado",
        # Jornada partida y equipo de cuatro: el negocio grande, el que menos abunda y el que
        # más estresa la agenda.
        "horario": [(d, _hora(9), _hora(13)) for d in (L, M, X, J, V)]
        + [(d, _hora(14), _hora(19)) for d in (L, M, X, J, V)]
        + [(S, _hora(9), _hora(14))],
        "servicios": [
            ("Depilación láser axilas", 30, 4000, 5, 10),
            ("Depilación láser piernas", 60, 9000, 5, 15),
            ("Radiofrecuencia facial", 45, 6000, 5, 10),
            ("Masaje reductor", 60, 5000, 5, 15),
            ("Limpieza facial profunda", 75, 5500, 5, 15),
        ],
        "equipo": [
            {
                "nombre": "Dra. Marisol Tejeira",
                "telefono": "+50762000011",
                "horario": [(d, _hora(9), _hora(13)) for d in (L, M, X, J, V)]
                + [(d, _hora(14), _hora(19)) for d in (L, M, X, J, V)],
                "almuerzo": None,
            },
            {
                "nombre": "Odalis Barría",
                "horario": [(d, _hora(9), _hora(13)) for d in (L, M, X, J, V)]
                + [(S, _hora(9), _hora(14))],
                "almuerzo": None,
            },
            {
                "nombre": "Jorge Icaza",
                "horario": [(d, _hora(14), _hora(19)) for d in (M, X, J, V)],
                "almuerzo": None,
            },
            {
                "nombre": "Nitzia Gómez",
                "horario": [(d, _hora(9), _hora(13)) for d in (X, J, V)]
                + [(S, _hora(9), _hora(14))],
                "almuerzo": None,
            },
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
    await _pesos_del_ranking(sesion)
    await _plan_gratis(sesion)
    await _consola_de_demo(sesion)
    zonas = await _zonas(sesion)
    categorias = await _categorias(sesion)
    clientes_plataforma = await _clientes_plataforma(sesion)

    for definicion in NEGOCIOS:
        await _negocio(sesion, definicion, zonas, categorias, clientes_plataforma)

    await _contadores_de_los_clientes(sesion)


async def _limpiar(sesion: AsyncSession) -> None:
    """Borra lo que gestiona el seed y nada más.

    En orden de dependencia y con `TRUNCATE … CASCADE` sobre las tablas del ejemplo: es más
    rápido y, sobre todo, no deja a medias una carga anterior que se hubiera quedado colgada.
    """
    await sesion.execute(
        text(
            "TRUNCATE bookings, booking_items, booking_events, staff_occupancy, "
            "business_clients, staff_services, staff_hours, staff_profiles, services, "
            "business_hours, business_settings, business_categories, business_media, "
            "reviews, review_media, review_replies, review_reports, business_rating_stats, "
            "favorites, locations, memberships, businesses, users, zones, ranking_weights, plans, "
            "admin_users, admin_sessions, "
            "service_categories RESTART IDENTITY CASCADE"
        )
    )


async def _consola_de_demo(sesion: AsyncSession) -> None:
    """La cuenta de la consola interna para poder enseñarla. **Solo en local.**

    Aquí hay una contraseña y un secreto de segundo factor escritos en el repositorio, y eso
    normalmente sería un fallo grave. Lo que lo hace aceptable es lo que va debajo: esta
    función **se niega a ejecutarse fuera de `ENTORNO=local`**. No es una convención ni un
    aviso en un comentario; es un `return` que impide que esta cuenta llegue a existir en
    staging o en producción por copiar el seed.

    La cuenta de verdad se crea con `python -m agenda.consola_alta`, que genera contraseña y
    secreto al azar y los enseña **una sola vez**.

    El secreto del 2FA es fijo a propósito: si fuera aleatorio, cada `make semilla` obligaría a
    reconfigurar el autenticador, y quien quiere enseñar la consola no tiene por qué tener uno.
    Para eso está `python -m agenda.consola_codigo`, que imprime el código de este momento.
    """
    if not ajustes.es_local:
        return

    sesion.add(
        AdminUser(
            email=CONSOLA_DEMO_EMAIL,
            full_name="Equipo M2G (demo)",
            password_hash=hashear_password(CONSOLA_DEMO_PASSWORD),
            totp_secret=desde_base32(CONSOLA_DEMO_2FA),
            totp_enabled=True,
            role="superadmin",
            status="activo",
        )
    )
    await sesion.flush()


async def _plan_gratis(sesion: AsyncSession) -> None:
    """El plan Gratis, versión 1 (ADR-0010, PAY-1).

    El motor de planes existe desde el día uno **aunque el precio sea cero**: así el camino
    está recorrido y probado miles de veces antes de que haya dinero de por medio. Un motor de
    cobro que se estrena el día que empieza a cobrar es un motor sin probar.
    """
    sesion.add(
        Plan(
            code="gratis",
            version=1,
            name="Gratis",
            price_minor=0,
            period="mensual",
            effective_from=datetime.now(UTC),
            features={"agenda": True, "marketplace": True, "recordatorios": True},
        )
    )
    await sesion.flush()


async def _pesos_del_ranking(sesion: AsyncSession) -> None:
    """La primera versión de los pesos del ranking (ADR-0009, REV-5).

    Sin esta fila pasan dos cosas: la búsqueda tira de los valores por defecto del dominio —así
    que funciona, pero nadie puede cambiarla— y la consola no tiene qué editar. Y hay un valor
    que **tiene** que estar sembrado desde el principio: `bayes_m`, la media global de la
    ponderación bayesiana. Si arrancara en cero, el primer negocio con una sola reseña de cinco
    estrellas se dispararía por encima de todos.

    Los números salen de `PesosRanking()`, que es la semilla escrita en el dominio, y no se
    copian a mano: dos listas de números para lo mismo es la forma segura de que un día no
    coincidan. A partir de aquí manda la base, y cambiarlos es insertar una versión nueva desde
    la consola, no desplegar.
    """
    semilla = PesosRanking()
    sesion.add(
        RankingWeights(
            version=1,
            effective_from=datetime.now(UTC),
            w_distancia=Decimal(str(semilla.distancia)),
            w_rating=Decimal(str(semilla.rating)),
            w_reservas_recientes=Decimal(str(semilla.reservas_recientes)),
            w_tasa_completado=Decimal(str(semilla.tasa_completado)),
            w_completitud=Decimal(str(semilla.completitud)),
            w_actividad=Decimal(str(semilla.actividad)),
            w_boost_nuevo=Decimal(str(semilla.boost_nuevo)),
            radius_km=Decimal(str(semilla.radio_metros / 1000)),
            # Cuánto decae la cercanía con la distancia. Hoy la fórmula usa el radio como
            # rampa lineal; la columna existe para poder cambiar a un decaimiento propio sin
            # migración, y de momento acompaña al radio.
            decay_km=Decimal(str(semilla.radio_metros / 1000)),
            recent_days=14,
            recent_cap=semilla.techo_reservas,
            activity_days=14,
            boost_days=semilla.dias_boost_nuevo,
            bayes_m=Decimal(str(semilla.rating_medio_global)),
            bayes_c=semilla.reviews_de_confianza,
            notes="Semilla inicial. Se cambia desde la consola, no desplegando.",
        )
    )
    await sesion.flush()


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
        # Fijo y escrito en la definición: `hash()` de Python cambia en cada proceso, así que
        # las credenciales de la demo cambiarían en cada carga y no habría forma de anotarlas.
        phone_e164=definicion["telefono_dueno"],
        phone_verified_at=datetime.now(UTC),
    )
    sesion.add(dueno)
    await sesion.flush()

    negocio = Business(
        slug=definicion["slug"],
        display_name=definicion["nombre"],
        description=definicion.get("descripcion"),
        owner_user_id=dueno.id,
        timezone="America/Panama",
        status=definicion["estado"],
        # `published_at` acompaña al estado y **no es decorativo**: de él salen el impulso a
        # los negocios nuevos del ranking (MKT-3) y la vuelta al marketplace al levantar una
        # suspensión. Sin fecha, todos los salones parecen viejísimos y reactivar uno lo
        # devuelve a borrador. Se reparte en el tiempo para que el boost de nuevo se vea.
        published_at=(
            datetime.now(UTC) - timedelta(days=definicion.get("dias_publicado", 120))
            if definicion["estado"] == "publicado"
            else None
        ),
        # El número **no sale nunca** por una respuesta pública: existe para que el salto de
        # click-to-chat funcione en servidor y se pueda probar de verdad (garantía nº 3).
        whatsapp_phone_e164=definicion["telefono_dueno"],
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
    # El dueño necesita su membresía o no puede entrar a su propio panel: el permiso no es
    # del usuario, es del par (usuario, negocio).
    sesion.add(
        Membership(
            business_id=negocio.id,
            user_id=dueno.id,
            role="dueno",
            status="activa",
            accepted_at=datetime.now(UTC),
        )
    )
    sesion.add(BusinessSettings(business_id=negocio.id))
    # La categoría del negocio es lo que hace que salga al filtrar por «barbería» en el
    # marketplace. Sin esta fila el negocio existe pero es invisible para media búsqueda.
    sesion.add(
        BusinessCategory(
            business_id=negocio.id,
            service_category_id=categorias[definicion["categoria"]].id,
            is_primary=True,
        )
    )
    for weekday, abre, cierra in definicion["horario"]:
        sesion.add(
            BusinessHours(business_id=negocio.id, weekday=weekday, opens_at=abre, closes_at=cierra)
        )

    # La portada. La clave es una **ruta servible** y no una URL firmada: hoy las fotos las
    # sirve la propia web desde `public/`, así que `/fotos/spa.webp` funciona sin montar un
    # almacenamiento de objetos que todavía no está decidido. El día que llegue, se rellena
    # `URL_BASE_MEDIA` y no se toca ni una fila.
    #
    # Solo hay dos fotos de marca generadas (`docs/marca` §02), así que se reparten y los
    # demás salones se quedan sin portada **a propósito**: el marketplace tiene que verse bien
    # con y sin foto, y una lista donde todos la tienen esconde el caso que va a ser normal.
    if (portada := PORTADAS.get(definicion["slug"])) is not None:
        sesion.add(
            BusinessMedia(
                business_id=negocio.id,
                kind="portada",
                storage_key=portada,
                alt_text=definicion["nombre"],
                moderation_status="aprobada",
            )
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
        # **El primero de cada salón tiene cuenta; los demás, no.** Es el reparto que se ve en
        # un salón real (ONB-4): el dueño apunta a su equipo en dos minutos y las invitaciones
        # llegan después, si llegan. Y hace falta que haya al menos uno con cuenta para poder
        # abrir la agenda del profesional (STF-3) y comprobar que solo ve la suya.
        cuenta = None
        if posicion == 0:
            cuenta = User(
                phone_e164=persona["telefono"],
                full_name=persona["nombre"],
                phone_verified_at=datetime.now(UTC),
            )
            sesion.add(cuenta)
            await sesion.flush()
            sesion.add(
                Membership(
                    business_id=negocio.id,
                    user_id=cuenta.id,
                    role="profesional",
                    status="activa",
                    accepted_at=datetime.now(UTC),
                )
            )

        profesional = StaffProfile(
            business_id=negocio.id,
            display_name=persona["nombre"],
            user_id=cuenta.id if cuenta else None,
            position=posicion,
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
        await _resenas_de_ejemplo(sesion, negocio, equipo, fichas, definicion["categoria"])


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

    # **Dos semanas hacia atrás y una hacia delante.** El pasado no es decoración: sin citas
    # completadas no hay historial en la ficha del cliente, no hay tasa de completado que
    # alimente el ranking y —sobre todo— **no se puede dejar ni una reseña**, porque REV-1 las
    # ata a una cita atendida. `_estado_segun_fecha` ya sabía repartir desenlaces; lo que le
    # faltaba era pasado sobre el que repartirlos.
    for dia_offset in range(-14, 7):
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


#: Qué escribe cada clienta, **por tipo de salón**. Los textos van por categoría porque una
#: reseña que dice «me dejó el corte impecable» en un spa de masajes se nota a la primera, y una
#: demo que se nota deja de servir para enseñar nada. `{quien}` se sustituye por el nombre de la
#: profesional que atendió esa cita de verdad, no por un nombre inventado.
RESENAS_POR_CATEGORIA: dict[str, list[tuple[int, str]]] = {
    "barberia": [
        (5, "{quien} me dejó el corte impecable y salí en cuarenta minutos. Vuelvo fijo."),
        (5, "Puntualísimos. Me atendieron a la hora exacta que reservé, cosa rara por aquí."),
        (4, "Buen corte, aunque el local es pequeño y hay que esperar de pie."),
        (5, "Le enseñé una foto a {quien} y salió igualito. Recomendadísimo."),
        (3, "El corte bien, pero me atendieron veinte minutos tarde."),
        (4, "Buen precio para la zona y trato amable. Repetiré."),
    ],
    "peluqueria": [
        (5, "El balayage me quedó justo del tono que quería. {quien} tiene muy buena mano."),
        (5, "Me explicaron qué le iba a hacer al pelo antes de tocarlo. Se agradece."),
        (4, "Bien el color, aunque tardó más de lo que decía la reserva."),
        (5, "Salí con el pelo como no lo tenía hace años. Ya reservé la próxima."),
        (3, "El corte correcto, pero el secado lo hicieron con prisa."),
        (4, "Trato buenísimo y precio justo para Ciudad de Panamá."),
    ],
    "unas": [
        (5, "Me duraron tres semanas enteras sin saltarse ni una. {quien} es una crack."),
        (5, "Súper limpio todo, y el diseño quedó igual a la foto que llevé."),
        (4, "Bonitas, pero se me astilló una a los diez días."),
        (5, "Es el único sitio donde no me han dejado la cutícula destrozada."),
        (3, "El trabajo bien; el problema fue la espera, casi media hora."),
        (4, "Buen precio y muy cómodo el sitio. Volveré."),
    ],
    "pestanas-cejas": [
        (5, "Me dejó las cejas simétricas por primera vez en mi vida. Gracias, {quien}."),
        (5, "Las pestañas duraron mes y medio y no se me cayó ni una tanda."),
        (4, "Buen resultado, aunque el diseño quedó un pelín más marcado de lo que pedí."),
        (5, "Me asesoró con la forma en vez de hacerme lo de siempre. Eso vale mucho."),
        (3, "Bien, pero la sesión se alargó y llegué tarde a lo mío."),
        (4, "Sitio limpio y precio razonable para la zona."),
    ],
    "spa-masajes": [
        (5, "{quien} encontró justo el nudo del hombro sin que se lo dijera. Salí de otra manera."),
        (5, "El sitio es tranquilísimo y no te meten prisa al terminar."),
        (4, "Muy buen masaje, aunque la sala estaba un poco fría."),
        (5, "Me reservé la hora un martes y me atendieron puntuales. Repetiré."),
        (3, "Bien el masaje, pero la música se oía desde la recepción."),
        (4, "Buena relación calidad-precio. Vuelvo el mes que viene."),
    ],
    "maquillaje": [
        (5, "Me maquilló {quien} para una boda y aguantó doce horas sin retocar."),
        (5, "Escuchó lo que quería en vez de hacerme lo que le gusta a ella. Eso se nota."),
        (4, "Muy bien el resultado, aunque hubo que ir con bastante antelación."),
        (5, "Salí en las fotos como quería salir. No se puede pedir más."),
        (3, "Correcto, pero para el precio esperaba algo más de asesoría."),
        (4, "Trato encantador y sitio muy cómodo."),
    ],
    "estetica": [
        (5, "La limpieza facial me dejó la piel como no la tenía hace meses."),
        (5, "{quien} me explicó qué me iba a hacer y por qué. Nada de vender por vender."),
        (4, "Buen tratamiento, aunque la cabina es pequeña."),
        (5, "Se nota que saben: me recomendaron esperar en vez de venderme una sesión más."),
        (3, "El resultado bien, pero me atendieron con retraso."),
        (4, "Precio honesto y trato cercano. Repetiré."),
    ],
}

#: Para un salón cuya categoría no está arriba. Sirve para cualquier oficio.
RESENAS_GENERICAS = [
    (5, "Puntualísimos y muy buen trato. {quien} sabe lo que hace."),
    (5, "Reservé desde el móvil y me atendieron a la hora exacta. Sin llamadas."),
    (4, "Muy buen resultado, aunque el sitio es pequeño."),
    (5, "Ya es el tercer mes que vuelvo. Eso lo dice todo."),
    (3, "Bien, pero me atendieron con veinte minutos de retraso."),
    (4, "Buen precio para la zona y trato amable."),
]

#: Lo que responde el salón. Una por reseña, que es lo que permite REV-3.
RESPUESTAS = [
    "¡Gracias por escribirnos! Te esperamos el próximo mes.",
    "Mil gracias. Nos alegra que hayas quedado contenta.",
    "Gracias por el comentario. Tomamos nota de lo de la espera y lo estamos ajustando.",
]


async def _resenas_de_ejemplo(
    sesion: AsyncSession,
    negocio: Business,
    equipo: list[StaffProfile],
    fichas: list[BusinessClient],
    categoria: str,
) -> None:
    """Reseñas sobre citas **completadas**, con su respuesta y el agregado ya calculado.

    Se atan a citas de verdad y no se inventan: si se insertaran sueltas, el seed enseñaría un
    estado que la API nunca podría producir —REV-1 exige cita atendida— y la demo mentiría
    sobre lo que el producto hace.

    El agregado se recalcula con el mismo servicio que usa la API, así que el número que se ve
    en el marketplace sale de la misma fórmula bayesiana y no de una copia.
    """
    completadas = (
        (
            await sesion.execute(
                select(Booking)
                .where(Booking.business_id == negocio.id, Booking.status == "completada")
                .order_by(Booking.starts_at)
            )
        )
        .scalars()
        .all()
    )
    if not completadas:
        return

    # Ni todas las citas llevan reseña ni ninguna: una de cada tres es lo que se ve en un
    # marketplace real, y es lo que hace que el rating bayesiano tenga sentido.
    textos = RESENAS_POR_CATEGORIA.get(categoria, RESENAS_GENERICAS)
    for indice, reserva in enumerate(completadas[::3]):
        nota, plantilla = textos[indice % len(textos)]
        # Quien atendió esa cita, por su nombre. Antes salía «Kevin» en todos los salones,
        # incluidos los spas cuyo equipo son Ivonne y Rita: se ve a la primera que es de mentira.
        quien = next((p.display_name for p in equipo if p.id == reserva.staff_id), "el equipo")
        texto = plantilla.format(quien=quien.split()[0])
        ficha = next((f for f in fichas if f.id == reserva.business_client_id), None)
        resena = Review(
            business_id=negocio.id,
            booking_id=reserva.id,
            author_user_id=ficha.user_id if ficha else None,
            staff_id=reserva.staff_id,
            rating=nota,
            body=texto,
            status="publicada",
            published_at=reserva.ends_at,
        )
        sesion.add(resena)
        await sesion.flush()

        # El salón responde a algunas, no a todas: responder a todas es lo que hace un bot.
        if indice % 2 == 0:
            sesion.add(
                ReviewReply(
                    business_id=negocio.id,
                    review_id=resena.id,
                    author_user_id=negocio.owner_user_id,
                    body=RESPUESTAS[indice % len(RESPUESTAS)],
                )
            )

    await sesion.flush()
    await servicio_resenas.recalcular_agregado(sesion, negocio.id)


async def _contadores_de_los_clientes(sesion: AsyncSession) -> None:
    """Rellena de una vez los contadores desnormalizados de `business_clients`.

    Están desnormalizados a propósito —la agenda los pinta en cada fila y contar reservas por
    cliente en cada carga es la consulta que convierte 3G en inutilizable— y por eso el seed
    tiene que dejarlos coherentes: si `last_booking_at` viniera vacío, la lista de clientes
    saldría ordenada al azar y sin decir cuándo vino cada persona.

    Un solo `UPDATE` derivado de `bookings`, que siempre dice la verdad, en vez de ir llevando
    la cuenta mientras se generan las citas, que es como se desincroniza.
    """
    await sesion.execute(
        text(
            """
            UPDATE business_clients c SET
              completed_count = t.completadas,
              no_show_count   = t.no_shows,
              cancel_count    = t.canceladas,
              first_seen_at   = t.primera,
              last_booking_at = t.ultima
            FROM (
              SELECT business_client_id,
                     count(*) FILTER (WHERE status = 'completada')         AS completadas,
                     count(*) FILTER (WHERE status = 'no_show')            AS no_shows,
                     count(*) FILTER (WHERE status LIKE 'cancelada%')      AS canceladas,
                     min(starts_at)                                        AS primera,
                     max(starts_at)                                        AS ultima
                FROM bookings GROUP BY business_client_id
            ) t
            WHERE t.business_client_id = c.id
            """
        )
    )


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
