# Cashflow

Онлайн-версия настольной игры «Денежный поток»: ведущий + до 6 игроков.
Голосовая связь — во внешнем сервисе. План разработки — в [PLAN.md](PLAN.md).

## Структура

```
backend/             Django 5.2 + Channels + DRF
frontend/            React + TypeScript + Vite (появится на шаге 7)
docker-compose.yml   PostgreSQL 16 и Redis 7 для разработки
.env.example         переменные окружения
```

## Запуск

Нужен Docker Desktop.

```sh
make up          # создаёт .env из .env.example, собирает и поднимает backend + postgres + redis
make superuser   # создать ведущего (суперпользователя)
make seed        # профессии, карточки и клетки поля (временные данные)
make logs        # логи
make down        # остановить
```

- Проверка здоровья: http://localhost:8000/api/health/ → `{"db": "ok", "redis": "ok"}`
- Админка: http://localhost:8000/admin/
- Код `backend/` смонтирован в контейнер, сервер перезапускается при изменениях.

Порты открыты только на `127.0.0.1`: backend — 8000, Postgres — 5433
(5432 часто занят локальным Postgres), Redis — 6379.

## Тесты и линтер

Тесты запускаются локально, в `.venv`, против Postgres и Redis из Docker:

```sh
make venv    # один раз
make test
make lint    # make fmt — автоисправление
```

Прочее: `make migrate`, `make makemigrations`, `make shell`, `make psql`.

### Если Docker Hub недоступен

Добавьте зеркало в Docker Desktop → Settings → Docker Engine:

```json
"registry-mirrors": ["https://mirror.gcr.io"]
```

и нажмите «Apply & restart».
