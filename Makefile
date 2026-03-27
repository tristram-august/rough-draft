# Makefile (repo root)
# Rough Draft dev commands (Docker-first)

SHELL := /bin/sh

COMPOSE ?= docker compose

API_SERVICE ?= api
DB_SERVICE ?= db

CSV_DIR ?= ./data/drafts
CLIENT_ID ?= morning-coffee-12345678

.PHONY: help up build down restart ps logs logs-db logs-api migrate ingest psql reset-db smoke health draft vote

help:
	@echo ""
	@echo "Rough Draft - Make targets"
	@echo ""
	@echo "Core:"
	@echo "  make up            Start db+api"
	@echo "  make build         Build images (no cache optional: make build NO_CACHE=1)"
	@echo "  make migrate       Apply alembic migrations"
	@echo "  make ingest        Ingest CSVs from CSV_DIR=$(CSV_DIR)"
	@echo ""
	@echo "Dev tools:"
	@echo "  make logs          Tail logs (db+api)"
	@echo "  make logs-db       Tail db logs"
	@echo "  make logs-api      Tail api logs"
	@echo "  make psql          Open psql in db container"
	@echo ""
	@echo "Reset:"
	@echo "  make down          Stop containers (keeps volume)"
	@echo "  make reset-db      Stop + DELETE volumes + recreate + migrate + ingest"
	@echo ""
	@echo "Smoke tests:"
	@echo "  make health        GET /api/health"
	@echo "  make draft         Sample draft query (YEAR=2000 ROUND=1)"
	@echo "  make vote          Sample vote (YEAR=2000 OVERALL=1 VALUE=success)"
	@echo "  make smoke         health + draft + vote"
	@echo ""

up:
	$(COMPOSE) up -d $(DB_SERVICE) $(API_SERVICE)

build:
ifeq ($(NO_CACHE),1)
	$(COMPOSE) build --no-cache $(API_SERVICE)
else
	$(COMPOSE) build $(API_SERVICE)
endif

down:
	$(COMPOSE) down

restart: down up

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

logs-db:
	$(COMPOSE) logs -f $(DB_SERVICE)

logs-api:
	$(COMPOSE) logs -f $(API_SERVICE)

migrate:
	$(COMPOSE) exec $(API_SERVICE) alembic upgrade head

ingest:
	$(COMPOSE) exec $(API_SERVICE) python scripts/ingest_csvs.py --csv-dir $(CSV_DIR)

psql:
	$(COMPOSE) exec $(DB_SERVICE) psql -U draftboard -d draftboard

reset-db:
	$(COMPOSE) down -v
	$(COMPOSE) up -d $(DB_SERVICE) $(API_SERVICE)
	$(COMPOSE) exec $(API_SERVICE) alembic upgrade head
	$(COMPOSE) exec $(API_SERVICE) python scripts/ingest_csvs.py --csv-dir $(CSV_DIR)

health:
	curl -fsS http://localhost:8000/api/health && echo ""

draft:
	curl -fsS "http://localhost:8000/api/draft?year=$(YEAR)&round=$(ROUND)" | head -c 2000 && echo ""
YEAR ?= 2000
ROUND ?= 1

vote:
	curl -fsS \
	  -H "X-Client-Id: $(CLIENT_ID)" \
	  -H "Content-Type: application/json" \
	  -X POST "http://localhost:8000/api/pick/$(YEAR)/$(OVERALL)/vote" \
	  -d '{"value":"$(VALUE)"}' && echo ""
OVERALL ?= 1
VALUE ?= success

smoke: up migrate health draft vote