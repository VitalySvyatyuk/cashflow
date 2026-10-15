# Cashflow

Онлайн-версия настольной игры «Денежный поток»: ведущий + до 6 игроков.
Голосовая связь — во внешнем сервисе. План разработки — в [PLAN.md](PLAN.md).

## Структура

```
backend/             Django 5.2 + Channels + DRF
frontend/            React 19 + TypeScript + Vite (Node 22 в Docker)
docker-compose.yml   PostgreSQL 16 и Redis 7 для разработки
.env.example         переменные окружения
```

## Запуск

Нужен Docker Desktop.

```sh
make up          # создаёт .env из .env.example, поднимает frontend + backend + postgres + redis
make superuser   # создать ведущего (суперпользователя)
make seed        # добавить тестовые профессии, карточки и клетки (ничего не удаляет)
make logs        # логи
make down        # остановить
```

| Адрес | Что |
|---|---|
| http://localhost:5173/ | вход игрока: код игры + имя |
| http://localhost:5173/host | ведущий: вход, создание игры, список игр |
| http://localhost:5173/admin/ | админка Django |
| http://localhost:5173/api/health/ | `{"db": "ok", "redis": "ok"}` |

Vite проксирует `/api`, `/ws`, `/admin` на бэкенд — браузер работает с одним адресом.
Код `backend/` и `frontend/` смонтирован в контейнеры, изменения подхватываются сразу.

Порты открыты только на `127.0.0.1`: frontend — 5173, backend — 8000, Postgres — 5433
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
| `{"type": "presence", "players", "host"}` | → клиент | кто сейчас на связи (также в `hello.presence`) |

Коды закрытия: `4404` — игра не найдена, `4403` — нет доступа, `4410` — игрока убрали из лобби.

## Действия (`game/engine.py`)

Политики: **сам** — выполняется сразу; **ведущий** — становится заявкой; **только ведущий**.
Действие ведущего от имени игрока выполняется сразу.

| `kind` | Политика | Когда | Параметры |
|---|---|---|---|
| `roll` | сам | фаза `roll`, свой ход | `dice` — 1, 2 или 3 (по умолчанию 1 на крысиных бегах, 2 на скоростной) |
| `choose_deal` | сам | `choose_deal` | `size`: `small` / `big` |
| `buy` | ведущий | `card` (сделка) | `quantity` для акций |
| `sell` | ведущий | пока карточка на столе, любой игрок | `asset_id`, `quantity` |
| `pay_card` | сам | `pay` — открыта карточка трат; не хватает наличных — кредит | — |
| `pass` | сам | отказ от сделки / благотворительности / бизнеса | — |
| `charity` | ведущий | `charity` | — |
| `buy_business`, `buy_dream` | ведущий | скоростная дорожка | — |
| `take_loan` | ведущий | в любой момент | `amount` кратно 10 000 |
| `repay_loan` | ведущий | в любой момент | `liability_id`, `amount` |
| `go_fast_track` | только ведущий | пассивный доход > расходов, не посреди хода игрока | `player_id` |
| `end_turn` | сам | `end_turn` | — |
| `pause`, `resume`, `next_turn`, `undo` | только ведущий | всегда | — |
| `finish_game` | только ведущий | всегда, в том числе в лобби | — |
| `adjust_cash` | только ведущий | всегда | `player_id`, `amount` (±), `reason` |

Если наличных не хватает на обязательный платёж, автоматически берётся
банковский кредит (кратно 10 000 ₽, 10% в месяц). `undo` откатывает последнее
действие по снимку состояния; паузу не снимает, победу и завершение игры — отменяет.

Игровая валюта — всегда рубль. Профессии взяты из `docs/Карточки_профессий_01-12_рубли.md`,
правила работы с ними — в `docs/Инструкция_программисту_карточки_профессий.docx`.
Выход в большой круг: игрок говорит ведущему «Я хочу выйти в большой круг», программа
проверяет условие, а переводит ведущий кнопкой «Перевести в большой круг».

Клетки поля: `GET /api/board/`.

## Тесты и линтер

Тесты запускаются локально, в `.venv`, против Postgres и Redis из Docker:

```sh
make venv    # один раз
make test        # быстрые тесты (~1 мин)
make test-all    # плюс полные партии ботом (~2,5 мин)
make lint    # make fmt — автоисправление
make typecheck       # проверка типов фронтенда (в контейнере)
make test-frontend   # тесты фронтенда (Vitest, в контейнере)
```

Прочее: `make migrate`, `make makemigrations`, `make shell`, `make psql`.

### Если Docker Hub недоступен

Добавьте зеркало в Docker Desktop → Settings → Docker Engine:

```json
"registry-mirrors": ["https://mirror.gcr.io"]
```

и нажмите «Apply & restart».

## Сервер

Игра: https://emelyanova-play.online — Caddy (HTTPS, фронтенд) + Django/Daphne + Postgres + Redis
в Docker на Ubuntu, код в `/opt/cashflow/app`, пароли в `/opt/cashflow/.env.prod` (только на сервере).
Вход на сервер — только по SSH-ключу.

```sh
make deploy          # выложить последний коммит (git archive → сборка на сервере)
make prod-superuser  # создать ведущего на сервере
make prod-logs       # логи
make prod-backup     # резервная копия сейчас (автоматически — каждый день в 04:15 UTC, хранятся 7 дней)
```

Копии лежат в `/opt/cashflow/backups/`: `db_*.sql.gz` (база) и `media_*.tar.gz` (картинки).
