# Imagen de desarrollo de la API y del worker: los dos usan esta misma imagen y se
# distinguen solo por el comando que arrancan.
#
# El despliegue no es de este equipo (ver PROMPT-CONSTRUCTOR.md): esta imagen está pensada
# para el entorno local. Quien la lleve a producción querrá una etapa final sin las
# dependencias de desarrollo y sin el montaje del código en caliente.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Las pruebas y los trabajos razonan en UTC; el huso local del contenedor no debe
    # esconder un error de conversión (ADR-0003).
    TZ=UTC \
    PATH="/opt/venv/bin:$PATH"

# libpq para psycopg, y las utilidades mínimas para que el healthcheck y los scripts funcionen.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml ./
COPY agenda ./agenda
RUN uv venv /opt/venv \
    && uv pip install --python /opt/venv/bin/python -e ".[dev]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "agenda.main:app", "--host", "0.0.0.0", "--port", "8000"]
