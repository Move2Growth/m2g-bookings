# M2G Agenda — comandos del entorno local.
# El despliegue no es de este equipo: aquí solo hay desarrollo y validación en local.

COMPOSE := docker compose -f infra/local/docker-compose.yml
API     := $(COMPOSE) exec -T api

.DEFAULT_GOAL := ayuda

.PHONY: ayuda arriba abajo logs migrar migracion semilla pruebas lint contrato consola reiniciar limpiar

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

lint:  ## Formatea y revisa el código
	$(COMPOSE) run --rm api ruff format .
	$(COMPOSE) run --rm api ruff check --fix .

contrato:  ## Regenera el OpenAPI y los tipos de packages/api-types
	$(API) python -m agenda.contrato > packages/api-types/openapi.json
	pnpm --filter @agenda/api-types generar

consola:  ## Abre una consola de psql en la base local
	$(COMPOSE) exec db psql -U agenda_owner -d agenda

reiniciar:  ## Recrea la base desde cero: borra los datos, migra y siembra
	$(COMPOSE) down -v
	$(MAKE) arriba

limpiar:  ## Borra volúmenes, imágenes construidas y cachés
	$(COMPOSE) down -v --rmi local
