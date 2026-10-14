.PHONY: env up down logs psql

env:
	test -f .env || cp .env.example .env

up: env
	docker compose up -d --wait

down:
	docker compose down

logs:
	docker compose logs -f

psql:
	docker compose exec postgres psql -U cashflow cashflow
