# M2G Agenda — comandos del entorno local.
# El despliegue no es de este equipo: aquí solo hay desarrollo y validación en local.

# `--env-file .env` es lo que hace que las variables del repositorio lleguen también a la
# **plantilla** del compose (`${NOMBRE_COMERCIAL}`). Sin esto, compose solo mira el `.env`
# de al lado del archivo —`infra/local/.env`, que no existe— y sustituye en silencio por el
# valor por defecto: se cambia el `.env` del repositorio y no pasa nada.
COMPOSE := docker compose --env-file .env -f infra/local/docker-compose.yml
API     := $(COMPOSE) exec -T api

.DEFAULT_GOAL := ayuda

.PHONY: ayuda arriba abajo logs migrar migracion semilla pruebas barrer variables lint recargar contrato consola reiniciar limpiar

ayuda:  ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

arriba:  ## Levanta el stack, aplica migraciones y carga el seed
	@test -f .env || (echo "No hay .env. Copia .env.example a .env y vuelve a intentarlo."; exit 1)
	$(COMPOSE) up -d --build
	$(MAKE) migrar
	$(MAKE) semilla
	@echo ""
	@echo "  API        http://localhost:8000/docs"
	@echo "  Base       postgresql://agenda_app@localhost:5433/agenda"
	@echo ""

abajo:  ## Para el stack y libera los puertos
	$(COMPOSE) down

logs:  ## Sigue los registros de la API y del worker
	$(COMPOSE) logs -f api worker

migrar:  ## Aplica las migraciones pendientes
	$(API) alembic upgrade head

migracion:  ## Crea una migración nueva: make migracion m="lo que cambia"
	$(API) alembic revision --autogenerate -m "$(m)"

semilla:  ## Recarga los datos de ejemplo sobre una base limpia
	$(API) python -m agenda.semilla

pruebas:  ## Ejecuta todas las pruebas contra un Postgres real
	# Las pruebas usan su propia base (agenda_pruebas): dejan filas escritas a propósito
	# -una carrera entre dos transacciones no se puede simular deshaciendo al final- y no
	# pueden mezclarlas con los datos de ejemplo del desarrollo.
	$(COMPOSE) up -d db redis
	$(COMPOSE) run --rm api pytest -q

barrer:  ## Barre las 20 pantallas a 390 px: que carguen, no revienten y no desborden
	node scripts/barrer-pantallas.mjs

variables:  ## Comprueba que toda variable de configuración está documentada en los dos sitios
	python3 scripts/comprobar-variables.py

lint:  ## Formatea y revisa el código
	$(COMPOSE) run --rm api ruff format .
	$(COMPOSE) run --rm api ruff check --fix .

contrato:  ## Regenera el OpenAPI y los tipos de packages/api-types
	$(API) python -m agenda.contrato > packages/api-types/openapi.json
	pnpm --filter @agenda/api-types generar

consola:  ## Abre una consola de psql en la base local
	$(COMPOSE) exec db psql -U agenda_owner -d agenda

recargar:  ## Aplica cambios del .env a los contenedores (restart NO los relee)
	# `docker compose restart` reinicia el proceso pero **conserva el entorno con el que se creó
	# el contenedor**: un cambio en el .env no llega, y el síntoma es que la pantalla carga y no
	# sale ni una petición. Hay que recrear.
	# La web también: desde que el nombre comercial sale del entorno (`NOMBRE_COMERCIAL`),
	# dejarla fuera hacía que se cambiara el `.env` y la cabecera siguiera diciendo lo de antes.
	$(COMPOSE) up -d --force-recreate api worker planificador web

reiniciar:  ## Recrea la base desde cero: borra los datos, migra y siembra
	$(COMPOSE) down -v
	$(MAKE) arriba

limpiar:  ## Borra volúmenes, imágenes construidas y cachés
	$(COMPOSE) down -v --rmi local
