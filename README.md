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

## API лобби

| Метод | Путь | Кто | Что делает |
|---|---|---|---|
| GET | `/api/auth/session/` | все | текущий пользователь + cookie `csrftoken` |
| POST | `/api/auth/login/` | все | вход ведущего `{username, password}` |
| POST | `/api/auth/logout/` | все | выход |
| GET / POST | `/api/games/` | ведущий | свои игры / создать `{max_players}` |
| GET | `/api/games/<код>/` | все | игра и список игроков |
| POST | `/api/games/<код>/join/` | все | войти `{name}` → `token` |
| GET / DELETE | `/api/games/<код>/me/` | игрок | о себе / выйти из лобби |
| DELETE | `/api/games/<код>/players/<id>/` | ведущий | убрать игрока из лобби |
| POST | `/api/games/<код>/start/` | ведущий | старт: профессии, колоды, первый ход |

Код игры — 4 цифры. Ведущий авторизуется сессией (POST-запросы — с заголовком
`X-CSRFToken`), игрок — заголовком `X-Player-Token: <token>`.

## WebSocket

`ws://localhost:8000/ws/games/<код>/` — ведущий (по сессии) или `?token=<token>` — игрок.

| Сообщение | Направление | Что это |
|---|---|---|
| `{"type": "hello", "role", "player_id", "state"}` | → клиент | сразу после подключения |
| `{"type": "event", "event", "state"}` | → клиент | любое событие игры + новое состояние |
| `ping` / `pong` | ↔ | проверка связи |
| `{"type": "sync"}` → `{"type": "state", "state"}` | ↔ | запросить состояние заново |

Коды закрытия: `4404` — игра не найдена, `4403` — нет доступа, `4410` — игрока убрали из лобби.

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
