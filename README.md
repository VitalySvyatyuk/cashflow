# Cashflow

Онлайн-версия настольной игры «Денежный поток»: ведущий + до 6 игроков.
Голосовая связь — во внешнем сервисе. План разработки — в [PLAN.md](PLAN.md).

## Структура

```
backend/             Django + Channels (появится на шаге 2)
frontend/            React + TypeScript + Vite (появится на шаге 7)
docker-compose.yml   PostgreSQL 16 и Redis 7 для разработки
.env.example         переменные окружения
```

## Запуск инфраструктуры

Нужен Docker (Docker Desktop или OrbStack).

```sh
make up      # создаёт .env из .env.example и поднимает postgres + redis
make psql    # консоль БД
make down    # остановить
```

Порты открыты только на `127.0.0.1`: Postgres — 5433 (5432 часто занят локальным Postgres), Redis — 6379.

### Если Docker Hub недоступен

Добавьте зеркало в Docker Desktop → Settings → Docker Engine:

```json
"registry-mirrors": ["https://mirror.gcr.io"]
```

и нажмите «Apply & restart».
