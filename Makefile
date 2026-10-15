.PHONY: deploy prod-superuser prod-logs prod-backup prod-shell env up down logs psql venv test test-all lint fmt typecheck test-frontend migrate makemigrations seed seed-reset superuser shell

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

# Добавляет недостающие тестовые данные, ничего не удаляя.
seed:
	$(MANAGE) seed

# ОСТОРОЖНО: удаляет ВСЕ карточки и клетки (в том числе введённые вручную) и создаёт тестовые.
seed-reset:
	@read -p "Удалить все карточки и клетки поля? Введите yes: " ans && [ "$$ans" = yes ]
	$(MANAGE) seed --reset

superuser:
	$(MANAGE) createsuperuser

shell:
	$(MANAGE) shell

# --- Сервер (emelyanova-play.online) ---
SERVER := root@95.163.229.64
PROD := cd /opt/cashflow/app && docker compose -p cashflow -f docker-compose.prod.yml --env-file ../.env.prod

deploy:  ## выложить последний коммит
	./deploy/deploy.sh $(SERVER)

prod-superuser:  ## создать ведущего на сервере (пароль вводите сами)
	ssh -t $(SERVER) '$(PROD) exec backend python manage.py createsuperuser'

prod-logs:
	ssh $(SERVER) '$(PROD) logs -f --tail 100'

prod-backup:  ## резервная копия прямо сейчас
	ssh $(SERVER) /usr/local/bin/cashflow-backup

prod-shell:
	ssh -t $(SERVER) '$(PROD) exec backend python manage.py shell'
