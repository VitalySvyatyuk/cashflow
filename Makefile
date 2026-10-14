.PHONY: env up down logs psql venv test test-all lint fmt typecheck test-frontend migrate makemigrations seed superuser shell

VENV := .venv/bin
MANAGE := docker compose exec backend python manage.py

env:
	test -f .env || cp .env.example .env

up: env
	docker compose up -d --build --wait

down:
	docker compose down

logs:
	docker compose logs -f

psql:
	docker compose exec postgres psql -U cashflow cashflow

# Локальное окружение для тестов, линтера и IDE
venv:
	python3 -m venv .venv
	$(VENV)/pip install -r backend/requirements-dev.txt

test:
	cd backend && ../$(VENV)/pytest

test-all:
	cd backend && ../$(VENV)/pytest -m ""

lint:
	cd backend && ../$(VENV)/ruff check . && ../$(VENV)/ruff format --check .

fmt:
	cd backend && ../$(VENV)/ruff check --fix . && ../$(VENV)/ruff format .

typecheck:
	docker compose exec frontend npm run typecheck

test-frontend:
	docker compose exec frontend npm test

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

seed:
	$(MANAGE) seed --reset

superuser:
	$(MANAGE) createsuperuser

shell:
	$(MANAGE) shell
