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

| `{"type": "action", "kind", "params"}` | → сервер | действие (см. ниже); ведущий может добавить `params.player_id` |
| `{"type": "decide", "id", "approve", "params", "comment"}` | → сервер | ведущий решает заявку (может исправить параметры) |
| `{"type": "cancel", "id"}` | → сервер | игрок отзывает свою заявку |
| `{"type": "error", "message"}` | → клиент | ошибка — только отправителю |

Коды закрытия: `4404` — игра не найдена, `4403` — нет доступа, `4410` — игрока убрали из лобби.

## Действия (`game/engine.py`)

Политики: **сам** — выполняется сразу; **ведущий** — становится заявкой; **только ведущий**.
Действие ведущего от имени игрока выполняется сразу.

| `kind` | Политика | Когда | Параметры |
|---|---|---|---|
| `roll` | сам | фаза `roll`, свой ход | `dice` — при благотворительности можно больше кубиков |
| `choose_deal` | сам | `choose_deal` | `size`: `small` / `big` |
| `buy` | ведущий | `card` (сделка) | `quantity` для акций |
| `sell` | ведущий | пока карточка на столе, любой игрок | `asset_id`, `quantity` |
| `pass` | сам | отказ от сделки / благотворительности / бизнеса | — |
| `charity` | ведущий | `charity` | — |
| `buy_business`, `buy_dream` | ведущий | скоростная дорожка | — |
| `take_loan` | ведущий | в любой момент | `amount` кратно 1000 |
| `repay_loan` | ведущий | в любой момент | `liability_id`, `amount` |
| `go_fast_track` | ведущий | `end_turn`, пассивный доход > расходов | — |
| `end_turn` | сам | `end_turn` | — |
| `pause`, `resume`, `next_turn`, `undo` | только ведущий | всегда | — |
| `adjust_cash` | только ведущий | всегда | `player_id`, `amount` (±), `reason` |

Если наличных не хватает на обязательный платёж, автоматически берётся
банковский кредит (кратно $1000, 10% в месяц). `undo` откатывает последнее
действие по снимку состояния; паузу не снимает, победу — отменяет.

Клетки поля: `GET /api/board/`.

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
