DATABASE_URL ?= postgresql://iris_user:iris_password@localhost:5432/iris_pilot

.PHONY: help up down wait migrate seed test verify reset

help:
	@echo "Available commands:"
	@echo "  make up       - Start PostGIS container"
	@echo "  make down     - Stop and wipe PostGIS container"
	@echo "  make migrate  - Run SQL migrations on DB"
	@echo "  make seed     - Ingest deterministic fixtures"
	@echo "  make test     - Run automated test suite"
	@echo "  make verify   - Run pilot spatial prospecting queries"
	@echo "  make reset    - Full zero-touch rebuild & verification"

up:
	docker compose up -d
	@$(MAKE) wait

down:
	docker compose down -v

wait:
	@echo "Waiting for PostgreSQL + PostGIS to become ready..."
	@docker compose exec -T db sh -c 'until pg_isready -U iris_user -d iris_pilot; do sleep 1; done'
	@echo "Database ready."

migrate:
	python3 -m src.migrate

seed:
	python3 -m src.loader

test:
	pytest -v tests/

verify:
	python3 -m src.queries

reset: down up migrate seed verify test